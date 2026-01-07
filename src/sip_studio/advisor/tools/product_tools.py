"""Product management tools."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from agents import function_tool
from typing_extensions import NotRequired, TypedDict

from sip_studio.brands.models import (
    PackagingTextDescription,
    PackagingTextElement,
    ProductAttribute,
    ProductFull,
)
from sip_studio.brands.product_description import (
    extract_attributes_from_description,
    has_attributes_block,
    merge_attributes_into_description,
)
from sip_studio.config.constants import Limits
from sip_studio.config.logging import get_logger

from . import _common
from .memory_tools import emit_tool_thinking

logger = get_logger(__name__)
# Slug pattern: lowercase alphanumeric with hyphens
SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
ALLOWED_PRODUCT_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_PRODUCT_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


class AttributeInput(TypedDict):
    """Input type for product attributes in create_product/update_product tools."""

    key: str
    value: str
    category: NotRequired[str]


class PackagingTextElementInput(TypedDict):
    """Input type for packaging text elements in update_product_packaging_text tool."""

    text: str
    notes: NotRequired[str]
    role: NotRequired[str]
    typography: NotRequired[str]
    size: NotRequired[str]
    color: NotRequired[str]
    position: NotRequired[str]
    emphasis: NotRequired[str]


def _validate_slug(slug: str) -> str | None:
    """Validate slug is safe for filesystem and URL use."""
    if not slug:
        return "Slug cannot be empty"
    if not SLUG_PATTERN.match(slug):
        return f"Invalid slug '{slug}': must be lowercase alphanumeric with hyphens, no leading/trailing hyphens"
    if ".." in slug or "/" in slug or "\\" in slug:
        return f"Invalid slug '{slug}': contains forbidden characters"
    return None


def _validate_filename(filename: str) -> str | None:
    """Validate filename is safe for product images."""
    if not filename:
        return "Filename cannot be empty"
    if "/" in filename or "\\" in filename or ".." in filename:
        return f"Invalid filename '{filename}': contains forbidden characters"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_PRODUCT_IMAGE_EXTS:
        return f"Invalid file extension '{ext}': allowed are {sorted(ALLOWED_PRODUCT_IMAGE_EXTS)} (product images must be raster)"
    return None


def _resolve_brand_path(relative_path: str) -> Path | None:
    """Resolve a relative path within the active brand directory."""
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return None
    brand_dir = _common.get_brand_dir(brand_slug)
    resolved = brand_dir / relative_path
    try:
        resolved.resolve().relative_to(brand_dir.resolve())
    except ValueError:
        logger.warning(f"Path escapes brand directory: {relative_path}")
        return None
    return resolved


def _build_packaging_context(
    brand_slug: str, product: ProductFull
) -> tuple[str | None, str | None]:
    """Build brand/product context strings for packaging text analysis."""
    from sip_studio.brands.storage import load_brand_summary

    brand_ctx, product_ctx = None, None
    summary = load_brand_summary(brand_slug)
    if summary:
        parts = [summary.name]
        if summary.tagline:
            parts.append(summary.tagline)
        if summary.category:
            parts.append(summary.category)
        if summary.tone:
            parts.append(summary.tone)
        brand_ctx = " - ".join(parts)
    if product.name:
        product_ctx = (
            f"{product.name} - {product.description}" if product.description else product.name
        )
    return brand_ctx, product_ctx


def _impl_create_product(
    name: str, description: str = "", attributes: list[AttributeInput] | None = None
) -> str:
    """Implementation of create_product tool."""
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug_error = _validate_slug(slug)
    if slug_error:
        return f"Error: Cannot generate valid slug from name '{name}'. {slug_error}"
    existing = _common.load_product(brand_slug, slug)
    if existing:
        return f"Error: Product '{slug}' already exists. Use update_product() instead."
    step_id = emit_tool_thinking(
        "Setting up your product...", name, expertise="Product Setup", status="pending"
    )
    description_text = (description or "").strip()
    parsed_attrs: list[ProductAttribute] = []
    if attributes is not None:
        for attr in attributes:
            parsed_attrs.append(
                ProductAttribute(
                    key=attr["key"], value=attr["value"], category=attr.get("category", "general")
                )
            )
    else:
        description_text, parsed_attrs = extract_attributes_from_description(description_text)
    description_text = merge_attributes_into_description(description_text, parsed_attrs)
    product = ProductFull(
        slug=slug, name=name, description=description_text, attributes=parsed_attrs
    )
    try:
        _common.storage_create_product(brand_slug, product)
        logger.info(f"Created product '{slug}' for brand '{brand_slug}'")
        emit_tool_thinking(
            "Product created", "", expertise="Product Setup", status="complete", step_id=step_id
        )
        return f"Created product **{name}** (`{slug}`)."
    except ValueError as e:
        emit_tool_thinking(
            "Product setup failed",
            str(e)[:100],
            expertise="Product Setup",
            status="failed",
            step_id=step_id,
        )
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Failed to create product: {e}")
        emit_tool_thinking(
            "Product setup failed",
            str(e)[:100],
            expertise="Product Setup",
            status="failed",
            step_id=step_id,
        )
        return f"Error creating product: {e}"


async def _impl_add_product_image(
    product_slug: str,
    image_path: str,
    set_as_primary: bool = False,
    allow_non_reference: bool = False,
) -> str:
    """Implementation of add_product_image tool."""
    import io
    import json
    from pathlib import PurePosixPath

    from PIL import Image as PILImage

    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"
    if "\\" in image_path:
        return f"Error: image_path must use forward slashes and be within the uploads/ folder. Got: '{image_path}'."
    parsed_path = PurePosixPath(image_path)
    if parsed_path.is_absolute() or not parsed_path.parts or parsed_path.parts[0] != "uploads":
        return f"Error: image_path must be within the uploads/ folder. Got: '{image_path}'. Upload images first, then add them to products."
    if any(part in {".", ".."} for part in parsed_path.parts):
        return f"Error: image_path must be within the uploads/ folder. Got: '{image_path}'. Upload images first, then add them to products."
    resolved = _resolve_brand_path(image_path)
    if resolved is None:
        return f"Error: Invalid path or no active brand: {image_path}"
    if not resolved.exists():
        return f"Error: File not found: {image_path}"
    if not allow_non_reference:
        analysis_path = resolved.with_name(f"{resolved.name}.analysis.json")
        if analysis_path.exists():
            try:
                analysis = json.loads(analysis_path.read_text())
            except Exception:
                analysis = None
            if isinstance(analysis, dict):
                image_type = str(analysis.get("image_type") or "").strip()
                is_suitable_reference = analysis.get("is_suitable_reference")
                if (
                    image_type in {"screenshot", "document", "label"}
                    or is_suitable_reference is False
                ):
                    pretty_type = image_type or "non-reference"
                    return f"Error: This upload was classified as **{pretty_type}** and is not suitable as a product reference image. Use it for extracting information only, and upload a clean product photo instead. If you still want to store it in the product images anyway, call `add_product_image(..., allow_non_reference=True)`."
    filename = resolved.name
    filename_error = _validate_filename(filename)
    if filename_error:
        return f"Error: {filename_error}"
    try:
        data = resolved.read_bytes()
    except Exception as e:
        return f"Error reading file: {e}"
    if len(data) > MAX_PRODUCT_IMAGE_SIZE_BYTES:
        size_mb = len(data) / (1024 * 1024)
        max_mb = MAX_PRODUCT_IMAGE_SIZE_BYTES / (1024 * 1024)
        return f"Error: Image too large ({size_mb:.1f}MB). Maximum is {max_mb:.0f}MB."
    try:
        img = PILImage.open(io.BytesIO(data))
        img.verify()
    except Exception as e:
        return f"Error: Invalid or corrupted image file: {e}"
    product = _common.load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."
    base_name = resolved.stem
    ext = resolved.suffix.lower()
    if any(img_path.endswith(f"/{filename}") for img_path in product.images):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_{timestamp}{ext}"
        logger.info(f"Filename collision detected, using: {filename}")
    try:
        brand_relative_path = _common.storage_add_product_image(
            brand_slug, product_slug, filename, data
        )
        logger.info(f"Added image '{filename}' to product '{product_slug}'")
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Failed to add product image: {e}")
        return f"Error adding image: {e}"
    if set_as_primary:
        success = _common.storage_set_primary_product_image(
            brand_slug, product_slug, brand_relative_path
        )
        if not success:
            return f"Added image `{filename}` to product **{product.name}**, but failed to set as primary."
        prod_name = product.name
        product = _common.load_product(brand_slug, product_slug)
        if product is None:
            return f"Added image `{filename}` to product **{prod_name}** and set as primary image."
        should_analyze = product.packaging_text is None or (
            product.packaging_text.source_image != brand_relative_path
            and not product.packaging_text.is_human_edited
        )
        if should_analyze:
            try:
                from sip_studio.advisor.image_analyzer import analyze_packaging_text

                full_path = _common.get_brand_dir(brand_slug) / brand_relative_path
                brand_ctx, product_ctx = _build_packaging_context(brand_slug, product)
                result = await analyze_packaging_text(full_path, brand_ctx, product_ctx)
                if result:
                    result.source_image = brand_relative_path
                    product.packaging_text = result
                    _common.storage_save_product(brand_slug, product)
                    elem_count = len(result.elements)
                    if elem_count > 0:
                        logger.info(
                            f"Auto-analyzed packaging text for {product_slug}: {elem_count} elements"
                        )
                        return f"Added image `{filename}` to product **{product.name}** and set as primary image. Auto-extracted {elem_count} text elements from packaging."
                    logger.info(f"Auto-analyzed packaging text for {product_slug}: no text found")
            except Exception as e:
                logger.warning(f"Auto packaging text analysis failed: {e}")
        return f"Added image `{filename}` to product **{product.name}** and set as primary image."
    return f"Added image `{filename}` to product **{product.name}** (`{product_slug}`)."


def _impl_update_product(
    product_slug: str,
    name: str | None = None,
    description: str | None = None,
    attributes: list[AttributeInput] | None = None,
    replace_attributes: bool = False,
) -> str:
    """Implementation of update_product tool."""
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"
    product = _common.load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."
    if name is not None:
        product.name = name
    description_text = product.description
    if description is not None:
        description_text = description
    if attributes is not None:
        if replace_attributes:
            product.attributes = [
                ProductAttribute(
                    key=attr["key"], value=attr["value"], category=attr.get("category", "general")
                )
                for attr in attributes
            ]
        else:
            existing_by_key = {}
            for pa in product.attributes:
                existing_by_key[(pa.category.lower(), pa.key.lower())] = pa
            for ai in attributes:
                category = (ai.get("category") or "general").strip()
                key = (category.lower(), ai["key"].lower())
                if key in existing_by_key:
                    existing_by_key[key].value = ai["value"]
                    existing_by_key[key].category = category
                else:
                    new_attr = ProductAttribute(key=ai["key"], value=ai["value"], category=category)
                    product.attributes.append(new_attr)
                    existing_by_key[key] = new_attr
    elif description is not None and has_attributes_block(description_text):
        description_text, parsed_attrs = extract_attributes_from_description(description_text)
        product.attributes = parsed_attrs
    product.description = merge_attributes_into_description(description_text, product.attributes)
    try:
        _common.storage_save_product(brand_slug, product)
        logger.info(f"Updated product '{product_slug}' for brand '{brand_slug}'")
        return f"Updated product **{product.name}** (`{product_slug}`)."
    except Exception as e:
        logger.error(f"Failed to update product: {e}")
        return f"Error updating product: {e}"


def _impl_delete_product(product_slug: str, confirm: bool = False) -> str:
    """Implementation of delete_product tool."""
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"
    product = _common.load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."
    if not confirm:
        image_count = len(product.images)
        return f"This will permanently delete **{product.name}** and all {image_count} images.\n\nTo confirm, call `delete_product(product_slug, confirm=True)`."
    try:
        _common.storage_delete_product(brand_slug, product_slug)
        logger.info(f"Deleted product '{product_slug}' from brand '{brand_slug}'")
        return f"Deleted product **{product.name}** (`{product_slug}`)."
    except Exception as e:
        logger.error(f"Failed to delete product: {e}")
        return f"Error deleting product: {e}"


def _impl_set_product_primary_image(product_slug: str, image_path: str) -> str:
    """Implementation of set_product_primary_image tool."""
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"
    product = _common.load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."
    if image_path not in product.images:
        available_images = "\n".join(f"- {img}" for img in product.images)
        return f"Error: Image '{image_path}' not found in product '{product_slug}'.\nAvailable images:\n{available_images}"
    try:
        success = _common.storage_set_primary_product_image(brand_slug, product_slug, image_path)
        if success:
            return f"Set `{image_path}` as primary image for product **{product.name}** (`{product_slug}`)."
        else:
            return f"Error: Failed to set `{image_path}` as primary image for product **{product.name}** (`{product_slug}`)."
    except Exception as e:
        logger.error(f"Failed to set primary product image: {e}")
        return f"Error setting primary image: {e}"


async def _impl_analyze_product_packaging(product_slug: str, force: bool = False) -> str:
    """Implementation of analyze_product_packaging tool."""
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"
    product = _common.load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."
    if not product.primary_image:
        return f"Error: Product '{product_slug}' has no primary image. Add an image first."
    if product.packaging_text is not None and not force:
        elem_count = len(product.packaging_text.elements)
        return f"Product '{product.name}' already has packaging text ({elem_count} elements). Use force=True to re-analyze."
    brand_dir = _common.get_brand_dir(brand_slug)
    image_path = brand_dir / product.primary_image
    if not image_path.exists():
        return f"Error: Primary image not found: {product.primary_image}"
    try:
        from sip_studio.advisor.image_analyzer import analyze_packaging_text

        brand_ctx, product_ctx = _build_packaging_context(brand_slug, product)
        result = await analyze_packaging_text(image_path, brand_ctx, product_ctx)
        if result is None:
            return f"Packaging text analysis failed for '{product.name}'. Check logs for details."
        result.source_image = product.primary_image
        product.packaging_text = result
        _common.storage_save_product(brand_slug, product)
        elem_count = len(result.elements)
        if elem_count == 0:
            return f"Analyzed **{product.name}** - no text found on packaging."
        texts = [e.text for e in result.elements[:3]]
        preview = ", ".join(f'"{t}"' for t in texts)
        more = f" (+{elem_count - 3} more)" if elem_count > 3 else ""
        return f"Analyzed **{product.name}** - found {elem_count} text elements: {preview}{more}"
    except Exception as e:
        logger.error(f"Packaging text analysis failed: {e}")
        return f"Error analyzing packaging text: {e}"


async def _impl_analyze_all_product_packaging(
    skip_existing: bool = True,
    skip_human_edited: bool = True,
    max_products: int = Limits.MAX_PRODUCTS,
) -> str:
    """Implementation of analyze_all_product_packaging tool."""
    import asyncio

    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    products = _common.storage_list_products(brand_slug)
    if not products:
        return "No products found for active brand."
    analyzed, skipped, failed = 0, 0, 0
    failures: list[str] = []
    for i, summary in enumerate(products[:max_products]):
        product = _common.load_product(brand_slug, summary.slug)
        if product is None:
            skipped += 1
            continue
        if not product.primary_image:
            skipped += 1
            continue
        if skip_existing and product.packaging_text is not None:
            skipped += 1
            continue
        if skip_human_edited and product.packaging_text and product.packaging_text.is_human_edited:
            skipped += 1
            continue
        try:
            brand_dir = _common.get_brand_dir(brand_slug)
            image_path = brand_dir / product.primary_image
            if not image_path.exists():
                skipped += 1
                continue
            from sip_studio.advisor.image_analyzer import analyze_packaging_text

            brand_ctx, product_ctx = _build_packaging_context(brand_slug, product)
            result = await analyze_packaging_text(image_path, brand_ctx, product_ctx)
            if result is None:
                failed += 1
                failures.append(f"{product.name}: analysis returned None")
                continue
            result.source_image = product.primary_image
            product.packaging_text = result
            _common.storage_save_product(brand_slug, product)
            analyzed += 1
            logger.info(f"Analyzed packaging text for {product.slug}")
        except Exception as e:
            failed += 1
            failures.append(f"{product.name}: {e}")
            logger.warning(f"Failed to analyze {product.slug}: {e}")
        if i < len(products[:max_products]) - 1:
            await asyncio.sleep(1)
    total = len(products[:max_products])
    result_lines = [
        f"Bulk packaging text analysis complete: {analyzed}/{total} analyzed, {skipped} skipped, {failed} failed."
    ]
    if failures:
        result_lines.append("Failures:")
        for f in failures[:5]:
            result_lines.append(f"  - {f}")
        if len(failures) > 5:
            result_lines.append(f"  ... and {len(failures) - 5} more")
    return "\n".join(result_lines)


def _impl_update_product_packaging_text(
    product_slug: str,
    summary: str | None = None,
    elements: list[PackagingTextElementInput] | None = None,
    layout_notes: str | None = None,
) -> str:
    """Implementation of update_product_packaging_text tool."""
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"
    product = _common.load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."
    if product.packaging_text is None:
        product.packaging_text = PackagingTextDescription()
    if summary is not None:
        product.packaging_text.summary = summary
    if layout_notes is not None:
        product.packaging_text.layout_notes = layout_notes
    if elements is not None:
        product.packaging_text.elements = [PackagingTextElement(**e) for e in elements]
    product.packaging_text.is_human_edited = True
    product.packaging_text.edited_at = datetime.now(timezone.utc)
    _common.storage_save_product(brand_slug, product)
    elem_count = len(product.packaging_text.elements)
    return f"Updated packaging text for **{product.name}** ({elem_count} elements). Marked as human-edited."


@function_tool
def create_product(
    name: str, description: str = "", attributes: list[AttributeInput] | None = None
) -> str:
    """Create a new product for the active brand.
    Args:
        name: Product name. A URL-safe slug will be generated.
        description: Optional product description.
        attributes: Optional list of product attributes.
    Returns:
        Success message with product name and slug, or error message.
    """
    return _impl_create_product(name, description, attributes)


@function_tool
async def add_product_image(
    product_slug: str,
    image_path: str,
    set_as_primary: bool = False,
    allow_non_reference: bool = False,
) -> str:
    """Add an image to a product from the uploads folder.
    Args:
        product_slug: The product's slug identifier.
        image_path: Path to the image within the brand directory (must be in uploads/).
        set_as_primary: If True, set this image as the product's primary image.
        allow_non_reference: If True, allow adding non-reference images.
    Returns:
        Success message with the added filename, or error message.
    """
    return await _impl_add_product_image(
        product_slug, image_path, set_as_primary, allow_non_reference
    )


@function_tool
def update_product(
    product_slug: str,
    name: str | None = None,
    description: str | None = None,
    attributes: list[AttributeInput] | None = None,
    replace_attributes: bool = False,
) -> str:
    """Update an existing product's details. Attributes merge by default.
    Args:
        product_slug: The product's slug identifier.
        name: Optional new product name.
        description: Optional new product description.
        attributes: Optional list of product attributes to merge or replace.
        replace_attributes: If True, replace all existing attributes.
    Returns:
        Success message with the updated product name and slug, or error message.
    """
    return _impl_update_product(product_slug, name, description, attributes, replace_attributes)


@function_tool
def delete_product(product_slug: str, confirm: bool = False) -> str:
    """Delete a product and all its files. Requires confirm=True.
    Args:
        product_slug: The product's slug identifier.
        confirm: Must be True to actually delete the product.
    Returns:
        Success message or error/warning.
    """
    return _impl_delete_product(product_slug, confirm)


@function_tool
def set_product_primary_image(product_slug: str, image_path: str) -> str:
    """Set the primary image for a product.
    Args:
        product_slug: The product's slug identifier.
        image_path: Path to the image within the product's images list.
    Returns:
        Success message or error message.
    """
    return _impl_set_product_primary_image(product_slug, image_path)


@function_tool
async def analyze_product_packaging(product_slug: str, force: bool = False) -> str:
    """Analyze packaging text from product's primary image using AI vision.
    Args:
        product_slug: Product to analyze (must have a primary image).
        force: Re-analyze even if packaging_text exists.
    Returns:
        Summary of extracted text elements or error message.
    """
    return await _impl_analyze_product_packaging(product_slug, force)


@function_tool
async def analyze_all_product_packaging(
    skip_existing: bool = True,
    skip_human_edited: bool = True,
    max_products: int = Limits.MAX_PRODUCTS,
) -> str:
    """Bulk analyze packaging text for all products in the active brand.
    Args:
        skip_existing: Skip products that already have packaging_text.
        skip_human_edited: Skip products where packaging_text was manually edited.
        max_products: Max products to process in one batch.
    Returns:
        Summary with counts of analyzed, skipped, and failed products.
    """
    return await _impl_analyze_all_product_packaging(skip_existing, skip_human_edited, max_products)


@function_tool
def update_product_packaging_text(
    product_slug: str,
    summary: str | None = None,
    elements: list[PackagingTextElementInput] | None = None,
    layout_notes: str | None = None,
) -> str:
    """Update packaging text with human corrections.
    Args:
        product_slug: Product to update.
        summary: New summary text (or None to keep existing).
        elements: New list of element objects.
        layout_notes: New layout notes (or None to keep existing).
    Returns:
        Success message or error.
    """
    return _impl_update_product_packaging_text(product_slug, summary, elements, layout_notes)
