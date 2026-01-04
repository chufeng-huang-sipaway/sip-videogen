"""Common utilities + path safety for brand storage."""

from __future__ import annotations

import os
import re
from pathlib import Path


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


def validate_slug(slug: str) -> None:
    """Raise ValueError if slug is invalid."""
    if not slug or len(slug) > 100:
        raise ValueError("Slug empty or too long")
    if ".." in slug or "/" in slug or "\\" in slug:
        raise ValueError("Invalid slug: path traversal")
    # Note: Allow underscores and uppercase to match existing data
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", slug):
        raise ValueError("Invalid slug format")


def safe_resolve_path(base: Path, relative: str) -> Path:
    """Resolve path safely, preventing traversal attacks (including symlinks)."""
    resolved = (base / relative).resolve()
    base_resolved = base.resolve()
    # Use commonpath for safe containment check (avoids /base vs /base2 bug)
    try:
        common = Path(os.path.commonpath([str(base_resolved), str(resolved)]))
        if common != base_resolved:
            raise ValueError("Path traversal detected")
    except ValueError:
        raise ValueError("Path traversal detected")
    return resolved
