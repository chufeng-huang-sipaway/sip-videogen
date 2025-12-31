"""Brand Marketing Advisor agent - single agent with skills architecture.

This module implements a single intelligent agent that uses skills to handle
all brand-related tasks. It replaces the previous multi-agent orchestration
pattern with a simpler, more maintainable architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator, Callable

from agents import Agent, RunHooks, Runner, Tool
from agents.run_context import RunContextWrapper

from sip_videogen.advisor.context_budget import ContextBudgetManager
from sip_videogen.advisor.history_manager import ConversationHistoryManager
from sip_videogen.advisor.skills.registry import get_skills_registry
from sip_videogen.advisor.tools import ADVISOR_TOOLS
from sip_videogen.brands.context import HierarchicalContextBuilder
from sip_videogen.brands.memory import list_brand_assets
from sip_videogen.brands.storage import (
    get_active_brand,
    get_brand_dir,
    load_brand,
    set_active_brand,
)
from sip_videogen.config.logging import get_logger

if TYPE_CHECKING:
    from sip_videogen.brands.models import BrandIdentityFull

logger = get_logger(__name__)

__all__ = ["BrandAdvisor", "AdvisorProgress", "ProgressCallback"]


# =============================================================================
# Progress Tracking
# =============================================================================


@dataclass
class AdvisorProgress:
    """Progress update from the advisor agent.

    Event types:
        - "thinking": LLM is generating a response
        - "tool_start": Agent started using a tool
        - "tool_end": Tool call completed
        - "skill_loaded": A skill was matched and loaded for the request
        - "thinking_step": Agent reported a thinking step via report_thinking tool
        - "response": Agent completed responding
    """

    event_type: str  # thinking, tool_start, tool_end, skill_loaded, thinking_step, response
    message: str
    detail: str = ""


ProgressCallback = Callable[[AdvisorProgress], None]


class AdvisorHooks(RunHooks):
    """Hooks for tracking advisor progress."""

    def __init__(self, callback: ProgressCallback | None = None):
        self.callback = callback
        self.captured_interaction: dict | None = None
        self.captured_memory_update: dict | None = None
        self._tool_descriptions = {
            "generate_image": "Generating image with Gemini",
            "read_file": "Reading file",
            "write_file": "Writing file",
            "list_files": "Listing directory contents",
            "load_brand": "Loading brand context",
            "propose_choices": "Presenting options to the user",
            "propose_images": "Showing images for selection",
            "update_memory": "Recording a preference",
        }

    def _report(self, progress: AdvisorProgress) -> None:
        """Report progress to callback if set."""
        if self.callback:
            self.callback(progress)
        logger.debug(f"[{progress.event_type}] {progress.message}")

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        """Called when the agent starts using a tool."""
        tool_name = tool.name
        #Skip progress reporting for report_thinking (meta tool, not useful to show as tool_start)
        if tool_name == "report_thinking":
            return
        description = self._tool_descriptions.get(tool_name, f"Running {tool_name}")
        self._report(
            AdvisorProgress(
                event_type="tool_start",
                message=f"Using {tool_name}",
                detail=description,
            )
        )

    async def on_tool_end(
        self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str
    ) -> None:
        """Called when a tool call completes."""
        from sip_videogen.advisor.tools import (
            get_pending_interaction,
            get_pending_memory_update,
            parse_thinking_step_result,
        )

        tool_name = tool.name

        #Handle report_thinking specially - emit thinking_step event instead of tool_end
        if tool_name == "report_thinking":
            step_data = parse_thinking_step_result(str(result))
            if step_data:
                self._report(AdvisorProgress(
                    event_type="thinking_step",
                    message=step_data["step"],
                    detail=step_data["detail"],
                ))
            return  #Skip normal tool_end reporting

        if tool_name in ("propose_choices", "propose_images"):
            interaction = get_pending_interaction()
            if interaction:
                self.captured_interaction = interaction

        if tool_name == "update_memory":
            mem_update = get_pending_memory_update()
            if mem_update:
                self.captured_memory_update = mem_update

        result_preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        self._report(
            AdvisorProgress(
                event_type="tool_end",
                message=f"{tool_name} completed",
                detail=result_preview,
            )
        )

    async def on_llm_start(self, context: RunContextWrapper, agent: Agent, *args, **kwargs) -> None:
        """Called when the LLM starts generating."""
        self._report(
            AdvisorProgress(
                event_type="thinking",
                message="Thinking...",
            )
        )


# =============================================================================
# System Prompt Builder
# =============================================================================


def _build_system_prompt(brand_slug: str | None = None) -> str:
    """Build the system prompt for the Brand Marketing Advisor.

    Args:
        brand_slug: Optional brand slug to include context for.

    Returns:
        Complete system prompt with skills and brand context.
    """
    # Load base prompt
    prompt_path = Path(__file__).parent / "prompts" / "advisor.md"
    if prompt_path.exists():
        base_prompt = prompt_path.read_text()
    else:
        base_prompt = _DEFAULT_PROMPT

    # Add skills section
    skills_registry = get_skills_registry()
    skills_section = skills_registry.format_for_prompt()

    # Add brand context if available
    brand_section = ""
    memory_section = ""
    if brand_slug:
        identity = load_brand(brand_slug)
        if identity:
            brand_section = _format_brand_context(brand_slug, identity)

        memory_path = get_brand_dir(brand_slug) / "memory.json"
        if memory_path.exists():
            try:
                import json

                memory = json.loads(memory_path.read_text())
                if memory:
                    memory_lines = ["## Remembered Preferences", ""]
                    for key, data in memory.items():
                        memory_lines.append(f"- **{key}**: {data.get('value', '')}")
                    memory_section = "\n".join(memory_lines)
            except (json.JSONDecodeError, KeyError):
                pass

    return f"""{base_prompt}

