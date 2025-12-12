"""Brand Director orchestrator agent for coordinating brand development.

This agent is the main orchestrator that coordinates the brand specialist agents
(Brand Strategist, Visual Designer, Brand Voice Writer, Brand Guardian) to
transform a user's concept into a complete BrandIdentityFull ready for
asset generation.

The Brand Director uses the agent-as-tool pattern where each specialist agent is
invoked as a tool to perform its specialized function.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from agents import Agent, RunHooks, Runner, Tool
from agents.exceptions import AgentsException
from agents.run_context import RunContextWrapper
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from sip_videogen.agents.brand_guardian import brand_guardian_agent
from sip_videogen.agents.brand_strategist import brand_strategist_agent
from sip_videogen.agents.brand_voice import brand_voice_agent
from sip_videogen.agents.visual_designer import visual_designer_agent
from sip_videogen.brands.models import BrandIdentityFull
from sip_videogen.brands.tools import browse_brand_assets, fetch_brand_detail
from sip_videogen.config.logging import get_logger
from sip_videogen.models.brand_agent_outputs import BrandDirectorOutput

logger = get_logger(__name__)


@dataclass
class BrandAgentProgress:
    """Progress update from brand agent orchestration."""

    event_type: str  # "agent_start", "agent_end", "tool_start", "tool_end", "thinking"
    agent_name: str
    message: str
    detail: str = ""


# Type alias for progress callback
BrandProgressCallback = Callable[[BrandAgentProgress], None]


class BrandProgressTrackingHooks(RunHooks):
    """Hooks for tracking brand agent progress and reporting to callback."""

    def __init__(self, callback: BrandProgressCallback | None = None):
        self.callback = callback
        self._tool_descriptions = {
            "brand_strategist": "Developing brand strategy and positioning",
            "visual_designer": "Creating visual identity and design system",
            "brand_voice": "Establishing brand voice and messaging",
            "brand_guardian": "Validating brand consistency",
            "fetch_brand_detail": "Retrieving brand information",
            "browse_brand_assets": "Exploring existing brand assets",
        }

    def _report(self, progress: BrandAgentProgress) -> None:
        """Report progress to callback if set."""
        if self.callback:
            self.callback(progress)
        logger.debug(f"[{progress.event_type}] {progress.agent_name}: {progress.message}")

    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        """Called when an agent starts processing."""
        self._report(
            BrandAgentProgress(
                event_type="agent_start",
                agent_name=agent.name,
                message=f"{agent.name} is analyzing the brand concept...",
            )
        )

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output) -> None:
        """Called when an agent finishes processing."""
        self._report(
            BrandAgentProgress(
                event_type="agent_end",
                agent_name=agent.name,
                message=f"{agent.name} completed",
            )
        )

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        """Called when an agent starts using a tool (calling another agent)."""
        tool_name = tool.name
        description = self._tool_descriptions.get(tool_name, f"Running {tool_name}")
        self._report(
            BrandAgentProgress(
                event_type="tool_start",
                agent_name=agent.name,
                message=f"Delegating to {tool_name.replace('_', ' ').title()}",
                detail=description,
            )
        )

    async def on_tool_end(
        self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str
    ) -> None:
        """Called when a tool call completes."""
        tool_name = tool.name
        # Truncate result for display
        result_preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        self._report(
            BrandAgentProgress(
                event_type="tool_end",
                agent_name=agent.name,
                message=f"{tool_name.replace('_', ' ').title()} finished",
                detail=result_preview,
            )
        )

    async def on_llm_start(self, context: RunContextWrapper, agent: Agent, *args, **kwargs) -> None:
        """Called when the LLM starts generating."""
        self._report(
            BrandAgentProgress(
                event_type="thinking",
                agent_name=agent.name,
                message=f"{agent.name} is thinking...",
            )
        )


# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_BRAND_DIRECTOR_PROMPT_PATH = _PROMPTS_DIR / "brand_director.md"


def _load_prompt() -> str:
    """Load the brand director prompt from the markdown file."""
    if _BRAND_DIRECTOR_PROMPT_PATH.exists():
        return _BRAND_DIRECTOR_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are a senior brand director who orchestrates brand development.

Your job is to coordinate the brand development process:
1. Call the brand strategist to develop the strategic foundation
2. Call the visual designer to create the visual identity
3. Call the brand voice writer to establish voice guidelines
4. Call the brand guardian to validate consistency
5. Synthesize everything into a final BrandIdentityFull

You have full creative authority to make decisions that create distinctive,
cohesive brands that resonate with target audiences.
"""


