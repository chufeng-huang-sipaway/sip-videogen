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

from sip_videogen.constants import (
    ALLOWED_IMAGE_EXTS,ALLOWED_TEXT_EXTS,ALLOWED_VIDEO_EXTS,ASSET_CATEGORIES)
from sip_videogen.utils.file_utils import write_atomically
from .models import (
    BrandIdentityFull,
    BrandIndex,
    BrandIndexEntry,
    BrandSummary,
    ProductFull,
    ProductIndex,
    ProductSummary,
    ProjectFull,
    ProjectIndex,
    ProjectSummary,
    TemplateFull,
    TemplateIndex,
    TemplateSummary,
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
    """Save the brand index to disk atomically."""
    index_path = get_index_path()
    write_atomically(index_path,index.model_dump_json(indent=2))
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

    #Create directory structure
    brand_dir.mkdir(parents=True,exist_ok=True)
    (brand_dir/"assets").mkdir(exist_ok=True)
    for cat in ASSET_CATEGORIES:
        if cat!="generated":(brand_dir/"assets"/cat).mkdir(exist_ok=True)
    (brand_dir/"history").mkdir(exist_ok=True)
    #Initialize templates directory with empty index
    templates_dir=brand_dir/"templates"
    templates_dir.mkdir(exist_ok=True)
    write_atomically(templates_dir/"index.json",TemplateIndex().model_dump_json(indent=2))

    # Save identity files atomically
    summary = identity.to_summary()
    write_atomically(brand_dir/"identity.json",summary.model_dump_json(indent=2))
    write_atomically(brand_dir/"identity_full.json",identity.model_dump_json(indent=2))

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

    # Save files atomically
    summary = identity.to_summary()
    write_atomically(brand_dir/"identity.json",summary.model_dump_json(indent=2))
    write_atomically(brand_dir/"identity_full.json",identity.model_dump_json(indent=2))

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

    #Count assets directly (avoid circular import with memory.py)
    assets_dir=brand_dir/"assets"
    asset_count=0
    if assets_dir.exists():
        for cat_dir in assets_dir.iterdir():
            if cat_dir.is_dir():
                for fp in cat_dir.iterdir():
                    if fp.suffix.lower()in ALLOWED_IMAGE_EXTS:asset_count+=1

    # Load, update, and save summary atomically
    try:
        data = json.loads(summary_path.read_text())
        data["asset_count"] = asset_count
        data["last_generation"] = datetime.utcnow().isoformat()
        write_atomically(summary_path,json.dumps(data, indent=2))
        logger.debug(
            "Updated brand %s stats: %d assets", slug, asset_count
        )
        return True
    except Exception as e:
        logger.error("Failed to update brand summary stats for %s: %s", slug, e)
        return False


# =============================================================================
# Brand Identity Backup Functions
# =============================================================================


def backup_brand_identity(slug: str) -> str:
    """Create a backup of the brand's full identity.

    Creates a timestamped copy of identity_full.json in the history/ folder.

    Args:
        slug: Brand identifier.

    Returns:
        Backup filename (e.g., 'identity_full_20240115_143022.json').

    Raises:
        ValueError: If brand doesn't exist or identity file not found.
    """
    brand_dir = get_brand_dir(slug)
    identity_path = brand_dir / "identity_full.json"

    if not brand_dir.exists():
        raise ValueError(f"Brand '{slug}' not found")

    if not identity_path.exists():
        raise ValueError(f"Identity file not found for brand '{slug}'")

    # Ensure history directory exists
    history_dir = brand_dir / "history"
    history_dir.mkdir(exist_ok=True)

    # Create timestamped filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"identity_full_{timestamp}.json"
    backup_path = history_dir / backup_filename

    # Copy identity file to history
    shutil.copy2(identity_path, backup_path)

    logger.info("Created backup for brand %s: %s", slug, backup_filename)
    return backup_filename


def list_brand_backups(slug: str) -> list[dict]:
    """List all backups for a brand's identity.

    Args:
        slug: Brand identifier.

    Returns:
        List of backup entries, each with:
        - filename: Backup filename (e.g., 'identity_full_20240115_143022.json')
        - timestamp: ISO format timestamp extracted from filename
        - size_bytes: File size in bytes

        Sorted by timestamp descending (most recent first).

    Raises:
        ValueError: If brand doesn't exist.
    """
    brand_dir = get_brand_dir(slug)

    if not brand_dir.exists():
        raise ValueError(f"Brand '{slug}' not found")

    history_dir = brand_dir / "history"

    if not history_dir.exists():
        return []

    backups = []
    for file_path in history_dir.iterdir():
        if file_path.is_file() and file_path.name.startswith("identity_full_"):
            # Extract timestamp from filename: identity_full_YYYYMMDD_HHMMSS.json
            name = file_path.stem  # identity_full_20240115_143022
            parts = name.split("_")
            if len(parts) >= 4:
                date_part = parts[2]  # 20240115
                time_part = parts[3]  # 143022
                try:
                    # Parse and format as ISO timestamp
                    dt = datetime.strptime(f"{date_part}_{time_part}", "%Y%m%d_%H%M%S")
                    iso_timestamp = dt.isoformat()
                except ValueError:
                    # Skip malformed filenames
                    continue

                backups.append({
                    "filename": file_path.name,
                    "timestamp": iso_timestamp,
                    "size_bytes": file_path.stat().st_size,
                })

    # Sort by timestamp descending (most recent first)
    backups.sort(key=lambda b: b["timestamp"], reverse=True)

    logger.debug("Found %d backups for brand %s", len(backups), slug)
    return backups


def restore_brand_backup(slug: str, filename: str) -> BrandIdentityFull:
    """Restore a brand identity from a backup file.

    Loads a backup from the history/ folder and returns the parsed identity.
    The identity's slug is forced to match the current brand slug for stability.

    Args:
        slug: Brand identifier.
        filename: Backup filename (e.g., 'identity_full_20240115_143022.json').

    Returns:
        BrandIdentityFull parsed from the backup file with slug enforced.

    Raises:
        ValueError: If brand doesn't exist, filename is invalid, or backup not found.
    """
    brand_dir = get_brand_dir(slug)

    if not brand_dir.exists():
        raise ValueError(f"Brand '{slug}' not found")

    # Security: Validate filename has no path separators (prevent directory traversal)
    if "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename: path separators not allowed")

    # Validate filename format
    if not filename.endswith(".json"):
        raise ValueError("Invalid filename: must end with .json")

    if not filename.startswith("identity_full_"):
        raise ValueError("Invalid filename: must start with 'identity_full_'")

    # Verify file exists in history folder
    history_dir = brand_dir / "history"
    backup_path = history_dir / filename

    if not backup_path.exists():
        raise ValueError(f"Backup '{filename}' not found for brand '{slug}'")

    # Ensure the resolved path is still within history/ (extra safety)
    try:
        backup_path.resolve().relative_to(history_dir.resolve())
    except ValueError:
        raise ValueError("Invalid filename: path traversal detected")

    # Load and parse the backup
    try:
        data = json.loads(backup_path.read_text())
        identity = BrandIdentityFull.model_validate(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in backup file: {e}")
    except Exception as e:
        raise ValueError(f"Failed to parse backup file: {e}")

    # Enforce slug stability - force the current slug regardless of backup content
    if identity.slug != slug:
        logger.warning(
            "Backup slug '%s' differs from current brand '%s', forcing current slug",
            identity.slug,
            slug,
        )
        identity.slug = slug

    logger.info("Restored backup for brand %s from %s", slug, filename)
    return identity


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


# =============================================================================
# Product Storage Functions
# =============================================================================


def get_products_dir(brand_slug: str) -> Path:
    """Get the products directory for a brand."""
    return get_brand_dir(brand_slug) / "products"


def get_product_dir(brand_slug: str, product_slug: str) -> Path:
    """Get the directory for a specific product."""
    return get_products_dir(brand_slug) / product_slug


def get_product_index_path(brand_slug: str) -> Path:
    """Get the path to the product index file for a brand."""
    return get_products_dir(brand_slug) / "index.json"


def load_product_index(brand_slug: str) -> ProductIndex:
    """Load the product index for a brand."""
    index_path = get_product_index_path(brand_slug)

    if index_path.exists():
        try:
            data = json.loads(index_path.read_text())
            index = ProductIndex.model_validate(data)
            logger.debug(
                "Loaded product index for %s with %d products",
                brand_slug,
                len(index.products),
            )
            return index
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in product index for %s: %s", brand_slug, e)
        except Exception as e:
            logger.warning("Failed to load product index for %s: %s", brand_slug, e)

    logger.debug("Creating new product index for %s", brand_slug)
    return ProductIndex()


def save_product_index(brand_slug: str, index: ProductIndex) -> None:
    """Save the product index for a brand atomically."""
    index_path = get_product_index_path(brand_slug)
    write_atomically(index_path,index.model_dump_json(indent=2))
    logger.debug(
        "Saved product index for %s with %d products",
        brand_slug,
        len(index.products),
    )


def create_product(brand_slug: str, product: ProductFull) -> ProductSummary:
    """Create a new product for a brand.

    Args:
        brand_slug: Brand identifier.
        product: Complete product data.

    Returns:
        ProductSummary extracted from the product.

    Raises:
        ValueError: If brand doesn't exist or product already exists.
    """
    brand_dir = get_brand_dir(brand_slug)
    if not brand_dir.exists():
        raise ValueError(f"Brand '{brand_slug}' not found")

    product_dir = get_product_dir(brand_slug, product.slug)
    if product_dir.exists():
        raise ValueError(
            f"Product '{product.slug}' already exists in brand '{brand_slug}'"
        )

    # Create directory structure
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "images").mkdir(exist_ok=True)

    # Save product files atomically
    summary = product.to_summary()
    write_atomically(product_dir/"product.json",summary.model_dump_json(indent=2))
    write_atomically(product_dir/"product_full.json",product.model_dump_json(indent=2))

    # Update index
    index = load_product_index(brand_slug)
    index.add_product(summary)
    save_product_index(brand_slug, index)

    logger.info("Created product %s for brand %s", product.slug, brand_slug)
    return summary


