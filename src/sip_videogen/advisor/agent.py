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

from sip_videogen.advisor.skills.registry import get_skills_registry
from sip_videogen.advisor.tools import ADVISOR_TOOLS
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
    """Progress update from the advisor agent."""

    event_type: str  # "thinking", "tool_start", "tool_end", "response"
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
        )

        tool_name = tool.name

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

        # Track conversation history for context
        self._conversation_history: list[dict] = []

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
            self._conversation_history = []
            logger.debug("Conversation history cleared on brand switch")

        # Rebuild system prompt with new brand context
        self._agent = Agent(
            name="Brand Marketing Advisor",
            model="gpt-5.1",
            instructions=_build_system_prompt(slug),
            tools=ADVISOR_TOOLS,
        )

        logger.info(f"Switched to brand: {slug}")

    async def chat_with_metadata(self, message: str) -> dict:
        """Send a message and get a response plus UI metadata."""
        hooks = AdvisorHooks(callback=self.progress_callback)

        # Find relevant skills and inject their instructions
        skills_context = self._get_relevant_skills_context(message)

        # Build prompt with conversation history and skills
        prompt_parts = []

        if skills_context:
            prompt_parts.append(skills_context)

        if self._conversation_history:
            context_messages = self._format_history()
            prompt_parts.append(context_messages)

        prompt_parts.append(f"User: {message}")
        full_prompt = "\n\n".join(prompt_parts)

        try:
            result = await Runner.run(self._agent, full_prompt, hooks=hooks)

            # Extract response text
            response = result.final_output
            if hasattr(response, "text"):
                response_text = response.text
            else:
                response_text = str(response)

            # Update conversation history
            self._conversation_history.append({"role": "user", "content": message})
            self._conversation_history.append({"role": "assistant", "content": response_text})

            # Keep history manageable (last 20 turns)
            if len(self._conversation_history) > 40:
                self._conversation_history = self._conversation_history[-40:]

            return {
                "response": response_text,
                "interaction": hooks.captured_interaction,
                "memory_update": hooks.captured_memory_update,
            }

        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise

    async def chat(self, message: str) -> str:
        """Send a message and get a response."""
        result = await self.chat_with_metadata(message)
        return result["response"]

    async def chat_stream(self, message: str) -> AsyncIterator[str]:
        """Send a message and stream the response.

        Args:
            message: User message to process.

        Yields:
            Response text chunks as they're generated.
        """
        hooks = AdvisorHooks(callback=self.progress_callback)

        # Find relevant skills and inject their instructions
        skills_context = self._get_relevant_skills_context(message)

        # Build prompt with conversation history and skills
        prompt_parts = []

        if skills_context:
            prompt_parts.append(skills_context)

        if self._conversation_history:
            context_messages = self._format_history()
            prompt_parts.append(context_messages)

        prompt_parts.append(f"User: {message}")
        full_prompt = "\n\n".join(prompt_parts)

        # Accumulate response for history
        response_chunks: list[str] = []

        try:
            # Use streaming runner
            async for chunk in Runner.run_streamed(self._agent, full_prompt, hooks=hooks):
                if hasattr(chunk, "text") and chunk.text:
                    response_chunks.append(chunk.text)
                    yield chunk.text

            # Update history after stream completes
            full_response = "".join(response_chunks)
            self._conversation_history.append({"role": "user", "content": message})
            self._conversation_history.append({"role": "assistant", "content": full_response})

            # Keep history manageable
            if len(self._conversation_history) > 40:
                self._conversation_history = self._conversation_history[-40:]

        except Exception as e:
            logger.error(f"Stream chat failed: {e}")
            raise

    def _format_history(self) -> str:
        """Format conversation history for context."""
        lines = []
        for msg in self._conversation_history[-10:]:  # Last 5 turns
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:500]  # Truncate long messages
            lines.append(f"{role}: {content}")
        return "\n\n".join(lines)

    def _get_relevant_skills_context(self, message: str, max_skills: int = 2) -> str:
        """Find and format relevant skill instructions for the message.

        Args:
            message: User message to match against skill triggers.
            max_skills: Maximum number of skills to include (to limit context size).

        Returns:
            Formatted skill instructions, or empty string if no matches.
        """
        skills_registry = get_skills_registry()
        relevant_skills = skills_registry.find_relevant_skills(message)

        if not relevant_skills:
            return ""

        # Limit to max_skills
        skills_to_use = relevant_skills[:max_skills]

        parts = ["## Relevant Skill Instructions\n"]
        parts.append(
            "The following skills are relevant to this request. Follow their guidelines:\n"
        )

        for skill in skills_to_use:
            parts.append(f"### {skill.name}\n")
            parts.append(skill.instructions)
            parts.append("")

        return "\n".join(parts)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history = []
        logger.debug("Conversation history cleared")


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