# Create the brand director orchestrator agent with specialist agents as tools
brand_director_agent = Agent(
    name="Brand Director",
    instructions=_load_prompt(),
    tools=[
        brand_strategist_agent.as_tool(
            tool_name="brand_strategist",
            tool_description=(
                "Develops brand strategy including core identity (name, tagline, mission, "
                "story, values), target audience profile, and market positioning. "
                "Call FIRST to establish the strategic foundation."
            ),
        ),
        visual_designer_agent.as_tool(
            tool_name="visual_designer",
            tool_description=(
                "Creates the visual identity including color palette, typography system, "
                "imagery direction, and logo brief. Call AFTER brand_strategist with "
                "the strategy context."
            ),
        ),
        brand_voice_agent.as_tool(
            tool_name="brand_voice",
            tool_description=(
                "Develops brand voice guidelines including personality, tone attributes, "
                "messaging do's/don'ts, and sample copy. Call AFTER brand_strategist with "
                "the strategy context."
            ),
        ),
        brand_guardian_agent.as_tool(
            tool_name="brand_guardian",
            tool_description=(
                "Validates brand consistency across strategy, visuals, and voice. "
                "Returns validation status, issues list, and consistency score. "
                "Call LAST before finalizing to ensure quality."
            ),
        ),
        fetch_brand_detail,
        browse_brand_assets,
    ],
    output_type=BrandDirectorOutput,
)


class BrandDevelopmentError(Exception):
    """Raised when brand development fails."""

    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((AgentsException, TimeoutError, ConnectionError)),
    reraise=True,
)
async def develop_brand(
    concept: str,
    existing_brand_slug: str | None = None,
    progress_callback: BrandProgressCallback | None = None,
) -> BrandIdentityFull:
    """Develop a complete brand identity from a concept.

    This is the main entry point for brand development. The Brand Director
    orchestrates the specialist agents to transform the user's concept into
    a complete BrandIdentityFull ready for asset generation.

    Args:
        concept: The user's brand concept or idea.
        existing_brand_slug: If evolving an existing brand, provide its slug.
            The Brand Director will use memory tools to understand the current
            brand state and evolve it appropriately.
        progress_callback: Optional callback for real-time progress updates.

    Returns:
        A complete BrandIdentityFull ready for asset generation.

    Raises:
        BrandDevelopmentError: If brand development fails after retries.
        ValueError: If input validation fails.
    """
    from sip_videogen.brands.context import build_brand_context
    from sip_videogen.brands.tools import set_brand_context

    # Validate inputs
    if not concept or not concept.strip():
        raise ValueError("Brand concept cannot be empty")
    if len(concept) > 5000:
        raise ValueError("Brand concept is too long (max 5000 characters)")

    concept = concept.strip()
    logger.info(
        f"Starting brand development: '{concept[:50]}...' "
        f"(existing: {existing_brand_slug or 'none'})"
    )

    # Set up brand context for memory tools
    if existing_brand_slug:
        set_brand_context(existing_brand_slug)
        brand_context = build_brand_context(existing_brand_slug)
        context_section = f"""## Existing Brand Context

You are EVOLVING an existing brand, not creating from scratch.
Use the memory tools to understand the current brand state before making changes.

{brand_context}

---

"""
        task_description = (
            "evolve this existing brand based on the concept. "
            "Respect established elements while implementing requested changes."
        )
    else:
        set_brand_context(None)
        context_section = """## New Brand Creation

You are creating a NEW brand from scratch. Be bold and distinctive.

---

"""
        task_description = "create a complete brand identity from this concept."

    prompt = f"""{context_section}## Brand Concept

{concept}

---

## Your Task

{task_description.capitalize()}

Follow your process:
1. Call the brand_strategist to develop the strategic foundation
2. Call the visual_designer with the strategy to create visual identity
3. Call the brand_voice with the strategy to establish voice guidelines
4. Call the brand_guardian to validate all work for consistency
5. Assemble the final BrandIdentityFull from all specialist outputs

Requirements:
- All specialist work must be coordinated and consistent
- Visual identity must reflect the brand strategy
- Voice guidelines must resonate with the target audience
- Brand Guardian must validate with no errors before finalizing
- Include meaningful creative_rationale explaining key decisions
- Provide actionable next_steps for the client

Remember: You are the orchestrator. Delegate to specialists, don't do their work yourself.
"""

    # Create progress tracking hooks
    hooks = BrandProgressTrackingHooks(callback=progress_callback)

    try:
        result = await Runner.run(brand_director_agent, prompt, hooks=hooks)
        output = result.final_output

        # Return the BrandIdentityFull from the output
        if isinstance(output, BrandDirectorOutput):
            logger.info(
                f"Brand development complete: '{output.brand_identity.core.name}' "
                f"(validation: {'passed' if output.validation_passed else 'issues found'})"
            )
            return output.brand_identity
        # Handle case where output is already a BrandIdentityFull
        if isinstance(output, BrandIdentityFull):
            logger.info(f"Brand development complete: '{output.core.name}'")
            return output
        # If somehow we get neither, raise an error
        raise BrandDevelopmentError(
            f"Unexpected output type from Brand Director: {type(output).__name__}. "
            "Expected BrandDirectorOutput or BrandIdentityFull."
        )
    except AgentsException as e:
        logger.error(f"Brand agent orchestration failed: {e}")
        raise BrandDevelopmentError(
            f"Brand development failed: {e}. Please check your OpenAI API key and try again."
        ) from e
    except Exception as e:
        if isinstance(e, (ValueError, BrandDevelopmentError)):
            raise
        logger.error(f"Unexpected error during brand development: {e}")
        raise BrandDevelopmentError(f"Brand development failed unexpectedly: {e}") from e