{skills_section}

{brand_section}

{memory_section}
""".strip()


def _format_brand_context(slug: str, identity: "BrandIdentityFull") -> str:
    """Format brand identity as context for the system prompt.

    Args:
        slug: Brand slug.
        identity: Full brand identity.

    Returns:
        Formatted brand context markdown.
    """
    parts = [
        "## Current Brand Context",
        "",
        f"**Brand**: {identity.core.name}",
        f"**Tagline**: {identity.core.tagline}",
        f"**Category**: {identity.positioning.market_category}",
        "",
    ]

    # Visual identity summary
    if identity.visual.primary_colors:
        colors = ", ".join(f"{c.name} ({c.hex})" for c in identity.visual.primary_colors[:3])
        parts.append(f"**Colors**: {colors}")
    if identity.visual.style_keywords:
        parts.append(f"**Style**: {', '.join(identity.visual.style_keywords[:5])}")

    # Voice summary
    if identity.voice.tone_attributes:
        parts.append(f"**Tone**: {', '.join(identity.voice.tone_attributes[:3])}")

    # Audience summary
    parts.append(f"**Audience**: {identity.audience.primary_summary}")

    # Assets summary
    try:
        assets = list_brand_assets(slug)
        if assets:
            asset_summary = ", ".join(
                f"{cat}: {len(files)}" for cat, files in _group_assets(assets).items()
            )
            parts.append(f"**Assets**: {asset_summary}")
    except Exception:
        pass

    parts.append("")
    parts.append(
        "Use `load_brand()` for a quick summary, or `load_brand(detail_level='full')` "
        "for complete context. Use `list_files()` to browse assets."
    )

    return "\n".join(parts)


def _group_assets(assets: list[dict]) -> dict[str, list[dict]]:
    """Group assets by category."""
    grouped: dict[str, list[dict]] = {}
    for asset in assets:
        cat = asset.get("category", "other")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(asset)
    return grouped


# Default prompt if file not found
_DEFAULT_PROMPT = """# Brand Marketing Advisor

You are a Brand Marketing Advisor - an expert in brand strategy, visual identity,
and marketing communications. You help users build, evolve, and maintain their
brand identities.

## Your Capabilities

You have 5 core tools:
1. **generate_image** - Create images via Gemini (logos, mascots, lifestyle photos)
2. **read_file** - Read files from the brand directory
3. **write_file** - Write/update files in the brand directory
4. **list_files** - Browse the brand directory structure
5. **load_brand** - Load brand identity (summary by default; use `detail_level='full'` for full)

## Your Approach

1. **Understand First**: Always load and understand the brand context before making decisions
2. **Be Consultative**: Ask clarifying questions when requirements are ambiguous
3. **Stay On-Brand**: Ensure all outputs align with established brand guidelines
4. **Document Decisions**: Use write_file to persist important decisions and rationale
5. **Reference Skills**: Use the available skills as guides for specific tasks

## Output Quality

