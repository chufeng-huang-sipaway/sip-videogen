"""Brand Kit planning agent.

This agent distills a freeform brand concept into a structured brief and
three distinct creative directions. The directions are then used by the
Brand Kit workflow to generate visual assets with the Nano Banana Pro model.
"""

from pathlib import Path

from agents import Agent, Runner

from sip_videogen.config.logging import get_logger
from sip_videogen.models.brand_kit import BrandKitPlan

logger = get_logger(__name__)

# Prompt file path
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_BRAND_DESIGNER_PROMPT_PATH = _PROMPTS_DIR / "brand_designer.md"


def _load_prompt() -> str:
    """Load the brand designer prompt from markdown."""
    if _BRAND_DESIGNER_PROMPT_PATH.exists():
        return _BRAND_DESIGNER_PROMPT_PATH.read_text()
    return (
        "You are a senior brand design strategist. Normalize the user's concept into a brief "
        "and propose three distinct creative directions with clear color, type, and material "
        "anchors. Stay general-purpose so any product category works."
    )


# Agent definition
brand_designer_agent = Agent(
    name="Brand Kit Planner",
    instructions=_load_prompt(),
    output_type=BrandKitPlan,
)


async def plan_brand_kit(concept: str) -> BrandKitPlan:
    """Turn a freeform concept into a structured brand kit plan.

    Args:
        concept: Freeform user description of the desired brand.

    Returns:
        BrandKitPlan containing normalized brief and three creative directions.
    """
    prompt = f"""You are planning a brand design library.

USER CONCEPT:
{concept}

Tasks:
- Normalize the concept into a concise brief (brand_name, product_category, core_product, target_audience, tone, style_keywords, constraints, avoidances, reference_notes if relevant).
- Propose exactly 3 distinct creative directions that could all satisfy the brief.
- Directions must diverge meaningfully (palette, materials, typography, mood, settings).
- Keep outputs reusable for any product category (beverages, bikes, food, SaaS, etc).

Return the result using the provided schema."""

    logger.info("Planning brand kit for concept: %s", concept[:80])
    result = await Runner.run(brand_designer_agent, prompt)
    return result.final_output
