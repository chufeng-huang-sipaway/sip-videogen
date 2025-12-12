"""Brand management system for sip-videogen.

This package provides persistent brand storage, hierarchical memory,
and brand-aware agent tools for the brand kit workflow.
"""

# Models (Tasks 1.2-1.4)
from .models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    BrandSummary,
    ColorDefinition,
    CompetitivePositioning,
    TypographyRule,
    VisualIdentity,
    VoiceGuidelines,
)

# NOTE: Imports below are commented out until the respective modules are created.
# Uncomment as each file is implemented in subsequent tasks.

# from .models import (
#     BrandIndex,
#     BrandIndexEntry,
# )
# from .storage import (
#     create_brand,
#     load_brand,
#     save_brand,
#     delete_brand,
#     list_brands,
#     get_active_brand,
#     set_active_brand,
# )

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
    # "BrandIndex",
    # "BrandIndexEntry",
    # Storage (Task 1.6)
    # "create_brand",
    # "load_brand",
    # "save_brand",
    # "delete_brand",
    # "list_brands",
    # "get_active_brand",
    # "set_active_brand",
]
