"""Showrunner orchestrator agent for coordinating script development.

This agent is the main orchestrator that coordinates the other specialist agents
(Screenwriter, Production Designer, Continuity Supervisor) to transform a user's
idea into a complete VideoScript ready for production.

The Showrunner uses the agent-as-tool pattern where each specialist agent is
invoked as a tool to perform its specialized function.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from agents import Agent, Runner, RunHooks, Tool
from agents.exceptions import AgentsException
from agents.run_context import RunContextWrapper
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from sip_videogen.agents.continuity_supervisor import continuity_supervisor_agent
from sip_videogen.agents.production_designer import production_designer_agent
from sip_videogen.agents.screenwriter import screenwriter_agent
from sip_videogen.config.logging import get_logger
from sip_videogen.models.agent_outputs import ShowrunnerOutput
from sip_videogen.models.script import VideoScript

logger = get_logger(__name__)


@dataclass
class AgentProgress:
    """Progress update from agent orchestration."""
    event_type: str  # "agent_start", "agent_end", "tool_start", "tool_end", "thinking"
    agent_name: str
    message: str
    detail: str = ""


# Type alias for progress callback
ProgressCallback = Callable[[AgentProgress], None]


class ProgressTrackingHooks(RunHooks):
    """Hooks for tracking agent progress and reporting to callback."""

    def __init__(self, callback: ProgressCallback | None = None):
        self.callback = callback
        self._tool_descriptions = {
            "screenwriter": "Writing scene breakdown and dialogue",
            "production_designer": "Identifying visual elements for consistency",
            "continuity_supervisor": "Validating continuity and optimizing prompts",
        }

    def _report(self, progress: AgentProgress) -> None:
        """Report progress to callback if set."""
        if self.callback:
            self.callback(progress)
        logger.debug(f"[{progress.event_type}] {progress.agent_name}: {progress.message}")

    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        """Called when an agent starts processing."""
        self._report(AgentProgress(
            event_type="agent_start",
            agent_name=agent.name,
            message=f"{agent.name} is analyzing the task...",
        ))

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output) -> None:
        """Called when an agent finishes processing."""
        self._report(AgentProgress(
            event_type="agent_end",
            agent_name=agent.name,
            message=f"{agent.name} completed",
        ))

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        """Called when an agent starts using a tool (calling another agent)."""
        tool_name = tool.name
        description = self._tool_descriptions.get(tool_name, f"Running {tool_name}")
        self._report(AgentProgress(
            event_type="tool_start",
            agent_name=agent.name,
            message=f"Delegating to {tool_name.replace('_', ' ').title()}",
            detail=description,
        ))

    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
        """Called when a tool call completes."""
        tool_name = tool.name
        # Truncate result for display
        result_preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        self._report(AgentProgress(
            event_type="tool_end",
            agent_name=agent.name,
            message=f"{tool_name.replace('_', ' ').title()} finished",
            detail=result_preview,
        ))

    async def on_llm_start(self, context: RunContextWrapper, agent: Agent, *args, **kwargs) -> None:
        """Called when the LLM starts generating."""
        self._report(AgentProgress(
            event_type="thinking",
            agent_name=agent.name,
            message=f"{agent.name} is thinking...",
        ))

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_SHOWRUNNER_PROMPT_PATH = _PROMPTS_DIR / "showrunner.md"


def _load_prompt() -> str:
    """Load the showrunner prompt from the markdown file."""
    if _SHOWRUNNER_PROMPT_PATH.exists():
        return _SHOWRUNNER_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are an experienced showrunner with creative control over short-form video production.

Your job is to orchestrate the script development process:
1. Interpret the user's idea into a creative vision
2. Call the screenwriter to develop the scene breakdown
3. Call the production designer to identify shared visual elements
4. Call the continuity supervisor to validate consistency and optimize prompts
5. Synthesize everything into a final VideoScript ready for production

You have full creative authority to make decisions that serve the story while
ensuring technical feasibility for AI video generation.
"""


