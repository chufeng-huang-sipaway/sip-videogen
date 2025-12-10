"""Prompt Repair agent for revising blocked video prompts.

This agent revises scene descriptions that were rejected by VEO's safety
policies, maintaining narrative intent while avoiding policy violations.
"""

from pathlib import Path

from agents import Agent

from sip_videogen.config.logging import get_logger
from sip_videogen.models.agent_outputs import PromptRepairOutput
from sip_videogen.models.script import SceneAction

logger = get_logger(__name__)

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_PROMPT_REPAIR_PROMPT_PATH = _PROMPTS_DIR / "prompt_repair.md"


def _load_prompt() -> str:
    """Load the prompt repair prompt from the markdown file."""
    if _PROMPT_REPAIR_PROMPT_PATH.exists():
        return _PROMPT_REPAIR_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are an expert at revising video generation prompts to comply
with AI safety policies while maintaining creative intent.

When a prompt is rejected, revise it to:
1. Remove problematic content (kids, celebrities, brands, violence)
2. Maintain the narrative intent
3. Keep the scene's role in the video sequence

Common fixes:
- "kids" -> "customers" or "onlookers"
- Celebrity names -> generic descriptors
- Brand names -> generic descriptions
"""


# Create the prompt repair agent
prompt_repair_agent = Agent(
    name="Prompt Repair",
    instructions=_load_prompt(),
    output_type=PromptRepairOutput,
)


async def repair_scene_prompt(
    scene: SceneAction,
    error_message: str,
    attempt_number: int = 1,
) -> PromptRepairOutput:
    """Repair a scene's prompt that was rejected by VEO.

    Takes a scene that failed video generation due to policy violations
    and produces a revised version that avoids the problematic content
    while maintaining narrative intent.

    Args:
        scene: The SceneAction that failed generation.
        error_message: The error message from VEO explaining the rejection.
        attempt_number: Which repair attempt this is (1 or 2).

    Returns:
        PromptRepairOutput with revised descriptions and explanation.
    """
    from agents import Runner

    # Build context about the scene
    previous_attempts_note = ""
    if attempt_number > 1:
        previous_attempts_note = f"""
This is repair attempt #{attempt_number}. The previous repair still triggered
a policy violation. Be MORE aggressive in removing potentially problematic
content. Consider completely rephrasing the scene while keeping the same
narrative purpose.
"""

    prompt = f"""A video generation prompt was rejected by Google's VEO model.
Please revise it to comply with safety policies while maintaining the scene's purpose.

SCENE NUMBER: {scene.scene_number}

ORIGINAL SETTING:
{scene.setting_description}

ORIGINAL ACTION:
{scene.action_description}

ERROR MESSAGE:
{error_message}
{previous_attempts_note}
Your task:
1. Identify what likely triggered the policy violation
2. Revise the setting and action descriptions to avoid the violation
3. Maintain the scene's narrative purpose and flow continuity
4. Explain what you changed

IMPORTANT:
- Keep any flow/continuity language (e.g., "continuing from previous scene")
- The revised scene should serve the same purpose in the video
- Only change what's necessary to avoid the policy violation
"""

    logger.info(f"Repairing prompt for scene {scene.scene_number} (attempt {attempt_number})")
    result = await Runner.run(prompt_repair_agent, prompt)
    logger.info(f"Prompt repair complete: {result.final_output.changes_made}")
    return result.final_output
