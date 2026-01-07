"""Path resolution and safety utilities."""

from pathlib import Path

from sip_studio.brands.storage import get_active_brand, get_brand_dir


def resolve_in_dir(base_dir: Path, relative_path: str) -> tuple[Path | None, str | None]:
    """Resolve a path safely within a base directory (prevents path traversal)."""
    try:
        r = (base_dir / relative_path).resolve()
        if not r.is_relative_to(base_dir.resolve()):
            return None, "Invalid path: outside allowed directory"
        return r, None
    except (ValueError, OSError) as e:
        return None, f"Invalid path: {e}"


def get_brand_dir_for_slug(slug: str | None) -> tuple[Path | None, str | None]:
    """Get brand directory for a given or active slug."""
    s = slug or get_active_brand()
    if not s:
        return None, "No brand selected"
    return get_brand_dir(s), None


def resolve_assets_path(brand_dir: Path, relative_path: str) -> tuple[Path | None, str | None]:
    """Resolve a path inside brand's assets directory."""
    return resolve_in_dir(brand_dir / "assets", relative_path)


def resolve_docs_path(brand_dir: Path, relative_path: str) -> tuple[Path | None, str | None]:
    """Resolve a path inside brand's docs directory."""
    return resolve_in_dir(brand_dir / "docs", relative_path)


def resolve_product_image_path(
    brand_dir: Path, relative_path: str
) -> tuple[Path | None, str | None]:
    """Resolve a path inside brand's products directory (for product images)."""
    return resolve_in_dir(brand_dir / "products", relative_path)
