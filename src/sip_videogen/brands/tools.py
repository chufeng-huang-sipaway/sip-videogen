"""Agent tools for brand memory access.

These functions are registered as tools in brand-aware agents,
allowing them to explore the brand memory hierarchy.

Note: This module is DEPRECATED. Use sip_videogen.advisor.tools instead.
The new advisor tools provide a better interface with explicit brand handling.
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from agents import function_tool

from .memory import (
    get_brand_detail,
    list_brand_assets,
)

logger = logging.getLogger(__name__)

# Global to track current brand context
_current_brand_slug: str | None = None


def set_brand_context(slug: str | None) -> None:
    """Set the current brand context for tools.

    Called before running agents to establish which brand they're working with.
    """
    global _current_brand_slug
    _current_brand_slug = slug
    logger.debug("Brand context set to: %s", slug or "(none)")


def get_brand_context() -> str | None:
    """Get the current brand context."""
    return _current_brand_slug


# =============================================================================
# Implementation Functions (for testing)
# =============================================================================


def _impl_fetch_brand_detail(
    detail_type: Literal[
        "visual_identity",
        "voice_guidelines",
        "audience_profile",
        "positioning",
        "full_identity",
    ],
) -> str:
    """Implementation of fetch_brand_detail."""
    slug = _current_brand_slug

    if not slug:
        return "Error: No brand context set. Cannot fetch brand details."

    logger.info("Agent fetching brand detail: %s for %s", detail_type, slug)
    return get_brand_detail(slug, detail_type)


def _impl_browse_brand_assets(category: str | None = None) -> str:
    """Implementation of browse_brand_assets."""
    slug = _current_brand_slug

    if not slug:
        return "Error: No brand context set. Cannot browse assets."

    logger.info("Agent browsing brand assets: category=%s for %s", category, slug)
    assets = list_brand_assets(slug, category)

    if not assets:
        return f"No assets found{' in category ' + category if category else ''}."

    return json.dumps(assets, indent=2)


# =============================================================================
# Wrapped Tools for Agent
# =============================================================================


@function_tool
def fetch_brand_detail(
    detail_type: Literal[
        "visual_identity",
        "voice_guidelines",
        "audience_profile",
        "positioning",
        "full_identity",
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
