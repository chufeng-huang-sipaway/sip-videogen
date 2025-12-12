"""Brand Guardian agent for brand consistency validation.

This agent validates brand identity consistency before asset generation.
It catches issues early to prevent expensive rework and ensures the brand
presents a unified, coherent identity across all elements.
"""

from pathlib import Path

from agents import Agent

from sip_videogen.brands.tools import browse_brand_assets, fetch_brand_detail
from sip_videogen.models.brand_agent_outputs import BrandGuardianOutput

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_BRAND_GUARDIAN_PROMPT_PATH = _PROMPTS_DIR / "brand_guardian.md"


def _load_prompt() -> str:
    """Load the brand guardian prompt from the markdown file."""
    if _BRAND_GUARDIAN_PROMPT_PATH.exists():
        return _BRAND_GUARDIAN_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are a senior brand quality assurance specialist.
Validate brand consistency before asset generation by checking:
1. Strategic consistency (name, tagline, mission, values alignment)
2. Visual consistency (colors, typography, imagery style harmony)
3. Voice consistency (personality, tone, messaging coherence)
4. Cross-section consistency (all elements reinforce each other)

IMPORTANT: Always fetch full brand details before validating.
Use fetch_brand_detail("full_identity") to get complete context.

Output your validation with:
- is_valid: true only if there are NO errors
- issues: List of specific problems with category, severity, description, recommendation
- consistency_score: 0.0 to 1.0 indicating overall coherence
- validation_notes: Summary of your findings
"""


# Create the brand guardian agent
brand_guardian_agent = Agent(
    name="Brand Guardian",
    instructions=_load_prompt(),
    tools=[fetch_brand_detail, browse_brand_assets],
    output_type=BrandGuardianOutput,
)


async def validate_brand_identity(
    brand_identity_json: str,
    brand_slug: str | None = None,
) -> BrandGuardianOutput:
    """Validate brand identity for consistency and completeness.

    Args:
        brand_identity_json: JSON string of the brand identity to validate.
            This can be a complete BrandIdentityFull or partial identity
            from specialist agents.
        brand_slug: If validating an evolution of an existing brand,
            provide its slug. The agent will use memory tools to compare
            against the established identity.

    Returns:
        BrandGuardianOutput containing validation results, issues list,
        consistency score, and validation notes.
    """
    from agents import Runner

    from sip_videogen.brands.context import build_brand_context
    from sip_videogen.brands.tools import set_brand_context

    # Set up brand context for memory tools if validating existing brand
    if brand_slug:
        set_brand_context(brand_slug)
        brand_context = build_brand_context(brand_slug)
        context_section = f"""
## Existing Brand Context

You are validating changes to an EXISTING brand. Compare the proposed identity
against the established brand to ensure consistency and appropriate evolution.

{brand_context}

---

"""
    else:
        set_brand_context(None)
        context_section = """
## New Brand Validation

You are validating a NEW brand identity. Ensure all elements are cohesive
and work together to create a unified brand presence.

---

"""

    prompt = f"""{context_section}
## Brand Identity to Validate

```json
{brand_identity_json}
```

---

## Your Task

Perform a comprehensive validation of this brand identity:

1. **Fetch full context first** - Use `fetch_brand_detail("full_identity")` if validating
   an existing brand
2. **Check strategic consistency** - Do name, tagline, mission, and values align?
3. **Check visual consistency** - Are colors, typography, and imagery coherent?
4. **Check voice consistency** - Does personality match tone attributes and examples?
5. **Check cross-section consistency** - Do all elements reinforce each other?

Produce:
- **is_valid**: `true` only if NO errors found (warnings are OK)
- **issues**: Specific list with category, severity, description, and recommendation for each
- **consistency_score**: 0.0-1.0 based on overall coherence
- **validation_notes**: Summary paragraph of your assessment

Be thorough but fair. Acknowledge what works well, not just what needs fixing.
"""

    result = await Runner.run(brand_guardian_agent, prompt)
    return result.final_output


async def validate_brand_work(
    strategy_output: str | None = None,
    visual_output: str | None = None,
    voice_output: str | None = None,
    brand_slug: str | None = None,
) -> BrandGuardianOutput:
    """Validate work from specialist agents before final assembly.

    This is a convenience function that combines outputs from multiple
    specialist agents into a single validation pass.

    Args:
        strategy_output: JSON from Brand Strategist (core identity, audience, positioning)
        visual_output: JSON from Visual Designer (visual identity, design rationale)
        voice_output: JSON from Brand Voice Writer (voice guidelines, sample copy)
        brand_slug: If evolving an existing brand, provide its slug

    Returns:
        BrandGuardianOutput with validation results for all submitted work.
    """
    from agents import Runner

    from sip_videogen.brands.context import build_brand_context
    from sip_videogen.brands.tools import set_brand_context

    # Set up brand context
    if brand_slug:
        set_brand_context(brand_slug)
        brand_context = build_brand_context(brand_slug)
        context_section = f"""
## Existing Brand Context

You are validating specialist work for an EXISTING brand.

{brand_context}

---

"""
    else:
        set_brand_context(None)
        context_section = """
## New Brand Validation

You are validating specialist work for a NEW brand.

---

"""

    # Build sections for each available output
    work_sections = []

    if strategy_output:
        work_sections.append(f"""### Brand Strategy (from Brand Strategist)

```json
{strategy_output}
```
""")

    if visual_output:
        work_sections.append(f"""### Visual Identity (from Visual Designer)

```json
{visual_output}
```
""")

    if voice_output:
        work_sections.append(f"""### Brand Voice (from Brand Voice Writer)

```json
{voice_output}
```
""")

    if not work_sections:
        # Return early with error if no work to validate
        from sip_videogen.models.brand_agent_outputs import BrandValidationIssue

        return BrandGuardianOutput(
            is_valid=False,
            issues=[
                BrandValidationIssue(
                    category="strategy",
                    severity="error",
                    description="No specialist work provided for validation",
                    recommendation=(
                        "Provide at least one of: strategy_output, visual_output, or voice_output"
                    ),
                )
            ],
            consistency_score=0.0,
            validation_notes="Validation cannot proceed without specialist work to review.",
        )

    work_content = "\n".join(work_sections)

    prompt = f"""{context_section}
## Specialist Work to Validate

{work_content}

---

## Your Task

Validate this specialist work for consistency and quality:

1. **Fetch existing brand details** if evolving (use `fetch_brand_detail("full_identity")`)
2. **Validate each section** against its checklist
3. **Check cross-section alignment** - Do strategy, visuals, and voice work together?
4. **Identify issues** with specific, actionable recommendations
5. **Score overall consistency** based on how well everything fits together

Focus especially on:
- Alignment between audience profile and voice tone
- Visual style matching brand personality
- Values reflected in both voice and visuals
- Positioning supported by all elements

Produce thorough but fair validation with acknowledgment of what works well.
"""

    result = await Runner.run(brand_guardian_agent, prompt)
    return result.final_output
