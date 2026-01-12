"""Style reference prompt helper for building layout constraints.
V1: Geometry-focused constraints (deprecated)
V2: Semantic constraints - prose layout, visual treatments, scene elements
V3: Color grading DNA - photographic signature for style consistency
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sip_studio.brands.models import (
        ColorGradingSpec,
        StyleReferenceAnalysis,
        StyleReferenceAnalysisV2,
        StyleReferenceAnalysisV3,
    )


def build_style_reference_constraints(
    analysis: "StyleReferenceAnalysis", strict: bool, include_usage: bool = True
) -> str:
    """Build style reference constraints string for agent prompts.
    Args:
        analysis: The StyleReferenceAnalysis containing layout specs.
        strict: True for exact reproduction, False for controlled variation.
        include_usage: When True, include tool usage hints (for agent context).
    Returns:
        Formatted constraint string for injection into agent context.
    """
    if strict:
        return _build_strict_constraints(analysis, include_usage)
    return _build_loose_constraints(analysis, include_usage)


def _build_strict_constraints(analysis: "StyleReferenceAnalysis", include_usage: bool) -> str:
    """Build strict mode constraints - exact reproduction required."""
    canvas = analysis.canvas
    style = analysis.style
    elements = analysis.elements
    product_slot = analysis.product_slot
    # Build element constraints
    elem_constraints = []
    for e in elements:
        g = e.geometry
        locked = "[LOCKED]" if e.constraints.locked_position else ""
        pos = f"pos=({g.x:.0%},{g.y:.0%})"
        size = f"size=({g.width:.0%}×{g.height:.0%})"
        elem_constraints.append(f"  - {e.id} ({e.type}/{e.role}): {pos}, {size} {locked}")
    elem_block = "\n".join(elem_constraints) if elem_constraints else "  (no elements)"
    # Product slot details
    slot_block = ""
    if product_slot:
        pg = product_slot.geometry
        slot_block = f"""
**Product Slot Constraints**:
  - Position: ({pg.x:.0%}, {pg.y:.0%})
  - Size: {pg.width:.0%} × {pg.height:.0%}
  - Scale Mode: {product_slot.interaction.scale_mode}
  - Shadow: {"preserve" if product_slot.interaction.preserve_shadow else "none"}

Only the product slot content may be replaced. Everything else is locked."""
    # Palette lock
    palette_str = ", ".join(style.palette[:5]) if style.palette else "(none)"
    usage_block = ""
    if include_usage:
        usage_block = """

**HOW TO USE**:
Call `generate_image(style_ref_slug="...", prompt="...")`
Style reference constraints are auto-applied to generation."""
    return f"""**STRICT MODE - EXACT REPRODUCTION**

**Canvas**: background: {canvas.background}

**Style Lock** (DO NOT MODIFY):
  - Palette: {palette_str}
  - Lighting: {style.lighting}
  - Mood: {style.mood}

**Element Positions** (DO NOT MOVE/RESIZE):
{elem_block}
{slot_block}

**CRITICAL RULES**:
1. PRESERVE exact element positions and sizes
2. MATCH palette and lighting exactly
3. ONLY replace content in product_slot
4. Do NOT add, remove, or reposition elements
5. Use geometry values as absolute constraints
{usage_block}"""


def _build_loose_constraints(analysis: "StyleReferenceAnalysis", include_usage: bool) -> str:
    """Build loose mode constraints - preserve intent, allow variation."""
    message = analysis.message
    style = analysis.style
    elements = analysis.elements
    product_slot = analysis.product_slot
    # Identify key elements to preserve
    key_roles = ["headline", "logo", "hero_image", "product", "call_to_action"]
    key_elems = [e for e in elements if e.role.lower() in key_roles or e.type == "product"]
    key_elem_list = (
        "\n".join(
            f"  - {e.role or e.type}: preserve prominence and hierarchy" for e in key_elems[:5]
        )
        if key_elems
        else "  (no key elements identified)"
    )
    # Composition hints
    elem_count = len(elements)
    composition = (
        "dense multi-element" if elem_count > 6 else "balanced" if elem_count > 3 else "minimal"
    )
    # Slot focus
    slot_hint = ""
    if product_slot:
        pg = product_slot.geometry
        slot_hint = f"""
