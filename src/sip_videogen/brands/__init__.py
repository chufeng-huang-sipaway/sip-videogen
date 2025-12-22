"""Brand management system for sip-videogen.

This package provides persistent brand storage, hierarchical memory,
and brand-aware agent tools for the brand kit workflow.
"""

# Models (Tasks 1.2-1.5)
# Memory layer access functions (Task 2.1)
# Context builder (Task 2.3)
from .context import (
    DETAIL_DESCRIPTIONS,
    BrandContextBuilder,
    HierarchicalContextBuilder,
    ProductContextBuilder,
    ProjectContextBuilder,
    build_brand_context,
    build_product_context,
    build_project_context,
    build_turn_context,
)
from .memory import (
    DetailType,
    get_brand_detail,
    get_brand_summary,
    get_product_detail,
    get_product_full,
    get_product_images_for_generation,
    get_product_summary,
    get_project_detail,
    get_project_full,
    get_project_instructions,
    get_project_summary,
    list_brand_assets,
)
from .models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    BrandIndex,
    BrandIndexEntry,
    BrandSummary,
    ColorDefinition,
    CompetitivePositioning,
    TypographyRule,
    VisualIdentity,
    VoiceGuidelines,
)

# Storage functions (Task 1.6)
from .storage import (
    create_brand,
    delete_brand,
    get_active_brand,
    get_brand_dir,
    get_brands_dir,
    list_brands,
    load_brand,
    load_brand_summary,
    save_brand,
    set_active_brand,
    slugify,
    update_brand_summary_stats,
)

# Agent tools (Task 2.2) - lazily imported via __getattr__ to avoid circular import
# Direct access: from sip_videogen.brands.tools import browse_brand_assets, etc.

__all__ = [
    # Models - L0 Summary (Task 1.2)
    "BrandSummary",
    # Models - L1 Supporting (Task 1.3)
    "ColorDefinition",
    "TypographyRule",
    "VisualIdentity",
    "VoiceGuidelines",
    "AudienceProfile",
    "CompetitivePositioning",
    # Models - L1 Full Identity (Task 1.4)
    "BrandCoreIdentity",
    "BrandIdentityFull",
    # Models - Index (Task 1.5)
    "BrandIndex",
    "BrandIndexEntry",
    # Storage (Task 1.6)
    "create_brand",
    "delete_brand",
    "get_active_brand",
    "get_brand_dir",
    "get_brands_dir",
    "list_brands",
    "load_brand",
    "load_brand_summary",
    "save_brand",
    "set_active_brand",
    "slugify",
    "update_brand_summary_stats",
    # Memory - Brand (Task 2.1)
    "DetailType",
    "get_brand_detail",
    "get_brand_summary",
    "list_brand_assets",
    # Memory - Product (Phase 3)
    "get_product_summary",
    "get_product_detail",
    "get_product_full",
    "get_product_images_for_generation",
    # Memory - Project (Phase 3)
    "get_project_summary",
    "get_project_detail",
    "get_project_full",
    "get_project_instructions",
    # Agent Tools (Task 2.2)
    "browse_brand_assets",
    "fetch_brand_detail",
    "get_brand_context",
    "set_brand_context",
    # Context Builder - Brand (Task 2.3)
    "BrandContextBuilder",
    "build_brand_context",
    "DETAIL_DESCRIPTIONS",
    # Context Builder - Product (Phase 3)
    "ProductContextBuilder",
    "build_product_context",
    # Context Builder - Project (Phase 3)
    "ProjectContextBuilder",
    "build_project_context",
    # Context Builder - Hierarchical (Phase 3)
    "HierarchicalContextBuilder",
    "build_turn_context",
]
#Lazy loading for tools to avoid circular import with advisor.tools
def __getattr__(name):
    if name in("browse_brand_assets","fetch_brand_detail","get_brand_context","set_brand_context"):
        from . import tools
        return getattr(tools,name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
