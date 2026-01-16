"""Brand Marketing Advisor agent - single agent with skills architecture.
This module implements a single intelligent agent that uses skills to handle
all brand-related tasks. It replaces the previous multi-agent orchestration
pattern with a simpler, more maintainable architecture.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator

import openai
from agents import Agent, MaxTurnsExceeded, Runner

from sip_studio.advisor.context_budget import ContextBudgetManager
from sip_studio.advisor.history_manager import ConversationHistoryManager
from sip_studio.advisor.hooks import AdvisorHooks, AdvisorProgress, ProgressCallback
from sip_studio.advisor.prompt_builder import build_system_prompt as _build_system_prompt
from sip_studio.advisor.session_context_cache import SessionContextCache
from sip_studio.advisor.session_history_manager import (
    MAX_CONTEXT_LIMIT,
    SessionHistoryManager,
    _call_llm_with_retry,
    cancel_compaction,
)
from sip_studio.advisor.session_manager import Message, SessionManager, SessionSettings
from sip_studio.advisor.skills.registry import get_skills_registry
from sip_studio.advisor.tools import (
    ADVISOR_TOOLS,
    reset_workflow_state,
    set_active_aspect_ratio,
    set_tool_progress_callback,
)
from sip_studio.advisor.tools.context_tools import set_context_cache
from sip_studio.brands.context import HierarchicalContextBuilder
from sip_studio.brands.storage import get_active_brand, get_brand_dir, set_active_brand
from sip_studio.config.constants import Limits
from sip_studio.config.logging import get_logger

logger = get_logger(__name__)


async def _generate_session_title(first_user_message: str) -> str:
    """Generate a session title from the first user message.
    Args:
        first_user_message: The first message in the conversation.
    Returns:
        A 3-5 word title for the session.
    """
    prompt = f"""Generate a 3-5 word title for a conversation starting with:
"{first_user_message[:200]}"

