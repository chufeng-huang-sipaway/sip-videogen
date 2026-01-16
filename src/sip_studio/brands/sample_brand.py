"""Sample brand creation for new user onboarding."""

from __future__ import annotations

import logging

from .models import BrandCoreIdentity, BrandIdentityFull, CompetitivePositioning
from .storage import create_brand, list_brands

logger = logging.getLogger(__name__)
SAMPLE_BRAND_SLUG = "sample-brand"


def _create_sample_identity() -> BrandIdentityFull:
    """Create minimal sample brand identity."""
    return BrandIdentityFull(
        slug=SAMPLE_BRAND_SLUG,
        core=BrandCoreIdentity(name="Sample Brand"),
        positioning=CompetitivePositioning(market_category="Uncategorized"),
    )


def ensure_sample_brand() -> bool:
    """Create sample brand if no brands exist. Returns True if created."""
    entries = list_brands()
    if entries:
        return False
    try:
        identity = _create_sample_identity()
        create_brand(identity)
        logger.info("Created sample brand for new user onboarding")
        return True
    except Exception as e:
        logger.warning("Failed to create sample brand: %s", e)
        return False
