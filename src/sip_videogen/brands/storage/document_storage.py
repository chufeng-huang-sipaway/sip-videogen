"""Document and asset management."""

from __future__ import annotations

import json
import logging
import os as _os
from pathlib import Path

from sip_videogen.constants import (
    ALLOWED_IMAGE_EXTS,
    ALLOWED_TEXT_EXTS,
    ALLOWED_VIDEO_EXTS,
    ASSET_CATEGORIES,
)

from .base import get_brand_dir

logger = logging.getLogger(__name__)
IMAGE_STATUS_FILE = "image_status.json"


def _safe_resolve_in_dir(base_dir: Path, rel_path: str) -> tuple[Path | None, str | None]:
    """Resolve path safely within base directory (stdlib-only, no external imports)."""
    try:
        r = (base_dir / rel_path).resolve()
        if not r.is_relative_to(base_dir.resolve()):
            return None, "Invalid path: outside allowed directory"
        return r, None
    except (ValueError, OSError) as e:
        return None, f"Invalid path: {e}"


def get_docs_dir(brand_slug: str) -> Path:
    """Get the docs directory for a brand."""
    return get_brand_dir(brand_slug) / "docs"


def list_documents(brand_slug: str) -> list[dict]:
    """List all documents for a brand.
    Supports nested subdirectories via rglob.
    Returns:
        List of document entries with name, path (relative to docs/), and size.
    """
    dd = get_docs_dir(brand_slug)
    if not dd.exists():
        return []
    docs: list[dict] = []
    for p in sorted(dd.rglob("*")):
        if not p.is_file() or p.name.startswith(".") or p.suffix.lower() not in ALLOWED_TEXT_EXTS:
            continue
        rel = str(p.relative_to(dd))
        docs.append({"name": p.name, "path": rel, "size": p.stat().st_size})
    return docs


def save_document(
    brand_slug: str, relative_path: str, content: bytes
) -> tuple[str | None, str | None]:
    """Save a document to the brand's docs directory.
    Args:
        brand_slug: Brand identifier.
        relative_path: Path relative to docs/ (supports nested dirs).
        content: Document binary content.
    Returns:
        Tuple of (saved_path, error). saved_path is relative to docs/.
    """
    dd = get_docs_dir(brand_slug)
    dd.mkdir(parents=True, exist_ok=True)
    resolved, err = _safe_resolve_in_dir(dd, relative_path)
    if err or resolved is None:
        return None, err or "Failed to resolve path"
    # Ensure parent directories exist
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_bytes(content)
    logger.debug("Saved document %s for brand %s", relative_path, brand_slug)
    return relative_path, None


def delete_document(brand_slug: str, relative_path: str) -> tuple[bool, str | None]:
    """Delete a document from the brand's docs directory.
    Args:
        brand_slug: Brand identifier.
        relative_path: Path relative to docs/.
    Returns:
        Tuple of (success, error).
    """
    dd = get_docs_dir(brand_slug)
    if not dd.exists():
        return False, "Docs directory not found"
    resolved, err = _safe_resolve_in_dir(dd, relative_path)
    if err or resolved is None:
        return False, err or "Failed to resolve path"
    if not resolved.exists():
        return False, "Document not found"
    if resolved.is_dir():
        return False, "Cannot delete folders"
    resolved.unlink()
    logger.debug("Deleted document %s for brand %s", relative_path, brand_slug)
    return True, None


def rename_document(
    brand_slug: str, relative_path: str, new_name: str
) -> tuple[str | None, str | None]:
    """Rename a document in the brand's docs directory.
    Args:
        brand_slug: Brand identifier.
        relative_path: Current path relative to docs/.
        new_name: New filename (not a path, just the name).
    Returns:
        Tuple of (new_relative_path, error).
    """
    dd = get_docs_dir(brand_slug)
    if not dd.exists():
        return None, "Docs directory not found"
    resolved, err = _safe_resolve_in_dir(dd, relative_path)
    if err or resolved is None:
        return None, err or "Failed to resolve path"
    if not resolved.exists():
        return None, "Document not found"
    if "/" in new_name or "\\" in new_name:
        return None, "Invalid filename: path separators not allowed"
    np = resolved.parent / new_name
    if np.exists():
        return None, f"File already exists: {new_name}"
    resolved.rename(np)
    nr = str(np.relative_to(dd))
    logger.debug("Renamed document %s to %s for brand %s", relative_path, nr, brand_slug)
    return nr, None


def load_image_status_raw(brand_slug: str) -> dict:
    """Load raw image status data from file (no migrations applied).
    Returns empty structure if file missing or invalid.
    """
    fp = get_brand_dir(brand_slug) / IMAGE_STATUS_FILE
    if not fp.exists():
        return {"version": 1, "images": {}}
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "images": {}}
    if not isinstance(data, dict):
        return {"version": 1, "images": {}}
    if not isinstance(data.get("version"), int):
        data["version"] = 1
    if not isinstance(data.get("images"), dict):
        data["images"] = {}
    return data


def save_image_status(brand_slug: str, data: dict) -> None:
    """Atomically save image status data to file.
    Uses temp file + rename for atomicity.
    """
    fp = get_brand_dir(brand_slug) / IMAGE_STATUS_FILE
    tmp = fp.with_suffix(".json.tmp")
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    _os.replace(tmp, fp)
    logger.debug("Saved image status for brand %s", brand_slug)


def get_assets_dir(brand_slug: str) -> Path:
    """Get the assets directory for a brand."""
    return get_brand_dir(brand_slug) / "assets"


def list_assets(brand_slug: str, category: str | None = None) -> list[dict]:
    """List assets for a brand, optionally filtered by category.
    Args:
        brand_slug: Brand identifier.
        category: Optional category to filter (e.g., 'logo', 'marketing', 'generated').
    Returns:
        List of asset entries with filename, path, category, and type.
    """
    ad = get_assets_dir(brand_slug)
    if not ad.exists():
        return []
    allowed = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS
    assets: list[dict] = []
    cats = [category] if category else ASSET_CATEGORIES
    for cat in cats:
        cd = ad / cat
        if not cd.exists():
            continue
        for p in sorted(cd.iterdir()):
            if not p.is_file() or p.name.startswith(".") or p.suffix.lower() not in allowed:
                continue
            atype = "video" if p.suffix.lower() in ALLOWED_VIDEO_EXTS else "image"
            assets.append({"filename": p.name, "path": str(p), "category": cat, "type": atype})
    return assets


def save_asset(
    brand_slug: str, category: str, filename: str, data: bytes
) -> tuple[str | None, str | None]:
    """Save an asset to the brand's assets directory.
    Args:
        brand_slug: Brand identifier.
        category: Asset category (e.g., 'logo', 'marketing', 'generated').
        filename: Filename (must not contain path separators).
        data: Binary content.
    Returns:
        Tuple of (relative_path, error). relative_path is 'category/filename'.
    """
    if category not in ASSET_CATEGORIES:
        return None, f"Invalid category: {category}"
    if "/" in filename or "\\" in filename:
        return None, "Invalid filename: path separators not allowed"
    suffix = Path(filename).suffix.lower()
    allowed = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS
    if suffix not in allowed:
        return None, f"Unsupported file type: {suffix}"
    ad = get_assets_dir(brand_slug)
    cd = ad / category
    cd.mkdir(parents=True, exist_ok=True)
    target = cd / filename
    if target.exists():
        return None, f"File already exists: {filename}"
    target.write_bytes(data)
    rp = f"{category}/{filename}"
    logger.debug("Saved asset %s for brand %s", rp, brand_slug)
    return rp, None
