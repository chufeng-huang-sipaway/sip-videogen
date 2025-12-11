"""Showrunner orchestrator agent for coordinating script development.

This agent is the main orchestrator that coordinates the other specialist agents
(Screenwriter, Production Designer, Continuity Supervisor) to transform a user's
idea into a complete VideoScript ready for production.

The Showrunner uses the agent-as-tool pattern where each specialist agent is
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

from sip_videogen.agents.continuity_supervisor import continuity_supervisor_agent
from sip_videogen.agents.music_director import music_director_agent
from sip_videogen.agents.production_designer import production_designer_agent
from sip_videogen.agents.screenwriter import screenwriter_agent
from sip_videogen.config.logging import get_logger
from sip_videogen.models.agent_outputs import DirectorsPitch, ShowrunnerOutput
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
            "music_director": "Designing background music style for the video",
        }

    def _report(self, progress: AgentProgress) -> None:
        """Report progress to callback if set."""
        if self.callback:
            self.callback(progress)
        logger.debug(f"[{progress.event_type}] {progress.agent_name}: {progress.message}")

    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        """Called when an agent starts processing."""
        self._report(
            AgentProgress(
                event_type="agent_start",
                agent_name=agent.name,
                message=f"{agent.name} is analyzing the task...",
            )
        )

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output) -> None:
        """Called when an agent finishes processing."""
        self._report(
            AgentProgress(
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
            AgentProgress(
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
            AgentProgress(
                event_type="tool_end",
                agent_name=agent.name,
                message=f"{tool_name.replace('_', ' ').title()} finished",
                detail=result_preview,
            )
        )

    async def on_llm_start(self, context: RunContextWrapper, agent: Agent, *args, **kwargs) -> None:
        """Called when the LLM starts generating."""
        self._report(
            AgentProgress(
                event_type="thinking",
                agent_name=agent.name,
                message=f"{agent.name} is thinking...",
            )
        )


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
        music_director_agent.as_tool(
            tool_name="music_director",
            tool_description="Analyzes the finalized script and designs background music style. Call AFTER continuity_supervisor, passing the complete script with title, logline, tone, and scenes.",
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

    prompt = f"""Create a video from this idea, targeting approximately {num_scenes} scenes:

{idea}

FIRST: Define a cohesive visual_style for the entire video. This is REQUIRED and must include:
- Color palette (warm golden, cool blue, muted pastels, high contrast, etc.)
- Lighting style (natural soft light, dramatic shadows, golden hour, neon-lit, etc.)
- Camera aesthetic (cinematic shallow DoF, documentary handheld, smooth tracking, etc.)
- Visual treatment (photorealistic, dreamlike, stylized, vintage film, clean modern, etc.)

This visual_style will be included in every video prompt to ensure cohesive clips.

SECOND: Select a clip_pattern for each scene to control pacing. VEO generates fixed 8-second clips.
Patterns allow multiple shots within each clip without splitting shots across clips.

Valid patterns (durations in seconds):
- [8] = single continuous shot (smooth, flowing)
- [6, 2] = long + quick (build to punctuation)
- [2, 6] = quick + long (hook then develop)
- [4, 4] = two equal (balanced rhythm)
- [4, 2, 2] = medium + two quick (building intensity)
- [2, 4, 2] = quick + medium + quick (sandwich rhythm)
- [2, 2, 4] = two quick + medium (quick start, resolve)
- [2, 2, 2, 2] = four quick (high energy, montage)

Example pattern sequence for a 4-scene video:
- Scene 1: [8] - smooth establishing
- Scene 2: [4, 4] - action-reaction
- Scene 3: [2, 2, 2, 2] - fast-paced climax
- Scene 4: [6, 2] - resolution with final beat

Then follow this process:
1. Call the screenwriter with the creative brief, scene count, AND clip patterns for each scene
2. Call the production designer to identify all shared visual elements from those scenes
3. Call the continuity supervisor to validate everything and optimize for AI generation
4. Call the music director to design background music style

Requirements:
- Target {num_scenes} scenes, but you may add 1-2 more if needed to keep actions simple
- Each scene MUST have a valid clip_pattern from the list above
- When pattern is not [8], screenwriter must create matching sub_shots
- Each scene should focus on ONE simple action (no complex multi-step actions)
- Scene durations: always 8 seconds (VEO constraint with reference images)
- Create a compelling narrative with beginning, middle, and end
- Ensure visual consistency by identifying recurring elements
- Optimize all descriptions for AI video generation
- The final output must include title, logline, tone, AND visual_style
- ALL scenes must pass complexity validation (no HIGH complexity allowed)
- Use optional visual_notes on specific scenes only when they need adjustments from the global style

