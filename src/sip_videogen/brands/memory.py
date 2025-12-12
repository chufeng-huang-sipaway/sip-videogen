"""Brand memory access functions.

Provides hierarchical access to brand information:
- L0 (Summary): Always available
- L1 (Details): Fetched on demand by detail type
- L2 (Assets): File listings
"""

from __future__ import annotations

import logging
from typing import Literal

from .models import (
    BrandSummary,
)
from .storage import get_brand_dir, load_brand, load_brand_summary

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
        category: Optional filter by category (logo, packaging, lifestyle, mascot, marketing)

    Returns:
        List of asset info dicts with path, category, name.
    """
    brand_dir = get_brand_dir(slug)
    assets_dir = brand_dir / "assets"

    if not assets_dir.exists():
        return []

    assets = []
    categories = (
        [category] if category else ["logo", "packaging", "lifestyle", "mascot", "marketing"]
    )

    for cat in categories:
        cat_dir = assets_dir / cat
        if not cat_dir.exists():
            continue

        for file_path in cat_dir.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in [
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
            ]:
                assets.append(
                    {
                        "path": str(file_path),
                        "category": cat,
                        "name": file_path.stem,
                        "filename": file_path.name,
                    }
                )

    return assets
