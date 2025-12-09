"""Production Designer agent for identifying shared visual elements.

This agent analyzes scenes to identify recurring visual elements (characters,
props, environments) that need consistency across scenes, and creates detailed
visual specifications for reference image generation.
"""

from pathlib import Path

from agents import Agent

from sip_videogen.models.agent_outputs import ProductionDesignerOutput
from sip_videogen.models.script import SceneAction

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_PRODUCTION_DESIGNER_PROMPT_PATH = _PROMPTS_DIR / "production_designer.md"


def _load_prompt() -> str:
    """Load the production designer prompt from the markdown file."""
    if _PRODUCTION_DESIGNER_PROMPT_PATH.exists():
        return _PRODUCTION_DESIGNER_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are a production designer specializing in visual consistency for AI-generated video.
Your job is to:
1. Analyze scenes to identify recurring visual elements
2. Create detailed visual specifications for each shared element
3. Distinguish between shared elements (need reference images) and unique elements
4. Track which scenes each element appears in

Focus on elements that appear in multiple scenes and need visual consistency.
"""


# Create the production designer agent
production_designer_agent = Agent(
    name="Production Designer",
    instructions=_load_prompt(),
    output_type=ProductionDesignerOutput,
)


async def identify_shared_elements(scenes: list[SceneAction]) -> ProductionDesignerOutput:
    """Identify shared visual elements from a list of scenes.

    Analyzes the provided scenes to find recurring characters, props, and
    environments that need visual consistency, and creates detailed
    specifications for reference image generation.

    Args:
        scenes: List of scene actions to analyze.

    Returns:
        ProductionDesignerOutput containing shared elements and design notes.
    """
    from agents import Runner

    # Format scenes for analysis
    scenes_description = "\n\n".join(
        f"Scene {scene.scene_number}:\n"
        f"- Setting: {scene.setting_description}\n"
        f"- Action: {scene.action_description}"
        + (f"\n- Dialogue: {scene.dialogue}" if scene.dialogue else "")
        for scene in scenes
    )

    prompt = f"""Analyze these scenes and identify all shared visual elements that need consistency:

{scenes_description}

Requirements:
- Identify all recurring characters, props, and environments
- Create detailed visual descriptions suitable for AI image generation
- Include physical attributes, colors, clothing, and distinguishing features
- Track which scenes each element appears in
- Use consistent ID format: char_*, prop_*, env_* for characters, props, environments
- Only include elements that appear in 2+ scenes OR are central to the story
- Focus on visual details that will ensure consistency across video clips
"""

    result = await Runner.run(production_designer_agent, prompt)
    return result.final_output
