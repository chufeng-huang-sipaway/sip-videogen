"""Brand information and exploration tools."""

from __future__ import annotations

import json
from typing import Literal

from agents import function_tool

from sip_videogen.brands.product_description import extract_attributes_from_description
from sip_videogen.config.logging import get_logger

from . import _common
from .memory_tools import emit_tool_thinking

logger = get_logger(__name__)


def _impl_load_brand(
    slug: str | None = None, detail_level: Literal["summary", "full"] = "summary"
) -> str:
    """Implementation of load_brand tool."""
    from sip_videogen.brands.memory import list_brand_assets

    if not slug:
        slug = _common.get_active_brand()
    if not slug:
        brands = _common.list_brands()
        if not brands:
            return "No brands found. Create a brand first by telling me about your brand, and I'll help you develop its identity."
        brand_list = "\n".join(f"  - {b.slug}: {b.name}" for b in brands)
        return f"No active brand. Available brands:\n{brand_list}\n\nTell me which brand to work with, or describe a new brand to create."
    identity = _common.storage_load_brand(slug)
    if identity is None:
        return f"Error: Brand not found: {slug}"
    try:
        assets = list_brand_assets(slug)
        asset_count = len(assets)
    except Exception:
        assets = []
        asset_count = 0
    if detail_level == "summary":
        context_parts = []
        context_parts.append(f"# Brand: {identity.core.name}")
        context_parts.append(f"*{identity.core.tagline}*\n")
        context_parts.append(f"**Category**: {identity.positioning.market_category}")
        if identity.voice.tone_attributes:
            context_parts.append(f"**Tone**: {', '.join(identity.voice.tone_attributes[:3])}")
        if identity.visual.primary_colors:
            colors = ", ".join(f"{c.name} ({c.hex})" for c in identity.visual.primary_colors[:3])
            context_parts.append(f"**Colors**: {colors}")
        if identity.visual.style_keywords:
            context_parts.append(f"**Style**: {', '.join(identity.visual.style_keywords[:3])}")
        context_parts.append(f"**Audience**: {identity.audience.primary_summary}")
        context_parts.append(f"**Assets**: {asset_count} files available")
        context_parts.append("")
        context_parts.append("---")
        context_parts.append(
            "For complete brand details including full visual identity, voice guidelines, and positioning, use `load_brand(detail_level='full')`"
        )
        return "\n".join(context_parts)
    # Full mode
    context_parts = []
    context_parts.append(f"# Brand: {identity.core.name}")
    context_parts.append(f"*{identity.core.tagline}*\n")
    context_parts.append("## Summary")
    context_parts.append(f"- **Category**: {identity.positioning.market_category}")
    context_parts.append(f"- **Mission**: {identity.core.mission}")
    if identity.voice.tone_attributes:
        context_parts.append(f"- **Tone**: {', '.join(identity.voice.tone_attributes[:3])}")
    context_parts.append("")
    context_parts.append("## Visual Identity")
    if identity.visual.primary_colors:
        colors = ", ".join(f"{c.name} ({c.hex})" for c in identity.visual.primary_colors)
        context_parts.append(f"- **Primary Colors**: {colors}")
    if identity.visual.style_keywords:
        context_parts.append(f"- **Style**: {', '.join(identity.visual.style_keywords)}")
    if identity.visual.overall_aesthetic:
        context_parts.append(f"- **Aesthetic**: {identity.visual.overall_aesthetic[:200]}...")
    context_parts.append("")
    context_parts.append("## Brand Voice")
    context_parts.append(f"- **Personality**: {identity.voice.personality}")
    if identity.voice.key_messages:
        context_parts.append("- **Key Messages**:")
        for msg in identity.voice.key_messages[:3]:
            context_parts.append(f'  - "{msg}"')
    context_parts.append("")
    context_parts.append("## Target Audience")
    context_parts.append(f"- **Primary**: {identity.audience.primary_summary}")
    if identity.audience.age_range:
        context_parts.append(f"- **Age**: {identity.audience.age_range}")
    context_parts.append("")
    context_parts.append("## Positioning")
    context_parts.append(f"- **UVP**: {identity.positioning.unique_value_proposition}")
    if identity.positioning.positioning_statement:
        context_parts.append(f"- **Statement**: {identity.positioning.positioning_statement}")
    context_parts.append("")
    if assets:
        by_category: dict[str, list[dict]] = {}
        for asset in assets:
            cat = asset.get("category", "other")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(asset)
        context_parts.append("## Available Assets")
        for category, files in sorted(by_category.items()):
            context_parts.append(f"- **{category}**: {len(files)} files")
        context_parts.append("")
    if identity.core.values:
        context_parts.append("## Core Values")
        for val in identity.core.values[:5]:
            context_parts.append(f"- {val}")
        context_parts.append("")
    return "\n".join(context_parts)


