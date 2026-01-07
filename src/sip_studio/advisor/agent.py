"""Brand Marketing Advisor agent - single agent with skills architecture.
This module implements a single intelligent agent that uses skills to handle
all brand-related tasks. It replaces the previous multi-agent orchestration
pattern with a simpler, more maintainable architecture.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator

from agents import Agent, Runner

from sip_studio.advisor.context_budget import ContextBudgetManager
from sip_studio.advisor.history_manager import ConversationHistoryManager
from sip_studio.advisor.hooks import AdvisorHooks, AdvisorProgress, ProgressCallback
from sip_studio.advisor.prompt_builder import (
    build_system_prompt as _build_system_prompt,
)
from sip_studio.advisor.skills.registry import get_skills_registry
from sip_studio.advisor.tools import (
    ADVISOR_TOOLS,
    set_active_aspect_ratio,
    set_tool_progress_callback,
)
from sip_studio.brands.context import HierarchicalContextBuilder
from sip_studio.brands.storage import get_active_brand, set_active_brand
from sip_studio.config.constants import Limits
from sip_studio.config.logging import get_logger

logger = get_logger(__name__)


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

    Example:
        ```python
        advisor = BrandAdvisor(brand_slug="summit-coffee")
        response = await advisor.chat("Create a playful mascot")
        print(response)
        ```
    """

    def __init__(
        self,
        brand_slug: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ):
        """Initialize the advisor.

        Args:
            brand_slug: Optional brand slug to load context for.
                If not provided, uses the active brand.
            progress_callback: Optional callback for progress updates.
        """
        # Resolve brand slug
        if brand_slug is None:
            brand_slug = get_active_brand()

        self.brand_slug = brand_slug
        self.progress_callback = progress_callback

        # Build system prompt
        system_prompt = _build_system_prompt(brand_slug)

        # Create the agent
        self._agent = Agent(
            name="Brand Marketing Advisor",
            model="gpt-5.1",  # 272K context, adaptive reasoning
            instructions=system_prompt,
            tools=ADVISOR_TOOLS,
        )

        # Track conversation history with token-aware management
        self._history_manager = ConversationHistoryManager(max_tokens=Limits.MAX_TOKENS_FULL)

        # Context budget manager for monitoring total token usage
        self._budget_manager = ContextBudgetManager()

        logger.info(f"BrandAdvisor initialized for brand: {brand_slug or '(none)'}")

    @property
    def agent(self) -> Agent:
        """Access the underlying agent."""
        return self._agent

    def set_brand(self, slug: str, preserve_history: bool = False) -> None:
        """Switch to a different brand.

        Args:
            slug: Brand slug to switch to.
            preserve_history: If False (default), clears conversation history
                to prevent cross-brand contamination.
        """
        set_active_brand(slug)
        self.brand_slug = slug

        # Clear history to prevent cross-brand contamination
        if not preserve_history:
            self._history_manager.clear()

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
        aspect_ratio: str | None = None,
        generation_mode: str | None = None,
        inject_generation_mode: bool = False,
    ) -> ChatContext:
        """Prepare all context needed for a chat turn.
        Args:
            message: User message to process.
            project_slug: Active project slug for context injection.
            attached_products: List of product slugs to include in context.
            attached_style_references: List of style reference dicts with style_ref_slug and strict.
            aspect_ratio: Aspect ratio for video/image generation.
            generation_mode: Generation mode ('image' or 'video').
            inject_generation_mode: If True, always inject generation_mode context (defaults to 'image').
        Returns:
            ChatContext with prepared prompt and metadata.
        """
        raw_user_message = message
        skills_context, matched_skills = self._get_relevant_skills_context(raw_user_message)
        history_text = ""
        if self._history_manager.message_count > 0:
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
                "_prepare_chat_context(): attached_products=%s, attached_style_refs=%s, turn_context_len=%d",
                attached_products,
                attached_style_references,
                len(turn_context),
            )
        # Generation mode injection - ALWAYS for chat_with_metadata (defaults to "image")
        if inject_generation_mode:
            mode = generation_mode if generation_mode in ("image", "video") else "image"
            mode_ctx = f"**Generation Mode**: {mode.capitalize()} - {'Generate videos using generate_video tool.' if mode == 'video' else 'Generate images using generate_image tool.'}"
            turn_context = f"{turn_context}\n\n{mode_ctx}" if turn_context else mode_ctx
            if aspect_ratio:
                set_active_aspect_ratio(aspect_ratio)
                ar_ctx = f"**Aspect Ratio**: Use {aspect_ratio} for any image or video generation."
                turn_context = f"{turn_context}\n\n{ar_ctx}"
        # Build augmented message with turn context prepended
        if turn_context:
            augmented_message = f"## Current Context\n\n{turn_context}\n\n---\n\n## User Request\n\n{raw_user_message}"
        else:
            augmented_message = raw_user_message
        # Check budget and trim if needed
        budget_result, _, trimmed_skills, trimmed_history, _ = self._budget_manager.check_and_trim(
            system_prompt=self._agent.instructions or "",
            skills_context=skills_context,
            history=history_text,
            user_message=augmented_message,
        )
        system_prompt_trimmed = "trimmed system prompt" in (budget_result.warning_message or "")
        # Build prompt with trimmed parts
        prompt_parts = []
        if trimmed_skills:
            prompt_parts.append(trimmed_skills)
        if trimmed_history:
            prompt_parts.append(trimmed_history)
        prompt_parts.append(f"User: {augmented_message}")
        full_prompt = "\n\n".join(prompt_parts)
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
                "System prompt was trimmed! This indicates the base prompt is too large. Consider reducing prompt size or brand context."
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
        aspect_ratio: str | None = None,
        generation_mode: str | None = None,
    ) -> dict:
        """Send a message and get a response plus UI metadata.
        Args:
            message: User message to process.
            project_slug: Active project slug for context injection.
            attached_products: List of product slugs to include in context.
            attached_style_references: List of style reference dicts with style_ref_slug and strict.
            aspect_ratio: Aspect ratio for video/image generation (e.g., "1:1", "16:9").
            generation_mode: Generation mode ('image' or 'video').
        Returns:
            Dict with response, interaction, and memory_update.
        """
        ctx = self._prepare_chat_context(
            message,
            project_slug,
            attached_products,
            attached_style_references,
            aspect_ratio,
            generation_mode,
            inject_generation_mode=True,
        )
        self._emit_skill_events(ctx.matched_skills)
        self._log_budget_warnings(ctx)
        self._setup_tool_callback()
        try:
            result = await Runner.run(self._agent, ctx.full_prompt, hooks=ctx.hooks)
            response = result.final_output
            response_text = response.text if hasattr(response, "text") else str(response)
            self._history_manager.add("user", ctx.raw_user_message)
            self._history_manager.add("assistant", response_text)
            return {
                "response": response_text,
                "interaction": ctx.hooks.captured_interaction,
                "memory_update": ctx.hooks.captured_memory_update,
            }
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise
        finally:
            set_tool_progress_callback(None)

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
            aspect_ratio=None,
            generation_mode=None,
            inject_generation_mode=False,
        )
        self._emit_skill_events(ctx.matched_skills)
        self._log_budget_warnings(ctx)
        self._setup_tool_callback()
        response_chunks: list[str] = []
        try:
            async for chunk in Runner.run_streamed(self._agent, ctx.full_prompt, hooks=ctx.hooks):
                if hasattr(chunk, "text") and chunk.text:
                    response_chunks.append(chunk.text)
                    yield chunk.text
            full_response = "".join(response_chunks)
            self._history_manager.add("user", ctx.raw_user_message)
            self._history_manager.add("assistant", full_response)
        except asyncio.CancelledError:
            logger.warning("Stream cancelled")
            raise
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
        # Estimate ~400 tokens per turn (user + assistant)
        max_tokens = max_turns * 400
        return self._history_manager.get_formatted(max_tokens=max_tokens)

    def _get_relevant_skills_context(
        self, message: str, max_skills: int = 2
    ) -> tuple[str, list[tuple[str, str]]]:
        """Find and format relevant skill instructions for the message.

        Args:
            message: User message to match against skill triggers.
            max_skills: Maximum number of skills to include (to limit context size).

        Returns:
            Tuple of (formatted skill instructions, list of (skill_name, description) tuples).
            Returns ("", []) if no matches.
        """
        skills_registry = get_skills_registry()
        relevant_skills = skills_registry.find_relevant_skills(message)

        if not relevant_skills:
            return "", []

        # Limit to max_skills
        skills_to_use = relevant_skills[:max_skills]

        # Collect skill info for progress reporting
        matched_skills = [(skill.name, skill.description) for skill in skills_to_use]

        parts = ["## Relevant Skill Instructions\n"]
        parts.append(
            "The following skills are relevant to this request. Follow their guidelines:\n"
        )

        for skill in skills_to_use:
            parts.append(f"### {skill.name}\n")
            parts.append(skill.instructions)
            parts.append("")

        return "\n".join(parts), matched_skills

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._history_manager.clear()


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
