"""Continuity Supervisor agent for validating consistency and optimizing prompts.

This agent reviews scenes and shared elements for consistency issues,
optimizes prompts for AI generation, and ensures reference image descriptions
match scene descriptions.
"""

from pathlib import Path

from agents import Agent

from sip_videogen.models.agent_outputs import ContinuitySupervisorOutput
from sip_videogen.models.script import SceneAction, SharedElement

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_CONTINUITY_SUPERVISOR_PROMPT_PATH = _PROMPTS_DIR / "continuity_supervisor.md"


def _load_prompt() -> str:
    """Load the continuity supervisor prompt from the markdown file."""
    if _CONTINUITY_SUPERVISOR_PROMPT_PATH.exists():
        return _CONTINUITY_SUPERVISOR_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are an experienced continuity supervisor for AI-generated video.
Your job is to:
1. Review scenes and shared elements for consistency
2. Optimize prompts for AI video generation
3. Flag potential continuity issues
4. Ensure reference image descriptions match scene descriptions

Focus on visual consistency and prompt optimization for AI generation.
"""


# Create the continuity supervisor agent
continuity_supervisor_agent = Agent(
    name="Continuity Supervisor",
    instructions=_load_prompt(),
    output_type=ContinuitySupervisorOutput,
)


async def validate_and_optimize(
    scenes: list[SceneAction],
    shared_elements: list[SharedElement],
    title: str,
    logline: str,
    tone: str,
) -> ContinuitySupervisorOutput:
    """Validate scenes and shared elements for consistency, and optimize prompts.

    Reviews the provided scenes and shared elements to:
    - Identify and resolve continuity issues
    - Optimize action descriptions for AI video generation
    - Ensure reference image descriptions are compatible with scene usage
    - Add specific descriptors to improve generation quality

    Args:
        scenes: List of scene actions to validate.
        shared_elements: List of shared visual elements.
        title: The video title.
        logline: One-sentence summary of the video.
        tone: The overall mood/style.

    Returns:
        ContinuitySupervisorOutput containing validated script with optimized prompts.
    """
    from agents import Runner

    # Format scenes for review
    scenes_text = "\n\n".join(
        f"Scene {scene.scene_number}:\n"
        f"- Setting: {scene.setting_description}\n"
        f"- Action: {scene.action_description}\n"
        f"- Duration: {scene.duration_seconds}s"
        + (f"\n- Dialogue: {scene.dialogue}" if scene.dialogue else "")
        + (f"\n- Camera: {scene.camera_direction}" if scene.camera_direction else "")
        + (
            f"\n- Uses elements: {', '.join(scene.shared_element_ids)}"
            if scene.shared_element_ids
            else ""
        )
        for scene in scenes
    )

    # Format shared elements for review
    elements_text = "\n\n".join(
        f"Element: {elem.name} (ID: {elem.id})\n"
        f"- Type: {elem.element_type.value}\n"
        f"- Visual Description: {elem.visual_description}\n"
        f"- Appears in scenes: {elem.appears_in_scenes}"
        for elem in shared_elements
    )

    # Calculate total scenes for flow validation
    total_scenes = len(scenes)

    prompt = f"""Review and validate this video script for consistency, then optimize for AI generation:

TITLE: {title}
LOGLINE: {logline}
TONE: {tone}

SCENES:
{scenes_text}

SHARED ELEMENTS:
{elements_text}

Your tasks:
1. Check for continuity issues:
   - Do shared elements appear consistently in their listed scenes?
   - Are visual descriptions consistent between scenes and element specs?
   - Are there any logical gaps or contradictions?

2. **Validate scene flow for seamless video assembly:**
   These {total_scenes} scenes will be generated as separate clips and assembled.
   To prevent awkward pauses between clips:
   - Scene 1 (first): May open naturally, but MUST end with action in progress
   - Scenes 2-{total_scenes - 1 if total_scenes > 2 else total_scenes} (middle): MUST begin AND end mid-action - NO pauses at either end
   - Scene {total_scenes} (last): MUST begin mid-action, may conclude naturally
   - Flag any scenes with "pause", "stop", "wait", or "look at camera" at scene boundaries
   - Add continuation language where needed

3. Optimize prompts for AI video generation:
   - Add specific visual descriptors (lighting, colors, textures)
   - Ensure action descriptions are concrete and filmable
   - Make camera directions clear and achievable
   - Ensure dialogue (if any) is brief and fits the scene duration
   - **Add flow continuity language to prevent inter-scene pauses**

4. Validate reference image compatibility:
   - Do element descriptions work for static reference images?
   - Are there details that won't translate to video?

5. Produce the validated VideoScript:
   - Apply all optimizations to scenes
   - Apply all optimizations to shared elements
   - Maintain the original narrative intent
   - Include title, logline, and tone

Flag any issues found and explain how you resolved them.
"""

    result = await Runner.run(continuity_supervisor_agent, prompt)
    return result.final_output