def load_product(brand_slug: str, product_slug: str) -> ProductFull | None:
    """Load a product's full details from disk.

    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.

    Returns:
        ProductFull or None if not found.
    """
    product_dir = get_product_dir(brand_slug, product_slug)
    product_path = product_dir / "product_full.json"

    if not product_path.exists():
        logger.debug("Product not found: %s/%s", brand_slug, product_slug)
        return None

    try:
        data = json.loads(product_path.read_text())
        return ProductFull.model_validate(data)
    except Exception as e:
        logger.error("Failed to load product %s/%s: %s", brand_slug, product_slug, e)
        return None


def load_product_summary(brand_slug: str, product_slug: str) -> ProductSummary | None:
    """Load just the product summary (L0 layer).

    This is faster than load_product() when you only need the summary.
    """
    product_dir = get_product_dir(brand_slug, product_slug)
    summary_path = product_dir / "product.json"

    if not summary_path.exists():
        return None

    try:
        data = json.loads(summary_path.read_text())
        return ProductSummary.model_validate(data)
    except Exception as e:
        logger.error(
            "Failed to load product summary %s/%s: %s", brand_slug, product_slug, e
        )
        return None


def save_product(brand_slug: str, product: ProductFull) -> ProductSummary:
    """Save/update a product.

    Args:
        brand_slug: Brand identifier.
        product: Updated product data.

    Returns:
        Updated ProductSummary.
    """
    product_dir = get_product_dir(brand_slug, product.slug)

    if not product_dir.exists():
        return create_product(brand_slug, product)

    # Update timestamp
    product.updated_at = datetime.utcnow()

    # Save files atomically
    summary = product.to_summary()
    write_atomically(product_dir/"product.json",summary.model_dump_json(indent=2))
    write_atomically(product_dir/"product_full.json",product.model_dump_json(indent=2))

    # Update index
    index = load_product_index(brand_slug)
    index.add_product(summary)
    save_product_index(brand_slug, index)

    logger.info("Saved product %s for brand %s", product.slug, brand_slug)
    return summary


