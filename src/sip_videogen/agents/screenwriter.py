"""Screenwriter agent for scene breakdown and narrative development.

This agent takes a creative brief and produces a structured scene breakdown
with clear narrative arc, visual action descriptions, and timing.
"""

from pathlib import Path

from agents import Agent

from sip_videogen.models.agent_outputs import ScreenwriterOutput

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_SCREENWRITER_PROMPT_PATH = _PROMPTS_DIR / "screenwriter.md"


def _load_prompt() -> str:
    """Load the screenwriter prompt from the markdown file."""
    if _SCREENWRITER_PROMPT_PATH.exists():
        return _SCREENWRITER_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are a professional screenwriter specializing in short-form video content.
Given a creative brief, produce:
1. Scene breakdown with clear narrative arc
2. Action descriptions (concrete, visual, suitable for AI video generation)
3. Dialogue if applicable
4. Duration per scene (4, 6, or 8 seconds)

Emphasize clear, visual descriptions. Each scene should be 4-8 seconds.
"""


# Create the screenwriter agent
screenwriter_agent = Agent(
    name="Screenwriter",
    instructions=_load_prompt(),
    output_type=ScreenwriterOutput,
)


async def develop_scenes(idea: str, num_scenes: int) -> ScreenwriterOutput:
    """Develop a scene breakdown from a creative idea.

    Args:
        idea: The user's creative idea or concept.
        num_scenes: Target number of scenes to produce.

    Returns:
        ScreenwriterOutput containing the scene breakdown and narrative notes.
    """
    from agents import Runner

    # Calculate middle scene range for flow instructions
    middle_end = num_scenes - 1 if num_scenes > 2 else num_scenes

    prompt = f"""Create a {num_scenes}-scene video from this idea:

{idea}

Requirements:
- Produce exactly {num_scenes} scenes
- Each scene should be 4-8 seconds
- Create a clear narrative arc with beginning, middle, and end
- Write concrete, visual action descriptions suitable for AI video generation
- Include camera directions where helpful
- Add dialogue only when it enhances the story

**CRITICAL - Scene Flow Requirements:**
These scenes will be generated as separate video clips and assembled together.
To avoid awkward pauses between clips:
- Scene 1 may open naturally but MUST end with action in progress
- Scenes 2-{middle_end} MUST begin AND end mid-action (no pauses at either end)
- Scene {num_scenes} MUST begin mid-action (natural conclusion is allowed)
- NO scene should end with characters pausing, looking at camera, or creating a sense of finality (except scene {num_scenes})
- Think of all scenes as segments of ONE continuous video, not separate clips
"""

    result = await Runner.run(screenwriter_agent, prompt)
    return result.final_output
