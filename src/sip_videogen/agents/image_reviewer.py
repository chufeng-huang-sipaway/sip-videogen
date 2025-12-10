"""Image Reviewer agent for evaluating generated reference images.

This agent uses a vision-capable model (GPT-4o) to assess whether
generated reference images match their intended visual specifications
and are suitable for VEO video generation.
"""

from pathlib import Path

from agents import Agent

from sip_videogen.models.image_review import ImageReviewResult

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_IMAGE_REVIEWER_PROMPT_PATH = _PROMPTS_DIR / "image_reviewer.md"


def _load_prompt() -> str:
    """Load the image reviewer prompt from the markdown file."""
    if _IMAGE_REVIEWER_PROMPT_PATH.exists():
        return _IMAGE_REVIEWER_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are a visual quality reviewer for AI-generated reference images.

Your job is to evaluate whether a generated image:
1. Matches the intended visual description
2. Is suitable as a reference for VEO video generation
3. Has consistent quality and style

ACCEPT if the image captures the essential visual identity.
REJECT if key elements are wrong, missing, or quality would affect video generation.

When rejecting, provide SPECIFIC, ACTIONABLE suggestions for improving the prompt.
Don't be overly critical - VEO needs reference identity, not perfection.
"""


# Create the image reviewer agent with vision-capable model
image_reviewer_agent = Agent(
    name="Image Reviewer",
    instructions=_load_prompt(),
    model="gpt-4o",  # Vision-capable model
    output_type=ImageReviewResult,
)


async def review_image(
    element_id: str,
    element_type: str,
    element_name: str,
    visual_description: str,
    image_base64: str,
) -> ImageReviewResult:
    """Review a generated reference image against its specification.

    Args:
        element_id: Unique identifier of the shared element.
        element_type: Type of element (character, environment, prop).
        element_name: Human-readable name of the element.
        visual_description: The visual description used to generate the image.
        image_base64: Base64-encoded image data.

    Returns:
        ImageReviewResult with accept/reject decision and feedback.
    """
    from agents import Runner

    prompt = f"""Review this reference image for the following shared element:

**Element ID:** {element_id}
**Type:** {element_type}
**Name:** {element_name}
**Visual Description:** {visual_description}

Evaluate whether this image:
1. Matches the visual description above
2. Is suitable as a reference image for VEO video generation
3. Has good enough quality (no artifacts, distortions, or major issues)

If accepting: Briefly explain why it's suitable.
If rejecting: Explain what's wrong and provide specific suggestions for improving the generation prompt.
"""

    # Create input with image for vision model
    # The input must be a message with role and content array for multimodal input
    input_message = {
        "role": "user",
        "content": [
            {"type": "input_text", "text": prompt},
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{image_base64}",
                "detail": "high",
            },
        ],
    }

    result = await Runner.run(image_reviewer_agent, [input_message])
    return result.final_output