def delete_product(brand_slug: str, product_slug: str) -> bool:
    """Delete a product and all its files.

    Returns:
        True if product was deleted, False if not found.
    """
    product_dir = get_product_dir(brand_slug, product_slug)

    if not product_dir.exists():
        return False

    shutil.rmtree(product_dir)

    # Update index
    index = load_product_index(brand_slug)
    index.remove_product(product_slug)
    save_product_index(brand_slug, index)

    logger.info("Deleted product %s from brand %s", product_slug, brand_slug)
    return True


def list_products(brand_slug: str) -> list[ProductSummary]:
    """List all products for a brand, sorted by name."""
    index = load_product_index(brand_slug)
    return sorted(index.products, key=lambda p: p.name.lower())


def list_product_images(brand_slug: str, product_slug: str) -> list[str]:
    """List all images for a product.

    Returns:
        List of brand-relative image paths.
    """
    product_dir = get_product_dir(brand_slug, product_slug)
    images_dir = product_dir / "images"

    if not images_dir.exists():return []
    images=[]
    for fp in sorted(images_dir.iterdir()):
        if fp.suffix.lower()in ALLOWED_IMAGE_EXTS:
            images.append(f"products/{product_slug}/images/{fp.name}")

    return images


def add_product_image(
    brand_slug: str, product_slug: str, filename: str, data: bytes
) -> str:
    """Add an image to a product.

    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.
        filename: Image filename.
        data: Image binary data.

    Returns:
        Brand-relative path to the saved image.

    Raises:
        ValueError: If product doesn't exist.
    """
    product_dir = get_product_dir(brand_slug, product_slug)
    if not product_dir.exists():
        raise ValueError(
            f"Product '{product_slug}' not found in brand '{brand_slug}'"
        )

    images_dir = product_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # Save image
    image_path = images_dir / filename
    image_path.write_bytes(data)

    # Return brand-relative path
    brand_relative = f"products/{product_slug}/images/{filename}"

    # Update product's images list
    product = load_product(brand_slug, product_slug)
    if product:
        if brand_relative not in product.images:
            product.images.append(brand_relative)
            # Set as primary if first image
            if not product.primary_image:
                product.primary_image = brand_relative
            save_product(brand_slug, product)

    logger.info("Added image %s to product %s/%s", filename, brand_slug, product_slug)
    return brand_relative


def delete_product_image(brand_slug: str, product_slug: str, filename: str) -> bool:
    """Delete an image from a product.

    Returns:
        True if image was deleted, False if not found.
    """
    product_dir = get_product_dir(brand_slug, product_slug)
    image_path = product_dir / "images" / filename

    if not image_path.exists():
        return False

    image_path.unlink()

    # Update product's images list
    brand_relative = f"products/{product_slug}/images/{filename}"
    product = load_product(brand_slug, product_slug)
    if product:
        if brand_relative in product.images:
            product.images.remove(brand_relative)
            # Update primary if it was the deleted image
            if product.primary_image == brand_relative:
                product.primary_image = product.images[0] if product.images else ""
            save_product(brand_slug, product)

    logger.info(
        "Deleted image %s from product %s/%s", filename, brand_slug, product_slug
    )
    return True


def set_primary_product_image(
    brand_slug: str, product_slug: str, brand_relative_path: str
) -> bool:
    """Set the primary image for a product.

    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.
        brand_relative_path: Brand-relative path to the image.

    Returns:
        True if primary was set, False if image not found in product.
    """
    product = load_product(brand_slug, product_slug)
    if not product:
        return False

    if brand_relative_path not in product.images:
        return False

    product.primary_image = brand_relative_path
    save_product(brand_slug, product)
    logger.info(
        "Set primary image for product %s/%s to %s",
        brand_slug,
        product_slug,
        brand_relative_path,
    )
    return True