**Product Focus**:
  - Approximate region: ({pg.x:.0%}, {pg.y:.0%}) ±20%
  - Target size: ~{pg.width:.0%} × {pg.height:.0%}
  - Keep product as primary focal point"""
    usage_block = ""
    if include_usage:
        usage_block = """

**HOW TO USE**:
Call `generate_image(style_ref_slug="...", prompt="...", strict=False)`"""
    return f"""**LOOSE MODE - PRESERVE INTENT, ALLOW VARIATION**

**Message Intent** (MUST PRESERVE):
  - Intent: {message.intent}
  - Audience: {message.audience}
  - Key Claims: {", ".join(message.key_claims[:3]) if message.key_claims else "(none)"}

**Style Guidelines** (follow spirit, not exact):
  - Mood: {style.mood}
  - Lighting: {style.lighting}
  - Palette family: {", ".join(style.palette[:3]) if style.palette else "(none)"}

**Composition**: {composition} layout

**Key Elements to Preserve**:
{key_elem_list}
{slot_hint}

**VARIATION RULES**:
✓ Element positions may shift ±20%
✓ Background details can vary
✓ Secondary elements may be adjusted
✓ Colors may vary within palette family
✓ Minor compositional improvements allowed

✗ Do NOT change message intent
✗ Do NOT remove key elements
✗ Do NOT reduce product prominence
{usage_block}"""


def format_element_summary(analysis: "StyleReferenceAnalysis") -> str:
    """Format a brief element summary for context display.
    Args:
        analysis: The StyleReferenceAnalysis.
    Returns:
        Brief summary string of layout elements.
    """
    from collections import Counter

    types = Counter(e.type for e in analysis.elements)
    parts = [f"{c}x {t}" for t, c in types.most_common()]
    return f"{len(analysis.elements)} elements ({', '.join(parts)})" if parts else "no elements"


def format_product_slot_summary(analysis: "StyleReferenceAnalysis") -> str:
    """Format product slot info for context display.
    Args:
        analysis: The StyleReferenceAnalysis.
    Returns:
        Product slot summary or empty string if none.
    """
    ps = analysis.product_slot
    if not ps:
        return ""
    g = ps.geometry
    pos = f"({g.x:.0%},{g.y:.0%})"
    size = f"{g.width:.0%}×{g.height:.0%}"
    return f"Product slot at {pos}, {size}, {ps.interaction.scale_mode} mode"


# V2 Semantic Constraint Builder
def build_style_reference_constraints_v2(
    analysis: "StyleReferenceAnalysisV2", strict: bool, include_usage: bool = True
) -> str:
    """Build semantic style reference constraints string for agent prompts (V2).
    Args:
        analysis: The StyleReferenceAnalysisV2 containing semantic layout specs.
        strict: True for exact reproduction, False for controlled variation.
        include_usage: When True, include tool usage hints.
    Returns:
        Formatted constraint string for injection into generation prompts.
    """
    if strict:
        return _build_strict_v2(analysis, include_usage)
    return _build_loose_v2(analysis, include_usage)


def _build_strict_v2(analysis: "StyleReferenceAnalysisV2", include_usage: bool) -> str:
    """Build strict V2 constraints - exact layout and visual style."""
    style = analysis.style
    layout = analysis.layout
    scene = analysis.visual_scene
    constraints = analysis.constraints
    # Visual treatments
    treatments = (
        ", ".join(scene.visual_treatments) if scene.visual_treatments else "(none specified)"
    )
    # Non-negotiables
    non_neg = (
        "\n".join(f"  - {item}" for item in constraints.non_negotiables)
        if constraints.non_negotiables
        else "  - Layout structure preserved\n  - Visual treatments replicated"
    )
    # Palette
    palette_str = ", ".join(style.palette[:5]) if style.palette else "(not specified)"
    usage_block = ""
    if include_usage:
        usage_block = """

**HOW TO USE**:
Call `generate_image(style_ref_slug="...", prompt="...")`
Style reference constraints are auto-applied."""
    return f"""**STRICT MODE - EXACT REPRODUCTION**