# Create the showrunner orchestrator agent with specialist agents as tools
showrunner_agent = Agent(
    name="Showrunner",
    instructions=_load_prompt(),
    tools=[
        screenwriter_agent.as_tool(
            tool_name="screenwriter",
            tool_description="Develops scene breakdown with narrative arc, action descriptions, dialogue, and timing. Give it the creative brief and number of scenes needed.",
        ),
        production_designer_agent.as_tool(
            tool_name="production_designer",
            tool_description="Analyzes scenes to identify shared visual elements (characters, props, environments) that need consistency. Pass it the scenes from the screenwriter.",
        ),
        continuity_supervisor_agent.as_tool(
            tool_name="continuity_supervisor",
            tool_description="Validates consistency across scenes and shared elements, optimizes prompts for AI generation. Pass it the scenes, shared elements, title, logline, and tone.",
        ),
    ],
    output_type=ShowrunnerOutput,
)


class ScriptDevelopmentError(Exception):
    """Raised when script development fails."""

    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((AgentsException, TimeoutError, ConnectionError)),
    reraise=True,
)
async def develop_script(
    idea: str,
    num_scenes: int,
    progress_callback: ProgressCallback | None = None,
) -> VideoScript:
    """Develop a complete video script from a creative idea.

    This is the main entry point for script development. The Showrunner
    orchestrates the specialist agents to transform the user's idea into
    a complete VideoScript ready for image and video generation.

    Args:
        idea: The user's creative idea or concept.
        num_scenes: Target number of scenes to produce (3-5 recommended).
        progress_callback: Optional callback for real-time progress updates.

    Returns:
        A complete VideoScript ready for production, with shared elements
        identified and prompts optimized for AI generation.

    Raises:
        ScriptDevelopmentError: If script development fails after retries.
        ValueError: If input validation fails.
    """
    # Validate inputs
    if not idea or not idea.strip():
        raise ValueError("Idea cannot be empty")
    if len(idea) > 2000:
        raise ValueError("Idea is too long (max 2000 characters)")
    if num_scenes < 1 or num_scenes > 10:
        raise ValueError("Number of scenes must be between 1 and 10")

    idea = idea.strip()
    logger.info(f"Starting script development: '{idea[:50]}...' with {num_scenes} scenes")

    prompt = f"""Create a {num_scenes}-scene video from this idea:

{idea}

Follow this process:
1. First, call the screenwriter to develop {num_scenes} scenes with a clear narrative arc
2. Then, call the production designer to identify all shared visual elements from those scenes
3. Finally, call the continuity supervisor to validate everything and optimize for AI generation

Requirements:
- The final video should be {num_scenes} scenes, each 4-8 seconds
- Create a compelling narrative with beginning, middle, and end
- Ensure visual consistency by identifying recurring elements
- Optimize all descriptions for AI video generation
- The final output must include a title, logline, and tone

Be creative and make bold artistic choices that will result in an engaging video.
"""

    # Create progress tracking hooks
    hooks = ProgressTrackingHooks(callback=progress_callback)

    try:
        result = await Runner.run(showrunner_agent, prompt, hooks=hooks)
        output = result.final_output

        # Return the VideoScript from the output
        if isinstance(output, ShowrunnerOutput):
            logger.info(f"Script development complete: '{output.script.title}'")
            return output.script
        # Handle case where output is already a VideoScript (shouldn't happen but be safe)
        if isinstance(output, VideoScript):
            logger.info(f"Script development complete: '{output.title}'")
            return output
        # If somehow we get neither, raise an error
        raise ScriptDevelopmentError(
            f"Unexpected output type from showrunner: {type(output).__name__}. "
            "Expected ShowrunnerOutput or VideoScript."
        )
    except AgentsException as e:
        logger.error(f"Agent orchestration failed: {e}")
        raise ScriptDevelopmentError(
            f"Script development failed: {e}. "
            "Please check your OpenAI API key and try again."
        ) from e
    except Exception as e:
        if isinstance(e, (ValueError, ScriptDevelopmentError)):
            raise
        logger.error(f"Unexpected error during script development: {e}")
        raise ScriptDevelopmentError(
            f"Script development failed unexpectedly: {e}"
        ) from e
