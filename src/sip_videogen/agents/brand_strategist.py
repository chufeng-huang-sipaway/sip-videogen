"""Brand Strategist agent for core identity and positioning development.

This agent takes a brand concept and produces a comprehensive brand strategy
including core identity (name, mission, values), audience profile, and
market positioning.
"""

from pathlib import Path

from agents import Agent

from sip_videogen.advisor.tools import browse_brand_assets, fetch_brand_detail
from sip_videogen.models.brand_agent_outputs import BrandStrategyOutput

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_BRAND_STRATEGIST_PROMPT_PATH = _PROMPTS_DIR / "brand_strategist.md"


def _load_prompt() -> str:
    """Load the brand strategist prompt from the markdown file."""
    if _BRAND_STRATEGIST_PROMPT_PATH.exists():
        return _BRAND_STRATEGIST_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are a senior brand strategist specializing in building iconic brands.
Given a brand concept, produce:
1. Core identity (name, tagline, mission, story, values)
2. Target audience profile (demographics, psychographics, pain points, desires)
3. Market positioning (category, unique value proposition, competitors)

Focus on creating distinctive, authentic brand foundations that can guide all future decisions.
"""


# Create the brand strategist agent
brand_strategist_agent = Agent(
    name="Brand Strategist",
    instructions=_load_prompt(),
    tools=[fetch_brand_detail, browse_brand_assets],
    output_type=BrandStrategyOutput,
)


async def develop_brand_strategy(
    concept: str,
    existing_brand_slug: str | None = None,
) -> BrandStrategyOutput:
    """Develop a brand strategy from a concept or evolve an existing brand.

    Args:
        concept: The brand concept, idea, or evolution request.
        existing_brand_slug: If evolving an existing brand, provide its slug.
            The agent will use memory tools to explore the current brand state.

    Returns:
        BrandStrategyOutput containing core identity, audience, and positioning.
    """
    from agents import Runner

    from sip_videogen.brands.context import build_brand_context
    from sip_videogen.brands.storage import set_active_brand

    # Build brand context for memory tools if evolving existing brand
    if existing_brand_slug:
        set_active_brand(existing_brand_slug)
        brand_context = build_brand_context(existing_brand_slug)
        context_section = f"""
## Existing Brand Context

You are EVOLVING an existing brand, not creating from scratch.

{brand_context}

---

"""
    else:
        context_section = """
## New Brand Creation

You are creating a NEW brand from scratch. Be bold and creative.

---

"""

    prompt = f"""{context_section}
## Brand Concept

{concept}

---

## Your Task

{
        "Evolve this existing brand based on the concept above. "
        "Respect established identity while proposing strategic improvements."
        if existing_brand_slug
        else "Create a comprehensive brand strategy for this new brand concept."
    }

Produce:
1. **Core Identity**: Name, tagline, mission, brand story, and 3-5 values
2. **Audience Profile**: Demographics, psychographics, pain points, desires
3. **Market Positioning**: Category, UVP, competitors, positioning statement

Include your strategic rationale in `strategy_notes`.
"""

    result = await Runner.run(brand_strategist_agent, prompt)
    return result.final_output