**Layout Structure**: {layout.structure}
  Hierarchy: {layout.hierarchy}
  Alignment: {layout.alignment}

**Visual Scene**: {scene.scene_description}
  Photography: {scene.photography_style}
  Product placement: {scene.product_placement}

**Visual Treatments** (MUST replicate): {treatments}

**Style**:
  Mood: {style.mood}
  Lighting: {style.lighting}
  Palette: {palette_str}

**NON-NEGOTIABLES** (MUST preserve exactly):
{non_neg}

**CRITICAL RULES**:
1. Preserve the layout structure described above
2. Replicate visual treatments (pill badges, shadows, etc.)
3. Maintain visual hierarchy
4. Place product as described in product_placement
{usage_block}"""


def _build_loose_v2(analysis: "StyleReferenceAnalysisV2", include_usage: bool) -> str:
    """Build loose V2 constraints - flexible layout with preserved visual style."""
    style = analysis.style
    layout = analysis.layout
    scene = analysis.visual_scene
    constraints = analysis.constraints
    # Creative freedom
    freedom = (
        "\n".join(f"  ✓ {item}" for item in constraints.creative_freedom)
        if constraints.creative_freedom
        else "  ✓ Background details can vary\n  ✓ Exact props can change"
    )
    # Palette
    palette_str = ", ".join(style.palette[:3]) if style.palette else "(not specified)"
    usage_block = ""
    if include_usage:
        usage_block = """

**HOW TO USE**:
Call `generate_image(style_ref_slug="...", prompt="...", strict=False)`"""
    return f"""**LOOSE MODE - PRESERVE INTENT, ALLOW VARIATION**

**Layout Intent**: {layout.structure}
  (Preserve general structure, exact positions can vary)

**Visual Scene Intent**: {scene.scene_description}
  Photography style: {scene.photography_style}
  Product integration: {constraints.product_integration or scene.product_placement}

**Style Guidelines** (follow spirit, not exact):
  Mood: {style.mood}
  Lighting: {style.lighting}
  Palette family: {palette_str}

**CREATIVE FREEDOM** (these CAN vary):
{freedom}

**VARIATION RULES**:
✓ Background scene can change (different setting, props)
✓ Exact styling/colors can shift within mood
✓ Lifestyle elements can vary
✓ Minor compositional adjustments allowed

