"""Brand storage and persistence functions.

Handles reading/writing brand data to ~/.sip-videogen/brands/
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path

from .models import (
    BrandIdentityFull,
    BrandIndex,
    BrandIndexEntry,
    BrandSummary,
)

logger = logging.getLogger(__name__)


def get_brands_dir() -> Path:
    """Get the brands directory path."""
    return Path.home() / ".sip-videogen" / "brands"


def get_brand_dir(slug: str) -> Path:
    """Get the directory for a specific brand."""
    return get_brands_dir() / slug


def get_index_path() -> Path:
    """Get the path to the brand index file."""
    return get_brands_dir() / "index.json"


def slugify(name: str) -> str:
    """Convert brand name to URL-safe slug.

    Examples:
        "Summit Coffee Co." -> "summit-coffee-co"
        "EternaCare" -> "eternacare"
    """
    # Lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug


# =============================================================================
# Index Management
# =============================================================================


def load_index() -> BrandIndex:
    """Load the brand index from disk."""
    index_path = get_index_path()

    if index_path.exists():
        try:
            data = json.loads(index_path.read_text())
            index = BrandIndex.model_validate(data)
            logger.debug("Loaded brand index with %d brands", len(index.brands))
            return index
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in brand index: %s", e)
        except Exception as e:
            logger.warning("Failed to load brand index: %s", e)

    logger.debug("Creating new brand index")
    return BrandIndex()


def save_index(index: BrandIndex) -> None:
    """Save the brand index to disk."""
    index_path = get_index_path()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(index.model_dump_json(indent=2))
    logger.debug("Saved brand index with %d brands", len(index.brands))


# =============================================================================
# Brand CRUD Functions
# =============================================================================


def create_brand(identity: BrandIdentityFull) -> BrandSummary:
    """Create a new brand and save to disk.

    Args:
        identity: Complete brand identity to save.

    Returns:
        BrandSummary extracted from the identity.

    Raises:
        ValueError: If brand with same slug already exists.
    """
    brand_dir = get_brand_dir(identity.slug)

    if brand_dir.exists():
        raise ValueError(f"Brand '{identity.slug}' already exists")

    # Create directory structure (matches file structure in spec)
    brand_dir.mkdir(parents=True, exist_ok=True)
    (brand_dir / "assets").mkdir(exist_ok=True)
    (brand_dir / "assets" / "logo").mkdir(exist_ok=True)
    (brand_dir / "assets" / "packaging").mkdir(exist_ok=True)
    (brand_dir / "assets" / "lifestyle").mkdir(exist_ok=True)
    (brand_dir / "assets" / "mascot").mkdir(exist_ok=True)
    (brand_dir / "assets" / "marketing").mkdir(exist_ok=True)
    (brand_dir / "history").mkdir(exist_ok=True)

    # Save identity files
    summary = identity.to_summary()
    (brand_dir / "identity.json").write_text(summary.model_dump_json(indent=2))
    (brand_dir / "identity_full.json").write_text(identity.model_dump_json(indent=2))

    # Update index
    index = load_index()
    entry = BrandIndexEntry(
        slug=identity.slug,
        name=identity.core.name,
        category=identity.positioning.market_category,
        created_at=identity.created_at,
        updated_at=identity.updated_at,
    )
    index.add_brand(entry)
    save_index(index)

    logger.info("Created brand: %s", identity.slug)
    return summary


def load_brand(slug: str) -> BrandIdentityFull | None:
    """Load a brand's full identity from disk.

    Args:
        slug: Brand identifier.

    Returns:
        BrandIdentityFull or None if not found.
    """
    brand_dir = get_brand_dir(slug)
    identity_path = brand_dir / "identity_full.json"

    if not identity_path.exists():
        logger.debug("Brand not found: %s", slug)
        return None

    try:
        data = json.loads(identity_path.read_text())
        identity = BrandIdentityFull.model_validate(data)

        # Update last_accessed in index
        index = load_index()
        entry = index.get_brand(slug)
        if entry:
            entry.last_accessed = datetime.utcnow()
            save_index(index)

        return identity
    except Exception as e:
        logger.error("Failed to load brand %s: %s", slug, e)
        return None


def load_brand_summary(slug: str) -> BrandSummary | None:
    """Load just the brand summary (L0 layer).

    This is faster than load_brand() when you only need the summary.
    """
    brand_dir = get_brand_dir(slug)
    summary_path = brand_dir / "identity.json"

    if not summary_path.exists():
        return None

    try:
        data = json.loads(summary_path.read_text())
        return BrandSummary.model_validate(data)
    except Exception as e:
        logger.error("Failed to load brand summary %s: %s", slug, e)
        return None


def save_brand(identity: BrandIdentityFull) -> BrandSummary:
    """Save/update a brand's identity.

    Args:
        identity: Updated brand identity.

    Returns:
        Updated BrandSummary.
    """
    brand_dir = get_brand_dir(identity.slug)

    if not brand_dir.exists():
        return create_brand(identity)

    # Update timestamp
    identity.updated_at = datetime.utcnow()

    # Save files
    summary = identity.to_summary()
    (brand_dir / "identity.json").write_text(summary.model_dump_json(indent=2))
    (brand_dir / "identity_full.json").write_text(identity.model_dump_json(indent=2))

    # Update index (re-register if missing for resilience)
    index = load_index()
    entry = index.get_brand(identity.slug)
    if entry:
        entry.name = identity.core.name
        entry.category = identity.positioning.market_category
        entry.updated_at = identity.updated_at
    else:
        # Brand exists on disk but not in index (corrupted/recreated index)
        # Re-register it
        logger.warning("Brand %s missing from index, re-registering", identity.slug)
        entry = BrandIndexEntry(
            slug=identity.slug,
            name=identity.core.name,
            category=identity.positioning.market_category,
            created_at=identity.created_at,
            updated_at=identity.updated_at,
        )
        index.add_brand(entry)
    save_index(index)

    logger.info("Saved brand: %s", identity.slug)
    return summary


def delete_brand(slug: str) -> bool:
    """Delete a brand and all its files.

    Returns:
        True if brand was deleted, False if not found.
    """
    brand_dir = get_brand_dir(slug)

    if not brand_dir.exists():
        return False

    shutil.rmtree(brand_dir)

    # Update index
    index = load_index()
    index.remove_brand(slug)
    save_index(index)

    logger.info("Deleted brand: %s", slug)
    return True


def list_brands() -> list[BrandIndexEntry]:
    """List all brands, sorted by last accessed (most recent first)."""
    index = load_index()

    def _normalize_dt(dt: datetime) -> datetime:
        """Convert to naive datetime for comparison (handles mixed tz-aware/naive)."""
        if dt.tzinfo is not None:
            # Convert to UTC then strip timezone
            return dt.replace(tzinfo=None)
        return dt

    return sorted(index.brands, key=lambda b: _normalize_dt(b.last_accessed), reverse=True)


def update_brand_summary_stats(slug: str) -> bool:
    """Update asset_count and last_generation in brand summary.

    Counts image files directly in assets/{category}/ subdirectories
    to avoid circular imports with memory.py.

    Args:
        slug: Brand identifier.

    Returns:
        True if stats were updated, False if brand not found.
    """
    brand_dir = get_brand_dir(slug)
    summary_path = brand_dir / "identity.json"

    if not summary_path.exists():
        logger.debug("Brand summary not found for stats update: %s", slug)
        return False

    # Count assets directly (avoid circular import with memory.py)
    assets_dir = brand_dir / "assets"
    asset_count = 0
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}

    if assets_dir.exists():
        for category_dir in assets_dir.iterdir():
            if category_dir.is_dir():
                for file_path in category_dir.iterdir():
                    if file_path.suffix.lower() in image_extensions:
                        asset_count += 1

    # Load, update, and save summary
    try:
        data = json.loads(summary_path.read_text())
        data["asset_count"] = asset_count
        data["last_generation"] = datetime.utcnow().isoformat()
        summary_path.write_text(json.dumps(data, indent=2))
        logger.debug(
            "Updated brand %s stats: %d assets", slug, asset_count
        )
        return True
    except Exception as e:
        logger.error("Failed to update brand summary stats for %s: %s", slug, e)
        return False


# =============================================================================
# Active Brand Management
# =============================================================================


def get_active_brand() -> str | None:
    """Get the slug of the currently active brand."""
    index = load_index()
    return index.active_brand


def set_active_brand(slug: str | None) -> None:
    """Set the active brand.

    Args:
        slug: Brand slug to set as active, or None to clear.
    """
    index = load_index()

    if slug and not index.get_brand(slug):
        raise ValueError(f"Brand '{slug}' not found")

    index.active_brand = slug
    save_index(index)
    logger.info("Active brand set to: %s", slug or "(none)")
