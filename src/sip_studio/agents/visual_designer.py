"""Visual Identity Designer agent for brand visual system development.

This agent takes a brand strategy and produces a comprehensive visual identity
including colors, typography, imagery direction, and logo brief.
"""

from pathlib import Path

from agents import Agent

from sip_studio.advisor.tools import browse_brand_assets, fetch_brand_detail
from sip_studio.models.brand_agent_outputs import VisualIdentityOutput

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_VISUAL_DESIGNER_PROMPT_PATH = _PROMPTS_DIR / "visual_designer.md"


def _load_prompt() -> str:
    """Load the visual designer prompt from the markdown file."""
    if _VISUAL_DESIGNER_PROMPT_PATH.exists():
        return _VISUAL_DESIGNER_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are a senior visual identity designer specializing in brand design systems.
Given a brand strategy, produce:
1. Color palette (primary, secondary, accent with hex codes and usage)
2. Typography system (heading, body, accent fonts with guidelines)
3. Imagery direction (style, keywords, avoidances)
4. Logo brief for generation

Focus on creating cohesive, distinctive visual languages that bring brand strategies to life.
"""


# Create the visual designer agent
visual_designer_agent = Agent(
    name="Visual Identity Designer",
    instructions=_load_prompt(),
    tools=[fetch_brand_detail, browse_brand_assets],
    output_type=VisualIdentityOutput,
)


async def develop_visual_identity(
    brand_strategy: str,
    existing_brand_slug: str | None = None,
) -> VisualIdentityOutput:
    """Develop a visual identity from a brand strategy or evolve an existing brand.

    Args:
        brand_strategy: The brand strategy context (name, positioning, audience info).
        existing_brand_slug: If evolving an existing brand, provide its slug.
            The agent will use memory tools to explore the current visual identity.

    Returns:
        VisualIdentityOutput containing visual identity, rationale, and logo brief.
    """
    from agents import Runner

    from sip_studio.brands.context import build_brand_context
    from sip_studio.brands.storage import set_active_brand

    # Build brand context for memory tools if evolving existing brand
    if existing_brand_slug:
        set_active_brand(existing_brand_slug)
        brand_context = build_brand_context(existing_brand_slug)
        context_section = f"""
## Existing Brand Context

You are EVOLVING an existing brand's visual identity, not creating from scratch.

{brand_context}

---

"""
    else:
        context_section = """
## New Brand Creation

You are creating a NEW visual identity from scratch. Be bold and creative.

---

"""

    prompt = f"""{context_section}
## Brand Strategy

{brand_strategy}

---

## Your Task

{
        "Evolve this brand's visual identity based on the strategy above. "
        "Respect established visual elements while proposing improvements."
        if existing_brand_slug
        else "Create a comprehensive visual identity for this brand strategy."
    }

Produce:
1. **Color Palette**: Primary (1-3), secondary (1-3), and accent (1-2) colors
   - Include hex codes, descriptive names, and usage guidelines
2. **Typography System**: Heading, body, and optional accent fonts
   - Include weight and style recommendations
3. **Imagery Direction**: Style, keywords (5-10), and avoidances (3-5)
4. **Materials & Textures**: Physical/visual textures representing the brand
5. **Logo Brief**: Detailed direction for logo generation
6. **Overall Aesthetic**: One paragraph unifying all visual elements
7. **Style Keywords**: 3-5 high-level descriptors

Include your design reasoning in `design_rationale`.
"""

    result = await Runner.run(visual_designer_agent, prompt)
    return result.final_output