# =============================================================================
# Project Storage Functions
# =============================================================================


def get_projects_dir(brand_slug: str) -> Path:
    """Get the projects directory for a brand."""
    return get_brand_dir(brand_slug) / "projects"


def get_project_dir(brand_slug: str, project_slug: str) -> Path:
    """Get the directory for a specific project."""
    return get_projects_dir(brand_slug) / project_slug


def get_project_index_path(brand_slug: str) -> Path:
    """Get the path to the project index file for a brand."""
    return get_projects_dir(brand_slug) / "index.json"


def load_project_index(brand_slug: str) -> ProjectIndex:
    """Load the project index for a brand."""
    index_path = get_project_index_path(brand_slug)

    if index_path.exists():
        try:
            data = json.loads(index_path.read_text())
            index = ProjectIndex.model_validate(data)
            logger.debug(
                "Loaded project index for %s with %d projects",
                brand_slug,
                len(index.projects),
            )
            return index
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in project index for %s: %s", brand_slug, e)
        except Exception as e:
            logger.warning("Failed to load project index for %s: %s", brand_slug, e)

    logger.debug("Creating new project index for %s", brand_slug)
    return ProjectIndex()


def save_project_index(brand_slug: str, index: ProjectIndex) -> None:
    """Save the project index for a brand atomically."""
    index_path = get_project_index_path(brand_slug)
    write_atomically(index_path,index.model_dump_json(indent=2))
    logger.debug(
        "Saved project index for %s with %d projects",
        brand_slug,
        len(index.projects),
    )


def count_project_assets(brand_slug: str, project_slug: str) -> int:
    """Count assets belonging to a project by filename prefix.

    Searches assets/generated/ and assets/video/ for files prefixed with '{project_slug}__'.
    """
    brand_dir = get_brand_dir(brand_slug)
    asset_dirs = [
        brand_dir / "assets" / "generated",
        brand_dir / "assets" / "video",
    ]

    prefix = f"{project_slug}__"
    count = 0
    allowed_exts = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS
    for asset_dir in asset_dirs:
        if not asset_dir.exists():
            continue
        for file_path in asset_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in allowed_exts:
                if file_path.name.startswith(prefix):
                    count += 1

    return count


