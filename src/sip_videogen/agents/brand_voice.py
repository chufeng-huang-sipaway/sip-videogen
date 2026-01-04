"""Brand Voice Writer agent for voice and messaging development.

This agent takes a brand strategy and produces comprehensive voice guidelines
including personality definition, tone attributes, messaging frameworks,
and sample copy demonstrating the voice in action.
"""

from pathlib import Path

from agents import Agent

from sip_videogen.advisor.tools import browse_brand_assets, fetch_brand_detail
from sip_videogen.models.brand_agent_outputs import BrandVoiceOutput

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_BRAND_VOICE_PROMPT_PATH = _PROMPTS_DIR / "brand_voice.md"


def _load_prompt() -> str:
    """Load the brand voice prompt from the markdown file."""
    if _BRAND_VOICE_PROMPT_PATH.exists():
        return _BRAND_VOICE_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are a senior brand voice writer and messaging strategist.
Given a brand strategy, produce:
1. Voice guidelines (personality, tone attributes, messaging do's and don'ts)
2. Key messages that communicate brand value
3. Sample copy demonstrating the voice in action

Focus on creating a distinctive, consistent voice that resonates with the target audience.
"""


# Create the brand voice agent
brand_voice_agent = Agent(
    name="Brand Voice Writer",
    instructions=_load_prompt(),
    tools=[fetch_brand_detail, browse_brand_assets],
    output_type=BrandVoiceOutput,
)


async def develop_brand_voice(
    brand_strategy: str,
    existing_brand_slug: str | None = None,
) -> BrandVoiceOutput:
    """Develop brand voice guidelines from a strategy or evolve an existing brand.

    Args:
        brand_strategy: The brand strategy context (core identity, audience, positioning)
            typically from the Brand Strategist agent output.
        existing_brand_slug: If evolving an existing brand, provide its slug.
            The agent will use memory tools to explore the current brand state.

    Returns:
        BrandVoiceOutput containing voice guidelines, sample copy, and rationale.
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

You are EVOLVING the voice for an existing brand, not creating from scratch.

{brand_context}

---

"""
    else:
        context_section = """
## New Brand Voice

You are creating a NEW brand voice from scratch. Be distinctive and memorable.

---

"""

    prompt = f"""{context_section}
## Brand Strategy

{brand_strategy}

---

## Your Task

{
        "Evolve this existing brand's voice based on the strategy above. "
        "Respect established voice elements while proposing refinements that enhance communication."
        if existing_brand_slug
        else "Create comprehensive voice guidelines for this new brand."
    }

Produce:
1. **Voice Guidelines**: Personality, 3-5 tone attributes, messaging do's (4-6) and don'ts (4-6)
2. **Key Messages**: 3-5 core talking points
3. **Example Headlines**: 4-6 headlines demonstrating the voice
4. **Example Taglines**: 3-5 alternative taglines (7 words or fewer each)
5. **Sample Copy**: 3-5 paragraphs demonstrating the voice in context

Include your voice rationale explaining how these choices serve the brand and audience.
"""

    result = await Runner.run(brand_voice_agent, prompt)
    return result.final_output