✗ Do NOT change the overall layout intent
✗ Do NOT lose the visual mood and atmosphere
{usage_block}"""


def format_v2_summary(analysis: "StyleReferenceAnalysisV2") -> str:
    """Format a brief V2 analysis summary for context display."""
    treatments = len(analysis.visual_scene.visual_treatments)
    mood = analysis.style.mood[:20] if analysis.style.mood else "no mood"
    return f"V2: {analysis.layout.structure[:40]}..., {mood}, {treatments} treatments"


# V3 Color Grading DNA Constraint Builder
def _build_color_grading_constraints(cg: "ColorGradingSpec") -> str:
    """Build color grading constraint block - HIGHEST PRIORITY for style matching."""
    lines = ["**COLOR GRADING DNA** (HIGHEST PRIORITY - match this exactly):"]
    if cg.film_stock_reference:
        lines.append(f"  Film Look: {cg.film_stock_reference}")
    if cg.color_temperature:
        lines.append(f"  Temperature: {cg.color_temperature}")
    shadow_parts = []
    if cg.black_point:
        shadow_parts.append(cg.black_point)
    if cg.shadow_tint:
        shadow_parts.append(f"with {cg.shadow_tint}")
    if shadow_parts:
        lines.append(f"  Shadows: {' '.join(shadow_parts)}")
    highlight_parts = []
    if cg.highlight_rolloff:
        highlight_parts.append(f"{cg.highlight_rolloff} rolloff")
    if cg.highlight_tint:
        highlight_parts.append(cg.highlight_tint)
    if highlight_parts:
        lines.append(f"  Highlights: {', '.join(highlight_parts)}")
    if cg.saturation_level:
        lines.append(f"  Saturation: {cg.saturation_level}")
    if cg.contrast_character:
        lines.append(f"  Contrast: {cg.contrast_character}")
    if cg.signature_elements:
        lines.append(f"  Signature: {', '.join(cg.signature_elements[:4])}")
    return "\n".join(lines)


def _build_style_suggestions(suggestions, mood_fallback: str = "") -> str:
    """Build style suggestions block - secondary to color grading."""
    lines = ["**STYLE SUGGESTIONS** (secondary - can vary):"]
    if suggestions.environment_tendency:
        lines.append(f"  Environment: {suggestions.environment_tendency}")
    if suggestions.mood:
        lines.append(f"  Mood: {suggestions.mood}")
    elif mood_fallback:
        lines.append(f"  Mood: {mood_fallback}")
    if suggestions.lighting_setup:
        lines.append(f"  Lighting: {suggestions.lighting_setup}")
    return "\n".join(lines) if len(lines) > 1 else ""


def build_style_reference_constraints_v3(
    analysis: "StyleReferenceAnalysisV3", strict: bool, include_usage: bool = True
) -> str:
    """Build color grading DNA constraints for agent prompts (V3).
    Args:
        analysis: StyleReferenceAnalysisV3 containing color grading DNA.
        strict: True for exact color matching, False for color family matching.
        include_usage: When True, include tool usage hints.
    Returns:
        Formatted constraint string prioritizing color grading over layout.
    """
    if strict:
        return _build_strict_v3(analysis, include_usage)
    return _build_loose_v3(analysis, include_usage)


def _build_strict_v3(analysis: "StyleReferenceAnalysisV3", include_usage: bool) -> str:
    """Build strict V3 constraints - exact color grading reproduction."""
    cg = analysis.color_grading
    suggestions = analysis.style_suggestions
    color_block = _build_color_grading_constraints(cg)
    suggestions_block = _build_style_suggestions(suggestions)
    usage_block = ""
    if include_usage:
        usage_block = """

**HOW TO USE**:
Call `generate_image(style_ref_slug="...", prompt="...")`
Color grading constraints are auto-applied."""
    return f"""**STRICT MODE - EXACT COLOR GRADING MATCH**

{color_block}

{suggestions_block}

**CRITICAL RULES**:
1. MATCH the color grading DNA exactly - this is the photographer's signature
2. Temperature, shadow treatment, and highlight rolloff MUST be preserved
3. Saturation and contrast character define the look - do not deviate
4. Film stock reference is your guide - emulate that aesthetic
5. Layout and composition CAN vary - color treatment CANNOT
{usage_block}"""


def _build_loose_v3(analysis: "StyleReferenceAnalysisV3", include_usage: bool) -> str:
    """Build loose V3 constraints - color family matching with flexibility."""
    cg = analysis.color_grading
    suggestions = analysis.style_suggestions
    color_block = _build_color_grading_constraints(cg)
    suggestions_block = _build_style_suggestions(suggestions)
    usage_block = ""
    if include_usage:
        usage_block = """

**HOW TO USE**:
Call `generate_image(style_ref_slug="...", prompt="...", strict=False)`"""
    return f"""**LOOSE MODE - COLOR FAMILY MATCHING**

{color_block}

{suggestions_block}

**VARIATION RULES**:
✓ Exact color values can shift within the same family
✓ Contrast can vary slightly while maintaining character
✓ Environment and composition are completely flexible
✓ Lighting setup can adapt to scene

✗ Do NOT change temperature direction (warm stays warm)
✗ Do NOT change shadow treatment dramatically
✗ Do NOT flip saturation (muted stays muted)
✗ Do NOT abandon the film stock aesthetic
{usage_block}"""


def format_v3_summary(analysis: "StyleReferenceAnalysisV3") -> str:
    """Format a brief V3 analysis summary for context display."""
    film = analysis.color_grading.film_stock_reference or "no film ref"
    sigs = len(analysis.color_grading.signature_elements)
    temp = (
        analysis.color_grading.color_temperature[:15]
        if analysis.color_grading.color_temperature
        else "unknown"
    )
    return f"V3: {film}, {temp}, {sigs} signatures"