def list_project_assets(brand_slug: str, project_slug: str) -> list[str]:
    """List assets belonging to a project by filename prefix.

    Returns:
        List of assets-relative paths (e.g., 'generated/project__file.png',
        'video/project__clip.mp4') for UI compatibility.
    """
    brand_dir = get_brand_dir(brand_slug)
    asset_dirs = {
        "generated": brand_dir / "assets" / "generated",
        "video": brand_dir / "assets" / "video",
    }

    prefix = f"{project_slug}__"
    assets = []
    allowed_exts = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS
    for category, asset_dir in asset_dirs.items():
        if not asset_dir.exists():
            continue
        for file_path in sorted(asset_dir.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in allowed_exts:
                if file_path.name.startswith(prefix):
                    assets.append(f"{category}/{file_path.name}")

    return assets


def create_project(brand_slug: str, project: ProjectFull) -> ProjectSummary:
    """Create a new project for a brand.

    Args:
        brand_slug: Brand identifier.
        project: Complete project data.

    Returns:
        ProjectSummary extracted from the project.

    Raises:
        ValueError: If brand doesn't exist or project already exists.
    """
    brand_dir = get_brand_dir(brand_slug)
    if not brand_dir.exists():
        raise ValueError(f"Brand '{brand_slug}' not found")

    project_dir = get_project_dir(brand_slug, project.slug)
    if project_dir.exists():
        raise ValueError(
            f"Project '{project.slug}' already exists in brand '{brand_slug}'"
        )

    # Create directory
    project_dir.mkdir(parents=True, exist_ok=True)

    # Save project files atomically (asset_count is 0 for new projects)
    asset_count = count_project_assets(brand_slug, project.slug)
    summary = project.to_summary(asset_count=asset_count)
    write_atomically(project_dir/"project.json",summary.model_dump_json(indent=2))
    write_atomically(project_dir/"project_full.json",project.model_dump_json(indent=2))

    # Update index
    index = load_project_index(brand_slug)
    index.add_project(summary)
    save_project_index(brand_slug, index)

    logger.info("Created project %s for brand %s", project.slug, brand_slug)
    return summary


def load_project(brand_slug: str, project_slug: str) -> ProjectFull | None:
    """Load a project's full details from disk.

    Args:
        brand_slug: Brand identifier.
        project_slug: Project identifier.

    Returns:
        ProjectFull or None if not found.
    """
    project_dir = get_project_dir(brand_slug, project_slug)
    project_path = project_dir / "project_full.json"

    if not project_path.exists():
        logger.debug("Project not found: %s/%s", brand_slug, project_slug)
        return None

    try:
        data = json.loads(project_path.read_text())
        return ProjectFull.model_validate(data)
    except Exception as e:
        logger.error("Failed to load project %s/%s: %s", brand_slug, project_slug, e)
        return None


def load_project_summary(brand_slug: str, project_slug: str) -> ProjectSummary | None:
    """Load just the project summary (L0 layer).

    This is faster than load_project() when you only need the summary.
    """
    project_dir = get_project_dir(brand_slug, project_slug)
    summary_path = project_dir / "project.json"

    if not summary_path.exists():
        return None

    try:
        data = json.loads(summary_path.read_text())
        return ProjectSummary.model_validate(data)
    except Exception as e:
        logger.error(
            "Failed to load project summary %s/%s: %s", brand_slug, project_slug, e
        )
        return None


def save_project(brand_slug: str, project: ProjectFull) -> ProjectSummary:
    """Save/update a project.

    Args:
        brand_slug: Brand identifier.
        project: Updated project data.

    Returns:
        Updated ProjectSummary.
    """
    project_dir = get_project_dir(brand_slug, project.slug)

    if not project_dir.exists():
        return create_project(brand_slug, project)

    # Update timestamp
    project.updated_at = datetime.utcnow()

    # Save files atomically (recalculate asset_count)
    asset_count = count_project_assets(brand_slug, project.slug)
    summary = project.to_summary(asset_count=asset_count)
    write_atomically(project_dir/"project.json",summary.model_dump_json(indent=2))
    write_atomically(project_dir/"project_full.json",project.model_dump_json(indent=2))

    # Update index
    index = load_project_index(brand_slug)
    index.add_project(summary)
    save_project_index(brand_slug, index)

    logger.info("Saved project %s for brand %s", project.slug, brand_slug)
    return summary


def delete_project(brand_slug: str, project_slug: str) -> bool:
    """Delete a project and its metadata (not generated assets).

    Note: Generated assets in assets/generated/ are NOT deleted,
    only the project metadata in projects/{slug}/.

    Returns:
        True if project was deleted, False if not found.
    """
    project_dir = get_project_dir(brand_slug, project_slug)

    if not project_dir.exists():
        return False

    shutil.rmtree(project_dir)

    # Update index
    index = load_project_index(brand_slug)
    index.remove_project(project_slug)
    save_project_index(brand_slug, index)

    logger.info("Deleted project %s from brand %s", project_slug, brand_slug)
    return True


def list_projects(brand_slug: str) -> list[ProjectSummary]:
    """List all projects for a brand, sorted by name."""
    index = load_project_index(brand_slug)
    return sorted(index.projects, key=lambda p: p.name.lower())


def get_active_project(brand_slug: str) -> str | None:
    """Get the slug of the currently active project for a brand."""
    index = load_project_index(brand_slug)
    logger.debug(
        "get_active_project(%s) -> %s (from index with %d projects)",
        brand_slug,
        index.active_project,
        len(index.projects),
    )
    return index.active_project


def set_active_project(brand_slug: str, project_slug: str | None) -> None:
    """Set the active project for a brand.

    Args:
        brand_slug: Brand identifier.
        project_slug: Project slug to set as active, or None to clear.

    Raises:
        ValueError: If project doesn't exist (when setting non-None).
    """
    index = load_project_index(brand_slug)

    if project_slug and not index.get_project(project_slug):
        raise ValueError(
            f"Project '{project_slug}' not found in brand '{brand_slug}'"
        )

    index.active_project = project_slug
    save_project_index(brand_slug, index)
    logger.info(
        "Active project for brand %s set to: %s",
        brand_slug,
        project_slug or "(none)",
    )


# =============================================================================
# Template Storage Functions
# =============================================================================


def get_templates_dir(brand_slug: str) -> Path:
    """Get the templates directory for a brand."""
    return get_brand_dir(brand_slug) / "templates"


def get_template_dir(brand_slug: str, template_slug: str) -> Path:
    """Get the directory for a specific template."""
    return get_templates_dir(brand_slug) / template_slug


def get_template_index_path(brand_slug: str) -> Path:
    """Get the path to the template index file for a brand."""
    return get_templates_dir(brand_slug) / "index.json"


def load_template_index(brand_slug: str) -> TemplateIndex:
    """Load the template index for a brand."""
    index_path = get_template_index_path(brand_slug)
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text())
            index = TemplateIndex.model_validate(data)
            logger.debug("Loaded template index for %s with %d templates",
                brand_slug,len(index.templates))
            return index
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in template index for %s: %s",brand_slug,e)
        except Exception as e:
            logger.warning("Failed to load template index for %s: %s",brand_slug,e)
    logger.debug("Creating new template index for %s",brand_slug)
    return TemplateIndex()


def save_template_index(brand_slug: str, index: TemplateIndex) -> None:
    """Save the template index for a brand atomically."""
    index_path = get_template_index_path(brand_slug)
    write_atomically(index_path,index.model_dump_json(indent=2))
    logger.debug("Saved template index for %s with %d templates",brand_slug,len(index.templates))