- Generate high-quality, professional brand assets
- Provide clear rationale for creative decisions
- Maintain consistency with existing brand materials
- Suggest improvements based on brand strategy principles
"""


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
        self._history_manager = ConversationHistoryManager(max_tokens=8000)

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

    async def chat_with_metadata(
        self,
        message: str,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_templates: list[dict] | None = None,
        aspect_ratio: str | None = None,
    ) -> dict:
        """Send a message and get a response plus UI metadata.

        Args:
            message: User message to process.
            project_slug: Active project slug for context injection.
            attached_products: List of product slugs to include in context.
            attached_templates: List of template dicts with template_slug and strict.
            aspect_ratio: Aspect ratio for video/image generation (e.g., "1:1", "16:9").

        Returns:
            Dict with response, interaction, and memory_update.
        """
        hooks = AdvisorHooks(callback=self.progress_callback)

        # Keep raw message for skill matching and history
        raw_user_message = message

        # Find relevant skills using RAW message (not augmented)
        skills_context, matched_skills = self._get_relevant_skills_context(raw_user_message)

        # Emit progress events for matched skills
        for skill_name, skill_description in matched_skills:
            if self.progress_callback:
                self.progress_callback(
                    AdvisorProgress(
                        event_type="skill_loaded",
                        message=f"Loading {skill_name} skill",
                        detail=skill_description,
                    )
                )

        # Get conversation history
        history_text = ""
        if self._history_manager.message_count > 0:
            history_text = self._history_manager.get_formatted(max_tokens=4000)

        # Build per-turn context (project + attached products + templates)
        turn_context = ""
        if self.brand_slug and (project_slug or attached_products or attached_templates):
            builder = HierarchicalContextBuilder(
                brand_slug=self.brand_slug,
                product_slugs=attached_products,
                project_slug=project_slug,
                attached_templates=attached_templates,
            )
            turn_context = builder.build_turn_context()
            logger.info("chat_with_metadata(): attached_products=%s, turn_context_len=%d",attached_products,len(turn_context))
        #Add aspect ratio to turn context if provided (chat_with_metadata only)
        if aspect_ratio:
            ar_ctx=f"**Aspect Ratio**: Use {aspect_ratio} for any image or video generation."
            turn_context=f"{turn_context}\n\n{ar_ctx}" if turn_context else ar_ctx

        # Build augmented message with turn context prepended
        if turn_context:
            augmented_message = f"""## Current Context

{turn_context}

---

## User Request

{raw_user_message}"""
        else:
            augmented_message = raw_user_message

        # Check budget and trim if needed (use augmented_message for accurate size)
        budget_result, trimmed_system, trimmed_skills, trimmed_history, _ = (
            self._budget_manager.check_and_trim(
                system_prompt=self._agent.instructions or "",
                skills_context=skills_context,
                history=history_text,
                user_message=augmented_message,
            )
        )

        if budget_result.trimmed:
            logger.warning(f"Context trimmed: {budget_result.warning_message}")

        if budget_result.is_over_budget:
            logger.error(
                f"CRITICAL: Still over budget after trimming: "
                f"{budget_result.total_tokens}/{budget_result.budget_limit} tokens. "
                f"Consider reducing system prompt size."
            )

        # Log severe warning if system prompt was trimmed (would need agent rebuild)
        if "trimmed system prompt" in (budget_result.warning_message or ""):
            logger.error(
                "System prompt was trimmed! This indicates the base prompt is too large. "
                "Consider reducing prompt size or brand context."
            )

        # Build prompt with trimmed parts (but NOT trimmed_system - would require Agent rebuild)
        prompt_parts = []

        if trimmed_skills:
            prompt_parts.append(trimmed_skills)

        if trimmed_history:
            prompt_parts.append(trimmed_history)

        # Use augmented message (with turn context) for LLM
        prompt_parts.append(f"User: {augmented_message}")
        full_prompt = "\n\n".join(prompt_parts)
        #Set up tool progress callback for emit_tool_thinking
        from sip_videogen.advisor.tools import set_tool_progress_callback
        def _tool_cb(step:str,detail:str)->None:
            if self.progress_callback:self.progress_callback(AdvisorProgress(event_type="thinking_step",message=step,detail=detail))
        set_tool_progress_callback(_tool_cb)
        try:
            result = await Runner.run(self._agent, full_prompt, hooks=hooks)

            # Extract response text
            response = result.final_output
            if hasattr(response, "text"):
                response_text = response.text
            else:
                response_text = str(response)

            # Update conversation history with RAW message (not augmented)
            # This prevents history from ballooning with repeated context
            self._history_manager.add("user", raw_user_message)
            self._history_manager.add("assistant", response_text)

            return {
                "response": response_text,
                "interaction": hooks.captured_interaction,
                "memory_update": hooks.captured_memory_update,
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
        attached_templates: list[dict] | None = None,
    ) -> str:
        """Send a message and get a response.

        Args:
            message: User message to process.
            project_slug: Active project slug for context injection.
            attached_products: List of product slugs to include in context.
            attached_templates: List of template dicts with template_slug and strict.

        Returns:
            Agent's response text.
        """
        result = await self.chat_with_metadata(
            message,
            project_slug=project_slug,
            attached_products=attached_products,
            attached_templates=attached_templates,
        )
        return result["response"]

    async def chat_stream(
        self,
        message: str,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_templates: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        """Send a message and stream the response.

        Args:
            message: User message to process.
            project_slug: Active project slug for context injection.
            attached_products: List of product slugs to include in context.
            attached_templates: List of template dicts with template_slug and strict.

        Yields:
            Response text chunks as they're generated.
        """
        hooks = AdvisorHooks(callback=self.progress_callback)

        # Keep raw message for skill matching and history
        raw_user_message = message

        # Find relevant skills using RAW message (not augmented)
        skills_context, matched_skills = self._get_relevant_skills_context(raw_user_message)

        # Emit progress events for matched skills
        for skill_name, skill_description in matched_skills:
            if self.progress_callback:
                self.progress_callback(
                    AdvisorProgress(
                        event_type="skill_loaded",
                        message=f"Loading {skill_name} skill",
                        detail=skill_description,
                    )
                )

        # Get conversation history
        history_text = ""
        if self._history_manager.message_count > 0:
            history_text = self._history_manager.get_formatted(max_tokens=4000)

        # Build per-turn context (project + attached products + templates)
        turn_context = ""
        if self.brand_slug and (project_slug or attached_products or attached_templates):
            builder = HierarchicalContextBuilder(
                brand_slug=self.brand_slug,
                product_slugs=attached_products,
                project_slug=project_slug,
                attached_templates=attached_templates,
            )
            turn_context = builder.build_turn_context()

        # Build augmented message with turn context prepended
        if turn_context:
            augmented_message = f"""## Current Context

