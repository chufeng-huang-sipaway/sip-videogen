"""Brand memory access functions.

Provides hierarchical access to brand information:
- L0 (Summary): Always available
- L1 (Details): Fetched on demand by detail type
- L2 (Assets): File listings

Also provides access to Product and Project memory layers.
"""

from __future__ import annotations

import logging
from typing import Literal

from sip_videogen.constants import ALLOWED_IMAGE_EXTS, ALLOWED_VIDEO_EXTS, ASSET_CATEGORIES

from .models import (
    BrandSummary,
    ProductFull,
    ProductSummary,
    ProjectFull,
    ProjectSummary,
)
from .storage import (
    get_brand_dir,
    list_product_images,
    load_brand,
    load_brand_summary,
    load_product,
    load_product_summary,
    load_project,
    load_project_summary,
)

logger = logging.getLogger(__name__)

# Valid detail types for fetch_brand_detail
DetailType = Literal[
    "visual_identity",
    "voice_guidelines",
    "audience_profile",
    "positioning",
    "full_identity",
]


def get_brand_summary(slug: str) -> BrandSummary | None:
    """Get the L0 summary layer for a brand.

    This is what agents always see in their context.
    """
    return load_brand_summary(slug)


def get_brand_detail(slug: str, detail_type: DetailType) -> str:
    """Get a specific detail layer (L1) for a brand.

    Args:
        slug: Brand identifier
        detail_type: One of "visual_identity", "voice_guidelines",
                    "audience_profile", "positioning", "full_identity"

    Returns:
        JSON string of the requested detail, or error message.
    """
    identity = load_brand(slug)

    if identity is None:
        return f"Error: Brand '{slug}' not found"

    if detail_type == "visual_identity":
        return identity.visual.model_dump_json(indent=2)
    elif detail_type == "voice_guidelines":
        return identity.voice.model_dump_json(indent=2)
    elif detail_type == "audience_profile":
        return identity.audience.model_dump_json(indent=2)
    elif detail_type == "positioning":
        return identity.positioning.model_dump_json(indent=2)
    elif detail_type == "full_identity":
        return identity.model_dump_json(indent=2)
    else:
        return f"Error: Unknown detail type '{detail_type}'"


def list_brand_assets(slug: str, category: str | None = None) -> list[dict]:
    """List assets for a brand (L2 layer).

    Args:
        slug: Brand identifier
        category: Optional filter by category (logo, packaging, lifestyle, mascot, marketing, video)

    Returns:
        List of asset info dicts with path, category, name, type (image/video).
    """
    brand_dir = get_brand_dir(slug)
    assets_dir = brand_dir / "assets"
    if not assets_dir.exists():
        return []
    assets = []
    cats = [category] if category else ASSET_CATEGORIES
    allowed_exts = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS
    for cat in cats:
        cat_dir = assets_dir / cat
        if not cat_dir.exists():
            continue
        for fp in cat_dir.glob("*"):
            if not fp.is_file():
                continue
            ext = fp.suffix.lower()
            if ext in allowed_exts:
                asset_type = "video" if ext in ALLOWED_VIDEO_EXTS else "image"
                assets.append(
                    {
                        "path": str(fp),
                        "category": cat,
                        "name": fp.stem,
                        "filename": fp.name,
                        "type": asset_type,
                    }
                )
    return assets


def list_brand_videos(slug: str) -> list[dict]:
    """List only video assets for a brand.

    Args:
        slug: Brand identifier

    Returns:
        List of video asset dicts with path, category, name.
    """
    # Check both 'generated' and 'video' folders since videos can be in either
    videos = []
    for cat in ["generated", "video"]:
        videos.extend(
            [a for a in list_brand_assets(slug, category=cat) if a.get("type") == "video"]
        )
    return videos


# =============================================================================
# Product Memory Access
# =============================================================================


def get_product_summary(brand_slug: str, product_slug: str) -> ProductSummary | None:
    """Get the L0 summary layer for a product.

    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.

    Returns:
        ProductSummary or None if not found.
    """
    return load_product_summary(brand_slug, product_slug)


def get_product_detail(brand_slug: str, product_slug: str) -> str:
    """Get detailed product info as JSON string for agent context.

    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.

    Returns:
        JSON string of the product details, or error message.
    """
    product = load_product(brand_slug, product_slug)

    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'"

    return product.model_dump_json(indent=2)


def get_product_images_for_generation(brand_slug: str, product_slug: str) -> list[str]:
    """Get product images for use in generation.

    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.

    Returns:
        List of brand-relative image paths.
    """
    return list_product_images(brand_slug, product_slug)


def get_product_full(brand_slug: str, product_slug: str) -> ProductFull | None:
    """Get the full product details (L1 layer).

    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.

    Returns:
        ProductFull or None if not found.
    """
    return load_product(brand_slug, product_slug)


# =============================================================================
# Project Memory Access
# =============================================================================


def get_project_summary(brand_slug: str, project_slug: str) -> ProjectSummary | None:
    """Get the L0 summary layer for a project.

    Args:
        brand_slug: Brand identifier.
        project_slug: Project identifier.

    Returns:
        ProjectSummary or None if not found.
    """
    return load_project_summary(brand_slug, project_slug)


def get_project_instructions(brand_slug: str, project_slug: str) -> str:
    """Get project instructions markdown.

    Args:
        brand_slug: Brand identifier.
        project_slug: Project identifier.

    Returns:
        Instructions markdown string, or error message.
    """
    project = load_project(brand_slug, project_slug)

    if project is None:
        return f"Error: Project '{project_slug}' not found in brand '{brand_slug}'"

    return project.instructions


def get_project_detail(brand_slug: str, project_slug: str) -> str:
    """Get detailed project info as JSON string for agent context.

    Args:
        brand_slug: Brand identifier.
        project_slug: Project identifier.

    Returns:
        JSON string of the project details, or error message.
    """
    project = load_project(brand_slug, project_slug)

    if project is None:
        return f"Error: Project '{project_slug}' not found in brand '{brand_slug}'"

    return project.model_dump_json(indent=2)


def get_project_full(brand_slug: str, project_slug: str) -> ProjectFull | None:
    """Get the full project details (L1 layer).

    Args:
        brand_slug: Brand identifier.
        project_slug: Project identifier.

    Returns:
        ProjectFull or None if not found.
    """
    return load_project(brand_slug, project_slug)