def create_template(brand_slug: str, template: TemplateFull) -> TemplateSummary:
    """Create a new template for a brand.

    Args:
        brand_slug: Brand identifier.
        template: Complete template data.

    Returns:
        TemplateSummary extracted from the template.

    Raises:
        ValueError: If brand doesn't exist or template already exists.
    """
    brand_dir = get_brand_dir(brand_slug)
    if not brand_dir.exists():
        raise ValueError(f"Brand '{brand_slug}' not found")
    template_dir = get_template_dir(brand_slug, template.slug)
    if template_dir.exists():
        raise ValueError(f"Template '{template.slug}' already exists in brand '{brand_slug}'")
    #Create directory structure
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "images").mkdir(exist_ok=True)
    #Save template files atomically
    summary = template.to_summary()
    write_atomically(template_dir/"template.json",summary.model_dump_json(indent=2))
    write_atomically(template_dir/"template_full.json",template.model_dump_json(indent=2))
    #Update index
    index = load_template_index(brand_slug)
    index.add_template(summary)
    save_template_index(brand_slug, index)
    logger.info("Created template %s for brand %s", template.slug, brand_slug)
    return summary


def load_template(brand_slug: str, template_slug: str) -> TemplateFull | None:
    """Load a template's full details from disk.

    Args:
        brand_slug: Brand identifier.
        template_slug: Template identifier.

    Returns:
        TemplateFull or None if not found.
    """
    template_dir = get_template_dir(brand_slug, template_slug)
    template_path = template_dir / "template_full.json"
    if not template_path.exists():
        logger.debug("Template not found: %s/%s", brand_slug, template_slug)
        return None
    try:
        data = json.loads(template_path.read_text())
        return TemplateFull.model_validate(data)
    except Exception as e:
        logger.error("Failed to load template %s/%s: %s", brand_slug, template_slug, e)
        return None


def load_template_summary(brand_slug: str, template_slug: str) -> TemplateSummary | None:
    """Load just the template summary (L0 layer).

    This is faster than load_template() when you only need the summary.
    """
    template_dir = get_template_dir(brand_slug, template_slug)
    summary_path = template_dir / "template.json"
    if not summary_path.exists():
        return None
    try:
        data = json.loads(summary_path.read_text())
        return TemplateSummary.model_validate(data)
    except Exception as e:
        logger.error("Failed to load template summary %s/%s: %s", brand_slug, template_slug, e)
        return None


def save_template(brand_slug: str, template: TemplateFull) -> TemplateSummary:
    """Save/update a template.

    Args:
        brand_slug: Brand identifier.
        template: Updated template data.

    Returns:
        Updated TemplateSummary.
    """
    template_dir = get_template_dir(brand_slug, template.slug)
    if not template_dir.exists():
        return create_template(brand_slug, template)
    #Update timestamp
    template.updated_at = datetime.utcnow()
    #Save files atomically
    summary = template.to_summary()
    write_atomically(template_dir/"template.json",summary.model_dump_json(indent=2))
    write_atomically(template_dir/"template_full.json",template.model_dump_json(indent=2))
    #Update index
    index = load_template_index(brand_slug)
    index.add_template(summary)
    save_template_index(brand_slug, index)
    logger.info("Saved template %s for brand %s", template.slug, brand_slug)
    return summary


def delete_template(brand_slug: str, template_slug: str) -> bool:
    """Delete a template and all its files.

    Returns:
        True if template was deleted, False if not found.
    """
    template_dir = get_template_dir(brand_slug, template_slug)
    if not template_dir.exists():
        return False
    shutil.rmtree(template_dir)
    #Update index
    index = load_template_index(brand_slug)
    index.remove_template(template_slug)
    save_template_index(brand_slug, index)
    logger.info("Deleted template %s from brand %s", template_slug, brand_slug)
    return True


def list_templates(brand_slug: str) -> list[TemplateSummary]:
    """List all templates for a brand, sorted by name."""
    index = load_template_index(brand_slug)
    return sorted(index.templates, key=lambda t: t.name.lower())


def list_template_images(brand_slug: str, template_slug: str) -> list[str]:
    """List all images for a template.

    Returns:
        List of brand-relative image paths.
    """
    template_dir = get_template_dir(brand_slug, template_slug)
    images_dir = template_dir / "images"
    if not images_dir.exists():
        return []
    images = []
    for fp in sorted(images_dir.iterdir()):
        if fp.suffix.lower() in ALLOWED_IMAGE_EXTS:
            images.append(f"templates/{template_slug}/images/{fp.name}")
    return images


def add_template_image(brand_slug: str, template_slug: str, filename: str, data: bytes) -> str:
    """Add an image to a template.

    Args:
        brand_slug: Brand identifier.
        template_slug: Template identifier.
        filename: Image filename.
        data: Image binary data.

    Returns:
        Brand-relative path to the saved image.

    Raises:
        ValueError: If template doesn't exist.
    """
    template_dir = get_template_dir(brand_slug, template_slug)
    if not template_dir.exists():
        raise ValueError(f"Template '{template_slug}' not found in brand '{brand_slug}'")
    images_dir = template_dir / "images"
    images_dir.mkdir(exist_ok=True)
    #Save image
    image_path = images_dir / filename
    image_path.write_bytes(data)
    #Return brand-relative path
    brand_relative = f"templates/{template_slug}/images/{filename}"
    #Update template's images list
    template = load_template(brand_slug, template_slug)
    if template:
        if brand_relative not in template.images:
            template.images.append(brand_relative)
            #Set as primary if first image
            if not template.primary_image:
                template.primary_image = brand_relative
            save_template(brand_slug, template)
    logger.info("Added image %s to template %s/%s", filename, brand_slug, template_slug)
    return brand_relative


