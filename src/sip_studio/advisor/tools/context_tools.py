"""Context fetching tools with caching for lean context pattern.
Per IMPLEMENTATION_PLAN.md Stage 3 - Lean Context Loading.
Provides cached on-demand fetching for brand/product/style details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from agents import function_tool

from sip_studio.advisor.session_context_cache import SessionContextCache
from sip_studio.config.logging import get_logger

from ._common import get_active_brand, load_product, load_style_reference

if TYPE_CHECKING:
    pass
logger = get_logger(__name__)
__all__ = [
    "fetch_context_cached",
    "get_cached_product_context",
    "get_cached_style_reference_context",
    "_impl_fetch_context_cached",
    "_impl_get_cached_product_context",
    "_impl_get_cached_style_reference_context",
    "set_context_cache",
    "get_context_cache",
]
# Module-level cache reference (set per-session by BrandAdvisor)
_active_context_cache: SessionContextCache | None = None


def set_context_cache(cache: SessionContextCache | None) -> None:
    """Set the active context cache for tool operations."""
    global _active_context_cache
    _active_context_cache = cache


def get_context_cache() -> SessionContextCache | None:
    """Get the active context cache."""
    return _active_context_cache


def _impl_fetch_context_cached(
    context_type: Literal["brand", "product", "style_reference", "project"],
    slug: str | None = None,
    version: str | None = None,
) -> str:
    """Fetch context with caching. Core implementation.
    Args:
        context_type: Type of context to fetch
        slug: Entity slug (required for product/style_reference/project)
        version: Source version for cache validation
    Returns:
        Formatted context string
    """
    from sip_studio.brands.context import (
        build_brand_context,
        build_product_context,
        build_project_context,
        build_style_reference_context,
    )
    from sip_studio.brands.storage import load_brand_summary, load_project

    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand. Use load_brand() first."
    cache_key = f"{context_type}:{slug or'brand'}"
    # Check cache
    if _active_context_cache:
        cached = _active_context_cache.get(cache_key, version)
        if cached:
            logger.debug(f"Cache hit for {cache_key}")
            return cached
    # Fetch fresh
    result: str = ""
    source_ver: str = ""
    if context_type == "brand":
        result = build_brand_context(brand_slug)
        summary = load_brand_summary(brand_slug)
        source_ver = summary.last_generation if summary and summary.last_generation else ""
    elif context_type == "product":
        if not slug:
            return "Error: product slug required"
        result = build_product_context(brand_slug, slug)
        p = load_product(brand_slug, slug)
        source_ver = p.updated_at.isoformat() if p else ""
    elif context_type == "style_reference":
        if not slug:
            return "Error: style_reference slug required"
        result = build_style_reference_context(brand_slug, slug)
        sr = load_style_reference(brand_slug, slug)
        source_ver = sr.updated_at.isoformat() if sr else ""
    elif context_type == "project":
        if not slug:
            return "Error: project slug required"
        result = build_project_context(brand_slug, slug)
        proj = load_project(brand_slug, slug)
        source_ver = proj.updated_at.isoformat() if proj else ""
    else:
        return f"Error: Unknown context type: {context_type}"
    # Cache result
    if _active_context_cache and result and not result.startswith("Error"):
        _active_context_cache.set(cache_key, result, source_ver or "unknown", ttl_minutes=30)
        logger.debug(f"Cached {cache_key}")
    return result


def _impl_get_cached_product_context(product_slug: str) -> str:
    """Get product context with caching."""
    return _impl_fetch_context_cached("product", product_slug)


def _impl_get_cached_style_reference_context(style_ref_slug: str) -> str:
    """Get style reference context with caching."""
    return _impl_fetch_context_cached("style_reference", style_ref_slug)


@function_tool
def fetch_context_cached(
    context_type: Literal["brand", "product", "style_reference", "project"], slug: str | None = None
) -> str:
    """Fetch detailed context information with caching.
    Use this for on-demand context loading. Results are cached per session
    and automatically invalidated when source data changes.
    Args:
        context_type: Type of context:
            - "brand": Full brand identity context
            - "product": Product details including attributes and images
            - "style_reference": Style reference layout constraints
            - "project": Project instructions and deliverables
        slug: Entity slug (required for product/style_reference/project)
    Returns:
        Formatted context string for the requested entity.
    """
    return _impl_fetch_context_cached(context_type, slug)


@function_tool
def get_cached_product_context(product_slug: str) -> str:
    """Get full product context with caching.
    Convenience tool for fetching product details. Uses session cache
    to avoid redundant file reads across conversation turns.
    Args:
        product_slug: Product identifier (e.g., "coffee-mug")
    Returns:
        Complete product context including attributes, images, packaging text.
    """
    return _impl_get_cached_product_context(product_slug)


@function_tool
def get_cached_style_reference_context(style_ref_slug: str) -> str:
    """Get full style reference context with caching.
    Convenience tool for fetching style reference layout constraints.
    Uses session cache to avoid redundant file reads.
    Args:
        style_ref_slug: Style reference identifier (e.g., "hero-banner")
    Returns:
        Complete style reference context including layout constraints.
    """
    return _impl_get_cached_style_reference_context(style_ref_slug)
