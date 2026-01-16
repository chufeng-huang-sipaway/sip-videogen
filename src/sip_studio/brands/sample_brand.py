"""Sample brand creation for new user onboarding."""

from __future__ import annotations

import logging

from .models import BrandCoreIdentity, BrandIdentityFull, CompetitivePositioning
from .storage import create_brand
from .storage.index import load_index, save_index

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
    """One-time migration: create sample brand for all users.

    Uses sample_brand_offered flag in index.json to ensure this runs only once.
    Returns True if sample brand was created.
    """
    try:
        index = load_index()
        if index.sample_brand_offered:
            return False
        # Check if sample brand already exists (user may have created/deleted it)
        if any(b.slug == SAMPLE_BRAND_SLUG for b in index.brands):
            index.sample_brand_offered = True
            save_index(index)
            return False
        # Create sample brand
        identity = _create_sample_identity()
        create_brand(identity)
        # Mark migration as done
        index = load_index()  # Reload after create_brand modified it
        index.sample_brand_offered = True
        save_index(index)
        logger.info("Created sample brand for user onboarding")
        return True
    except Exception as e:
        logger.warning("Failed to create sample brand: %s", e)
        return False