Remember: Simple scenes with one clear action produce much better AI video than complex
scenes with multiple actions. When in doubt, split a complex scene into two simpler ones.
"""

    # Create progress tracking hooks
    hooks = ProgressTrackingHooks(callback=progress_callback)

    try:
        result = await Runner.run(showrunner_agent, prompt, hooks=hooks)
        output = result.final_output

        # Return the VideoScript from the output
        if isinstance(output, ShowrunnerOutput):
            logger.info(f"Script development complete: '{output.script.title}'")
            # Transfer music_brief to the script if present
            if output.music_brief and output.script.music_brief is None:
                output.script.music_brief = output.music_brief
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
            f"Script development failed: {e}. Please check your OpenAI API key and try again."
        ) from e
    except Exception as e:
        if isinstance(e, (ValueError, ScriptDevelopmentError)):
            raise
        logger.error(f"Unexpected error during script development: {e}")
        raise ScriptDevelopmentError(f"Script development failed unexpectedly: {e}") from e


# Prompt for quick pitch generation
_PITCH_PROMPT = """You are a creative director who crafts compelling video pitches quickly.

Your job is to create a concise but captivating pitch that:
1. Captures the essence of the video idea
2. Sets clear creative direction
3. Gets the user excited about the concept

## Output Requirements

Provide:
- **title**: Memorable, descriptive, 2-5 words
- **logline**: One compelling sentence that sells the concept
- **tone**: 2-3 adjectives describing mood and style
- **brief_description**: 2-3 sentences outlining the narrative arc
- **key_elements**: 3-5 main visual components (characters, settings, props)
- **scene_count**: Based on target duration (duration / 8 seconds per scene)
- **estimated_duration**: The target duration provided

## Guidelines

- Be bold and creative - this is your chance to excite the user
- Think visually - what will look amazing on screen?
- Keep it concise - this is a pitch, not a script
- Consider the target duration when planning complexity

## When Revising Based on Feedback

- Incorporate specific requests directly
- Maintain coherent creative vision
- You may adjust the approach significantly if feedback warrants it
"""

# Create a lightweight pitch agent for quick proposals
pitch_agent = Agent(
    name="PitchAgent",
    instructions=_PITCH_PROMPT,
    output_type=DirectorsPitch,
)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((AgentsException, TimeoutError, ConnectionError)),
    reraise=True,
)
async def generate_directors_pitch(
    idea: str,
    target_duration: int,
    num_scenes: int,
    previous_feedback: list[str] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> DirectorsPitch:
    """Generate a quick Director's Pitch for user approval.

    This is a lightweight call that produces only the creative overview
    (title, logline, tone, description) without full scene development.

    Args:
        idea: The user's creative idea.
        target_duration: Target video duration in seconds.
        num_scenes: Calculated number of scenes.
        previous_feedback: List of previous user feedback for revision.
        progress_callback: Optional callback for progress updates.

    Returns:
        DirectorsPitch with title, logline, tone, and brief description.

    Raises:
        ScriptDevelopmentError: If pitch generation fails.
    """
    # Validate inputs
    if not idea or not idea.strip():
        raise ValueError("Idea cannot be empty")

    idea = idea.strip()
    logger.info(f"Generating Director's Pitch for: '{idea[:50]}...'")

    # Build feedback section if there's previous feedback
    feedback_section = ""
    if previous_feedback:
        feedback_section = "\n\n## Previous Feedback to Incorporate\n"
        for i, fb in enumerate(previous_feedback, 1):
            feedback_section += f"{i}. {fb}\n"
        feedback_section += "\nPlease revise the pitch based on this feedback."

    prompt = f"""Create a Director's Pitch for this video idea:

{idea}

Target duration: {target_duration} seconds (~{num_scenes} scenes at 8 seconds each)
{feedback_section}

