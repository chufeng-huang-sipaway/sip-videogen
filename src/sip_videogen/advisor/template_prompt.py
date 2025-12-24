"""Template prompt helper for building layout constraints.
V1: Geometry-focused constraints (deprecated)
V2: Semantic constraints - verbatim copywriting, prose layout, visual treatments
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sip_videogen.brands.models import TemplateAnalysis,TemplateAnalysisV2
def build_template_constraints(analysis:"TemplateAnalysis",strict:bool,include_usage:bool=True)->str:
    """Build template constraints string for agent prompts.
    Args:
        analysis: The TemplateAnalysis containing layout specs.
        strict: True for exact reproduction, False for controlled variation.
        include_usage: When True, include tool usage hints (for agent context).
    Returns:
        Formatted constraint string for injection into agent context.
    """
    if strict:return _build_strict_constraints(analysis,include_usage)
    return _build_loose_constraints(analysis,include_usage)
def _build_strict_constraints(analysis:"TemplateAnalysis",include_usage:bool)->str:
    """Build strict mode constraints - exact reproduction required."""
    canvas=analysis.canvas
    style=analysis.style
    elements=analysis.elements
    product_slot=analysis.product_slot
    #Build element constraints
    elem_constraints=[]
    for e in elements:
        g=e.geometry
        locked="[LOCKED]" if e.constraints.locked_position else ""
        elem_constraints.append(f"  - {e.id} ({e.type}/{e.role}): pos=({g.x:.0%},{g.y:.0%}), size=({g.width:.0%}×{g.height:.0%}) {locked}")
    elem_block="\n".join(elem_constraints) if elem_constraints else "  (no elements)"
    #Product slot details
    slot_block=""
    if product_slot:
        pg=product_slot.geometry
        slot_block=f"""
**Product Slot Constraints**:
  - Position: ({pg.x:.0%}, {pg.y:.0%})
  - Size: {pg.width:.0%} × {pg.height:.0%}
  - Scale Mode: {product_slot.interaction.scale_mode}
  - Shadow: {"preserve" if product_slot.interaction.preserve_shadow else "none"}

Only the product slot content may be replaced. Everything else is locked."""
    #Palette lock
    palette_str=", ".join(style.palette[:5]) if style.palette else "(none)"
    usage_block=""
    if include_usage:
        usage_block="""

**HOW TO USE**:
Call `generate_image(template_slug="...", prompt="...")`
Template constraints are auto-applied to generation."""
    return f"""**STRICT MODE - EXACT REPRODUCTION**

**Canvas**: {canvas.aspect_ratio}, background: {canvas.background}

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
def _build_loose_constraints(analysis:"TemplateAnalysis",include_usage:bool)->str:
    """Build loose mode constraints - preserve intent, allow variation."""
    canvas=analysis.canvas
    message=analysis.message
    style=analysis.style
    elements=analysis.elements
    product_slot=analysis.product_slot
    #Identify key elements to preserve
    key_roles=["headline","logo","hero_image","product","call_to_action"]
    key_elems=[e for e in elements if e.role.lower() in key_roles or e.type=="product"]
    key_elem_list="\n".join(f"  - {e.role or e.type}: preserve prominence and hierarchy"for e in key_elems[:5])if key_elems else"  (no key elements identified)"
    #Composition hints
    elem_count=len(elements)
    composition="dense multi-element" if elem_count>6 else "balanced" if elem_count>3 else "minimal"
    #Slot focus
    slot_hint=""
    if product_slot:
        pg=product_slot.geometry
        slot_hint=f"""
**Product Focus**:
  - Approximate region: ({pg.x:.0%}, {pg.y:.0%}) ±20%
  - Target size: ~{pg.width:.0%} × {pg.height:.0%}
  - Keep product as primary focal point"""
    usage_block=""
    if include_usage:
        usage_block="""

**HOW TO USE**:
Call `generate_image(template_slug="...", prompt="...", strict=False)`"""
    return f"""**LOOSE MODE - PRESERVE INTENT, ALLOW VARIATION**

**Canvas**: {canvas.aspect_ratio} (preserve aspect ratio)

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
✗ Do NOT change aspect ratio
✗ Do NOT reduce product prominence
{usage_block}"""
def format_element_summary(analysis:"TemplateAnalysis")->str:
    """Format a brief element summary for context display.
    Args:
        analysis: The TemplateAnalysis.
    Returns:
        Brief summary string of layout elements.
    """
    from collections import Counter
    types=Counter(e.type for e in analysis.elements)
    parts=[f"{c}x {t}" for t,c in types.most_common()]
    return f"{len(analysis.elements)} elements ({', '.join(parts)})" if parts else "no elements"
def format_product_slot_summary(analysis:"TemplateAnalysis")->str:
    """Format product slot info for context display.
    Args:
        analysis: The TemplateAnalysis.
    Returns:
        Product slot summary or empty string if none.
    """
    ps=analysis.product_slot
    if not ps:return ""
    g=ps.geometry
    return f"Product slot at ({g.x:.0%},{g.y:.0%}), {g.width:.0%}×{g.height:.0%}, {ps.interaction.scale_mode} mode"


#V2 Semantic Constraint Builder
def build_template_constraints_v2(analysis:"TemplateAnalysisV2",strict:bool,include_usage:bool=True)->str:
    """Build semantic template constraints string for agent prompts (V2).
    Args:
        analysis: The TemplateAnalysisV2 containing semantic layout specs.
        strict: True for exact reproduction, False for controlled variation.
        include_usage: When True, include tool usage hints.
    Returns:
        Formatted constraint string for injection into generation prompts.
    """
    if strict:return _build_strict_v2(analysis,include_usage)
    return _build_loose_v2(analysis,include_usage)


