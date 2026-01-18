"""Knowledge summary builders for lean context loading.
Per IMPLEMENTATION_PLAN.md Stage 3 - Lean Context Loading (CLAUDE.md Pattern).
Provides compact summaries with tool pointers instead of full data injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sip_studio.config.logging import get_logger

if TYPE_CHECKING:
    from sip_studio.brands.models import (
        BrandSummary,
        ProductSummary,
        ProjectSummary,
        StyleReferenceSummary,
    )
logger = get_logger(__name__)
__all__ = [
    "build_brand_knowledge_pointer",
    "build_product_knowledge_pointer",
    "build_products_list_summary",
    "build_project_knowledge_pointer",
    "build_style_reference_knowledge_pointer",
    "build_style_references_list_summary",
    "build_knowledge_context",
]


def build_brand_knowledge_pointer(summary: "BrandSummary") -> str:
    """Build lean brand context with tool pointers.
    Instead of injecting full brand identity, provides summary + tool hints.
    ~150 tokens vs ~500+ for full context.
    """
    colors = ", ".join(summary.primary_colors[:3]) if summary.primary_colors else "Not defined"
    return f"""## Brand: {summary.name}
**Tagline**: {summary.tagline}
**Category**: {summary.category}
**Tone**: {summary.tone}
**Colors**: {colors}
**Visual**: {summary.visual_style[:100] if summary.visual_style else "Not defined"}
**Audience**: {summary.audience_summary[:100] if summary.audience_summary else "Not defined"}

→ Use `fetch_brand_detail(type)` for details (visual_identity, voice_guidelines, etc)."""


def build_product_knowledge_pointer(summary: "ProductSummary") -> str:
    """Build lean product context with tool pointers.
    ~50 tokens vs ~200+ for full product context.
    """
    pkg = "Yes" if summary.has_packaging_text else "No"
    return f"""### Product: {summary.name} (`{summary.slug}`)
{summary.description[:150]}...
**Attrs**: {summary.attribute_count} | **Packaging**: {pkg}
→ Use `get_product_detail("{summary.slug}")` for attributes, images, packaging text."""


def build_products_list_summary(products: list["ProductSummary"]) -> str:
    """Build compact product list for context.
    ~30 tokens per product vs ~200+ for full product details.
    """
    if not products:
        return "No products registered. Use `manage_product(action='create')` to add one."
    lines = ["**Products** ({} total):".format(len(products))]
    for p in products[:10]:
        pkg = "📦" if p.has_packaging_text else ""
        lines.append(f"- `{p.slug}`: {p.name[:30]} {pkg}")
    if len(products) > 10:
        lines.append(f"  ...and {len(products)-10} more")
    lines.append("→ Use `get_product_detail(slug)` for full info, `list_products()` for all.")
    return "\n".join(lines)


def build_project_knowledge_pointer(summary: "ProjectSummary") -> str:
    """Build lean project context with tool pointer."""
    return f"""### Active Project: {summary.name} (`{summary.slug}`)
**Status**: {summary.status}
**Assets**: {summary.asset_count}
→ Use `get_project_detail("{summary.slug}")` for instructions and deliverables."""


def build_style_reference_knowledge_pointer(summary: "StyleReferenceSummary") -> str:
    """Build lean style reference context with tool pointer."""
    mode = "Strict" if summary.default_strict else "Loose"
    return f"""### Style: {summary.name} (`{summary.slug}`)
{summary.description[:100] if summary.description else"No description"}
**Mode**: {mode}
→ Use `get_style_reference(slug="{summary.slug}")` for layout constraints."""


def build_style_references_list_summary(style_refs: list["StyleReferenceSummary"]) -> str:
    """Build compact style reference list for context."""
    if not style_refs:
        return "No style references. Use `manage_style_reference(action='create')` to add one."
    lines = ["**Style References** ({} total):".format(len(style_refs))]
    for sr in style_refs[:5]:
        mode = "⚡" if sr.default_strict else "~"
        lines.append(f"- `{sr.slug}`: {sr.name[:25]} {mode}")
    if len(style_refs) > 5:
        lines.append(f"  ...and {len(style_refs)-5} more")
    lines.append("→ Use `get_style_reference(slug=...)` for constraints.")
    return "\n".join(lines)


def build_knowledge_context(
    brand_summary: "BrandSummary|None" = None,
    products: "list[ProductSummary]|None" = None,
    style_refs: "list[StyleReferenceSummary]|None" = None,
    active_project: "ProjectSummary|None" = None,
    conversation_summary: str | None = None,
) -> str:
    """Build complete lean context for a chat turn.
    Combines all knowledge pointers into a single context block.
    This replaces full data injection with ~300 tokens of context + tool pointers.
    Args:
        brand_summary: Current brand summary (L0)
        products: List of product summaries (L0)
        style_refs: List of style reference summaries (L0)
        active_project: Active project summary (L0)
        conversation_summary: Compacted conversation summary (if any)
    Returns:
        Formatted context string for system prompt injection.
    """
    sections = []
    # Conversation summary first (if exists)
    if conversation_summary:
        sections.append(f"## Previous Conversation Summary\n{conversation_summary}")
    # Brand context
    if brand_summary:
        sections.append(build_brand_knowledge_pointer(brand_summary))
    # Active project
    if active_project:
        sections.append(build_project_knowledge_pointer(active_project))
    # Products summary
    if products is not None:
        sections.append(build_products_list_summary(products))
    # Style references summary
    if style_refs is not None:
        sections.append(build_style_references_list_summary(style_refs))
    if not sections:
        return "No brand context loaded. Use `load_brand(slug)` to start."
    return "\n\n---\n\n".join(sections)