Remember: This is a pitch for user approval, not a full script. Keep it compelling and concise.
"""

    hooks = ProgressTrackingHooks(callback=progress_callback)

    try:
        result = await Runner.run(pitch_agent, prompt, hooks=hooks)
        output = result.final_output

        if isinstance(output, DirectorsPitch):
            logger.info(f"Pitch generated: '{output.title}'")
            return output

        raise ScriptDevelopmentError(
            f"Unexpected output type from pitch agent: {type(output).__name__}"
        )
    except AgentsException as e:
        logger.error(f"Pitch generation failed: {e}")
        raise ScriptDevelopmentError(f"Pitch generation failed: {e}") from e
    except Exception as e:
        if isinstance(e, (ValueError, ScriptDevelopmentError)):
            raise
        logger.error(f"Unexpected error during pitch generation: {e}")
        raise ScriptDevelopmentError(f"Pitch generation failed: {e}") from e


async def develop_script_from_pitch(
    idea: str,
    pitch: DirectorsPitch,
    progress_callback: ProgressCallback | None = None,
) -> VideoScript:
    """Develop a full script based on an approved Director's Pitch.

    This function takes an approved pitch and develops it into a complete
    VideoScript, maintaining the creative direction from the pitch.

    Args:
        idea: The original user idea.
        pitch: The approved DirectorsPitch.
        progress_callback: Optional callback for progress updates.

    Returns:
        A complete VideoScript ready for production.

    Raises:
        ScriptDevelopmentError: If script development fails.
    """
    logger.info(f"Developing script from approved pitch: '{pitch.title}'")

    prompt = f"""Develop a complete video script based on this APPROVED Director's Pitch:

## Approved Creative Direction (MUST be maintained)
- **Title**: {pitch.title}
- **Logline**: {pitch.logline}
- **Tone**: {pitch.tone}
- **Description**: {pitch.brief_description}
- **Key Elements**: {', '.join(pitch.key_elements)}
- **Target**: {pitch.scene_count} scenes, ~{pitch.estimated_duration} seconds total

## Original Idea
{idea}

## Instructions

The pitch has been APPROVED by the user. You MUST:
1. Use the title EXACTLY as approved
2. Maintain the logline EXACTLY as approved
3. Keep the tone EXACTLY as approved
4. Include ALL key elements mentioned in the pitch
5. Match the approved scene count (within +/- 1 for technical needs)

Now develop the full script:
1. Define a cohesive visual_style that matches the tone
2. Select clip_pattern for each scene (see valid patterns below)
3. Call the screenwriter with scenes AND clip patterns
4. Call the production designer to identify shared visual elements
5. Call the continuity supervisor to validate and optimize
6. Call the music director to design background music

## Valid Clip Patterns (select one per scene)
- [8] = single continuous shot (smooth, flowing)
- [6, 2] = long + quick (build to punctuation)
- [2, 6] = quick + long (hook then develop)
- [4, 4] = two equal (balanced rhythm)
- [4, 2, 2] = medium + two quick (building intensity)
- [2, 4, 2] = quick + medium + quick (sandwich rhythm)
- [2, 2, 4] = two quick + medium (quick start, resolve)
- [2, 2, 2, 2] = four quick (high energy, montage)

Requirements:
- Each scene MUST have a valid clip_pattern
- When pattern is not [8], screenwriter must create matching sub_shots
- Each scene should focus on ONE simple action
- Scene durations: always 8 seconds (VEO constraint with reference images)
- Ensure visual consistency with identified shared elements
- ALL scenes must pass complexity validation
"""

    hooks = ProgressTrackingHooks(callback=progress_callback)

    try:
        result = await Runner.run(showrunner_agent, prompt, hooks=hooks)
        output = result.final_output

        if isinstance(output, ShowrunnerOutput):
            logger.info(f"Script development complete: '{output.script.title}'")
            if output.music_brief and output.script.music_brief is None:
                output.script.music_brief = output.music_brief
            return output.script

        if isinstance(output, VideoScript):
            logger.info(f"Script development complete: '{output.title}'")
            return output

        raise ScriptDevelopmentError(
            f"Unexpected output type: {type(output).__name__}"
        )
    except AgentsException as e:
        logger.error(f"Script development from pitch failed: {e}")
        raise ScriptDevelopmentError(f"Script development failed: {e}") from e
    except Exception as e:
        if isinstance(e, (ValueError, ScriptDevelopmentError)):
            raise
        logger.error(f"Unexpected error during script development: {e}")
        raise ScriptDevelopmentError(f"Script development failed: {e}") from e