def delete_template_image(brand_slug: str, template_slug: str, filename: str) -> bool:
    """Delete an image from a template.

    Returns:
        True if image was deleted, False if not found.
    """
    template_dir = get_template_dir(brand_slug, template_slug)
    image_path = template_dir / "images" / filename
    if not image_path.exists():
        return False
    image_path.unlink()
    #Update template's images list
    brand_relative = f"templates/{template_slug}/images/{filename}"
    template = load_template(brand_slug, template_slug)
    if template:
        if brand_relative in template.images:
            template.images.remove(brand_relative)
            #Update primary if it was the deleted image
            if template.primary_image == brand_relative:
                template.primary_image = template.images[0] if template.images else ""
            save_template(brand_slug, template)
    logger.info("Deleted image %s from template %s/%s", filename, brand_slug, template_slug)
    return True


def set_primary_template_image(
    brand_slug: str, template_slug: str, brand_relative_path: str
) -> bool:
    """Set the primary image for a template.

    Args:
        brand_slug: Brand identifier.
        template_slug: Template identifier.
        brand_relative_path: Brand-relative path to the image.

    Returns:
        True if primary was set, False if image not found in template.
    """
    template = load_template(brand_slug, template_slug)
    if not template:
        return False
    if brand_relative_path not in template.images:
        return False
    template.primary_image = brand_relative_path
    save_template(brand_slug, template)
    logger.info("Set primary image for template %s/%s to %s",
        brand_slug,template_slug,brand_relative_path)
    return True


def sync_template_index(brand_slug: str) -> int:
    """Reconcile template index with filesystem.

    Adds templates that exist on disk but not in index,
    removes index entries for templates that no longer exist.

    Returns:
        Number of changes made (additions + removals).
    """
    templates_dir = get_templates_dir(brand_slug)
    if not templates_dir.exists():
        return 0
    index = load_template_index(brand_slug)
    changes = 0
    #Find templates on disk
    disk_slugs = set()
    for item in templates_dir.iterdir():
        if item.is_dir() and (item / "template_full.json").exists():
            disk_slugs.add(item.name)
    #Find templates in index
    index_slugs = {t.slug for t in index.templates}
    #Add missing to index
    for slug in disk_slugs - index_slugs:
        template = load_template(brand_slug, slug)
        if template:
            index.add_template(template.to_summary())
            logger.info("Synced template %s to index for brand %s", slug, brand_slug)
            changes += 1
    #Remove orphaned from index
    for slug in index_slugs - disk_slugs:
        index.remove_template(slug)
        logger.info("Removed orphaned template %s from index for brand %s", slug, brand_slug)
        changes += 1
    if changes > 0:
        save_template_index(brand_slug, index)
    return changes
#=============================================================================
#Document Storage Functions
#=============================================================================
def _safe_resolve_in_dir(base_dir:Path,rel_path:str)->tuple[Path|None,str|None]:
    """Resolve path safely within base directory (stdlib-only, no external imports)."""
    try:
        r=(base_dir/rel_path).resolve()
        if not r.is_relative_to(base_dir.resolve()):
            return None,"Invalid path: outside allowed directory"
        return r,None
    except(ValueError,OSError)as e:return None,f"Invalid path: {e}"
def get_docs_dir(brand_slug:str)->Path:
    """Get the docs directory for a brand."""
    return get_brand_dir(brand_slug)/"docs"
def list_documents(brand_slug:str)->list[dict]:
    """List all documents for a brand.
    Supports nested subdirectories via rglob.
    Returns:
        List of document entries with name, path (relative to docs/), and size.
    """
    docs_dir=get_docs_dir(brand_slug)
    if not docs_dir.exists():return []
    documents:list[dict]=[]
    for p in sorted(docs_dir.rglob("*")):
        if not p.is_file()or p.name.startswith(".")or p.suffix.lower()not in ALLOWED_TEXT_EXTS:
            continue
        rel=str(p.relative_to(docs_dir))
        documents.append({"name":p.name,"path":rel,"size":p.stat().st_size})
    return documents
def save_document(brand_slug:str,relative_path:str,content:bytes)->tuple[str|None,str|None]:
    """Save a document to the brand's docs directory.
    Args:
        brand_slug: Brand identifier.
        relative_path: Path relative to docs/ (supports nested dirs).
        content: Document binary content.
    Returns:
        Tuple of (saved_path, error). saved_path is relative to docs/.
    """
    docs_dir=get_docs_dir(brand_slug)
    docs_dir.mkdir(parents=True,exist_ok=True)
    resolved,err=_safe_resolve_in_dir(docs_dir,relative_path)
    if err:return None,err
    #Ensure parent directories exist
    resolved.parent.mkdir(parents=True,exist_ok=True)
    resolved.write_bytes(content)
    logger.debug("Saved document %s for brand %s",relative_path,brand_slug)
    return relative_path,None
def delete_document(brand_slug:str,relative_path:str)->tuple[bool,str|None]:
    """Delete a document from the brand's docs directory.
    Args:
        brand_slug: Brand identifier.
        relative_path: Path relative to docs/.
    Returns:
        Tuple of (success, error).
    """
    docs_dir=get_docs_dir(brand_slug)
    if not docs_dir.exists():return False,"Docs directory not found"
    resolved,err=_safe_resolve_in_dir(docs_dir,relative_path)
    if err:return False,err
    if not resolved.exists():return False,"Document not found"
    if resolved.is_dir():return False,"Cannot delete folders"
    resolved.unlink()
    logger.debug("Deleted document %s for brand %s",relative_path,brand_slug)
    return True,None