def _impl_list_products() -> str:
    """Implementation of list_products tool."""
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    products = _common.storage_list_products(brand_slug)
    if not products:
        return f"No products found for brand '{brand_slug}'. Use create_product() to add products."
    lines = [f"Products for brand '{brand_slug}':\n"]
    for product in products:
        primary = f" (primary image: {product.primary_image})" if product.primary_image else ""
        attrs = f", {product.attribute_count} attributes" if product.attribute_count > 0 else ""
        lines.append(f"- **{product.name}** (`{product.slug}`){attrs}{primary}")
        if product.description:
            desc = product.description
            if len(desc) > 100:
                desc = desc[:100] + "..."
            lines.append(f"  {desc}")
    lines.append("")
    lines.append("---")
    lines.append("Use `get_product_detail(product_slug)` for full product information.")
    return "\n".join(lines)


def _impl_list_projects() -> str:
    """Implementation of list_projects tool."""
    from sip_videogen.brands.storage import get_active_project as storage_get_active_project

    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    projects = _common.storage_list_projects(brand_slug)
    active_project = storage_get_active_project(brand_slug)
    if not projects:
        return f"No projects found for brand '{brand_slug}'. Use the bridge to create projects."
    lines = [f"Projects for brand '{brand_slug}':\n"]
    for project in projects:
        active_marker = " ★ ACTIVE" if project.slug == active_project else ""
        status_badge = f"[{project.status.value}]"
        assets = f", {project.asset_count} assets" if project.asset_count > 0 else ""
        line = f"- **{project.name}** (`{project.slug}`) {status_badge}{assets}{active_marker}"
        lines.append(line)
    lines.append("")
    lines.append("---")
    lines.append(
        "Use `get_project_detail(project_slug)` for full project info including instructions."
    )
    return "\n".join(lines)


