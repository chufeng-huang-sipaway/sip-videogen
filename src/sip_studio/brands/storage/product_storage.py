"""Product CRUD operations."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from sip_studio.constants import ALLOWED_IMAGE_EXTS
from sip_studio.exceptions import BrandNotFoundError, DuplicateEntityError, ProductNotFoundError
from sip_studio.utils.file_utils import write_atomically

from ..models import ProductFull, ProductIndex, ProductSummary
from .base import get_brand_dir

logger = logging.getLogger(__name__)


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
    ip = get_product_index_path(brand_slug)
    if ip.exists():
        try:
            data = json.loads(ip.read_text())
            idx = ProductIndex.model_validate(data)
            logger.debug(
                "Loaded product index for %s with %d products", brand_slug, len(idx.products)
            )
            return idx
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in product index for %s: %s", brand_slug, e)
        except Exception as e:
            logger.warning("Failed to load product index for %s: %s", brand_slug, e)
    logger.debug("Creating new product index for %s", brand_slug)
    return ProductIndex()


def save_product_index(brand_slug: str, index: ProductIndex) -> None:
    """Save the product index for a brand atomically."""
    ip = get_product_index_path(brand_slug)
    write_atomically(ip, index.model_dump_json(indent=2))
    logger.debug("Saved product index for %s with %d products", brand_slug, len(index.products))


def create_product(brand_slug: str, product: ProductFull) -> ProductSummary:
    """Create a new product for a brand.
    Args:
        brand_slug: Brand identifier.
        product: Complete product data.
    Returns:
        ProductSummary extracted from the product.
    Raises:
        BrandNotFoundError: If brand doesn't exist.
        DuplicateEntityError: If product already exists.
    """
    bd = get_brand_dir(brand_slug)
    if not bd.exists():
        raise BrandNotFoundError(f"Brand '{brand_slug}' not found")
    pd = get_product_dir(brand_slug, product.slug)
    if pd.exists():
        raise DuplicateEntityError(
            f"Product '{product.slug}' already exists in brand '{brand_slug}'"
        )
    # Create directory structure
    pd.mkdir(parents=True, exist_ok=True)
    (pd / "images").mkdir(exist_ok=True)
    # Save product files atomically
    summary = product.to_summary()
    write_atomically(pd / "product.json", summary.model_dump_json(indent=2))
    write_atomically(pd / "product_full.json", product.model_dump_json(indent=2))
    # Update index
    idx = load_product_index(brand_slug)
    idx.add_product(summary)
    save_product_index(brand_slug, idx)
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
    pd = get_product_dir(brand_slug, product_slug)
    pp = pd / "product_full.json"
    if not pp.exists():
        logger.debug("Product not found: %s/%s", brand_slug, product_slug)
        return None
    try:
        data = json.loads(pp.read_text())
        return ProductFull.model_validate(data)
    except Exception as e:
        logger.error("Failed to load product %s/%s: %s", brand_slug, product_slug, e)
        return None


def load_product_summary(brand_slug: str, product_slug: str) -> ProductSummary | None:
    """Load just the product summary (L0 layer).
    This is faster than load_product() when you only need the summary.
    """
    pd = get_product_dir(brand_slug, product_slug)
    sp = pd / "product.json"
    if not sp.exists():
        return None
    try:
        data = json.loads(sp.read_text())
        return ProductSummary.model_validate(data)
    except Exception as e:
        logger.error("Failed to load product summary %s/%s: %s", brand_slug, product_slug, e)
        return None


def save_product(brand_slug: str, product: ProductFull) -> ProductSummary:
    """Save/update a product.
    Args:
        brand_slug: Brand identifier.
        product: Updated product data.
    Returns:
        Updated ProductSummary.
    """
    pd = get_product_dir(brand_slug, product.slug)
    if not pd.exists():
        return create_product(brand_slug, product)
    # Update timestamp
    product.updated_at = datetime.utcnow()
    # Save files atomically
    summary = product.to_summary()
    write_atomically(pd / "product.json", summary.model_dump_json(indent=2))
    write_atomically(pd / "product_full.json", product.model_dump_json(indent=2))
    # Update index
    idx = load_product_index(brand_slug)
    idx.add_product(summary)
    save_product_index(brand_slug, idx)
    logger.info("Saved product %s for brand %s", product.slug, brand_slug)
    return summary


def delete_product(brand_slug: str, product_slug: str) -> bool:
    """Delete a product and all its files.
    Returns:
        True if product was deleted, False if not found.
    """
    pd = get_product_dir(brand_slug, product_slug)
    if not pd.exists():
        return False
    shutil.rmtree(pd)
    # Update index
    idx = load_product_index(brand_slug)
    idx.remove_product(product_slug)
    save_product_index(brand_slug, idx)
    logger.info("Deleted product %s from brand %s", product_slug, brand_slug)
    return True


def list_products(brand_slug: str) -> list[ProductSummary]:
    """List all products for a brand, sorted by name."""
    idx = load_product_index(brand_slug)
    return sorted(idx.products, key=lambda p: p.name.lower())


def list_product_images(brand_slug: str, product_slug: str) -> list[str]:
    """List all images for a product.
    Returns:
        List of brand-relative image paths.
    """
    pd = get_product_dir(brand_slug, product_slug)
    imd = pd / "images"
    if not imd.exists():
        return []
    imgs = []
    for fp in sorted(imd.iterdir()):
        if fp.suffix.lower() in ALLOWED_IMAGE_EXTS:
            imgs.append(f"products/{product_slug}/images/{fp.name}")
    return imgs


def add_product_image(brand_slug: str, product_slug: str, filename: str, data: bytes) -> str:
    """Add an image to a product.
    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.
        filename: Image filename.
        data: Image binary data.
    Returns:
        Brand-relative path to the saved image.
    Raises:
        ProductNotFoundError: If product doesn't exist.
    """
    pd = get_product_dir(brand_slug, product_slug)
    if not pd.exists():
        raise ProductNotFoundError(f"Product '{product_slug}' not found in brand '{brand_slug}'")
    imd = pd / "images"
    imd.mkdir(exist_ok=True)
    # Save image
    (imd / filename).write_bytes(data)
    # Return brand-relative path
    br = f"products/{product_slug}/images/{filename}"
    # Update product's images list
    prod = load_product(brand_slug, product_slug)
    if prod:
        if br not in prod.images:
            prod.images.append(br)
            # Set as primary if first image
            if not prod.primary_image:
                prod.primary_image = br
            save_product(brand_slug, prod)
    logger.info("Added image %s to product %s/%s", filename, brand_slug, product_slug)
    return br


def delete_product_image(brand_slug: str, product_slug: str, filename: str) -> bool:
    """Delete an image from a product.
    Returns:
        True if image was deleted, False if not found.
    """
    pd = get_product_dir(brand_slug, product_slug)
    ip = pd / "images" / filename
    if not ip.exists():
        return False
    ip.unlink()
    # Update product's images list
    br = f"products/{product_slug}/images/{filename}"
    prod = load_product(brand_slug, product_slug)
    if prod:
        if br in prod.images:
            prod.images.remove(br)
            # Update primary if it was the deleted image
            if prod.primary_image == br:
                prod.primary_image = prod.images[0] if prod.images else ""
            save_product(brand_slug, prod)
    logger.info("Deleted image %s from product %s/%s", filename, brand_slug, product_slug)
    return True


def set_primary_product_image(brand_slug: str, product_slug: str, brand_relative_path: str) -> bool:
    """Set the primary image for a product.
    Args:
        brand_slug: Brand identifier.
        product_slug: Product identifier.
        brand_relative_path: Brand-relative path to the image.
    Returns:
        True if primary was set, False if image not found in product.
    """
    prod = load_product(brand_slug, product_slug)
    if not prod:
        return False
    if brand_relative_path not in prod.images:
        return False
    prod.primary_image = brand_relative_path
    save_product(brand_slug, prod)
    logger.info(
        "Set primary image for product %s/%s to %s", brand_slug, product_slug, brand_relative_path
    )
    return True
