"""Agent tools for brand memory access.

DEPRECATED: This module is a backwards-compatibility shim.
Use sip_studio.advisor.tools instead.

This shim will be removed in a future release.
"""

from __future__ import annotations

import logging
import warnings

logger = logging.getLogger(__name__)
__all__ = ["browse_brand_assets", "fetch_brand_detail", "set_brand_context", "get_brand_context"]
# Lazy loading to avoid circular import (advisor.tools -> brands.models -> brands.__init__ -> brands.tools)
_cache = {}


def __getattr__(name):
    """Lazy load browse_brand_assets and fetch_brand_detail from advisor.tools."""
    if name in ("browse_brand_assets", "fetch_brand_detail"):
        if name not in _cache:
            from sip_studio.advisor import tools as advisor_tools

            _cache["browse_brand_assets"] = advisor_tools.browse_brand_assets
            _cache["fetch_brand_detail"] = advisor_tools.fetch_brand_detail
        return _cache[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def set_brand_context(slug: str | None) -> None:
    """DEPRECATED: No longer needed. Active brand is managed by storage."""
    warnings.warn(
        "set_brand_context() is deprecated. Use storage.set_active_brand().",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "DEPRECATED: set_brand_context() called with slug=%s. Delegating to storage.set_active_brand().",
        slug,
    )
    from sip_studio.brands.storage import set_active_brand

    set_active_brand(slug)


def get_brand_context() -> str | None:
    """DEPRECATED: Use get_active_brand() from sip_studio.brands.storage instead."""
    warnings.warn(
        "get_brand_context() deprecated. Use storage.get_active_brand().",
        DeprecationWarning,
        stacklevel=2,
    )
    from sip_studio.brands.storage import get_active_brand

    return get_active_brand()