def rename_document(brand_slug:str,relative_path:str,new_name:str)->tuple[str|None,str|None]:
    """Rename a document in the brand's docs directory.
    Args:
        brand_slug: Brand identifier.
        relative_path: Current path relative to docs/.
        new_name: New filename (not a path, just the name).
    Returns:
        Tuple of (new_relative_path, error).
    """
    docs_dir=get_docs_dir(brand_slug)
    if not docs_dir.exists():return None,"Docs directory not found"
    resolved,err=_safe_resolve_in_dir(docs_dir,relative_path)
    if err:return None,err
    if not resolved.exists():return None,"Document not found"
    if"/"in new_name or"\\"in new_name:return None,"Invalid filename: path separators not allowed"
    new_path=resolved.parent/new_name
    if new_path.exists():return None,f"File already exists: {new_name}"
    resolved.rename(new_path)
    new_rel=str(new_path.relative_to(docs_dir))
    logger.debug("Renamed document %s to %s for brand %s",relative_path,new_rel,brand_slug)
    return new_rel,None
#=============================================================================
#Image Status Storage Functions
#=============================================================================
IMAGE_STATUS_FILE="image_status.json"
def load_image_status_raw(brand_slug:str)->dict:
    """Load raw image status data from file (no migrations applied).
    Returns empty structure if file missing or invalid.
    """
    fp=get_brand_dir(brand_slug)/IMAGE_STATUS_FILE
    if not fp.exists():return {"version":1,"images":{}}
    try:
        with open(fp,"r",encoding="utf-8")as f:data=json.load(f)
    except(json.JSONDecodeError,OSError):return {"version":1,"images":{}}
    if not isinstance(data,dict):return {"version":1,"images":{}}
    if not isinstance(data.get("version"),int):data["version"]=1
    if not isinstance(data.get("images"),dict):data["images"]={}
    return data
def save_image_status(brand_slug:str,data:dict)->None:
    """Atomically save image status data to file.
    Uses temp file + rename for atomicity.
    """
    import os as _os
    fp=get_brand_dir(brand_slug)/IMAGE_STATUS_FILE
    tmp=fp.with_suffix(".json.tmp")
    fp.parent.mkdir(parents=True,exist_ok=True)
    with open(tmp,"w",encoding="utf-8")as f:json.dump(data,f,indent=2)
    _os.replace(tmp,fp)
    logger.debug("Saved image status for brand %s",brand_slug)
#=============================================================================
#Asset Storage Functions
#=============================================================================
def get_assets_dir(brand_slug:str)->Path:
    """Get the assets directory for a brand."""
    return get_brand_dir(brand_slug)/"assets"
def list_assets(brand_slug:str,category:str|None=None)->list[dict]:
    """List assets for a brand, optionally filtered by category.
    Args:
        brand_slug: Brand identifier.
        category: Optional category to filter (e.g., 'logo', 'marketing', 'generated').
    Returns:
        List of asset entries with filename, path, category, and type.
    """
    assets_dir=get_assets_dir(brand_slug)
    if not assets_dir.exists():return []
    allowed=ALLOWED_IMAGE_EXTS|ALLOWED_VIDEO_EXTS
    assets:list[dict]=[]
    cats=[category]if category else ASSET_CATEGORIES
    for cat in cats:
        cat_dir=assets_dir/cat
        if not cat_dir.exists():continue
        for p in sorted(cat_dir.iterdir()):
            if not p.is_file()or p.name.startswith(".")or p.suffix.lower()not in allowed:continue
            atype="video"if p.suffix.lower()in ALLOWED_VIDEO_EXTS else"image"
            assets.append({"filename":p.name,"path":str(p),"category":cat,"type":atype})
    return assets
def save_asset(brand_slug:str,category:str,filename:str,data:bytes)->tuple[str|None,str|None]:
    """Save an asset to the brand's assets directory.
    Args:
        brand_slug: Brand identifier.
        category: Asset category (e.g., 'logo', 'marketing', 'generated').
        filename: Filename (must not contain path separators).
        data: Binary content.
    Returns:
        Tuple of (relative_path, error). relative_path is 'category/filename'.
    """
    if category not in ASSET_CATEGORIES:return None,f"Invalid category: {category}"
    if"/"in filename or"\\"in filename:return None,"Invalid filename: path separators not allowed"
    suffix=Path(filename).suffix.lower()
    allowed=ALLOWED_IMAGE_EXTS|ALLOWED_VIDEO_EXTS
    if suffix not in allowed:return None,f"Unsupported file type: {suffix}"
    assets_dir=get_assets_dir(brand_slug)
    cat_dir=assets_dir/category
    cat_dir.mkdir(parents=True,exist_ok=True)
    target=cat_dir/filename
    if target.exists():return None,f"File already exists: {filename}"
    target.write_bytes(data)
    rel_path=f"{category}/{filename}"
    logger.debug("Saved asset %s for brand %s",rel_path,brand_slug)
    return rel_path,None