def _impl_get_product_detail(product_slug: str) -> str:
    """Implementation of get_product_detail tool."""
    from sip_videogen.brands.memory import get_product_full

    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    product = get_product_full(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."
    description_text, desc_attrs = extract_attributes_from_description(product.description or "")
    attributes = product.attributes or desc_attrs
    lines = [f"# Product: {product.name}"]
    lines.append(f"*Slug: `{product.slug}`*\n")
    if description_text:
        lines.append("## Description")
        lines.append(description_text)
        lines.append("")
    if attributes:
        lines.append("## Attributes")
        for attr in attributes:
            lines.append(f"- **{attr.key}** ({attr.category}): {attr.value}")
        lines.append("")
    if product.images:
        lines.append("## Images")
        for img in product.images:
            primary_marker = " ★ PRIMARY" if img == product.primary_image else ""
            lines.append(f"- `{img}`{primary_marker}")
        lines.append("")
    lines.append("## Metadata")
    lines.append(f"- Created: {product.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- Updated: {product.updated_at.strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


def _impl_get_project_detail(project_slug: str) -> str:
    """Implementation of get_project_detail tool."""
    from sip_videogen.brands.memory import get_project_full
    from sip_videogen.brands.storage import get_active_project as storage_get_active_project

    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    project = get_project_full(brand_slug, project_slug)
    if project is None:
        return f"Error: Project '{project_slug}' not found in brand '{brand_slug}'."
    active_project = storage_get_active_project(brand_slug)
    is_active = project.slug == active_project
    lines = [f"# Project: {project.name}"]
    lines.append(f"*Slug: `{project.slug}`*\n")
    active_marker = " ★ ACTIVE" if is_active else ""
    lines.append(f"**Status**: {project.status.value}{active_marker}\n")
    if project.instructions:
        lines.append("## Instructions")
        lines.append(project.instructions)
        lines.append("")
    else:
        lines.append("## Instructions")
        lines.append("*No instructions set.*")
        lines.append("")
    assets = _common.list_project_assets(brand_slug, project_slug)
    if assets:
        lines.append("## Generated Assets")
        lines.append(f"This project has {len(assets)} generated assets:")
        for asset in assets[:10]:
            lines.append(f"- `{asset}`")
        if len(assets) > 10:
            lines.append(f"- *...and {len(assets) - 10} more*")
        lines.append("")
    lines.append("## Metadata")
    lines.append(f"- Created: {project.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- Updated: {project.updated_at.strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


def _impl_fetch_brand_detail(
    detail_type: Literal[
        "visual_identity", "voice_guidelines", "audience_profile", "positioning", "full_identity"
    ],
) -> str:
    """Implementation of fetch_brand_detail."""
    from sip_videogen.brands.memory import get_brand_detail

    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set. Cannot fetch brand details."
    step_id = emit_tool_thinking(
        "Looking at your brand identity...",
        detail_type.replace("_", " "),
        expertise="Research",
        status="pending",
    )
    logger.info("Agent fetching brand detail: %s for %s", detail_type, slug)
    try:
        result = get_brand_detail(slug, detail_type)
        emit_tool_thinking(
            "Brand context loaded", "", expertise="Research", status="complete", step_id=step_id
        )
        return result
    except Exception as e:
        emit_tool_thinking(
            "Couldn't load brand context",
            str(e)[:100],
            expertise="Research",
            status="failed",
            step_id=step_id,
        )
        raise


def _impl_browse_brand_assets(category: str | None = None) -> str:
    """Implementation of browse_brand_assets."""
    from sip_videogen.brands.memory import list_brand_assets

    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set. Cannot browse assets."
    cat_label = category or "all"
    step_id = emit_tool_thinking(
        "Browsing your brand assets...", cat_label, expertise="Research", status="pending"
    )
    logger.info("Agent browsing brand assets: category=%s for %s", category, slug)
    try:
        assets = list_brand_assets(slug, category)
        if not assets:
            emit_tool_thinking(
                "No assets found", "", expertise="Research", status="complete", step_id=step_id
            )
            return f"No assets found{' in category ' + category if category else ''}."
        emit_tool_thinking(
            f"Found {len(assets)} assets",
            "",
            expertise="Research",
            status="complete",
            step_id=step_id,
        )
        return json.dumps(assets, indent=2)
    except Exception as e:
        emit_tool_thinking(
            "Couldn't browse assets",
            str(e)[:100],
            expertise="Research",
            status="failed",
            step_id=step_id,
        )
        raise


@function_tool
def load_brand(
    slug: str | None = None, detail_level: Literal["summary", "full"] = "summary"
) -> str:
    """Load brand identity and context for creative work.
    Call this at the start of a session to understand the brand you're working with.
    The brand context informs all creative decisions.
    Args:
        slug: Brand slug to load. If not provided, uses active brand.
        detail_level: Level of detail to return:
            - "summary" (default): Quick overview (~500 chars)
            - "full": Complete brand context (~2000 chars)
    Returns:
        Formatted brand context as markdown.
    """
    return _impl_load_brand(slug, detail_level)


@function_tool
def list_products() -> str:
    """List all products for the active brand.
    Returns:
        Formatted list of products with names, slugs, image counts, and descriptions.
        Use get_product_detail() for complete product information.
    """
    return _impl_list_products()


@function_tool
def list_projects() -> str:
    """List all projects/campaigns for the active brand.
    Returns:
        Formatted list of projects with names, slugs, status, and asset counts.
        Active project is marked with ★. Use get_project_detail() for complete info.
    """
    return _impl_list_projects()


@function_tool
def get_product_detail(product_slug: str) -> str:
    """Get detailed information about a specific product.
    Args:
        product_slug: Product identifier (e.g., "night-cream").
    Returns:
        Complete product info including description, attributes, and images.
    """
    return _impl_get_product_detail(product_slug)


@function_tool
def get_project_detail(project_slug: str) -> str:
    """Get detailed information about a specific project.
    Args:
        project_slug: Project identifier (e.g., "summer-campaign").
    Returns:
        Complete project info including instructions and generated assets.
    """
    return _impl_get_project_detail(project_slug)


@function_tool
def fetch_brand_detail(
    detail_type: Literal[
        "visual_identity", "voice_guidelines", "audience_profile", "positioning", "full_identity"
    ],
) -> str:
    """Fetch detailed brand information.
    Use this tool to get comprehensive information about a specific aspect
    of the brand before making creative decisions.
    Args:
        detail_type: The type of detail to fetch:
            - "visual_identity": Colors, typography, imagery guidelines
            - "voice_guidelines": Tone, messaging, copy examples
            - "audience_profile": Target audience demographics and psychographics
            - "positioning": Market position and competitive differentiation
            - "full_identity": Complete brand identity (use sparingly)
    Returns:
        JSON string containing the requested brand details.
    """
    return _impl_fetch_brand_detail(detail_type)


@function_tool
def browse_brand_assets(category: str | None = None) -> str:
    """Browse existing brand assets.
    Use this tool to see what assets have already been generated for the brand.
    This helps maintain consistency and avoid recreating existing work.
    Args:
        category: Optional category filter. One of:
            - "logo": Brand logos
            - "packaging": Product packaging images
            - "lifestyle": Lifestyle/in-use photography
            - "mascot": Brand mascot images
            - "marketing": Marketing materials
            - None: Return all assets
    Returns:
        JSON string listing available assets with paths and metadata.
    """
    return _impl_browse_brand_assets(category)
