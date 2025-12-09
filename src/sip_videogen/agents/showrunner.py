"""Showrunner orchestrator agent for coordinating script development.

This agent is the main orchestrator that coordinates the other specialist agents
(Screenwriter, Production Designer, Continuity Supervisor) to transform a user's
idea into a complete VideoScript ready for production.

The Showrunner uses the agent-as-tool pattern where each specialist agent is
invoked as a tool to perform its specialized function.
"""

from pathlib import Path

from agents import Agent, Runner

from sip_videogen.agents.continuity_supervisor import continuity_supervisor_agent
from sip_videogen.agents.production_designer import production_designer_agent
from sip_videogen.agents.screenwriter import screenwriter_agent
from sip_videogen.models.agent_outputs import ShowrunnerOutput
from sip_videogen.models.script import VideoScript

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


async def develop_script(idea: str, num_scenes: int) -> VideoScript:
    """Develop a complete video script from a creative idea.

    This is the main entry point for script development. The Showrunner
    orchestrates the specialist agents to transform the user's idea into
    a complete VideoScript ready for image and video generation.

    Args:
        idea: The user's creative idea or concept.
        num_scenes: Target number of scenes to produce (3-5 recommended).

    Returns:
        A complete VideoScript ready for production, with shared elements
        identified and prompts optimized for AI generation.
    """
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

    result = await Runner.run(showrunner_agent, prompt)
    output = result.final_output

    # Return the VideoScript from the output
    if isinstance(output, ShowrunnerOutput):
        return output.script
    # Handle case where output is already a VideoScript (shouldn't happen but be safe)
    if isinstance(output, VideoScript):
        return output
    # If somehow we get neither, raise an error
    raise TypeError(f"Unexpected output type from showrunner: {type(output)}")