async def develop_brand_with_output(
    concept: str,
    existing_brand_slug: str | None = None,
    progress_callback: BrandProgressCallback | None = None,
) -> BrandDirectorOutput:
    """Develop a brand and return the full director output.

    This variant returns the complete BrandDirectorOutput including
    creative_rationale, validation_passed status, and next_steps,
    in addition to the brand identity.

    Args:
        concept: The user's brand concept or idea.
        existing_brand_slug: If evolving an existing brand, provide its slug.
        progress_callback: Optional callback for real-time progress updates.

    Returns:
        Complete BrandDirectorOutput with identity, rationale, and recommendations.

    Raises:
        BrandDevelopmentError: If brand development fails.
        ValueError: If input validation fails.
    """
    from sip_videogen.brands.context import build_brand_context
    from sip_videogen.brands.tools import set_brand_context

    # Validate inputs
    if not concept or not concept.strip():
        raise ValueError("Brand concept cannot be empty")
    if len(concept) > 5000:
        raise ValueError("Brand concept is too long (max 5000 characters)")

    concept = concept.strip()
    logger.info(
        f"Starting brand development (full output): '{concept[:50]}...' "
        f"(existing: {existing_brand_slug or 'none'})"
    )

    # Set up brand context for memory tools
    if existing_brand_slug:
        set_brand_context(existing_brand_slug)
        brand_context = build_brand_context(existing_brand_slug)
        context_section = f"""## Existing Brand Context

You are EVOLVING an existing brand, not creating from scratch.

{brand_context}

---

"""
        task_description = "evolve this existing brand"
    else:
        set_brand_context(None)
        context_section = ""
        task_description = "create a complete brand identity"

    prompt = f"""{context_section}## Brand Concept

{concept}

---

## Your Task

{task_description.capitalize()} from this concept.

Follow your process:
1. Call the brand_strategist to develop the strategic foundation
2. Call the visual_designer with the strategy to create visual identity
3. Call the brand_voice with the strategy to establish voice guidelines
4. Call the brand_guardian to validate all work for consistency
5. Assemble the final BrandIdentityFull from all specialist outputs

Requirements:
- All specialist work must be coordinated and consistent
- Brand Guardian must validate before finalizing
- Include meaningful creative_rationale
- Provide actionable next_steps
"""

    hooks = BrandProgressTrackingHooks(callback=progress_callback)

    try:
        result = await Runner.run(brand_director_agent, prompt, hooks=hooks)
        output = result.final_output

        if isinstance(output, BrandDirectorOutput):
            logger.info(f"Brand development complete: '{output.brand_identity.core.name}'")
            return output

        raise BrandDevelopmentError(
            f"Unexpected output type: {type(output).__name__}. Expected BrandDirectorOutput."
        )
    except AgentsException as e:
        logger.error(f"Brand development failed: {e}")
        raise BrandDevelopmentError(f"Brand development failed: {e}") from e
    except Exception as e:
        if isinstance(e, (ValueError, BrandDevelopmentError)):
            raise
        logger.error(f"Unexpected error: {e}")
        raise BrandDevelopmentError(f"Brand development failed: {e}") from e
