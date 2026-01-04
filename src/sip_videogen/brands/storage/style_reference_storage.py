"""Style Reference CRUD operations."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from sip_videogen.constants import ALLOWED_IMAGE_EXTS
from sip_videogen.exceptions import (
    BrandNotFoundError,
    DuplicateEntityError,
    StyleReferenceNotFoundError,
)
from sip_videogen.utils.file_utils import write_atomically

from ..models import StyleReferenceFull, StyleReferenceIndex, StyleReferenceSummary
from .base import get_brand_dir

logger = logging.getLogger(__name__)


def get_style_references_dir(brand_slug: str) -> Path:
    """Get the style_references directory for a brand."""
    return get_brand_dir(brand_slug) / "style_references"


def get_style_reference_dir(brand_slug: str, style_ref_slug: str) -> Path:
    """Get the directory for a specific style reference."""
    return get_style_references_dir(brand_slug) / style_ref_slug


def get_style_reference_index_path(brand_slug: str) -> Path:
    """Get the path to the style reference index file for a brand."""
    return get_style_references_dir(brand_slug) / "index.json"


def load_style_reference_index(brand_slug: str) -> StyleReferenceIndex:
    """Load the style reference index for a brand."""
    ip = get_style_reference_index_path(brand_slug)
    if ip.exists():
        try:
            data = json.loads(ip.read_text())
            idx = StyleReferenceIndex.model_validate(data)
            logger.debug(
                "Loaded style reference index for %s with %d style references",
                brand_slug,
                len(idx.style_references),
            )
            return idx
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in style reference index for %s: %s", brand_slug, e)
        except Exception as e:
            logger.warning("Failed to load style reference index for %s: %s", brand_slug, e)
    logger.debug("Creating new style reference index for %s", brand_slug)
    return StyleReferenceIndex()


def save_style_reference_index(brand_slug: str, index: StyleReferenceIndex) -> None:
    """Save the style reference index for a brand atomically."""
    ip = get_style_reference_index_path(brand_slug)
    write_atomically(ip, index.model_dump_json(indent=2))
    logger.debug(
        "Saved style reference index for %s with %d style references",
        brand_slug,
        len(index.style_references),
    )


def create_style_reference(brand_slug: str, style_ref: StyleReferenceFull) -> StyleReferenceSummary:
    """Create a new style reference for a brand.
    Args:
        brand_slug: Brand identifier.
        style_ref: Complete style reference data.
    Returns:
        StyleReferenceSummary extracted from the style reference.
    Raises:
        BrandNotFoundError: If brand doesn't exist.
        DuplicateEntityError: If style reference already exists.
    """
    bd = get_brand_dir(brand_slug)
    if not bd.exists():
        raise BrandNotFoundError(f"Brand '{brand_slug}' not found")
    srd = get_style_reference_dir(brand_slug, style_ref.slug)
    if srd.exists():
        raise DuplicateEntityError(
            f"Style reference '{style_ref.slug}' already exists in brand '{brand_slug}'"
        )
    # Create directory structure
    srd.mkdir(parents=True, exist_ok=True)
    (srd / "images").mkdir(exist_ok=True)
    # Save style reference files atomically
    summary = style_ref.to_summary()
    write_atomically(srd / "style_reference.json", summary.model_dump_json(indent=2))
    write_atomically(srd / "style_reference_full.json", style_ref.model_dump_json(indent=2))
    # Update index
    idx = load_style_reference_index(brand_slug)
    idx.add_style_reference(summary)
    save_style_reference_index(brand_slug, idx)
    logger.info("Created style reference %s for brand %s", style_ref.slug, brand_slug)
    return summary


def load_style_reference(brand_slug: str, style_ref_slug: str) -> StyleReferenceFull | None:
    """Load a style reference's full details from disk.
    Args:
        brand_slug: Brand identifier.
        style_ref_slug: Style reference identifier.
    Returns:
        StyleReferenceFull or None if not found.
    """
    srd = get_style_reference_dir(brand_slug, style_ref_slug)
    sp = srd / "style_reference_full.json"
    if not sp.exists():
        logger.debug("Style reference not found: %s/%s", brand_slug, style_ref_slug)
        return None
    try:
        data = json.loads(sp.read_text())
        return StyleReferenceFull.model_validate(data)
    except Exception as e:
        logger.error("Failed to load style reference %s/%s: %s", brand_slug, style_ref_slug, e)
        return None


def load_style_reference_summary(
    brand_slug: str, style_ref_slug: str
) -> StyleReferenceSummary | None:
    """Load just the style reference summary (L0 layer).
    This is faster than load_style_reference() when you only need the summary.
    """
    srd = get_style_reference_dir(brand_slug, style_ref_slug)
    sp = srd / "style_reference.json"
    if not sp.exists():
        return None
    try:
        data = json.loads(sp.read_text())
        return StyleReferenceSummary.model_validate(data)
    except Exception as e:
        logger.error(
            "Failed to load style reference summary %s/%s: %s", brand_slug, style_ref_slug, e
        )
        return None


def save_style_reference(brand_slug: str, style_ref: StyleReferenceFull) -> StyleReferenceSummary:
    """Save/update a style reference.
    Args:
        brand_slug: Brand identifier.
        style_ref: Updated style reference data.
    Returns:
        Updated StyleReferenceSummary.
    """
    srd = get_style_reference_dir(brand_slug, style_ref.slug)
    if not srd.exists():
        return create_style_reference(brand_slug, style_ref)
    # Update timestamp
    style_ref.updated_at = datetime.utcnow()
    # Save files atomically
    summary = style_ref.to_summary()
    write_atomically(srd / "style_reference.json", summary.model_dump_json(indent=2))
    write_atomically(srd / "style_reference_full.json", style_ref.model_dump_json(indent=2))
    # Update index
    idx = load_style_reference_index(brand_slug)
    idx.add_style_reference(summary)
    save_style_reference_index(brand_slug, idx)
    logger.info("Saved style reference %s for brand %s", style_ref.slug, brand_slug)
    return summary


def delete_style_reference(brand_slug: str, style_ref_slug: str) -> bool:
    """Delete a style reference and all its files.
    Returns:
        True if style reference was deleted, False if not found.
    """
    srd = get_style_reference_dir(brand_slug, style_ref_slug)
    if not srd.exists():
        return False
    shutil.rmtree(srd)
    # Update index
    idx = load_style_reference_index(brand_slug)
    idx.remove_style_reference(style_ref_slug)
    save_style_reference_index(brand_slug, idx)
    logger.info("Deleted style reference %s from brand %s", style_ref_slug, brand_slug)
    return True


def list_style_references(brand_slug: str) -> list[StyleReferenceSummary]:
    """List all style references for a brand, sorted by name."""
    idx = load_style_reference_index(brand_slug)
    return sorted(idx.style_references, key=lambda t: t.name.lower())


def list_style_reference_images(brand_slug: str, style_ref_slug: str) -> list[str]:
    """List all images for a style reference.
    Returns:
        List of brand-relative image paths.
    """
    srd = get_style_reference_dir(brand_slug, style_ref_slug)
    imd = srd / "images"
    if not imd.exists():
        return []
    imgs = []
    for fp in sorted(imd.iterdir()):
        if fp.suffix.lower() in ALLOWED_IMAGE_EXTS:
            imgs.append(f"style_references/{style_ref_slug}/images/{fp.name}")
    return imgs


def add_style_reference_image(
    brand_slug: str, style_ref_slug: str, filename: str, data: bytes
) -> str:
    """Add an image to a style reference.
    Args:
        brand_slug: Brand identifier.
        style_ref_slug: Style reference identifier.
        filename: Image filename.
        data: Image binary data.
    Returns:
        Brand-relative path to the saved image.
    Raises:
        StyleReferenceNotFoundError: If style reference doesn't exist.
    """
    srd = get_style_reference_dir(brand_slug, style_ref_slug)
    if not srd.exists():
        raise StyleReferenceNotFoundError(
            f"Style reference '{style_ref_slug}' not found in brand '{brand_slug}'"
        )
    imd = srd / "images"
    imd.mkdir(exist_ok=True)
    # Save image
    (imd / filename).write_bytes(data)
    # Return brand-relative path
    br = f"style_references/{style_ref_slug}/images/{filename}"
    # Update style reference's images list
    sr = load_style_reference(brand_slug, style_ref_slug)
    if sr:
        if br not in sr.images:
            sr.images.append(br)
            # Set as primary if first image
            if not sr.primary_image:
                sr.primary_image = br
            save_style_reference(brand_slug, sr)
    logger.info("Added image %s to style reference %s/%s", filename, brand_slug, style_ref_slug)
    return br


def delete_style_reference_image(brand_slug: str, style_ref_slug: str, filename: str) -> bool:
    """Delete an image from a style reference.
    Returns:
        True if image was deleted, False if not found.
    """
    srd = get_style_reference_dir(brand_slug, style_ref_slug)
    ip = srd / "images" / filename
    if not ip.exists():
        return False
    ip.unlink()
    # Update style reference's images list
    br = f"style_references/{style_ref_slug}/images/{filename}"
    sr = load_style_reference(brand_slug, style_ref_slug)
    if sr:
        if br in sr.images:
            sr.images.remove(br)
            # Update primary if it was the deleted image
            if sr.primary_image == br:
                sr.primary_image = sr.images[0] if sr.images else ""
            save_style_reference(brand_slug, sr)
    logger.info("Deleted image %s from style reference %s/%s", filename, brand_slug, style_ref_slug)
    return True


def set_primary_style_reference_image(
    brand_slug: str, style_ref_slug: str, brand_relative_path: str
) -> bool:
    """Set the primary image for a style reference.
    Args:
        brand_slug: Brand identifier.
        style_ref_slug: Style reference identifier.
        brand_relative_path: Brand-relative path to the image.
    Returns:
        True if primary was set, False if image not found in style reference.
    """
    sr = load_style_reference(brand_slug, style_ref_slug)
    if not sr:
        return False
    if brand_relative_path not in sr.images:
        return False
    sr.primary_image = brand_relative_path
    save_style_reference(brand_slug, sr)
    logger.info(
        "Set primary image for style reference %s/%s to %s",
        brand_slug,
        style_ref_slug,
        brand_relative_path,
    )
    return True


def sync_style_reference_index(brand_slug: str) -> int:
    """Reconcile style reference index with filesystem.
    Adds style references that exist on disk but not in index,
    removes index entries for style references that no longer exist.
    Returns:
        Number of changes made (additions + removals).
    """
    srd = get_style_references_dir(brand_slug)
    if not srd.exists():
        return 0
    idx = load_style_reference_index(brand_slug)
    changes = 0
    # Find style references on disk
    dslugs = set()
    for item in srd.iterdir():
        if item.is_dir() and (item / "style_reference_full.json").exists():
            dslugs.add(item.name)
    # Find style references in index
    islugs = {t.slug for t in idx.style_references}
    # Add missing to index
    for s in dslugs - islugs:
        sr = load_style_reference(brand_slug, s)
        if sr:
            idx.add_style_reference(sr.to_summary())
            logger.info("Synced style reference %s to index for brand %s", s, brand_slug)
            changes += 1
    # Remove orphaned from index
    for s in islugs - dslugs:
        idx.remove_style_reference(s)
        logger.info("Removed orphaned style reference %s from index for brand %s", s, brand_slug)
        changes += 1
    if changes > 0:
        save_style_reference_index(brand_slug, idx)
    return changes