def _build_strict_v2(analysis:"TemplateAnalysisV2",include_usage:bool)->str:
    """Build strict V2 constraints - verbatim copy, exact layout."""
    canvas=analysis.canvas
    style=analysis.style
    layout=analysis.layout
    copy=analysis.copywriting
    scene=analysis.visual_scene
    constraints=analysis.constraints
    #Verbatim copywriting block
    copy_lines=[]
    if copy.headline:copy_lines.append(f'Headline: "{copy.headline}"')
    if copy.subheadline:copy_lines.append(f'Subheadline: "{copy.subheadline}"')
    for i,b in enumerate(copy.benefits,1):copy_lines.append(f'Benefit {i}: "{b}"')
    for t in copy.body_texts:copy_lines.append(f'Body: "{t}"')
    if copy.cta:copy_lines.append(f'CTA: "{copy.cta}"')
    if copy.disclaimer:copy_lines.append(f'Disclaimer: "{copy.disclaimer}"')
    if copy.tagline:copy_lines.append(f'Tagline: "{copy.tagline}"')
    copy_block="\n".join(f"  - {ln}" for ln in copy_lines) if copy_lines else "  (no text content)"
    #Visual treatments
    treatments=", ".join(scene.visual_treatments) if scene.visual_treatments else "(none specified)"
    #Non-negotiables
    non_neg="\n".join(f"  - {item}" for item in constraints.non_negotiables) if constraints.non_negotiables else "  - All copywriting verbatim\n  - Layout structure preserved"
    #Palette
    palette_str=", ".join(style.palette[:5]) if style.palette else "(not specified)"
    usage_block=""
    if include_usage:
        usage_block="""

**HOW TO USE**:
Call `generate_image(template_slug="...", prompt="...")`
Template constraints are auto-applied."""
    return f"""**STRICT MODE - EXACT REPRODUCTION**

**Canvas**: {canvas.aspect_ratio} aspect ratio

**Layout Structure**: {layout.structure}
  Hierarchy: {layout.hierarchy}
  Alignment: {layout.alignment}

**VERBATIM COPYWRITING** (use EXACTLY as written, character-for-character):
{copy_block}

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
1. Use ALL copywriting text VERBATIM - do not paraphrase or reword
2. Preserve the layout structure described above
3. Replicate visual treatments (pill badges, shadows, etc.)
4. Maintain visual hierarchy
5. Place product as described in product_placement
{usage_block}"""


def _build_loose_v2(analysis:"TemplateAnalysisV2",include_usage:bool)->str:
    """Build loose V2 constraints - verbatim copy, flexible layout."""
    canvas=analysis.canvas
    style=analysis.style
    layout=analysis.layout
    copy=analysis.copywriting
    scene=analysis.visual_scene
    constraints=analysis.constraints
    #Verbatim copywriting block - STILL EXACT even in loose mode
    copy_lines=[]
    if copy.headline:copy_lines.append(f'Headline: "{copy.headline}"')
    if copy.subheadline:copy_lines.append(f'Subheadline: "{copy.subheadline}"')
    for i,b in enumerate(copy.benefits,1):copy_lines.append(f'Benefit {i}: "{b}"')
    for t in copy.body_texts:copy_lines.append(f'Body: "{t}"')
    if copy.cta:copy_lines.append(f'CTA: "{copy.cta}"')
    if copy.disclaimer:copy_lines.append(f'Disclaimer: "{copy.disclaimer}"')
    copy_block="\n".join(f"  - {ln}" for ln in copy_lines) if copy_lines else "  (no text content)"
    #Creative freedom
    freedom="\n".join(f"  ✓ {item}" for item in constraints.creative_freedom) if constraints.creative_freedom else "  ✓ Background details can vary\n  ✓ Exact props can change"
    #Palette
    palette_str=", ".join(style.palette[:3]) if style.palette else "(not specified)"
    usage_block=""
    if include_usage:
        usage_block="""

**HOW TO USE**:
Call `generate_image(template_slug="...", prompt="...", strict=False)`"""
    return f"""**LOOSE MODE - PRESERVE INTENT, ALLOW VARIATION**

**Canvas**: {canvas.aspect_ratio} (preserve aspect ratio)

**Layout Intent**: {layout.structure}
  (Preserve general structure, exact positions can vary)

**VERBATIM COPYWRITING** (STILL EXACT - do not paraphrase):
{copy_block}

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

✗ Do NOT change copywriting text - use VERBATIM
✗ Do NOT change aspect ratio
✗ Do NOT remove key elements (headline, benefits, product)
✗ Do NOT change the overall layout intent
{usage_block}"""


def format_v2_summary(analysis:"TemplateAnalysisV2")->str:
    """Format a brief V2 analysis summary for context display."""
    copy=analysis.copywriting
    items=[]
    if copy.headline:items.append("headline")
    if copy.benefits:items.append(f"{len(copy.benefits)} benefits")
    if copy.disclaimer:items.append("disclaimer")
    copy_summary=", ".join(items) if items else "no copy"
    treatments=len(analysis.visual_scene.visual_treatments)
    return f"V2: {analysis.layout.structure[:40]}..., {copy_summary}, {treatments} treatments"
