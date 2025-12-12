"""Brand management system for sip-videogen.

This package provides persistent brand storage, hierarchical memory,
and brand-aware agent tools for the brand kit workflow.
"""

# Models (Tasks 1.2-1.5)
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
)

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
]
