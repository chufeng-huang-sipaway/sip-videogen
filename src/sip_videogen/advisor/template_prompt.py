"""Template prompt helper for building layout constraints.
Generates prompt constraints from TemplateAnalysis based on strict/loose mode.
Used by TemplateContextBuilder to format constraints for the agent.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sip_videogen.brands.models import TemplateAnalysis
def build_template_constraints(analysis:"TemplateAnalysis",strict:bool)->str:
    """Build template constraints string for agent prompts.
    Args:
        analysis: The TemplateAnalysis containing layout specs.
        strict: True for exact reproduction, False for controlled variation.
    Returns:
        Formatted constraint string for injection into agent context.
    """
    if strict:return _build_strict_constraints(analysis)
    return _build_loose_constraints(analysis)
def _build_strict_constraints(analysis:"TemplateAnalysis")->str:
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

**HOW TO USE**:
Call `generate_image(template_slug="...", prompt="...")`
Template constraints are auto-applied to generation."""
def _build_loose_constraints(analysis:"TemplateAnalysis")->str:
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

**HOW TO USE**:
Call `generate_image(template_slug="...", prompt="...", strict=False)`"""
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