Title (no quotes, no punctuation at end):"""
    result = await _call_llm_with_retry(prompt, max_tokens=20)
    if result:
        title = result.strip().strip("\"'").strip(".")[:50]
        return title if title else "New conversation"
    return "New conversation"


@dataclass
class ChatContext:
    """Prepared context for a chat turn."""

    full_prompt: str
    hooks: AdvisorHooks
    matched_skills: list[tuple[str, str]] = field(default_factory=list)
    raw_user_message: str = ""
    budget_trimmed: bool = False
    budget_warning: str | None = None
    is_over_budget: bool = False
    system_prompt_trimmed: bool = False


# Re-export for backward compatibility
__all__ = ["BrandAdvisor", "AdvisorProgress", "ProgressCallback", "AdvisorHooks"]


# =============================================================================
# Brand Advisor Agent
# =============================================================================


class BrandAdvisor:
    """Brand Marketing Advisor agent.

    A single intelligent agent that uses skills to handle all brand-related tasks.
    Uses GPT-5.1 with 5 universal tools and dynamically loaded skills.

    Now supports session-aware mode (Stage 7) with:
    - SessionManager for CRUD on sessions
    - SessionHistoryManager for per-session history with auto-compaction
    - Lean context loading with tool pointers (~300 tokens vs ~500+)
    - Hard context limit guardrail with emergency truncation

    Example:
        ```python
        advisor = BrandAdvisor(brand_slug="summit-coffee", session_aware=True)
        response = await advisor.chat("Create a playful mascot")
        print(response)
        ```
    """

    def __init__(
        self,
        brand_slug: str | None = None,
        progress_callback: ProgressCallback | None = None,
        session_aware: bool = False,
        session_id: str | None = None,
    ):
        """Initialize the advisor.

        Args:
            brand_slug: Optional brand slug to load context for.
                If not provided, uses the active brand.
            progress_callback: Optional callback for progress updates.
            session_aware: If True, use new session-aware architecture (Stage 7).
            session_id: Optional specific session to load. If None and session_aware=True,
                uses active session or creates new one.
        """
        # Resolve brand slug
        if brand_slug is None:
            brand_slug = get_active_brand()
        self.brand_slug = brand_slug
        self.progress_callback = progress_callback
        self._session_aware = session_aware
        # Session-aware components (Stage 7)
        self._session_manager: SessionManager | None = None
        self._session_history: SessionHistoryManager | None = None
        self._context_cache: SessionContextCache | None = None
        self._current_session_id: str | None = None
        if session_aware and brand_slug:
            self._init_session_aware(brand_slug, session_id)
        # Build system prompt (with lean context if session-aware)
        summary = None
        if self._session_history:
            summary = self._session_history.get_summary()
        system_prompt = _build_system_prompt(
            brand_slug,
            use_lean_context=session_aware,
            conversation_summary=summary,
        )
        # Create the agent
        self._agent = Agent(
            name="Brand Marketing Advisor",
            model="gpt-5.1",  # 272K context, adaptive reasoning
            instructions=system_prompt,
            tools=ADVISOR_TOOLS,
        )
        # Get brand directory for legacy history persistence
        brand_dir = get_brand_dir(brand_slug) if brand_slug else None
        # Track conversation history (legacy mode)
        self._history_manager = ConversationHistoryManager(
            max_tokens=Limits.MAX_TOKENS_FULL, brand_dir=brand_dir
        )
        # Load existing legacy history from disk if available (not session-aware)
        if brand_dir and not session_aware:
            self._history_manager.load_from_disk()
        # Context budget manager for monitoring total token usage
        self._budget_manager = ContextBudgetManager()
        logger.info(
            f"BrandAdvisor initialized for brand: {brand_slug or '(none)'}, "
            f"session_aware={session_aware}, session_id={self._current_session_id}"
        )

    def _init_session_aware(self, brand_slug: str, session_id: str | None = None) -> None:
        """Initialize session-aware components.
        Args:
            brand_slug: Brand to initialize sessions for.
            session_id: Optional specific session ID. If None, uses active or creates new.
        """
        self._session_manager = SessionManager(brand_slug)
        # Get or create session
        if session_id:
            self._current_session_id = session_id
        else:
            active = self._session_manager.get_active_session()
            if active:
                self._current_session_id = active.id
            else:
                # Create new session
                session = self._session_manager.create_session(SessionSettings())
                self._current_session_id = session.id
        # Initialize session history manager
        self._session_history = SessionHistoryManager(
            brand_slug, self._current_session_id, self._session_manager
        )
        # Initialize context cache
        self._context_cache = SessionContextCache(brand_slug, self._current_session_id)
        set_context_cache(self._context_cache)
        logger.debug(f"Session-aware mode initialized: session_id={self._current_session_id}")

    @property
    def session_id(self) -> str | None:
        """Get current session ID (session-aware mode only)."""
        return self._current_session_id

    @property
    def session_history(self) -> SessionHistoryManager | None:
        """Get session history manager (session-aware mode only)."""
        return self._session_history

    def switch_session(self, session_id: str) -> bool:
        """Switch to a different session (session-aware mode only).
        Args:
            session_id: Session ID to switch to.
        Returns:
            True if switch succeeded, False otherwise.
        """
        if not self._session_aware or not self._session_manager or not self.brand_slug:
            logger.warning("switch_session called but not in session-aware mode")
            return False
        # Cancel any pending compaction for current session
        if self._current_session_id:
            cancel_compaction(self._current_session_id)
        # Validate session exists
        session = self._session_manager.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return False
        # Switch
        self._session_manager.set_active_session(session_id)
        self._current_session_id = session_id
        self._session_history = SessionHistoryManager(
            self.brand_slug, session_id, self._session_manager
        )
        self._context_cache = SessionContextCache(self.brand_slug, session_id)
        set_context_cache(self._context_cache)
        # Rebuild system prompt with new session's summary
        summary = self._session_history.get_summary()
        self._agent = Agent(
            name="Brand Marketing Advisor",
            model="gpt-5.1",
            instructions=_build_system_prompt(
                self.brand_slug, use_lean_context=True, conversation_summary=summary
            ),
            tools=ADVISOR_TOOLS,
        )
        logger.info(f"Switched to session: {session_id}")
        return True

    def create_new_session(self, settings: SessionSettings | None = None) -> str:
        """Create a new session and switch to it (session-aware mode only).
        Args:
            settings: Optional session settings.
        Returns:
            New session ID.
        """
        if not self._session_aware or not self._session_manager or not self.brand_slug:
            raise RuntimeError("create_new_session requires session-aware mode")
        # Cancel any pending compaction for current session
        if self._current_session_id:
            cancel_compaction(self._current_session_id)
        session = self._session_manager.create_session(settings or SessionSettings())
        self._current_session_id = session.id
        self._session_history = SessionHistoryManager(
            self.brand_slug, session.id, self._session_manager
        )
        self._context_cache = SessionContextCache(self.brand_slug, session.id)
        set_context_cache(self._context_cache)
        # Rebuild system prompt (no summary for new session)
        self._agent = Agent(
            name="Brand Marketing Advisor",
            model="gpt-5.1",
            instructions=_build_system_prompt(self.brand_slug, use_lean_context=True),
            tools=ADVISOR_TOOLS,
        )
        logger.info(f"Created new session: {session.id}")
        return session.id

    def _get_last_response_id(self) -> str | None:
        """Get last response ID from current session for conversation chaining."""
        if not self._session_manager or not self._current_session_id:
            return None
        session = self._session_manager.get_session(self._current_session_id)
        return session.last_response_id if session else None

    def _save_response_id(self, response_id: str | None) -> None:
        """Save response ID to current session for conversation chaining."""
        if not self._session_manager or not self._current_session_id:
            return
        self._session_manager.update_session_response_id(self._current_session_id, response_id)

    def _estimate_task_count(self, prompt: str) -> int:
        """Estimate task count from prompt for dynamic max_turns."""
        import re

        p = prompt.lower()
        # Explicit number patterns
        patterns = [
            r"(\d+)\s*(?:images?|variations?|shots?|ideas?|concepts?|options?)",
            r"(?:generate|create|make)\s+(\d+)",
            r"(\d+)\s+(?:different|unique|distinct)",
        ]
        for pattern in patterns:
            m = re.search(pattern, p)
            if m:
                count = min(int(m.group(1)), 20)
                logger.info(f"[DYNAMIC_TURNS] Detected task count: {count} (pattern: '{pattern}')")
                return count
        # "all of them" patterns - default to 10 to ensure enough turns
        all_patterns = [
            r"(?:generate|create|make|do)\s+(?:all|them|these)",
            r"all\s+(?:of\s+)?(?:them|these|the\s+images?)",
            r"(?:every|each)\s+(?:one|image|idea)",
        ]
        for pattern in all_patterns:
            if re.search(pattern, p):
                logger.info(
                    f"[DYNAMIC_TURNS] Detected 'all' pattern: '{pattern}' -> defaulting to 10 tasks"
                )
                return 10
        logger.debug("[DYNAMIC_TURNS] No task count detected in prompt")
        return 0

    def _calculate_max_turns(self, task_count: int = 0) -> int:
        """Dynamic turn limit: base 25 + 5 per task, capped at 100."""
        max_turns = min(25 + (5 * task_count), 100)
        logger.info(f"[DYNAMIC_TURNS] Calculated max_turns: {max_turns} (base=25 + 5×{task_count})")
        return max_turns

    async def _enforce_context_limit(self, system_prompt: str) -> list[Message]:
        """Enforce hard context limit with compaction and emergency truncation.
        Per IMPLEMENTATION_PLAN.md Stage 7 - Hard context limit guardrail.
        Args:
            system_prompt: Current system prompt for token estimation.
        Returns:
            List of messages to use in prompt (after any compaction/truncation).
        """
        if not self._session_history:
            return []
        messages = self._session_history.get_prompt_messages()
        max_iterations = 5
        for _ in range(max_iterations):
            total_tokens = self._session_history.estimate_total_tokens(system_prompt)
            if total_tokens <= MAX_CONTEXT_LIMIT:
                break
            # Try compaction first
            if self._session_history.can_compact():
                await self._session_history.force_compact()
                messages = self._session_history.get_prompt_messages()
                continue
            # Emergency truncation - drop oldest non-system message
            if messages:
                self._session_history.advance_prompt_window(1)
                messages = self._session_history.get_prompt_messages()
        return messages

    @property
    def agent(self) -> Agent:
        """Access the underlying agent."""
        return self._agent

    def set_brand(self, slug: str, preserve_history: bool = True) -> None:
        """Switch to a different brand.
        Args:
            slug: Brand slug to switch to.
            preserve_history: If True (default), loads the new brand's conversation
                history from disk. If False, clears history completely.
        """
        set_active_brand(slug)
        self.brand_slug = slug

        # Get new brand's directory
        new_brand_dir = get_brand_dir(slug)

        # Update history manager's brand directory
        self._history_manager.brand_dir = new_brand_dir

        if preserve_history:
            # Load the new brand's history from disk (each brand has its own history)
            self._history_manager.clear()  # Clear in-memory first
            self._history_manager.load_from_disk()  # Load new brand's history
        else:
            # Explicitly clear (used by "Create New Chat")
            self._history_manager.clear(delete_file=True)

        # Rebuild system prompt with new brand context
        self._agent = Agent(
            name="Brand Marketing Advisor",
            model="gpt-5.1",
            instructions=_build_system_prompt(slug),
            tools=ADVISOR_TOOLS,
        )

        logger.info(f"Switched to brand: {slug}")

    def _prepare_chat_context(
        self,
        message: str,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_style_references: list[dict] | None = None,
        image_aspect_ratio: str | None = None,
        video_aspect_ratio: str | None = None,
    ) -> ChatContext:
        """Prepare all context needed for a chat turn.
        Args:
            message: User message to process.
            project_slug: Active project slug for context injection.
            attached_products: List of product slugs to include in context.
            attached_style_references: List of style reference dicts with style_ref_slug and strict.
            image_aspect_ratio: Default aspect ratio for image generation (passive, used by tools).
            video_aspect_ratio: Default aspect ratio for video generation (passive, used by tools).
        Returns:
            ChatContext with prepared prompt and metadata.
        """
        raw_user_message = message
        skills_context, matched_skills = self._get_relevant_skills_context(raw_user_message)
        # Build history text - HYBRID APPROACH: include client history even in session-aware mode
        # Server chain may summarize/lose details, so we send local history as backup
        history_text = ""
        if self._session_aware and self._session_history:
            messages = self._session_history.get_prompt_messages()
            if messages:
                history_text = self._format_session_history(
                    messages, max_tokens=Limits.MAX_TOKENS_COMPACT
                )
        elif not self._session_aware and self._history_manager.message_count > 0:
            history_text = self._history_manager.get_formatted(max_tokens=Limits.MAX_TOKENS_COMPACT)
        # Build per-turn context (project + attached products + templates)
        turn_context = ""
        if self.brand_slug and (project_slug or attached_products or attached_style_references):
            builder = HierarchicalContextBuilder(
                brand_slug=self.brand_slug,
                product_slugs=attached_products,
                project_slug=project_slug,
                attached_style_references=attached_style_references,
            )
            turn_context = builder.build_turn_context()
            logger.info(
                "_prepare_chat_context(): prods=%s, style_refs=%s, ctx_len=%d",
                attached_products,
                attached_style_references,
                len(turn_context),
            )
        # Set aspect ratios silently for tools to use
        if image_aspect_ratio:
            set_active_aspect_ratio(image_aspect_ratio)
        # Build augmented message with turn context prepended
        if turn_context:
            augmented_message = (
                f"## Current Context\n\n{turn_context}\n\n---\n\n"
                f"## User Request\n\n{raw_user_message}"
            )
        else:
            augmented_message = raw_user_message
        # Check budget and trim if needed (skip history for session-aware mode)
        budget_result, _, trimmed_skills, trimmed_history, _ = self._budget_manager.check_and_trim(
            system_prompt=self._agent.instructions or "",
            skills_context=skills_context,
            history=history_text,
            user_message=augmented_message,
        )
        system_prompt_trimmed = "trimmed system prompt" in (budget_result.warning_message or "")
        # Build prompt - include history as context backup (hybrid approach)
        prompt_parts = []
        if trimmed_skills:
            prompt_parts.append(trimmed_skills)
        if trimmed_history:
            prompt_parts.append(trimmed_history)
        prompt_parts.append(f"User: {augmented_message}")
        full_prompt = "\n\n".join(prompt_parts)
        # Debug logging for prompt inspection
        logger.debug(
            "[PROMPT_DEBUG] len=%d composer=%s prompt-eng=%s",
            len(full_prompt),
            "image-composer" in full_prompt,
            "image-prompt-engineering" in full_prompt,
        )
        hooks = AdvisorHooks(callback=self.progress_callback)
        return ChatContext(
            full_prompt=full_prompt,
            hooks=hooks,
            matched_skills=matched_skills,
            raw_user_message=raw_user_message,
            budget_trimmed=budget_result.trimmed,
            budget_warning=budget_result.warning_message,
            is_over_budget=budget_result.is_over_budget,
            system_prompt_trimmed=system_prompt_trimmed,
        )

    def _emit_skill_events(self, matched_skills: list[tuple[str, str]]) -> None:
        """Emit progress events for matched skills."""
        for skill_name, skill_description in matched_skills:
            if self.progress_callback:
                self.progress_callback(
                    AdvisorProgress(
                        event_type="skill_loaded",
                        message=f"Loading {skill_name} skill",
                        detail=skill_description,
                    )
                )

    def _log_budget_warnings(self, ctx: ChatContext) -> None:
        """Log budget warnings from chat context."""
        if ctx.budget_trimmed:
            logger.warning(f"Context trimmed: {ctx.budget_warning}")
        if ctx.is_over_budget:
            logger.error(
                "CRITICAL: Still over budget after trimming. Consider reducing system prompt size."
            )
        if ctx.system_prompt_trimmed:
            logger.error(
                "System prompt was trimmed! Base prompt too large. "
                "Consider reducing prompt size or brand context."
            )

    def _setup_tool_callback(self) -> None:
        """Set up tool progress callback for emit_tool_thinking."""

        def _tool_cb(
            step: str, detail: str, expertise: str | None, status: str, step_id: str | None
        ) -> None:
            if self.progress_callback:
                self.progress_callback(
                    AdvisorProgress(
                        event_type="thinking_step",
                        message=step,
                        detail=detail,
                        expertise=expertise,
                        step_id=step_id,
                        status=status,
                    )
                )

        set_tool_progress_callback(_tool_cb)

    async def chat_with_metadata(
        self,
        message: str,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_style_references: list[dict] | None = None,
        image_aspect_ratio: str | None = None,
        video_aspect_ratio: str | None = None,
    ) -> dict:
        """Send a message and get a response plus UI metadata.
        Args:
            message: User message to process.
            project_slug: Active project slug for context injection.
            attached_products: List of product slugs to include in context.
            attached_style_references: Style reference dicts with style_ref_slug and strict.
            image_aspect_ratio: Default image aspect ratio (passive, used by tools).
            video_aspect_ratio: Default video aspect ratio (passive, used by tools).
        Returns:
            Dict with response, interaction, and memory_update.
        """
        # Reset skill workflow state for new turn (progressive disclosure)
        reset_workflow_state()
        ctx = self._prepare_chat_context(
            message,
            project_slug,
            attached_products,
            attached_style_references,
            image_aspect_ratio,
            video_aspect_ratio,
        )
        self._emit_skill_events(ctx.matched_skills)
        self._log_budget_warnings(ctx)
        self._setup_tool_callback()
        # Session-aware mode: enforce context limits and generate title
        if self._session_aware and self._session_history:
            system_prompt = str(self._agent.instructions) if self._agent.instructions else ""
            await self._enforce_context_limit(system_prompt)
            # Generate session title on first user message
            if self._session_history.get_prompt_window_start() == 0:
                messages = self._session_history.get_messages()
                if not messages:
                    # First message in session - generate title asynchronously
                    asyncio.create_task(self._update_session_title(message))
        # Get previous response ID for conversation chaining (session-aware mode)
        prev_response_id = self._get_last_response_id() if self._session_aware else None
        # Dynamic max_turns based on estimated task count
        task_count = self._estimate_task_count(ctx.full_prompt)
        max_turns = self._calculate_max_turns(task_count)
        try:
            result = await Runner.run(
                self._agent,
                ctx.full_prompt,
                hooks=ctx.hooks,
                previous_response_id=prev_response_id,
                max_turns=max_turns,
            )
            response = result.final_output
            response_text = response.text if hasattr(response, "text") else str(response)
            # Save response ID for conversation chaining
            if self._session_aware:
                self._save_response_id(result.last_response_id)
            # Add to history (session-aware or legacy)
            if self._session_aware and self._session_history:
                user_msg = Message.create("user", ctx.raw_user_message)
                assistant_msg = Message.create("assistant", response_text)
                self._session_history.add_messages([user_msg, assistant_msg])
            else:
                self._history_manager.add("user", ctx.raw_user_message)
                self._history_manager.add("assistant", response_text)
            return {
                "response": response_text,
                "interaction": ctx.hooks.captured_interaction,
                "memory_update": ctx.hooks.captured_memory_update,
            }
        except openai.BadRequestError as e:
            # Handle context_length_exceeded with emergency recovery
            if "context_length_exceeded" in str(e) and self._session_history:
                logger.warning("Context length exceeded, attempting emergency truncation")
                messages = self._session_history.get_prompt_messages()
                new_start = len(self._session_history.get_messages()) - len(messages) // 2
                self._session_history.set_prompt_window_start(new_start)
                # Reset response chain after emergency truncation
                self._save_response_id(None)
                # Retry without previous_response_id (fresh start with summary)
                result = await Runner.run(
                    self._agent, ctx.full_prompt, hooks=ctx.hooks, max_turns=max_turns
                )
                response = result.final_output
                response_text = response.text if hasattr(response, "text") else str(response)
                self._save_response_id(result.last_response_id)
                user_msg = Message.create("user", ctx.raw_user_message)
                assistant_msg = Message.create("assistant", response_text)
                self._session_history.add_messages([user_msg, assistant_msg])
                return {
                    "response": response_text,
                    "interaction": ctx.hooks.captured_interaction,
                    "memory_update": ctx.hooks.captured_memory_update,
                }
            logger.error(f"Chat failed: {e}")
            raise
        except MaxTurnsExceeded:
            logger.error("Max turns exceeded - task too complex for single request")
            raise RuntimeError(
                "This task requires too many steps. Try requesting fewer images "
                "or breaking the task into smaller parts."
            ) from None
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise
        finally:
            set_tool_progress_callback(None)

    async def _update_session_title(self, first_message: str) -> None:
        """Generate and update session title from first message.
        Args:
            first_message: First user message in the session.
        """
        if not self._session_manager or not self._current_session_id:
            return
        try:
            title = await _generate_session_title(first_message)
            self._session_manager.update_session_meta(self._current_session_id, title=title)
            logger.debug(f"Updated session title: {title}")
        except Exception as e:
            logger.warning(f"Failed to generate session title: {e}")

    async def chat(
        self,
        message: str,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_style_references: list[dict] | None = None,
    ) -> str:
        """Send a message and get a response.

        Args:
            message: User message to process.
            project_slug: Active project slug for context injection.
            attached_products: List of product slugs to include in context.
            attached_style_references: List of style reference dicts with style_ref_slug and strict.

        Returns:
            Agent's response text.
        """
        result = await self.chat_with_metadata(
            message,
            project_slug=project_slug,
            attached_products=attached_products,
            attached_style_references=attached_style_references,
        )
        return result["response"]

    async def chat_stream(
        self,
        message: str,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_style_references: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        """Send a message and stream the response.
        Args:
            message: User message to process.
            project_slug: Active project slug for context injection.
            attached_products: List of product slugs to include in context.
            attached_style_references: List of style reference dicts with style_ref_slug and strict.
        Yields:
            Response text chunks as they're generated.
        """
        ctx = self._prepare_chat_context(
            message,
            project_slug,
            attached_products,
            attached_style_references,
        )
        self._emit_skill_events(ctx.matched_skills)
        self._log_budget_warnings(ctx)
        self._setup_tool_callback()
        # Session-aware mode: enforce context limits and generate title
        if self._session_aware and self._session_history:
            system_prompt = str(self._agent.instructions) if self._agent.instructions else ""
            await self._enforce_context_limit(system_prompt)
            # Generate session title on first user message
            if self._session_history.get_prompt_window_start() == 0:
                messages = self._session_history.get_messages()
                if not messages:
                    asyncio.create_task(self._update_session_title(message))
        # Get previous response ID for conversation chaining (session-aware mode)
        prev_response_id = self._get_last_response_id() if self._session_aware else None
        # Dynamic max_turns based on estimated task count
        task_count = self._estimate_task_count(ctx.full_prompt)
        max_turns = self._calculate_max_turns(task_count)
        response_chunks: list[str] = []
        stream_result = None
        try:
            stream = Runner.run_streamed(
                self._agent,
                ctx.full_prompt,
                hooks=ctx.hooks,
                previous_response_id=prev_response_id,
                max_turns=max_turns,
            )
            async for chunk in stream:
                if hasattr(chunk, "text") and chunk.text:
                    response_chunks.append(chunk.text)
                    yield chunk.text
            stream_result = stream
            full_response = "".join(response_chunks)
            # Save response ID for conversation chaining (if available)
            if self._session_aware and stream_result:
                self._save_response_id(getattr(stream_result, "last_response_id", None))
            # Add to history (session-aware or legacy)
            if self._session_aware and self._session_history:
                user_msg = Message.create("user", ctx.raw_user_message)
                assistant_msg = Message.create("assistant", full_response)
                self._session_history.add_messages([user_msg, assistant_msg])
            else:
                self._history_manager.add("user", ctx.raw_user_message)
                self._history_manager.add("assistant", full_response)
        except asyncio.CancelledError:
            logger.warning("Stream cancelled")
            raise
        except MaxTurnsExceeded:
            logger.error("Max turns exceeded - task too complex for single request")
            raise RuntimeError(
                "This task requires too many steps. Try requesting fewer images "
                "or breaking the task into smaller parts."
            ) from None
        except Exception as e:
            logger.error(f"Stream chat failed: {e}")
            raise
        finally:
            set_tool_progress_callback(None)

    def _format_history(self, max_turns: int = 10) -> str:
        """Format conversation history for prompt.
        Args:
            max_turns: Maximum conversation turns to include.
        Returns:
            Formatted history string.
        """
        max_tokens = max_turns * 400
        return self._history_manager.get_formatted(max_tokens=max_tokens)

    def _format_session_history(self, messages: list[Message], max_tokens: int = 8000) -> str:
        """Format session messages for prompt injection.
        Args:
            messages: List of Message objects from SessionHistoryManager.
            max_tokens: Maximum tokens to include.
        Returns:
            Formatted conversation history string.
        """
        if not messages:
            return ""
        parts = ["## Conversation History\n"]
        current_tokens = 20
        chars_per_token = 4
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            content = msg.content[:2000] if len(msg.content) > 2000 else msg.content
            msg_text = f"{role}: {content}"
            msg_tokens = len(msg_text) // chars_per_token
            if current_tokens + msg_tokens > max_tokens:
                parts.append("[... older messages truncated ...]")
                break
            parts.append(msg_text)
            current_tokens += msg_tokens
        return "\n\n".join(parts)

    def _get_relevant_skills_context(
        self, message: str, max_skills: int = 2
    ) -> tuple[str, list[tuple[str, str]]]:
        """Find and format relevant skill ACTIVATION PROMPTS for the message.
        Uses progressive disclosure: only inject condensed activation prompts (~200 tokens each)
        instead of full instructions (10K+ chars). Agent must call activate_skill() to load full.
        Args:
            message: User message to match against skill triggers.
            max_skills: Maximum number of skills to include.
        Returns:
            Tuple of (formatted activation prompts, list of (skill_name, description) tuples).
        """
        skills_registry = get_skills_registry()
        relevant_skills = skills_registry.find_relevant_skills(message)
        if not relevant_skills:
            logger.info("[SKILL_CONTEXT] No skills matched - agent will use base instructions only")
            return "", []
        skills_to_use = relevant_skills[:max_skills]
        matched_skills = [(skill.name, skill.description) for skill in skills_to_use]
        # Check if any workflow-required skills are matched
        workflow_skills = [s for s in skills_to_use if s.workflow_required]
        parts = ["## Image Generation Workflow\n"]
        if workflow_skills:
            parts.append("**MANDATORY**: For image generation, you MUST follow this workflow:\n")
            parts.append(
                "1. Call `activate_skill('image-composer')` to load composition guidelines"
            )
            parts.append(
                "2. Create a structured visual brief (concept, subject, setting, lighting)"
            )
            parts.append(
                "3. Call `activate_skill('image-prompt-engineering')` to load prompt guidelines"
            )
            parts.append("4. Craft your prompt using the 5-point formula (80+ words)")
            parts.append("5. Call `generate_image` with your crafted prompt\n")
            parts.append("**DO NOT** skip directly to generate_image with a simple prompt.\n")
        parts.append("### Available Skills (call activate_skill to load full instructions)\n")
        for skill in skills_to_use:
            # Use activation_prompt if available, otherwise generate default
            activation = skill.get_activation_prompt()
            parts.append(f"**{skill.name}**")
            parts.append(activation)
            parts.append("")
            logger.info(
                "[SKILL_CONTEXT] Skill '%s' activation prompt: %d chars (vs full: %d chars)",
                skill.name,
                len(activation),
                len(skill.instructions),
            )
        total_chars = sum(len(p) for p in parts)
        logger.info(
            "[SKILL_CONTEXT] Total context: %d chars (saved ~%d chars)",
            total_chars,
            sum(len(s.instructions) for s in skills_to_use) - total_chars,
        )
        return "\n".join(parts), matched_skills

    def clear_history(self, delete_file: bool = True) -> None:
        """Clear conversation history.
        Args:
            delete_file: If True (default), also deletes the history file from disk.
        """
        self._history_manager.clear(delete_file=delete_file)


# =============================================================================
# Convenience Functions
# =============================================================================


async def quick_chat(message: str, brand_slug: str | None = None) -> str:
    """Quick one-off chat with the advisor.

    Args:
        message: User message.
        brand_slug: Optional brand slug.

    Returns:
        Agent's response.
    """
    advisor = BrandAdvisor(brand_slug=brand_slug)
    return await advisor.chat(message)