{turn_context}

---

## User Request

{raw_user_message}"""
        else:
            augmented_message = raw_user_message

        # Check budget and trim if needed (use augmented_message for accurate size)
        budget_result, trimmed_system, trimmed_skills, trimmed_history, _ = (
            self._budget_manager.check_and_trim(
                system_prompt=self._agent.instructions or "",
                skills_context=skills_context,
                history=history_text,
                user_message=augmented_message,
            )
        )

        if budget_result.trimmed:
            logger.warning(f"Context trimmed: {budget_result.warning_message}")

        if budget_result.is_over_budget:
            logger.error(
                f"CRITICAL: Still over budget after trimming: "
                f"{budget_result.total_tokens}/{budget_result.budget_limit} tokens. "
                f"Consider reducing system prompt size."
            )

        # Log severe warning if system prompt was trimmed (would need agent rebuild)
        if "trimmed system prompt" in (budget_result.warning_message or ""):
            logger.error(
                "System prompt was trimmed! This indicates the base prompt is too large. "
                "Consider reducing prompt size or brand context."
            )

        # Build prompt with trimmed parts (but NOT trimmed_system - would require Agent rebuild)
        prompt_parts = []

        if trimmed_skills:
            prompt_parts.append(trimmed_skills)

        if trimmed_history:
            prompt_parts.append(trimmed_history)

        # Use augmented message (with turn context) for LLM
        prompt_parts.append(f"User: {augmented_message}")
        full_prompt = "\n\n".join(prompt_parts)
        #Set up tool progress callback for emit_tool_thinking
        from sip_videogen.advisor.tools import set_tool_progress_callback
        def _tool_cb(step:str,detail:str)->None:
            if self.progress_callback:self.progress_callback(AdvisorProgress(event_type="thinking_step",message=step,detail=detail))
        set_tool_progress_callback(_tool_cb)
        # Accumulate response for history
        response_chunks: list[str] = []

        try:
            # Use streaming runner
            async for chunk in Runner.run_streamed(self._agent, full_prompt, hooks=hooks):
                if hasattr(chunk, "text") and chunk.text:
                    response_chunks.append(chunk.text)
                    yield chunk.text

            # Update history with RAW message (not augmented)
            # This prevents history from ballooning with repeated context
            full_response = "".join(response_chunks)
            self._history_manager.add("user", raw_user_message)
            self._history_manager.add("assistant", full_response)

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
