"""Brand CRUD operations."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime

from sip_videogen.constants import ALLOWED_IMAGE_EXTS, ASSET_CATEGORIES
from sip_videogen.exceptions import BrandNotFoundError, DuplicateEntityError, StorageError
from sip_videogen.utils.file_utils import write_atomically

from ..models import BrandIdentityFull, BrandIndexEntry, BrandSummary, StyleReferenceIndex
from .base import get_brand_dir
from .index import load_index, save_index

logger = logging.getLogger(__name__)


def create_brand(identity: BrandIdentityFull) -> BrandSummary:
    """Create a new brand and save to disk.
    Args:
        identity: Complete brand identity to save.
    Returns:
        BrandSummary extracted from the identity.
    Raises:
        DuplicateEntityError: If brand with same slug already exists.
    """
    bd = get_brand_dir(identity.slug)
    if bd.exists():
        raise DuplicateEntityError(f"Brand '{identity.slug}' already exists")
    # Create directory structure
    bd.mkdir(parents=True, exist_ok=True)
    (bd / "assets").mkdir(exist_ok=True)
    for cat in ASSET_CATEGORIES:
        if cat != "generated":
            (bd / "assets" / cat).mkdir(exist_ok=True)
    (bd / "history").mkdir(exist_ok=True)
    # Initialize style_references directory with empty index
    srd = bd / "style_references"
    srd.mkdir(exist_ok=True)
    write_atomically(srd / "index.json", StyleReferenceIndex().model_dump_json(indent=2))
    # Save identity files atomically
    summary = identity.to_summary()
    write_atomically(bd / "identity.json", summary.model_dump_json(indent=2))
    write_atomically(bd / "identity_full.json", identity.model_dump_json(indent=2))
    # Update index
    idx = load_index()
    entry = BrandIndexEntry(
        slug=identity.slug,
        name=identity.core.name,
        category=identity.positioning.market_category,
        created_at=identity.created_at,
        updated_at=identity.updated_at,
    )
    idx.add_brand(entry)
    save_index(idx)
    logger.info("Created brand: %s", identity.slug)
    return summary


def load_brand(slug: str) -> BrandIdentityFull | None:
    """Load a brand's full identity from disk.
    Args:
        slug: Brand identifier.
    Returns:
        BrandIdentityFull or None if not found.
    """
    bd = get_brand_dir(slug)
    ip = bd / "identity_full.json"
    if not ip.exists():
        logger.debug("Brand not found: %s", slug)
        return None
    try:
        data = json.loads(ip.read_text())
        identity = BrandIdentityFull.model_validate(data)
        # Update last_accessed in index
        idx = load_index()
        entry = idx.get_brand(slug)
        if entry:
            entry.last_accessed = datetime.utcnow()
            save_index(idx)
        return identity
    except Exception as e:
        logger.error("Failed to load brand %s: %s", slug, e)
        return None


def load_brand_summary(slug: str) -> BrandSummary | None:
    """Load just the brand summary (L0 layer).
    This is faster than load_brand() when you only need the summary.
    """
    bd = get_brand_dir(slug)
    sp = bd / "identity.json"
    if not sp.exists():
        return None
    try:
        data = json.loads(sp.read_text())
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
    bd = get_brand_dir(identity.slug)
    if not bd.exists():
        return create_brand(identity)
    # Update timestamp
    identity.updated_at = datetime.utcnow()
    # Save files atomically
    summary = identity.to_summary()
    write_atomically(bd / "identity.json", summary.model_dump_json(indent=2))
    write_atomically(bd / "identity_full.json", identity.model_dump_json(indent=2))
    # Update index (re-register if missing for resilience)
    idx = load_index()
    entry = idx.get_brand(identity.slug)
    if entry:
        entry.name = identity.core.name
        entry.category = identity.positioning.market_category
        entry.updated_at = identity.updated_at
    else:
        # Brand exists on disk but not in index (corrupted/recreated index)
        logger.warning("Brand %s missing from index, re-registering", identity.slug)
        entry = BrandIndexEntry(
            slug=identity.slug,
            name=identity.core.name,
            category=identity.positioning.market_category,
            created_at=identity.created_at,
            updated_at=identity.updated_at,
        )
        idx.add_brand(entry)
    save_index(idx)
    logger.info("Saved brand: %s", identity.slug)
    return summary


def delete_brand(slug: str) -> bool:
    """Delete a brand and all its files.
    Returns:
        True if brand was deleted, False if not found.
    """
    bd = get_brand_dir(slug)
    if not bd.exists():
        return False
    shutil.rmtree(bd)
    # Update index
    idx = load_index()
    idx.remove_brand(slug)
    save_index(idx)
    logger.info("Deleted brand: %s", slug)
    return True


def list_brands() -> list[BrandIndexEntry]:
    """List all brands, sorted by last accessed (most recent first)."""
    idx = load_index()

    def _norm_dt(dt: datetime) -> datetime:
        """Convert to naive datetime for comparison (handles mixed tz-aware/naive)."""
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    return sorted(idx.brands, key=lambda b: _norm_dt(b.last_accessed), reverse=True)


def update_brand_summary_stats(slug: str) -> bool:
    """Update asset_count and last_generation in brand summary.
    Counts image files directly in assets/{category}/ subdirectories
    to avoid circular imports with memory.py.
    Args:
        slug: Brand identifier.
    Returns:
        True if stats were updated, False if brand not found.
    """
    bd = get_brand_dir(slug)
    sp = bd / "identity.json"
    if not sp.exists():
        logger.debug("Brand summary not found for stats update: %s", slug)
        return False
    # Count assets directly (avoid circular import with memory.py)
    ad = bd / "assets"
    cnt = 0
    if ad.exists():
        for cd in ad.iterdir():
            if cd.is_dir():
                for fp in cd.iterdir():
                    if fp.suffix.lower() in ALLOWED_IMAGE_EXTS:
                        cnt += 1
    # Load, update, and save summary atomically
    try:
        data = json.loads(sp.read_text())
        data["asset_count"] = cnt
        data["last_generation"] = datetime.utcnow().isoformat()
        write_atomically(sp, json.dumps(data, indent=2))
        logger.debug("Updated brand %s stats: %d assets", slug, cnt)
        return True
    except Exception as e:
        logger.error("Failed to update brand summary stats for %s: %s", slug, e)
        return False


def backup_brand_identity(slug: str) -> str:
    """Create a backup of the brand's full identity.
    Creates a timestamped copy of identity_full.json in the history/ folder.
    Args:
        slug: Brand identifier.
    Returns:
        Backup filename (e.g., 'identity_full_20240115_143022.json').
    Raises:
        BrandNotFoundError: If brand doesn't exist or identity file not found.
    """
    bd = get_brand_dir(slug)
    ip = bd / "identity_full.json"
    if not bd.exists():
        raise BrandNotFoundError(f"Brand '{slug}' not found")
    if not ip.exists():
        raise BrandNotFoundError(f"Identity file not found for brand '{slug}'")
    # Ensure history directory exists
    hd = bd / "history"
    hd.mkdir(exist_ok=True)
    # Create timestamped filename
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bfn = f"identity_full_{ts}.json"
    bp = hd / bfn
    # Copy identity file to history
    shutil.copy2(ip, bp)
    logger.info("Created backup for brand %s: %s", slug, bfn)
    return bfn


def list_brand_backups(slug: str) -> list[dict]:
    """List all backups for a brand's identity.
    Args:
        slug: Brand identifier.
    Returns:
        List of backup entries, each with:
        - filename: Backup filename
        - timestamp: ISO format timestamp
        - size_bytes: File size in bytes
        Sorted by timestamp descending (most recent first).
    Raises:
        BrandNotFoundError: If brand doesn't exist.
    """
    bd = get_brand_dir(slug)
    if not bd.exists():
        raise BrandNotFoundError(f"Brand '{slug}' not found")
    hd = bd / "history"
    if not hd.exists():
        return []
    backups = []
    for fp in hd.iterdir():
        if fp.is_file() and fp.name.startswith("identity_full_"):
            # Extract timestamp from filename
            nm = fp.stem
            parts = nm.split("_")
            if len(parts) >= 4:
                dp, tp = parts[2], parts[3]
                try:
                    dt = datetime.strptime(f"{dp}_{tp}", "%Y%m%d_%H%M%S")
                    its = dt.isoformat()
                except ValueError:
                    continue
                backups.append(
                    {"filename": fp.name, "timestamp": its, "size_bytes": fp.stat().st_size}
                )
    # Sort by timestamp descending
    backups.sort(key=lambda b: float(str(b["timestamp"])), reverse=True)
    logger.debug("Found %d backups for brand %s", len(backups), slug)
    return backups


def restore_brand_backup(slug: str, filename: str) -> BrandIdentityFull:
    """Restore a brand identity from a backup file.
    Loads a backup from the history/ folder and returns the parsed identity.
    The identity's slug is forced to match the current brand slug for stability.
    Args:
        slug: Brand identifier.
        filename: Backup filename.
    Returns:
        BrandIdentityFull parsed from the backup file with slug enforced.
    Raises:
        BrandNotFoundError: If brand doesn't exist.
        StorageError: If filename is invalid or backup not found.
    """
    bd = get_brand_dir(slug)
    if not bd.exists():
        raise BrandNotFoundError(f"Brand '{slug}' not found")
    # Security: Validate filename has no path separators
    if "/" in filename or "\\" in filename:
        raise StorageError("Invalid filename: path separators not allowed")
    # Validate filename format
    if not filename.endswith(".json"):
        raise StorageError("Invalid filename: must end with .json")
    if not filename.startswith("identity_full_"):
        raise StorageError("Invalid filename: must start with 'identity_full_'")
    # Verify file exists in history folder
    hd = bd / "history"
    bp = hd / filename
    if not bp.exists():
        raise StorageError(f"Backup '{filename}' not found for brand '{slug}'")
    # Ensure the resolved path is still within history/
    try:
        bp.resolve().relative_to(hd.resolve())
    except ValueError:
        raise StorageError("Invalid filename: path traversal detected")
    # Load and parse the backup
    try:
        data = json.loads(bp.read_text())
        identity = BrandIdentityFull.model_validate(data)
    except json.JSONDecodeError as e:
        raise StorageError(f"Invalid JSON in backup file: {e}")
    except Exception as e:
        raise StorageError(f"Failed to parse backup file: {e}")
    # Enforce slug stability
    if identity.slug != slug:
        logger.warning(
            "Backup slug '%s' differs from current brand '%s', forcing current slug",
            identity.slug,
            slug,
        )
        identity.slug = slug
    logger.info("Restored backup for brand %s from %s", slug, filename)
    return identity


def get_active_brand() -> str | None:
    """Get the slug of the currently active brand."""
    idx = load_index()
    return idx.active_brand


def set_active_brand(slug: str | None) -> None:
    """Set the active brand.
    Args:
        slug: Brand slug to set as active, or None to clear.
    Raises:
        BrandNotFoundError: If brand doesn't exist.
    """
    idx = load_index()
    if slug and not idx.get_brand(slug):
        raise BrandNotFoundError(f"Brand '{slug}' not found")
    idx.active_brand = slug
    save_index(idx)
    logger.info("Active brand set to: %s", slug or "(none)")
