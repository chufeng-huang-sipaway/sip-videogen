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
    ProductFull,
    ProductIndex,
    ProductSummary,
    ProjectFull,
    ProjectIndex,
    ProjectSummary,
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
    """Save the product index for a brand."""
    index_path = get_product_index_path(brand_slug)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(index.model_dump_json(indent=2))
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

    # Save product files
    summary = product.to_summary()
    (product_dir / "product.json").write_text(summary.model_dump_json(indent=2))
    (product_dir / "product_full.json").write_text(product.model_dump_json(indent=2))

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

    # Save files
    summary = product.to_summary()
    (product_dir / "product.json").write_text(summary.model_dump_json(indent=2))
    (product_dir / "product_full.json").write_text(product.model_dump_json(indent=2))

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

    if not images_dir.exists():
        return []

    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    images = []

    for file_path in sorted(images_dir.iterdir()):
        if file_path.suffix.lower() in image_extensions:
            # Return brand-relative path
            brand_relative = f"products/{product_slug}/images/{file_path.name}"
            images.append(brand_relative)

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
    """Save the project index for a brand."""
    index_path = get_project_index_path(brand_slug)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(index.model_dump_json(indent=2))
    logger.debug(
        "Saved project index for %s with %d projects",
        brand_slug,
        len(index.projects),
    )


def count_project_assets(brand_slug: str, project_slug: str) -> int:
    """Count assets belonging to a project by filename prefix.

    Searches assets/generated/ for files prefixed with '{project_slug}__'.
    """
    brand_dir = get_brand_dir(brand_slug)
    generated_dir = brand_dir / "assets" / "generated"

    if not generated_dir.exists():
        return 0

    prefix = f"{project_slug}__"
    count = 0
    for file_path in generated_dir.iterdir():
        if file_path.name.startswith(prefix):
            count += 1

    return count


def list_project_assets(brand_slug: str, project_slug: str) -> list[str]:
    """List assets belonging to a project by filename prefix.

    Returns:
        List of assets-relative paths (e.g., 'generated/project__file.png')
        for UI compatibility with existing image loading.
    """
    brand_dir = get_brand_dir(brand_slug)
    generated_dir = brand_dir / "assets" / "generated"

    if not generated_dir.exists():
        return []

    prefix = f"{project_slug}__"
    assets = []
    for file_path in sorted(generated_dir.iterdir()):
        if file_path.name.startswith(prefix):
            # Return assets-relative path for UI compatibility
            assets.append(f"generated/{file_path.name}")

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

    # Save project files (asset_count is 0 for new projects)
    asset_count = count_project_assets(brand_slug, project.slug)
    summary = project.to_summary(asset_count=asset_count)
    (project_dir / "project.json").write_text(summary.model_dump_json(indent=2))
    (project_dir / "project_full.json").write_text(project.model_dump_json(indent=2))

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

    # Save files (recalculate asset_count)
    asset_count = count_project_assets(brand_slug, project.slug)
    summary = project.to_summary(asset_count=asset_count)
    (project_dir / "project.json").write_text(summary.model_dump_json(indent=2))
    (project_dir / "project_full.json").write_text(project.model_dump_json(indent=2))

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
