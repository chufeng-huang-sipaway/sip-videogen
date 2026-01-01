"""Universal tools for Brand Marketing Advisor.

Core tools available to the advisor agent:
1. generate_image - Create images via Gemini 3.0 Pro
2. read_file - Read files from brand directory
3. write_file - Write files to brand directory
4. list_files - List files in brand directory
5. load_brand - Load brand identity and context
6. propose_choices - Present choices to user
7. propose_images - Present images for selection
8. update_memory - Store user preferences

Product and Project exploration tools:
9. list_products - List all products for the active brand
10. list_projects - List all projects/campaigns for the active brand
11. get_product_detail - Get detailed product information
12. get_project_detail - Get detailed project information

Tool functions are defined as pure functions (prefixed with _impl_) for testing,
then wrapped with @function_tool for agent use.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from agents import function_tool
from typing_extensions import NotRequired, TypedDict

from sip_videogen.brands.models import ProductAttribute, ProductFull, TemplateFull, TemplateSummary
from sip_videogen.utils.file_utils import write_atomically
from sip_videogen.brands.product_description import (
    extract_attributes_from_description,
    has_attributes_block,
    merge_attributes_into_description,
)
from sip_videogen.brands.storage import (
    add_product_image as storage_add_product_image,
)
from sip_videogen.brands.storage import (
    create_product as storage_create_product,
)
from sip_videogen.brands.storage import (
    delete_product as storage_delete_product,
)
from sip_videogen.brands.storage import (
    get_active_brand,
    get_active_project,
    get_brand_dir,
    get_brands_dir,
    load_product,
    load_template,
    load_template_summary,
)
from sip_videogen.brands.storage import (
    list_products as storage_list_products,
)
from sip_videogen.brands.storage import (
    list_projects as storage_list_projects,
)
from sip_videogen.brands.storage import (
    load_brand as storage_load_brand,
)
from sip_videogen.brands.storage import (
    save_product as storage_save_product,
)
from sip_videogen.brands.storage import (
    set_primary_product_image as storage_set_primary_product_image,
)
from sip_videogen.brands.storage import (
    create_template as storage_create_template,
    save_template as storage_save_template,
    add_template_image as storage_add_template_image,
    list_templates as storage_list_templates,
    delete_template as storage_delete_template,
)
from sip_videogen.advisor.template_analyzer import analyze_template_v2
from sip_videogen.config.logging import get_logger
from sip_videogen.config.settings import get_settings

logger = get_logger(__name__)


# =============================================================================
# TypedDicts for Tool Input Parameters
# =============================================================================


class AttributeInput(TypedDict):
    """Input type for product attributes in create_product/update_product tools."""

    key: str
    value: str
    category: NotRequired[str]


# =============================================================================
# Image Generation Metadata
# =============================================================================


@dataclass
class ImageGenerationMetadata:
    """Metadata captured during image generation for debugging visibility."""

    prompt: str
    original_prompt: str
    model: str  # "gemini-3-pro-image-preview"
    aspect_ratio: str  # "1:1", "16:9", etc.
    image_size: str  # "4K"
    reference_image: str | None  # Path if used
    product_slugs: list[str]  # Products referenced
    validate_identity: bool
    generated_at: str  # ISO timestamp
    generation_time_ms: int
    api_call_code: str  # The actual Python code executed
    reference_images: list[str] = field(default_factory=list)
    reference_images_detail: list[dict] = field(default_factory=list)
    validation_passed: bool | None = None
    validation_warning: str | None = None
    validation_attempts: int | None = None
    final_attempt_number: int | None = None
    attempts: list[dict] = field(default_factory=list)
    request_payload: dict | None = None


def _build_api_call_code(
    prompt: str,
    model: str,
    aspect_ratio: str,
    image_size: str,
    reference_images: list[str] | None = None,
    grouped_reference_images: list[tuple[str, list[str]]] | None = None,
) -> str:
    """Build a string representation of the actual API call for debugging.

    Shows the complete prompt and actual reference image path(s) so developers
    can understand exactly what was sent to the Gemini API.

    Args:
        prompt: The generation prompt.
        model: Model name.
        aspect_ratio: Image aspect ratio.
        image_size: Image size.
        reference_images: Flat list of image paths (legacy, for single product).
        grouped_reference_images: Grouped structure [(product_name, [paths...]), ...]
            for multi-product with interleaved labels.
    """
    # Escape triple quotes in prompt for valid Python syntax
    prompt_escaped = prompt.replace('"""', '\\"\\"\\"')

    # Use grouped structure if provided (shows interleaved labels)
    if grouped_reference_images:
        contents_lines = ["[", f'    """{prompt_escaped}""",']
        img_idx = 1
        for product_name, paths in grouped_reference_images:
            img_count = len(paths)
            plural = "s" if img_count > 1 else ""
            # Add the label that's sent to Gemini
            label = f"[Reference images for {product_name} ({img_count} image{plural}):]"
            contents_lines.append(f'    "{label}",')
            # Add all images for this product
            for ref_path in paths:
                ref_comment = f"  # Loaded from: {ref_path}"
                contents_lines.append(
                    f"    PILImage.open(io.BytesIO(reference_image_bytes_{img_idx})),{ref_comment}"
                )
                img_idx += 1
        contents_lines.append("]")
        contents_repr = "\n".join(contents_lines)
    elif reference_images:
        # Legacy flat list (for single product or backward compatibility)
        reference_images = [path for path in reference_images if path]
        contents_lines = ["[", f'    """{prompt_escaped}""",']
        for idx, ref_path in enumerate(reference_images, start=1):
            ref_comment = f"  # Loaded from: {ref_path}"
            contents_lines.append(
                f"    PILImage.open(io.BytesIO(reference_image_bytes_{idx})),{ref_comment}"
            )
        contents_lines.append("]")
        contents_repr = "\n".join(contents_lines)
    else:
        contents_repr = f'"""{prompt_escaped}"""'

    return f'''client.models.generate_content(
    model="{model}",
    contents={contents_repr},
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="{aspect_ratio}",
            image_size="{image_size}",
        ),
    ),
)'''


def _build_request_payload(
    prompt: str,
    model: str,
    aspect_ratio: str,
    image_size: str,
    reference_images: list[str] | None = None,
    grouped_reference_images: list[tuple[str, list[str]]] | None = None,
) -> dict:
    """Build a structured representation of the generate_content request.

    Args:
        prompt: The generation prompt.
        model: Model name.
        aspect_ratio: Image aspect ratio.
        image_size: Image size.
        reference_images: Flat list of image paths (legacy).
        grouped_reference_images: Grouped structure [(product_name, [paths...]), ...]
    """
    # Build contents structure
    if grouped_reference_images:
        # Show grouped structure with labels
        contents_items: list[dict] = [{"type": "prompt", "text": prompt}]
        for product_name, paths in grouped_reference_images:
            img_count = len(paths)
            plural = "s" if img_count > 1 else ""
            label = f"[Reference images for {product_name} ({img_count} image{plural}):]"
            contents_items.append({"type": "label", "text": label})
            for path in paths:
                contents_items.append({"type": "image", "path": path})
        contents = {"items": contents_items}
    else:
        contents = {
            "prompt": prompt,
            "reference_images": reference_images or [],
        }

    return {
        "model": model,
        "contents": contents,
        "config": {
            "response_modalities": ["IMAGE"],
            "image_config": {
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
            },
        },
    }


def _build_attempts_metadata(
    attempts: list[dict],
    model: str,
    aspect_ratio: str,
    image_size: str,
    reference_images: list[str] | None = None,
    grouped_reference_images: list[tuple[str, list[str]]] | None = None,
) -> list[dict]:
    """Attach API call details to each attempt record.

    Args:
        attempts: List of attempt records.
        model: Model name.
        aspect_ratio: Image aspect ratio.
        image_size: Image size.
        reference_images: Flat list of image paths (legacy).
        grouped_reference_images: Grouped structure [(product_name, [paths...]), ...]
    """
    enriched_attempts: list[dict] = []
    for attempt in attempts:
        prompt = attempt.get("prompt")
        enriched = dict(attempt)
        if prompt:
            enriched["api_call_code"] = _build_api_call_code(
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
                grouped_reference_images=grouped_reference_images,
            )
            enriched["request_payload"] = _build_request_payload(
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
                grouped_reference_images=grouped_reference_images,
            )
        enriched_attempts.append(enriched)
    return enriched_attempts


# Module-level storage for metadata (keyed by output path)
_image_metadata: dict[str, dict] = {}


def _get_metadata_path(image_path: str) -> Path:
    """Get the .meta.json path for an image."""
    p = Path(image_path)
    return p.with_suffix(".meta.json")


def store_image_metadata(path: str, metadata: ImageGenerationMetadata) -> None:
    """Store metadata for a generated image (in memory and on disk)."""
    import json
    data = asdict(metadata)
    _image_metadata[path] = data
    #Persist to .meta.json file atomically
    try:
        meta_path = _get_metadata_path(path)
        write_atomically(meta_path,json.dumps(data, indent=2))
        logger.debug(f"Saved image metadata to {meta_path}")
    except Exception as e:
        logger.warning(f"Failed to save image metadata: {e}")


def get_image_metadata(path: str) -> dict | None:
    """Get and remove metadata for a generated image from memory."""
    return _image_metadata.pop(path, None)


def load_image_metadata(path: str) -> dict | None:
    """Load metadata for an image from disk (.meta.json file).

    Args:
        path: Path to the image file.

    Returns:
        Metadata dict or None if not found.
    """
    import json
    meta_path = _get_metadata_path(path)
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except Exception as e:
        logger.warning(f"Failed to load image metadata from {meta_path}: {e}")
        return None


# =============================================================================
# Filename Generation Helper
# =============================================================================


def _generate_output_filename(project_slug: str | None = None) -> str:
    """Generate a filename with optional project prefix.

    When a project is active, generated images are tagged with the project
    slug prefix so they can be filtered and listed per-project.

    Args:
        project_slug: Optional project slug to prefix the filename.

    Returns:
        Filename (without extension) with format:
        - With project: "{project_slug}__{timestamp}_{hash}"
        - Without project: "{timestamp}_{hash}"

    Example:
        >>> _generate_output_filename("christmas-campaign")
        "christmas-campaign__20241215_143022_a1b2c3d4"
        >>> _generate_output_filename(None)
        "20241215_143022_a1b2c3d4"
    """
    import uuid
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hash_suffix = uuid.uuid4().hex[:8]

    if project_slug:
        return f"{project_slug}__{timestamp}_{hash_suffix}"
    else:
        return f"{timestamp}_{hash_suffix}"


# =============================================================================
# Path Resolution Helper
# =============================================================================


def _resolve_brand_path(relative_path: str) -> Path | None:
    """Resolve a relative path within the active brand directory.

    Args:
        relative_path: Path relative to brand directory (e.g., "assets/logo/")

    Returns:
        Absolute Path, or None if no active brand or path escapes.
    """
    brand_slug = get_active_brand()
    if not brand_slug:
        return None

    brand_dir = get_brand_dir(brand_slug)
    resolved = brand_dir / relative_path

    # Security: ensure path doesn't escape brand directory
    try:
        resolved.resolve().relative_to(brand_dir.resolve())
    except ValueError:
        logger.warning(f"Path escapes brand directory: {relative_path}")
        return None

    return resolved


# =============================================================================
# Input Validation Helpers (Path Traversal Prevention)
# =============================================================================

# Slug pattern: lowercase alphanumeric with hyphens, no leading/trailing hyphens
SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

# Product images are used as reference images for generation (Pillow-based).
# Do NOT allow SVG here (Pillow can't open it for reference-based generation).
ALLOWED_PRODUCT_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# Maximum product image file size (10MB)
MAX_PRODUCT_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


def _validate_slug(slug: str) -> str | None:
    """Validate slug is safe for filesystem and URL use.

    Args:
        slug: The slug to validate.

    Returns:
        Error message if invalid, None if valid.
    """
    if not slug:
        return "Slug cannot be empty"
    if not SLUG_PATTERN.match(slug):
        return (
            f"Invalid slug '{slug}': must be lowercase alphanumeric with hyphens, "
            "no leading/trailing hyphens"
        )
    if ".." in slug or "/" in slug or "\\" in slug:
        return f"Invalid slug '{slug}': contains forbidden characters"
    return None


def _validate_filename(filename: str) -> str | None:
    """Validate filename is safe for product images.

    Args:
        filename: The filename to validate.

    Returns:
        Error message if invalid, None if valid.
    """
    if not filename:
        return "Filename cannot be empty"
    if "/" in filename or "\\" in filename or ".." in filename:
        return f"Invalid filename '{filename}': contains forbidden characters"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_PRODUCT_IMAGE_EXTS:
        return (
            f"Invalid file extension '{ext}': allowed are "
            f"{sorted(ALLOWED_PRODUCT_IMAGE_EXTS)} (product images must be raster)"
        )
    return None


# =============================================================================
# Interaction + Memory State (captured via hooks)
# =============================================================================

# Stored between tool calls and cleared when hooks read them
_pending_interaction: dict | None = None
_pending_memory_update: dict | None = None
# Progress callback for emitting thinking steps from within tools
_tool_progress_callback: "Callable[[str,str],None]|None" = None
def set_tool_progress_callback(cb:"Callable[[str,str],None]|None")->None:
    """Set callback for tools to emit thinking steps. Called by agent before running."""
    global _tool_progress_callback
    _tool_progress_callback=cb
def emit_tool_thinking(step:str,detail:str="")->None:
    """Emit a thinking step from within a tool. No-op if no callback set."""
    if _tool_progress_callback:_tool_progress_callback(step,detail)


def get_pending_interaction() -> dict | None:
    """Get and clear any pending interaction."""
    global _pending_interaction
    result = _pending_interaction
    _pending_interaction = None
    return result


def get_pending_memory_update() -> dict | None:
    """Get and clear any pending memory update."""
    global _pending_memory_update
    result = _pending_memory_update
    _pending_memory_update = None
    return result


# =============================================================================
# Implementation Functions (for testing)
# =============================================================================


async def _impl_generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    filename: str | None = None,
    reference_image: str | None = None,
    product_slug: str | None = None,
    product_slugs: list[str] | None = None,
    template_slug: str | None = None,
    strict: bool = True,
    validate_identity: bool = False,
    max_retries: int = 3,
) -> str:
    """Implementation of generate_image tool with optional reference-based generation.

    Args:
        prompt: Text description for image generation.
        aspect_ratio: Image aspect ratio.
        filename: Optional output filename (without extension).
        reference_image: Optional path to reference image within brand directory.
        product_slug: Optional product slug - auto-loads the product's primary image
            plus additional reference images (up to the per-product cap) for generation.
        product_slugs: Optional list of product slugs for multi-product generation.
            When provided with 2+ products, uses multi-product validation.
        template_slug: Optional template slug. When provided, loads the template's
            analyzed JSON constraints and applies them to the generation prompt.
        strict: When True with template_slug, enforces exact layout reproduction.
        validate_identity: When True with reference_image, validates that the
            generated image preserves object identity from the reference.
        max_retries: Maximum validation attempts (only used with validate_identity).

    Returns:
        Path to saved image, or error message.
    """
    import io

    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    settings = get_settings()
    brand_slug = get_active_brand()
    model = "gemini-3-pro-image-preview"
    image_size = "4K"

    # Determine output path
    if brand_slug:
        output_dir = get_brand_dir(brand_slug) / "assets" / "generated"
    else:
        output_dir = get_brands_dir() / "_temp"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with project prefix when a project is active
    # IMPORTANT: Always use our format when project is active to ensure proper tagging
    active_project = get_active_project(brand_slug) if brand_slug else None

    if active_project:
        # Always generate our own filename to ensure proper project tagging format
        # (agent may provide filename but with wrong separator format)
        generated_filename = _generate_output_filename(active_project)
        if filename:
            logger.debug(
                f"Agent provided filename '{filename}', "
                f"overriding with '{generated_filename}' for project tagging"
            )
        filename = generated_filename
        logger.info(f"Tagging generated image with project: {active_project}")
    elif not filename:
        # No project active and no filename provided - generate one without prefix
        filename = _generate_output_filename(None)

    output_path = output_dir / f"{filename}.png"

    template_constraints = ""
    if template_slug:
        if not brand_slug:
            return "Error: No active brand - cannot load template"
        template = load_template(brand_slug, template_slug)
        if template is None:
            return f"Error: Template not found: {template_slug}"
        if template.analysis is None:
            return f"Error: Template '{template_slug}' has no analysis"
        #Detect V2 vs V1 analysis and use appropriate builder
        is_v2=getattr(template.analysis,"version","1.0")=="2.0"
        if is_v2:
            from sip_videogen.advisor.template_prompt import build_template_constraints_v2
            template_constraints=build_template_constraints_v2(template.analysis,strict=strict,include_usage=False)
        else:
            from sip_videogen.advisor.template_prompt import build_template_constraints
            template_constraints=build_template_constraints(template.analysis,strict=strict,include_usage=False)
        template_aspect_ratio = template.analysis.canvas.aspect_ratio
        allowed_aspects = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"}
        if template_aspect_ratio and template_aspect_ratio in allowed_aspects:
            if template_aspect_ratio != aspect_ratio:
                logger.info(
                    "Template aspect ratio override: %s -> %s",
                    aspect_ratio,
                    template_aspect_ratio,
                )
            aspect_ratio = template_aspect_ratio

    def _apply_template_constraints(base_prompt: str) -> str:
        if not template_constraints:
            return base_prompt
        return f"{base_prompt}\n\n[TEMPLATE CONSTRAINTS]\n{template_constraints}"

    # Handle multi-product generation with validation
    if product_slugs and len(product_slugs) >= 2:
        if not brand_slug:
            return "Error: No active brand - cannot load products"

        # Load reference images per product (primary + additional, capped)
        # We maintain two structures:
        # - product_references: one (name, bytes) per product for VALIDATION
        # - grouped_generation_images: images grouped by product for GEMINI generation
        #   This allows us to add explicit labels in the API call so Gemini knows
        #   which images belong to which product.
        max_total_images = 16  # Safety cap to avoid API payload issues

        product_references: list[tuple[str, bytes]] = []  # For validation (1 per product)
        # Grouped structure: [(product_name, [image_bytes, ...]), ...]
        grouped_generation_images: list[tuple[str, list[bytes]]] = []
        # Grouped paths for metadata display: [(product_name, [paths, ...]), ...]
        grouped_reference_image_paths: list[tuple[str, list[str]]] = []
        generation_image_paths: list[str] = []
        reference_images_detail: list[dict] = []
        total_images_loaded = 0

        for slug in product_slugs:
            product = load_product(brand_slug, slug)
            if product is None:
                return f"Error: Product not found: {slug}"
            if not product.primary_image:
                return f"Error: Product '{slug}' has no primary image for reference"

            # Get product images (primary first, then additional)
            product_images: list[str] = []
            if product.primary_image:
                product_images.append(product.primary_image)

            # Add all additional images
            if product.images:
                for img in product.images:
                    if img != product.primary_image:
                        product_images.append(img)

            max_refs = min(settings.sip_product_ref_images_per_product, len(product_images))
            if max_refs < len(product_images):
                logger.info(
                    f"Limiting '{product.name}' references to {max_refs} "
                    f"of {len(product_images)} available"
                )
                product_images = product_images[:max_refs]

            # Load the images for this product
            images_loaded = 0
            primary_bytes: bytes | None = None
            current_product_images: list[bytes] = []  # Image bytes for this product
            current_product_paths: list[str] = []  # Image paths for this product

            for img_path in product_images:
                # Safety cap: skip additional images if we've hit the total limit
                if total_images_loaded >= max_total_images and images_loaded > 0:
                    logger.warning(
                        f"Total image cap ({max_total_images}) reached, "
                        f"skipping remaining images for '{product.name}'"
                    )
                    break

                ref_path = _resolve_brand_path(img_path)
                if ref_path is None or not ref_path.exists():
                    if images_loaded == 0:
                        return f"Error: Reference image not found for product '{slug}': {img_path}"
                    else:
                        logger.warning(f"Image not found for '{product.name}': {img_path} → resolved to {ref_path}")
                        continue

                try:
                    ref_bytes = ref_path.read_bytes()
                    current_product_images.append(ref_bytes)  # Add to this product's bytes
                    current_product_paths.append(img_path)  # Add to this product's paths
                    generation_image_paths.append(img_path)
                    role = "primary" if img_path == product.primary_image else "additional"
                    used_for = "generation+validation" if role == "primary" else "generation"
                    reference_images_detail.append(
                        {
                            "path": img_path,
                            "product_slug": slug,
                            "role": role,
                            "used_for": used_for,
                        }
                    )
                    if images_loaded == 0:
                        primary_bytes = ref_bytes  # Keep primary for validation
                        logger.info(f"Loaded primary reference for '{product.name}': {img_path}")
                    else:
                        logger.info(
                            f"Loaded angle {images_loaded + 1} for '{product.name}': {img_path}"
                        )
                    images_loaded += 1
                    total_images_loaded += 1
                except Exception as e:
                    if images_loaded == 0:
                        return f"Error reading reference image for '{slug}': {e}"
                    else:
                        logger.warning(f"Failed to read image for '{product.name}': {img_path} - {type(e).__name__}: {e}")
                        continue

            # Add ONE entry per product to validation refs (primary only)
            if primary_bytes:
                product_references.append((product.name, primary_bytes))

            # Add grouped images for this product (for Gemini generation with labels)
            if current_product_images:
                grouped_generation_images.append((product.name, current_product_images))
                grouped_reference_image_paths.append((product.name, current_product_paths))

            logger.info(f"Loaded {images_loaded}/{len(product_images)} images for '{product.name}'")
            if images_loaded != len(product_images):
                logger.warning(f"Some images failed to load for '{product.name}': expected {len(product_images)}, got {images_loaded}")

        # Phase 1: Inject product specs into prompt if enabled
        generation_prompt = prompt
        if settings.sip_product_specs_injection:
            from sip_videogen.advisor.product_specs import inject_specs_into_prompt

            generation_prompt = inject_specs_into_prompt(
                prompt=prompt,
                brand_slug=brand_slug,
                product_slugs=product_slugs,
            )
            logger.info(f"Injected product specs for {len(product_slugs)} products")
        generation_prompt = _apply_template_constraints(generation_prompt)

        # Use multi-product validation
        from sip_videogen.advisor.validation import generate_with_multi_validation

        total_gen_images = sum(len(imgs) for _, imgs in grouped_generation_images)
        expected_images = 0
        for slug in product_slugs:
            product = load_product(brand_slug, slug)
            if not product:
                continue
            expected_images += min(
                len(product.images),
                settings.sip_product_ref_images_per_product,
            )
        if total_gen_images < expected_images:
            logger.warning(f"Reference image mismatch: expected {expected_images} total images, but only loaded {total_gen_images}. Some images may have failed to load.")
        logger.info(f"Generating multi-product image with {len(product_references)} products, {total_gen_images} total reference images (max {max_retries} retries)...")

        import time
        from datetime import datetime

        start_time = time.time()

        try:
            from google import genai

            client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)
            result = await generate_with_multi_validation(
                client=client,
                prompt=generation_prompt,
                product_references=product_references,  # For validation (1 per product)
                grouped_generation_images=grouped_generation_images,  # Grouped by product
                output_dir=output_dir,
                filename=filename,
                aspect_ratio=aspect_ratio,
                max_retries=max_retries,
                product_slugs=product_slugs,  # Phase 0: Pass for metrics
            )
            if isinstance(result, str):
                return result

            actual_path = result.path
            return_value = actual_path
            if result.warning:
                return_value = f"{actual_path}\n\n{result.warning}"

            reference_images = generation_image_paths
            attempts = _build_attempts_metadata(
                attempts=result.attempts,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
                grouped_reference_images=grouped_reference_image_paths,
            )
            final_prompt = result.final_prompt
            final_api_call = _build_api_call_code(
                prompt=final_prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
                grouped_reference_images=grouped_reference_image_paths,
            )
            final_request_payload = _build_request_payload(
                prompt=final_prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
                grouped_reference_images=grouped_reference_image_paths,
            )
            metadata = ImageGenerationMetadata(
                prompt=final_prompt,
                original_prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_image=reference_images[0] if reference_images else None,
                product_slugs=product_slugs,
                validate_identity=True,
                validation_passed=result.validation_passed,
                validation_warning=result.warning,
                validation_attempts=len(result.attempts),
                final_attempt_number=result.final_attempt_number,
                attempts=attempts,
                request_payload=final_request_payload,
                generated_at=datetime.utcnow().isoformat(),
                generation_time_ms=int((time.time() - start_time) * 1000),
                api_call_code=final_api_call,
                reference_images=reference_images,
                reference_images_detail=reference_images_detail,
            )
            store_image_metadata(actual_path, metadata)

            return return_value
        except Exception as e:
            logger.error(f"Multi-product image generation failed: {e}")
            return f"Error generating multi-product image: {str(e)}"

    # Single-product reference handling (primary + additional images)
    generation_prompt = prompt  # Will be modified if specs injection is enabled
    reference_candidates: list[dict] = []
    reference_images: list[str] = []
    reference_images_detail: list[dict] = []
    reference_images_bytes: list[bytes] = []
    reference_image_bytes: bytes | None = None
    # Save original reference_image before potential overwrite
    original_reference_image = reference_image

    if product_slug:
        if not brand_slug:
            return "Error: No active brand - cannot load product"
        product = load_product(brand_slug, product_slug)
        if product is None:
            return f"Error: Product not found: {product_slug}"
        if product.primary_image:
            product_images = [product.primary_image]
            if product.images:
                for img in product.images:
                    if img != product.primary_image:
                        product_images.append(img)
            max_refs = min(settings.sip_product_ref_images_per_product, len(product_images))
            selected_images = product_images[:max_refs]
            if len(selected_images) < len(product_images):
                logger.info(
                    f"Limiting '{product_slug}' reference images to {max_refs} "
                    f"of {len(product_images)} available"
                )

            reference_image = selected_images[0]
            validate_identity = True
            logger.info(
                f"Using product '{product_slug}' reference images: {', '.join(selected_images)}"
            )

            for img_path in selected_images:
                role = "primary" if img_path == product.primary_image else "additional"
                used_for = "generation+validation" if role == "primary" else "generation"
                reference_candidates.append(
                    {
                        "path": img_path,
                        "product_slug": product_slug,
                        "role": role,
                        "used_for": used_for,
                        "is_primary": role == "primary",
                    }
                )

            # Phase 1: Inject product specs into prompt if enabled
            if settings.sip_product_specs_injection:
                from sip_videogen.advisor.product_specs import inject_specs_into_prompt

                generation_prompt = inject_specs_into_prompt(
                    prompt=prompt,
                    brand_slug=brand_slug,
                    product_slugs=[product_slug],
                )
                logger.info(f"Injected product specs for '{product_slug}'")
            # If original reference_image was provided (e.g., Quick Edit), add it as additional reference
            if original_reference_image and original_reference_image not in selected_images:
                reference_candidates.append({
                    "path": original_reference_image,
                    "product_slug": product_slug,
                    "role": "edit-source",
                    "used_for": "generation",
                    "is_primary": False,
                })
                logger.info(f"Added edit source image: {original_reference_image}")
        else:
            logger.warning(f"Product '{product_slug}' has no primary image")

    generation_prompt = _apply_template_constraints(generation_prompt)

    if reference_image and not reference_candidates:
        role = "primary" if product_slug else "reference"
        used_for = "generation+validation" if validate_identity else "generation"
        reference_candidates.append(
            {
                "path": reference_image,
                "product_slug": product_slug,
                "role": role,
                "used_for": used_for,
                "is_primary": True,
            }
        )

    for candidate in reference_candidates:
        img_path = candidate["path"]
        ref_path = _resolve_brand_path(img_path)
        if ref_path is None:
            if candidate["is_primary"]:
                return f"Error: No active brand or invalid path: {img_path}"
            logger.warning(f"Skipping reference image (invalid path): {img_path}")
            continue
        if not ref_path.exists():
            if candidate["is_primary"]:
                return f"Error: Reference image not found: {img_path}"
            logger.warning(f"Skipping missing reference image: {img_path}")
            continue
        try:
            ref_bytes = ref_path.read_bytes()
        except Exception as e:
            if candidate["is_primary"]:
                return f"Error reading reference image: {e}"
            logger.warning(
                f"Failed to read reference image {img_path}: {type(e).__name__}: {e}"
            )
            continue

        reference_images.append(img_path)
        reference_images_bytes.append(ref_bytes)
        reference_images_detail.append(
            {
                "path": img_path,
                "product_slug": candidate.get("product_slug"),
                "role": candidate.get("role"),
                "used_for": candidate.get("used_for"),
            }
        )
        if candidate["is_primary"]:
            reference_image = img_path
            reference_image_bytes = ref_bytes
            logger.info(f"Loaded reference image: {img_path} ({len(ref_bytes)} bytes)")

    import time
    from datetime import datetime

    start_time = time.time()

    try:
        client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)

        # Use validation loop if enabled and reference provided
        if validate_identity and reference_image_bytes:
            from sip_videogen.advisor.validation import generate_with_validation
            logger.info(f"Generating with validation (max {max_retries} retries)...")
            result = await generate_with_validation(
                client=client,
                prompt=generation_prompt,  # Phase 1: Use specs-injected prompt
                reference_image_bytes=reference_image_bytes,
                reference_images_bytes=reference_images_bytes or None,
                output_dir=output_dir,
                filename=filename,
                aspect_ratio=aspect_ratio,
                max_retries=max_retries,
            )
            if isinstance(result, str):
                return result

            actual_path = result.path
            return_value = actual_path
            if result.warning:
                return_value = f"{actual_path}\n\n{result.warning}"

            attempts = _build_attempts_metadata(
                attempts=result.attempts,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
            )
            final_prompt = result.final_prompt
            final_api_call = _build_api_call_code(
                prompt=final_prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
            )
            final_request_payload = _build_request_payload(
                prompt=final_prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_images=reference_images,
            )
            metadata = ImageGenerationMetadata(
                prompt=final_prompt,
                original_prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                reference_image=reference_image,
                product_slugs=product_slugs or ([product_slug] if product_slug else []),
                validate_identity=validate_identity,
                validation_passed=result.validation_passed,
                validation_warning=result.warning,
                validation_attempts=len(result.attempts),
                final_attempt_number=result.final_attempt_number,
                attempts=attempts,
                request_payload=final_request_payload,
                generated_at=datetime.utcnow().isoformat(),
                generation_time_ms=int((time.time() - start_time) * 1000),
                api_call_code=final_api_call,
                reference_images=reference_images,
                reference_images_detail=reference_images_detail,
            )
            store_image_metadata(actual_path, metadata)

            return return_value

        # Standard generation (with or without reference)
        if reference_images_bytes:
            # Include reference image(s) in contents
            ref_pils = [
                PILImage.open(io.BytesIO(ref_bytes)) for ref_bytes in reference_images_bytes
            ]
            contents = [generation_prompt, *ref_pils]  # Phase 1: Use specs-injected prompt
            logger.info(
                f"Generating image with {len(reference_images_bytes)} reference image(s): "
                f"{generation_prompt[:100]}..."
            )
        else:
            contents = generation_prompt
            logger.info(f"Generating image: {generation_prompt[:100]}...")
        #Emit thinking steps: show enhanced prompt, then indicate API call
        emit_tool_thinking("Prompt enhancement",generation_prompt)
        emit_tool_thinking("Calling Gemini API","Generating image with Gemini 3.0 Pro")
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                ),
            ),
        )

        # Extract and save the image
        for part in response.parts:
            if part.inline_data:
                image = part.as_image()
                image.save(str(output_path))
                logger.info(f"Saved image to: {output_path}")

                # Store metadata for debugging visibility
                final_api_call = _build_api_call_code(
                    prompt=generation_prompt,
                    model=model,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                    reference_images=reference_images,
                )
                final_request_payload = _build_request_payload(
                    prompt=generation_prompt,
                    model=model,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                    reference_images=reference_images,
                )
                attempts = [
                    {
                        "attempt_number": 1,
                        "prompt": generation_prompt,
                        "validation_passed": None,
                        "api_call_code": final_api_call,
                        "request_payload": final_request_payload,
                    }
                ]
                metadata = ImageGenerationMetadata(
                    prompt=generation_prompt,
                    original_prompt=prompt,
                    model=model,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                    reference_image=reference_image,
                    product_slugs=product_slugs or ([product_slug] if product_slug else []),
                    validate_identity=validate_identity,
                    validation_passed=None,
                    validation_warning=None,
                    validation_attempts=None,
                    final_attempt_number=1,
                    attempts=attempts,
                    request_payload=final_request_payload,
                    generated_at=datetime.utcnow().isoformat(),
                    generation_time_ms=int((time.time() - start_time) * 1000),
                    api_call_code=final_api_call,
                    reference_images=reference_images,
                    reference_images_detail=reference_images_detail,
                )
                store_image_metadata(str(output_path), metadata)

                return str(output_path)

        return "Error: No image generated in response"

    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return f"Error generating image: {str(e)}"


# =============================================================================
# Video Generation Implementation
# =============================================================================

#Module-level storage for video metadata (keyed by output path)
_video_metadata: dict[str, dict] = {}


def store_video_metadata(path: str, metadata: dict) -> None:
    """Store metadata for a generated video (in memory and on disk)."""
    import json
    _video_metadata[path] = metadata
    try:
        meta_path = Path(path).with_suffix(".meta.json")
        write_atomically(meta_path,json.dumps(metadata, indent=2))
        logger.debug(f"Saved video metadata to {meta_path}")
    except Exception as e:
        logger.warning(f"Failed to save video metadata: {e}")


def get_video_metadata(path: str) -> dict | None:
    """Get and remove video metadata from memory."""
    return _video_metadata.pop(path, None)


def load_video_metadata(path: str) -> dict | None:
    """Load video metadata from disk (.meta.json file)."""
    import json
    meta_path = Path(path).with_suffix(".meta.json")
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except Exception as e:
        logger.warning(f"Failed to load video metadata from {meta_path}: {e}")
        return None


async def _impl_generate_video_clip(
    prompt: str | None = None,
    concept_image_path: str | None = None,
    aspect_ratio: str = "1:1",
    duration: int | None = None,
    provider: str = "veo",
) -> str:
    """Implementation of generate_video_clip tool.

    Args:
        prompt: Video description. Uses stored prompt from concept image if provided.
        concept_image_path: Path to concept image (from generate_image).
        aspect_ratio: Video aspect ratio ("1:1", "16:9", "9:16", "4:3", "3:4").
        duration: Clip duration in seconds (4, 6, or 8). Forced to 8 with refs.
        provider: Video provider (only "veo" supported).

    Returns:
        Path to saved video, or error message.
    """
    import time as time_mod
    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."
    start_time = time_mod.time()
    settings = get_settings()
    #Determine output directory (same as images - in generated folder for project visibility)
    brand_dir = get_brand_dir(brand_slug)
    output_dir = brand_dir / "assets" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    active_project = get_active_project(brand_slug)
    video_filename_base = _generate_output_filename(active_project)
    #Build effective prompt and reference images
    effective_prompt = prompt
    reference_images: list = []
    image_metadata: dict | None = None
    resolved_concept: Path | None = None
    constraints_context: str | None = None
    product_slugs: list[str] = []
    shared_elements: dict = {}
    scene_element_ids: list[str] = []

    def _resolve_reference_path(path_value: str) -> Path | None:
        if not path_value:
            return None
        candidate = Path(path_value)
        if candidate.is_absolute():
            return candidate if candidate.exists() else None
        #Try assets-relative first (most common for generated images)
        assets_path = brand_dir / "assets" / path_value
        if assets_path.exists():
            return assets_path
        #Try brand-relative as fallback
        brand_path = brand_dir / path_value
        if brand_path.exists():
            return brand_path
        return None

    def _split_product_specs_block(text: str) -> tuple[str, str | None]:
        if not text:
            return "", None
        marker = "### PRODUCT SPECS"
        idx = text.find(marker)
        if idx == -1:
            return text.strip(), None
        prompt_core = text[:idx].rstrip()
        specs_block = text[idx:].strip()
        return prompt_core, specs_block if specs_block else None

    def _normalize_element_id(value: str) -> str:
        clean = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
        return clean or "ref"

    def _derive_product_role_descriptor(product_name: str, index: int) -> str:
        name_lower = (product_name or "").lower()
        if any(keyword in name_lower for keyword in ["jar", "pot"]):
            return "the product jar"
        if "bottle" in name_lower:
            return "the product bottle"
        if "tube" in name_lower:
            return "the product tube"
        if "pump" in name_lower:
            return "the pump bottle"
        for keyword in ["cream", "serum", "toner", "lotion", "oil", "mask", "gel"]:
            if keyword in name_lower:
                return f"the {keyword}"
        return f"product {index}"

    def _build_placeholder_music_brief():
        from sip_videogen.models.music import MusicBrief, MusicGenre, MusicMood

        return MusicBrief(
            prompt=(
                "Placeholder brief for single-clip generation; no background music is needed."
            ),
            mood=MusicMood.CALM,
            genre=MusicGenre.AMBIENT,
            tempo="moderate",
            instruments=[],
            rationale="Placeholder brief for prompt construction only.",
        )

    if concept_image_path:
        #Resolve the concept image path
        resolved_concept = _resolve_reference_path(concept_image_path)
        if resolved_concept is None:
            return f"Error: Concept image not found: {concept_image_path}"
        #Load metadata from the concept image
        image_metadata = load_image_metadata(str(resolved_concept))
        if image_metadata:
            #Use the stored prompt from image generation
            if not effective_prompt:
                effective_prompt = image_metadata.get("prompt")
                if not effective_prompt:
                    effective_prompt = image_metadata.get("original_prompt")
            if effective_prompt:
                logger.info(f"Loaded prompt from concept image: {effective_prompt[:100]}...")
        if not effective_prompt:
            return "Error: No prompt and no prompt in concept image metadata"

        #Collect product slugs (for specs injection and reference labeling)
        raw_product_slugs = image_metadata.get("product_slugs") if image_metadata else None
        if isinstance(raw_product_slugs, list):
            product_slugs = [str(s).strip() for s in raw_product_slugs if str(s).strip()]
            product_slugs = list(dict.fromkeys(product_slugs))

        #Build reference images: prioritize product refs, then concept image, then other refs
        ref_details = image_metadata.get("reference_images_detail") if image_metadata else None
        ref_images = image_metadata.get("reference_images") if image_metadata else None
        ref_candidates: list[dict] = []

        if isinstance(ref_details, list):
            for detail in ref_details:
                if not isinstance(detail, dict):
                    continue
                ref_path = detail.get("path")
                if not ref_path:
                    continue
                product_slug = detail.get("product_slug")
                role = detail.get("role")
                kind = "product" if product_slug else "other"
                ref_candidates.append(
                    {
                        "path": ref_path,
                        "kind": kind,
                        "product_slug": product_slug,
                        "role": role,
                    }
                )
        elif isinstance(ref_images, list):
            for ref_path in ref_images:
                if ref_path:
                    ref_candidates.append(
                        {
                            "path": ref_path,
                            "kind": "other",
                            "product_slug": None,
                            "role": None,
                        }
                    )

        max_refs = 3
        selected_refs: list[dict] = []
        seen_refs: set[str] = set()

        def add_ref(candidate: dict) -> None:
            if len(selected_refs) >= max_refs:
                return
            resolved_path = candidate.get("resolved_path")
            if not resolved_path:
                resolved_path = _resolve_reference_path(candidate.get("path") or "")
            if resolved_path is None:
                return
            key = str(resolved_path)
            if key in seen_refs:
                return
            seen_refs.add(key)
            candidate = {**candidate, "resolved_path": resolved_path}
            selected_refs.append(candidate)

        product_primary = [
            c for c in ref_candidates if c["kind"] == "product" and c.get("role") == "primary"
        ]
        product_secondary = [
            c for c in ref_candidates if c["kind"] == "product" and c.get("role") != "primary"
        ]
        other_refs = [c for c in ref_candidates if c["kind"] == "other"]

        for candidate in product_primary:
            add_ref(candidate)
        if resolved_concept:
            add_ref(
                {
                    "path": str(resolved_concept),
                    "kind": "concept",
                    "product_slug": None,
                    "role": None,
                    "resolved_path": resolved_concept,
                }
            )
        for candidate in product_secondary:
            add_ref(candidate)
        for candidate in other_refs:
            add_ref(candidate)

        if selected_refs:
            from sip_videogen.models.assets import AssetType, GeneratedAsset
            from sip_videogen.models.script import ElementType, SharedElement

            product_index = 0
            for idx, ref in enumerate(selected_refs, start=1):
                kind = ref.get("kind")
                if kind == "product":
                    slug = str(ref.get("product_slug") or "product")
                    element_id = _normalize_element_id(f"product_{slug}")
                    if element_id not in shared_elements:
                        product_index += 1
                        product = load_product(brand_slug, slug)
                        product_name = product.name if product else slug
                        shared_elements[element_id] = SharedElement(
                            id=element_id,
                            element_type=ElementType.PROP,
                            name=product_name,
                            visual_description="Matches the provided reference image exactly.",
                            role_descriptor=_derive_product_role_descriptor(
                                product_name, product_index
                            ),
                            appears_in_scenes=[1],
                        )
                        scene_element_ids.append(element_id)
                elif kind == "concept":
                    element_id = "env_concept_scene"
                    if element_id not in shared_elements:
                        shared_elements[element_id] = SharedElement(
                            id=element_id,
                            element_type=ElementType.ENVIRONMENT,
                            name="scene setting",
                            visual_description=(
                                "Overall lighting, composition, and environment match the "
                                "reference image."
                            ),
                            role_descriptor="",
                            appears_in_scenes=[1],
                        )
                        scene_element_ids.append(element_id)
                else:
                    element_id = _normalize_element_id(f"ref_{idx}")
                    if element_id not in shared_elements:
                        shared_elements[element_id] = SharedElement(
                            id=element_id,
                            element_type=ElementType.PROP,
                            name="style reference",
                            visual_description="Style and texture anchor from the reference image.",
                            role_descriptor="",
                            appears_in_scenes=[1],
                        )
                        scene_element_ids.append(element_id)

                reference_images.append(
                    GeneratedAsset(
                        asset_type=AssetType.REFERENCE_IMAGE,
                        local_path=str(ref["resolved_path"]),
                        element_id=element_id,
                    )
                )
    if effective_prompt:
        effective_prompt, extracted_specs = _split_product_specs_block(effective_prompt)
        if settings.sip_product_specs_injection and product_slugs:
            from sip_videogen.advisor.product_specs import build_product_specs_block

            constraints_context = build_product_specs_block(
                brand_slug=brand_slug,
                product_slugs=product_slugs,
                include_description=False,
                include_constraints=True,
            )
        elif extracted_specs:
            constraints_context = extracted_specs

    if not effective_prompt:
        return "Error: prompt or concept_image_path with metadata required"
    #Validate provider
    if provider != "veo":
        return f"Error: Provider '{provider}' not supported. Only 'veo' available."
    #VEO constraints
    valid_durations = [4, 6, 8]
    if reference_images:
        duration = 8  #VEO forces 8s with reference images
    elif duration is None:
        duration = 8  #Default
    elif duration not in valid_durations:
        duration = min(valid_durations, key=lambda x: abs(x - duration))
        logger.debug(f"Adjusted duration to {duration}s (valid: {valid_durations})")
    try:
        #Create minimal VideoScript with one scene
        from sip_videogen.models.script import SceneAction, VideoScript
        scene = SceneAction(
            scene_number=1,
            duration_seconds=duration,
            setting_description="",
            action_description=effective_prompt,
            dialogue="",
            camera_direction="",
            shared_element_ids=scene_element_ids,
        )
        script_context = None
        if shared_elements:
            script_context = VideoScript(
                title="Single clip",
                logline="Single clip generation",
                tone="",
                visual_style="",
                shared_elements=list(shared_elements.values()),
                scenes=[scene],
                music_brief=_build_placeholder_music_brief(),
            )
        #Initialize VEO generator
        from sip_videogen.generators.video_generator import VEOVideoGenerator
        generator = VEOVideoGenerator(api_key=settings.gemini_api_key)
        #Generate the video clip
        logger.info(f"Generating video with VEO ({duration}s, {aspect_ratio})")
        refs = reference_images if reference_images else None
        result = await generator.generate_video_clip(
            scene=scene,
            output_dir=str(output_dir),
            reference_images=refs,
            aspect_ratio=aspect_ratio,
            script=script_context,
            constraints_context=constraints_context,
        )
        if result and result.local_path:
            #Rename output to a unique, project-prefixed filename
            output_path = Path(result.local_path)
            target_path = output_dir / f"{video_filename_base}.mp4"
            if output_path != target_path:
                output_path.replace(target_path)
            #Store video metadata
            gen_time = int((time_mod.time() - start_time) * 1000)
            video_meta = {
                "prompt": effective_prompt,
                "concept_image_path": concept_image_path,
                "aspect_ratio": aspect_ratio,
                "duration": duration,
                "provider": provider,
                "project_slug": active_project,
                "generated_at": datetime.utcnow().isoformat(),
                "generation_time_ms": gen_time
            }
            if reference_images:
                video_meta["reference_images"] = [
                    asset.local_path for asset in reference_images
                ]
            if constraints_context:
                video_meta["constraints_context"] = constraints_context
            if image_metadata:
                video_meta["source_image_metadata"] = image_metadata
            store_video_metadata(str(target_path), video_meta)
            #Delete concept image after successful video generation (user preference: immediate cleanup)
            if concept_image_path:
                try:
                    cimg=Path(concept_image_path)
                    if cimg.exists():
                        cimg.unlink()
                        logger.info(f"Deleted concept image: {concept_image_path}")
                    #Also delete metadata sidecar if exists
                    meta_sidecar=cimg.with_suffix('.meta.json')
                    if meta_sidecar.exists():
                        meta_sidecar.unlink()
                except OSError as del_err:
                    logger.warning(f"Failed to delete concept image {concept_image_path}: {del_err}")
            logger.info(f"Video clip saved to: {target_path}")
            return str(target_path)
        return "Error: Video generation did not produce a file"
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        return f"Error generating video: {str(e)}"


def _impl_create_product(
    name: str,
    description: str = "",
    attributes: list[AttributeInput] | None = None,
) -> str:
    """Implementation of create_product tool.

    Args:
        name: Product name.
        description: Product description.
        attributes: Optional list of AttributeInput dicts with keys: key, value, category.
            If provided, these are appended to the description in an Attributes block.

    Returns:
        Success message or error.
    """
    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."

    # Generate slug from name
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    # Validate generated slug
    slug_error = _validate_slug(slug)
    if slug_error:
        return f"Error: Cannot generate valid slug from name '{name}'. {slug_error}"

    # Check product doesn't already exist
    existing = load_product(brand_slug, slug)
    if existing:
        return f"Error: Product '{slug}' already exists. Use update_product() instead."

    description_text = (description or "").strip()

    # Parse attributes if provided, otherwise allow description to supply them.
    parsed_attrs: list[ProductAttribute] = []
    if attributes is not None:
        for attr in attributes:
            parsed_attrs.append(
                ProductAttribute(
                    key=attr["key"],
                    value=attr["value"],
                    category=attr.get("category", "general"),
                )
            )
    else:
        description_text, parsed_attrs = extract_attributes_from_description(description_text)

    description_text = merge_attributes_into_description(description_text, parsed_attrs)

    # Create product
    product = ProductFull(
        slug=slug,
        name=name,
        description=description_text,
        attributes=parsed_attrs,
    )

    try:
        storage_create_product(brand_slug, product)
        logger.info(f"Created product '{slug}' for brand '{brand_slug}'")
        return f"Created product **{name}** (`{slug}`)."
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Failed to create product: {e}")
        return f"Error creating product: {e}"


def _impl_add_product_image(
    product_slug: str,
    image_path: str,
    set_as_primary: bool = False,
    allow_non_reference: bool = False,
) -> str:
    """Implementation of add_product_image tool.

    Args:
        product_slug: Product identifier.
        image_path: Path to image within brand directory (must be in uploads/).
        set_as_primary: If True, set this image as the product's primary image.
        allow_non_reference: If True, allow adding images classified as non-reference
            (e.g., screenshots/documents) when a cached analysis exists.

    Returns:
        Success message or error.
    """
    import io

    from PIL import Image as PILImage

    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."

    # Validate product_slug
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"

    # Require image_path to be within uploads/ and disallow traversal segments.
    # Note: we treat tool paths as POSIX-style (forward slashes), which matches the
    # brand-relative paths used across the app.
    from pathlib import PurePosixPath

    if "\\" in image_path:
        return (
            "Error: image_path must use forward slashes and be within the uploads/ folder. "
            f"Got: '{image_path}'."
        )

    parsed_path = PurePosixPath(image_path)
    if parsed_path.is_absolute() or not parsed_path.parts or parsed_path.parts[0] != "uploads":
        return (
            "Error: image_path must be within the uploads/ folder. "
            f"Got: '{image_path}'. Upload images first, then add them to products."
        )

    if any(part in {".", ".."} for part in parsed_path.parts):
        return (
            "Error: image_path must be within the uploads/ folder. "
            f"Got: '{image_path}'. Upload images first, then add them to products."
        )

    # Resolve path
    resolved = _resolve_brand_path(image_path)
    if resolved is None:
        return f"Error: Invalid path or no active brand: {image_path}"

    if not resolved.exists():
        return f"Error: File not found: {image_path}"

    # If the Studio bridge cached a vision analysis for this upload, enforce reference
    # suitability by default to avoid accidentally storing screenshots/docs as product images.
    if not allow_non_reference:
        import json

        analysis_path = resolved.with_name(f"{resolved.name}.analysis.json")
        if analysis_path.exists():
            try:
                analysis = json.loads(analysis_path.read_text())
            except Exception:
                analysis = None

            if isinstance(analysis, dict):
                image_type = str(analysis.get("image_type") or "").strip()
                is_suitable_reference = analysis.get("is_suitable_reference")

                if image_type in {"screenshot", "document", "label"} or is_suitable_reference is False:
                    pretty_type = image_type or "non-reference"
                    return (
                        "Error: This upload was classified as "
                        f"**{pretty_type}** and is not suitable as a product reference image. "
                        "Use it for extracting information only, and upload a clean product photo instead. "
                        "If you still want to store it in the product images anyway, call "
                        "`add_product_image(..., allow_non_reference=True)`."
                    )

    # Get filename and validate
    filename = resolved.name
    filename_error = _validate_filename(filename)
    if filename_error:
        return f"Error: {filename_error}"

    # Read file and check size
    try:
        data = resolved.read_bytes()
    except Exception as e:
        return f"Error reading file: {e}"

    if len(data) > MAX_PRODUCT_IMAGE_SIZE_BYTES:
        size_mb = len(data) / (1024 * 1024)
        max_mb = MAX_PRODUCT_IMAGE_SIZE_BYTES / (1024 * 1024)
        return f"Error: Image too large ({size_mb:.1f}MB). Maximum is {max_mb:.0f}MB."

    # Validate it's a valid raster image using Pillow
    try:
        img = PILImage.open(io.BytesIO(data))
        img.verify()  # Verify image integrity
    except Exception as e:
        return f"Error: Invalid or corrupted image file: {e}"

    # Check product exists
    product = load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."

    # Handle filename collisions with timestamp suffix
    base_name = resolved.stem
    ext = resolved.suffix.lower()
    if any(img_path.endswith(f"/{filename}") for img_path in product.images):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_{timestamp}{ext}"
        logger.info(f"Filename collision detected, using: {filename}")

    # Add image to product
    try:
        brand_relative_path = storage_add_product_image(brand_slug, product_slug, filename, data)
        logger.info(f"Added image '{filename}' to product '{product_slug}'")
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Failed to add product image: {e}")
        return f"Error adding image: {e}"

    # Set as primary if requested
    if set_as_primary:
        success = storage_set_primary_product_image(brand_slug, product_slug, brand_relative_path)
        if success:
            return (
                f"Added image `{filename}` to product **{product.name}** and set as primary image."
            )
        else:
            return (
                f"Added image `{filename}` to product **{product.name}**, "
                "but failed to set as primary."
            )

    return f"Added image `{filename}` to product **{product.name}** (`{product_slug}`)."


def _impl_update_product(
    product_slug: str,
    name: str | None = None,
    description: str | None = None,
    attributes: list[AttributeInput] | None = None,
    replace_attributes: bool = False,
) -> str:
    """Implementation of update_product tool.

    Args:
        product_slug: Product identifier.
        name: Optional new name.
        description: Optional new description.
        attributes: Optional list of AttributeInput dicts. If replace_attributes=False (default),
            merges with existing attributes by (category, key) case-insensitive. If True,
            replaces all existing attributes.
            Any resulting attributes are appended to the description in an "Attributes" block.
        replace_attributes: If True, replace all attributes. If False (default), merge.

    Returns:
        Success message or error.
    """
    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."

    # Validate product_slug
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"

    # Load existing product
    product = load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."

    # Update fields
    if name is not None:
        product.name = name

    description_text = product.description
    if description is not None:
        description_text = description

    # Handle attributes
    if attributes is not None:
        if replace_attributes:
            # Replace all attributes
            product.attributes = [
                ProductAttribute(
                    key=attr["key"],
                    value=attr["value"],
                    category=attr.get("category", "general"),
                )
                for attr in attributes
            ]
        else:
            # Merge attributes by (category, key) case-insensitive
            # Build a dict of existing attributes for quick lookup
            existing_by_key = {}
            for attr in product.attributes:
                key = (attr.category.lower(), attr.key.lower())
                existing_by_key[key] = attr

            # Update or add attributes
            for attr in attributes:
                category = (attr.get("category") or "general").strip()
                key = (category.lower(), attr["key"].lower())
                if key in existing_by_key:
                    # Update existing
                    existing_by_key[key].value = attr["value"]
                    existing_by_key[key].category = category
                else:
                    # Add new
                    new_attr = ProductAttribute(
                        key=attr["key"],
                        value=attr["value"],
                        category=category,
                    )
                    product.attributes.append(new_attr)
                    existing_by_key[key] = new_attr
    elif description is not None and has_attributes_block(description_text):
        # Allow a description-only edit to update structured attributes.
        description_text, parsed_attrs = extract_attributes_from_description(description_text)
        product.attributes = parsed_attrs

    product.description = merge_attributes_into_description(description_text, product.attributes)

    try:
        storage_save_product(brand_slug, product)
        logger.info(f"Updated product '{product_slug}' for brand '{brand_slug}'")
        return f"Updated product **{product.name}** (`{product_slug}`)."
    except Exception as e:
        logger.error(f"Failed to update product: {e}")
        return f"Error updating product: {e}"


def _impl_delete_product(
    product_slug: str,
    confirm: bool = False,
) -> str:
    """Implementation of delete_product tool.

    Args:
        product_slug: Product identifier.
        confirm: Must be True to actually delete the product. If False,
            returns a warning message with product name and image count.

    Returns:
        Success message or error/warning.
    """
    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."

    # Validate product_slug
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"

    # Load product to check if it exists and get details
    product = load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."

    # If confirm=False, return warning message
    if not confirm:
        image_count = len(product.images)
        warning_msg = (
            f"This will permanently delete **{product.name}** and all {image_count} images.\n\n"
            "To confirm, call `delete_product(product_slug, confirm=True)`."
        )
        return warning_msg

    # If confirm=True, proceed with deletion
    try:
        storage_delete_product(brand_slug, product_slug)
        logger.info(f"Deleted product '{product_slug}' from brand '{brand_slug}'")
        return f"Deleted product **{product.name}** (`{product_slug}`)."
    except Exception as e:
        logger.error(f"Failed to delete product: {e}")
        return f"Error deleting product: {e}"


def _impl_set_product_primary_image(
    product_slug: str,
    image_path: str,
) -> str:
    """Implementation of set_product_primary_image tool.

    Args:
        product_slug: Product identifier.
        image_path: Path to image within product.images list.

    Returns:
        Success message or error.
    """
    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."

    # Validate product_slug
    slug_error = _validate_slug(product_slug)
    if slug_error:
        return f"Error: {slug_error}"

    # Load product to check if it exists
    product = load_product(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."

    # Verify image exists in product.images
    if image_path not in product.images:
        available_images = "\n".join(f"- {img}" for img in product.images)
        return (
            f"Error: Image '{image_path}' not found in product '{product_slug}'.\n"
            f"Available images:\n{available_images}"
        )

    # Set as primary image
    try:
        success = storage_set_primary_product_image(brand_slug, product_slug, image_path)
        if success:
            return (
                f"Set `{image_path}` as primary image for product **{product.name}** "
                f"(`{product_slug}`)."
            )
        else:
            return (
                f"Error: Failed to set `{image_path}` as primary image for product "
                f"**{product.name}** (`{product_slug}`)."
            )
    except Exception as e:
        logger.error(f"Failed to set primary product image: {e}")
        return f"Error setting primary image: {e}"


def _impl_read_file(path: str, chunk: int = 0, chunk_size: int = 2000) -> str:
    """Implementation of read_file tool with chunking support.

    Args:
        path: Relative path within brand directory.
        chunk: Chunk number to read (0-indexed, default 0).
        chunk_size: Characters per chunk (100-10000, default 2000).

    Returns:
        File content (possibly chunked) or error message.
    """
    # Parameter validation
    if chunk < 0:
        return f"Error: chunk must be >= 0, got {chunk}"
    if chunk_size < 100:
        chunk_size = 100  # Minimum chunk size
    if chunk_size > 10000:
        chunk_size = 10000  # Maximum chunk size

    resolved = _resolve_brand_path(path)

    if resolved is None:
        return "Error: No active brand selected. Use load_brand() first."

    if not resolved.exists():
        return f"Error: File not found: {path}"

    if not resolved.is_file():
        return f"Error: {path} is a directory, not a file. Use list_files() to browse."

    # Check if it's a text file or binary
    text_extensions = {".json", ".md", ".txt", ".yaml", ".yml", ".csv"}

    if resolved.suffix.lower() in text_extensions:
        try:
            content = resolved.read_text(encoding="utf-8")

            # If small file, return as-is
            if len(content) <= chunk_size:
                return content

            # Calculate chunks
            total_chunks = (len(content) + chunk_size - 1) // chunk_size

            # Validate chunk number
            if chunk >= total_chunks:
                return (
                    f"Error: chunk {chunk} does not exist. "
                    f"File has {total_chunks} chunks (0-{total_chunks - 1})."
                )

            start = chunk * chunk_size
            end = min(start + chunk_size, len(content))
            chunk_content = content[start:end]

            # Add metadata header
            total_len = len(content)
            header = (
                f"[Chunk {chunk + 1}/{total_chunks}] (chars {start + 1}-{end} of {total_len})\n\n"
            )
            footer = ""
            if chunk < total_chunks - 1:
                footer = f'\n\n---\nUse read_file("{path}", chunk={chunk + 1}) for next chunk.'

            return header + chunk_content + footer
        except Exception as e:
            return f"Error reading file: {e}"
    else:
        # Binary file (image, etc.) - just confirm it exists
        size = resolved.stat().st_size
        return f"Binary file exists: {path} ({size} bytes)"


def _impl_write_file(path: str, content: str) -> str:
    """Implementation of write_file tool."""
    resolved = _resolve_brand_path(path)

    if resolved is None:
        return "Error: No active brand selected. Use load_brand() first."

    try:
        # Write content atomically
        write_atomically(resolved,content)

        logger.info(f"Wrote file: {resolved}")
        return f"Successfully wrote to: {path}"

    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        return f"Error writing file: {e}"


def _impl_list_files(path: str = "", limit: int = 20, offset: int = 0) -> str:
    """Implementation of list_files tool with pagination support."""
    # Parameter validation
    if limit < 1:
        limit = 20  # Reset to default
    if limit > 100:
        limit = 100  # Cap at maximum
    if offset < 0:
        offset = 0  # No negative offsets

    resolved = _resolve_brand_path(path) if path else None

    if resolved is None and path:
        return "Error: No active brand selected. Use load_brand() first."

    if resolved is None:
        # List at brand root
        brand_slug = get_active_brand()
        if not brand_slug:
            return "Error: No active brand selected. Use load_brand() first."
        resolved = get_brand_dir(brand_slug)

    if not resolved.exists():
        return f"Error: Directory not found: {path or '/'}"

    if not resolved.is_dir():
        return f"Error: {path} is a file, not a directory. Use read_file() to read it."

    try:
        items = sorted(resolved.iterdir())
        total_count = len(items)

        # Validate offset
        if offset >= total_count and total_count > 0:
            return (
                f"Error: offset {offset} is past end of directory "
                f"({total_count} items). Use offset 0-{total_count - 1}."
            )

        # Apply pagination
        paginated_items = items[offset : offset + limit]
        lines = []

        for item in paginated_items:
            if item.is_dir():
                # Count items in directory
                count = len(list(item.iterdir()))
                lines.append(f"  {item.name}/ ({count} items)")
            else:
                size = item.stat().st_size
                lines.append(f"  {item.name} ({size} bytes)")

        if not lines and total_count == 0:
            return f"Directory is empty: {path or '/'}"

        # Build header with pagination info
        start_idx = offset + 1
        end_idx = min(offset + limit, total_count)
        display_path = path or "/"
        if total_count <= limit and offset == 0:
            header = f"Contents of {display_path}:\n"
        else:
            header = (
                f"Contents of {display_path} (showing {start_idx}-{end_idx} of {total_count}):\n"
            )

        result = header + "\n".join(lines)

        # Add pagination hint if there are more items
        if offset + limit < total_count:
            next_offset = offset + limit
            if path:
                hint = f'\n\nUse list_files("{path}", offset={next_offset}) to see more.'
            else:
                hint = f"\n\nUse list_files(offset={next_offset}) to see more."
            result += hint

        return result

    except Exception as e:
        logger.error(f"Failed to list directory: {e}")
        return f"Error listing directory: {e}"


def _impl_load_brand(
    slug: str | None = None,
    detail_level: Literal["summary", "full"] = "summary",
) -> str:
    """Implementation of load_brand tool.

    Args:
        slug: Brand slug to load. If not provided, uses active brand.
        detail_level: Level of detail to return:
            - "summary" (default): Quick overview (~500 chars)
            - "full": Complete brand context (~2000 chars)

    Returns:
        Formatted brand context as markdown.
    """
    from sip_videogen.brands.memory import list_brand_assets
    from sip_videogen.brands.storage import list_brands

    # Get brand slug - defaults to active brand if not specified
    if not slug:
        slug = get_active_brand()

    if not slug:
        # List available brands
        brands = list_brands()
        if not brands:
            return (
                "No brands found. Create a brand first by telling me about your brand, "
                "and I'll help you develop its identity."
            )

        brand_list = "\n".join(f"  - {b.slug}: {b.name}" for b in brands)
        return (
            f"No active brand. Available brands:\n{brand_list}\n\n"
            "Tell me which brand to work with, or describe a new brand to create."
        )

    # Load the brand identity without changing global active brand state
    # (active brand is managed by the bridge, not by tools)
    identity = storage_load_brand(slug)
    if identity is None:
        return f"Error: Brand not found: {slug}"

    # Get asset count for both modes
    try:
        assets = list_brand_assets(slug)
        asset_count = len(assets)
    except Exception:
        assets = []
        asset_count = 0

    # SUMMARY MODE (default) - ~500 chars
    if detail_level == "summary":
        context_parts = []
        context_parts.append(f"# Brand: {identity.core.name}")
        context_parts.append(f"*{identity.core.tagline}*\n")
        context_parts.append(f"**Category**: {identity.positioning.market_category}")

        if identity.voice.tone_attributes:
            context_parts.append(f"**Tone**: {', '.join(identity.voice.tone_attributes[:3])}")

        # Primary colors only (max 3)
        if identity.visual.primary_colors:
            colors = ", ".join(f"{c.name} ({c.hex})" for c in identity.visual.primary_colors[:3])
            context_parts.append(f"**Colors**: {colors}")

        # Style keywords (max 3)
        if identity.visual.style_keywords:
            context_parts.append(f"**Style**: {', '.join(identity.visual.style_keywords[:3])}")

        # Audience one-liner
        context_parts.append(f"**Audience**: {identity.audience.primary_summary}")

        # Asset count
        context_parts.append(f"**Assets**: {asset_count} files available")

        # Hint for full details
        context_parts.append("")
        context_parts.append("---")
        context_parts.append(
            "For complete brand details including full visual identity, "
            "voice guidelines, and positioning, use `load_brand(detail_level='full')`"
        )

        return "\n".join(context_parts)

    # FULL MODE - existing behavior
    context_parts = []

    # Header
    context_parts.append(f"# Brand: {identity.core.name}")
    context_parts.append(f"*{identity.core.tagline}*\n")

    # Summary
    context_parts.append("## Summary")
    context_parts.append(f"- **Category**: {identity.positioning.market_category}")
    context_parts.append(f"- **Mission**: {identity.core.mission}")
    if identity.voice.tone_attributes:
        context_parts.append(f"- **Tone**: {', '.join(identity.voice.tone_attributes[:3])}")
    context_parts.append("")

    # Visual Identity
    context_parts.append("## Visual Identity")
    if identity.visual.primary_colors:
        colors = ", ".join(f"{c.name} ({c.hex})" for c in identity.visual.primary_colors)
        context_parts.append(f"- **Primary Colors**: {colors}")
    if identity.visual.style_keywords:
        context_parts.append(f"- **Style**: {', '.join(identity.visual.style_keywords)}")
    if identity.visual.overall_aesthetic:
        context_parts.append(f"- **Aesthetic**: {identity.visual.overall_aesthetic[:200]}...")
    context_parts.append("")

    # Voice
    context_parts.append("## Brand Voice")
    context_parts.append(f"- **Personality**: {identity.voice.personality}")
    if identity.voice.key_messages:
        context_parts.append("- **Key Messages**:")
        for msg in identity.voice.key_messages[:3]:
            context_parts.append(f'  - "{msg}"')
    context_parts.append("")

    # Audience
    context_parts.append("## Target Audience")
    context_parts.append(f"- **Primary**: {identity.audience.primary_summary}")
    if identity.audience.demographics:
        demo = identity.audience.demographics
        if demo.age_range:
            context_parts.append(f"- **Age**: {demo.age_range}")
    context_parts.append("")

    # Positioning
    context_parts.append("## Positioning")
    context_parts.append(f"- **UVP**: {identity.positioning.unique_value_proposition}")
    if identity.positioning.positioning_statement:
        context_parts.append(f"- **Statement**: {identity.positioning.positioning_statement}")
    context_parts.append("")

    # Assets - group by category
    if assets:
        # Group assets by category
        by_category: dict[str, list[dict]] = {}
        for asset in assets:
            cat = asset.get("category", "other")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(asset)

        context_parts.append("## Available Assets")
        for category, files in sorted(by_category.items()):
            context_parts.append(f"- **{category}**: {len(files)} files")
        context_parts.append("")

    # Values
    if identity.core.values:
        context_parts.append("## Core Values")
        for value in identity.core.values[:5]:
            context_parts.append(f"- **{value.name}**: {value.meaning}")
        context_parts.append("")

    return "\n".join(context_parts)


def _impl_list_products() -> str:
    """Implementation of list_products tool.

    Returns:
        Formatted list of products for the active brand.
    """
    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."

    products = storage_list_products(brand_slug)

    if not products:
        return f"No products found for brand '{brand_slug}'. Use create_product() to add products."

    lines = [f"Products for brand '{brand_slug}':\n"]
    for product in products:
        primary = f" (primary image: {product.primary_image})" if product.primary_image else ""
        attrs = f", {product.attribute_count} attributes" if product.attribute_count > 0 else ""
        lines.append(f"- **{product.name}** (`{product.slug}`){attrs}{primary}")
        if product.description:
            # Truncate long descriptions
            desc = product.description
            if len(desc) > 100:
                desc = desc[:100] + "..."
            lines.append(f"  {desc}")

    lines.append("")
    lines.append("---")
    lines.append("Use `get_product_detail(product_slug)` for full product information.")

    return "\n".join(lines)


def _impl_list_projects() -> str:
    """Implementation of list_projects tool.

    Returns:
        Formatted list of projects for the active brand.
    """
    from sip_videogen.brands.storage import get_active_project as storage_get_active_project

    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."

    projects = storage_list_projects(brand_slug)
    active_project = storage_get_active_project(brand_slug)

    if not projects:
        return f"No projects found for brand '{brand_slug}'. Use the bridge to create projects."

    lines = [f"Projects for brand '{brand_slug}':\n"]
    for project in projects:
        active_marker = " ★ ACTIVE" if project.slug == active_project else ""
        status_badge = f"[{project.status.value}]"
        assets = f", {project.asset_count} assets" if project.asset_count > 0 else ""
        line = f"- **{project.name}** (`{project.slug}`) {status_badge}{assets}{active_marker}"
        lines.append(line)

    lines.append("")
    lines.append("---")
    lines.append(
        "Use `get_project_detail(project_slug)` for full project info including instructions."
    )

    return "\n".join(lines)


def _impl_get_product_detail(product_slug: str) -> str:
    """Implementation of get_product_detail tool.

    Args:
        product_slug: Product identifier.

    Returns:
        Formatted product detail as markdown.
    """
    from sip_videogen.brands.memory import get_product_full

    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."

    product = get_product_full(brand_slug, product_slug)
    if product is None:
        return f"Error: Product '{product_slug}' not found in brand '{brand_slug}'."

    description_text, desc_attrs = extract_attributes_from_description(product.description or "")
    attributes = product.attributes or desc_attrs

    lines = [f"# Product: {product.name}"]
    lines.append(f"*Slug: `{product.slug}`*\n")

    # Description
    if description_text:
        lines.append("## Description")
        lines.append(description_text)
        lines.append("")

    # Attributes
    if attributes:
        lines.append("## Attributes")
        for attr in attributes:
            lines.append(f"- **{attr.key}** ({attr.category}): {attr.value}")
        lines.append("")

    # Images
    if product.images:
        lines.append("## Images")
        for img in product.images:
            primary_marker = " ★ PRIMARY" if img == product.primary_image else ""
            lines.append(f"- `{img}`{primary_marker}")
        lines.append("")

    # Timestamps
    lines.append("## Metadata")
    lines.append(f"- Created: {product.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- Updated: {product.updated_at.strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


def _impl_get_project_detail(project_slug: str) -> str:
    """Implementation of get_project_detail tool.

    Args:
        project_slug: Project identifier.

    Returns:
        Formatted project detail as markdown.
    """
    from sip_videogen.brands.memory import get_project_full
    from sip_videogen.brands.storage import get_active_project as storage_get_active_project
    from sip_videogen.brands.storage import list_project_assets

    brand_slug = get_active_brand()
    if not brand_slug:
        return "Error: No active brand selected. Use load_brand() first."

    project = get_project_full(brand_slug, project_slug)
    if project is None:
        return f"Error: Project '{project_slug}' not found in brand '{brand_slug}'."

    active_project = storage_get_active_project(brand_slug)
    is_active = project.slug == active_project

    lines = [f"# Project: {project.name}"]
    lines.append(f"*Slug: `{project.slug}`*\n")

    # Status
    active_marker = " ★ ACTIVE" if is_active else ""
    lines.append(f"**Status**: {project.status.value}{active_marker}\n")

    # Instructions
    if project.instructions:
        lines.append("## Instructions")
        lines.append(project.instructions)
        lines.append("")
    else:
        lines.append("## Instructions")
        lines.append("*No instructions set.*")
        lines.append("")

    # Assets
    assets = list_project_assets(brand_slug, project_slug)
    if assets:
        lines.append("## Generated Assets")
        lines.append(f"This project has {len(assets)} generated assets:")
        for asset in assets[:10]:  # Show first 10
            lines.append(f"- `{asset}`")
        if len(assets) > 10:
            lines.append(f"- *...and {len(assets) - 10} more*")
        lines.append("")

    # Timestamps
    lines.append("## Metadata")
    lines.append(f"- Created: {project.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- Updated: {project.updated_at.strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


# =============================================================================
# Wrapped Tools for Agent (with @function_tool decorator)
# =============================================================================


@function_tool
def propose_choices(
    question: str,
    choices: list[str],
    allow_custom: bool = False,
) -> str:
    """Present a multiple-choice question to the user with clickable options.

    Use this tool when you want the user to select from specific options.
    The user will see clickable buttons in the UI. Their selection will be
    returned as the next message in the conversation.

    Args:
        question: The question to ask (e.g., "Which logo style do you prefer?")
        choices: List of 2-5 choices to present as buttons
        allow_custom: If True, show an input field for custom response

    Returns:
        Confirmation that choices are being presented.
    """
    global _pending_interaction

    if len(choices) < 2:
        return "Error: Please provide at least 2 choices"
    if len(choices) > 5:
        choices = choices[:5]

    _pending_interaction = {
        "type": "choices",
        "question": question,
        "choices": choices,
        "allow_custom": allow_custom,
    }

    # Return text for the agent to include in its response
    return f"[Presenting choices to user: {question}]"


@function_tool
def propose_images(
    question: str,
    image_paths: list[str],
    labels: list[str] | None = None,
) -> str:
    """Present images for the user to select from.

    Use this after generating multiple images when you want the user
    to pick their favorite. Images will be shown as clickable cards.

    Args:
        question: The question (e.g., "Which logo do you prefer?")
        image_paths: List of image file paths (relative to brand assets directory,
            e.g. "generated/foo.png")
        labels: Optional short labels for each image (e.g., ["Modern", "Classic"])

    Returns:
        Confirmation that image selection is being presented.
    """
    global _pending_interaction

    if len(image_paths) < 2:
        return "Error: Please provide at least 2 images to choose from"

    # Normalize paths for the UI thumbnail API:
    # - Frontend calls bridge.getAssetThumbnail(path), expects "generated/foo.png"
    # - generate_image returns absolute paths; convert to relative-to-assets
    brand_slug = get_active_brand()
    if brand_slug:
        assets_dir = (get_brand_dir(brand_slug) / "assets").resolve()
        normalized: list[str] = []
        for p in image_paths:
            try:
                candidate = Path(p)
                if candidate.is_absolute():
                    rel = candidate.resolve().relative_to(assets_dir)
                    normalized.append(rel.as_posix())
                else:
                    normalized.append(p)
            except Exception:
                # Skip paths outside assets/ (PyWebView bridge will reject them anyway)
                continue
        image_paths = normalized
        if len(image_paths) < 2:
            return "Error: Please provide at least 2 images within the brand assets folder"

    _pending_interaction = {
        "type": "image_select",
        "question": question,
        "image_paths": image_paths,
        "labels": labels or [f"Option {i + 1}" for i in range(len(image_paths))],
    }

    return f"[Presenting {len(image_paths)} images for user to select]"


@function_tool
async def generate_image(
    prompt: str,
    aspect_ratio: Literal["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"] = "1:1",
    filename: str | None = None,
    reference_image: str | None = None,
    product_slug: str | None = None,
    product_slugs: list[str] | None = None,
    template_slug: str | None = None,
    strict: bool = True,
    validate_identity: bool = False,
    max_retries: int = 3,
) -> str:
    """Generate an image using Gemini 3.0 Pro.

    Creates a high-quality image from a text prompt. Use for brand assets like
    logos, mascots, lifestyle photos, and marketing materials.

    Args:
        prompt: Detailed description of the image to generate. Be specific about
            style, colors, composition, and what to avoid.
        aspect_ratio: Image aspect ratio. Common choices:
            - "1:1" for logos, mascots, social posts
            - "4:5" for Instagram, lifestyle photos
            - "16:9" for hero images, landing pages
            - "9:16" for stories, vertical content
        filename: Optional filename to save as (without extension).
            If not provided, uses a generated name.
        reference_image: Optional path to a reference image within the brand directory.
            When provided, the generated image will incorporate visual elements from
            this reference to maintain consistency. Path should be relative to the
            brand folder (e.g., "uploads/product.png", "assets/logo/main.png").
        product_slug: Optional product slug. When provided without reference_image,
            automatically loads the product's primary image plus additional reference
            images (up to the per-product cap) and enables identity validation. Use
            this when generating images featuring a specific product - the product's
            actual appearance will be preserved.
        product_slugs: Optional list of product slugs for MULTI-PRODUCT images.
            Use this when the user wants to generate an image featuring 2-3 products.
            Each product's primary image (plus any additional product images) will be
            used as references, and multi-product validation ensures EVERY product
            appears accurately. The prompt should describe each product with specific
            details (materials, colors, etc.).
            Example: product_slugs=["night-cream", "day-serum", "toner"]
        template_slug: Optional template slug. When provided, applies the stored
            template layout constraints (JSON analysis) to the prompt.
        strict: When True with template_slug, enforces exact layout reproduction.
        validate_identity: When True AND reference_image is provided, enables a
            validation loop that ensures the generated image preserves the identity
            of objects in the reference. Use when the user needs the EXACT SAME
            object (their specific product, logo, etc.) to appear in the generated
            image, not just something similar. Auto-enabled when using product_slug.
        max_retries: Maximum attempts for the validation loop (default 3). Only
            used when validate_identity is True. If validation fails after all
            retries, returns the best attempt with a warning.

    Returns:
        Path to the saved image file, or error message if generation fails.
        If validation was enabled but didn't pass, includes a warning about
        potential differences from the reference.
    """
    return await _impl_generate_image(
        prompt,
        aspect_ratio,
        filename,
        reference_image,
        product_slug,
        product_slugs,
        template_slug,
        strict,
        validate_identity,
        max_retries,
    )


@function_tool
async def generate_video_clip(
    prompt: str | None = None,
    concept_image_path: str | None = None,
    aspect_ratio: Literal["1:1", "16:9", "9:16", "5:3", "3:5", "4:3", "3:4", "3:2", "2:3"] = "1:1",
    duration: int | None = None,
    provider: Literal["veo"] = "veo",
) -> str:
    """Generate a single video clip using VEO 3.1.

    Creates a short video clip from a text prompt. Use for product videos, lifestyle scenes, and marketing content. Video generation takes 2-3 minutes.

    **Preview-First Workflow (Recommended)**:
    1. First generate a concept image using generate_image
    2. Show the image and get user confirmation
    3. Call generate_video_clip with concept_image_path to use that image as reference

    Args:
        prompt: Video description with motion/action details. If concept_image_path is provided and prompt is None, uses the stored prompt from the concept image generation.
        concept_image_path: Path to a concept image generated by generate_image. When provided:
            - Loads the stored prompt from that image's metadata
            - Uses the image as a visual reference for the video
            - Duration is forced to 8 seconds (VEO constraint)
        aspect_ratio: Video aspect ratio.
            - "1:1" for square (default)
            - "16:9" for landscape
            - "9:16" for portrait/vertical
            - "4:3" for classic
            - "3:4" for portrait classic
        duration: Clip duration in seconds. Valid values: 4, 6, or 8.
            Forced to 8 when using reference images. Defaults to 8.
        provider: Video generation provider. Only "veo" is supported.

    Returns:
        Path to the saved video file (.mp4), or error message if generation fails.
    """
    return await _impl_generate_video_clip(prompt,concept_image_path,aspect_ratio,duration,provider)


@function_tool
def read_file(path: str, chunk: int = 0, chunk_size: int = 2000) -> str:
    """Read a file from the brand directory.

    Args:
        path: Relative path within the brand directory.
            Examples: "identity.json", "assets/logo/logo_primary.png",
            "uploads/reference.jpg"
        chunk: Chunk number to read (0-indexed, default 0).
            For large files, content is split into chunks.
        chunk_size: Characters per chunk (100-10000, default 2000).
            Smaller values save context but require more calls.

    Returns:
        File contents as string (for text files), or
        confirmation that binary file exists (for images/binaries),
        or error message if file not found.

        For large text files, returns the requested chunk with
        metadata showing chunk position and hint for next chunk.
    """
    return _impl_read_file(path, chunk, chunk_size)


@function_tool
def write_file(path: str, content: str) -> str:
    """Write content to a file in the brand directory.

    Creates parent directories if they don't exist.

    Args:
        path: Relative path within the brand directory.
            Examples: "identity.json", "memory.json", "notes.md"
        content: Content to write. For JSON, ensure it's valid JSON string.

    Returns:
        Confirmation message or error.
    """
    return _impl_write_file(path, content)


@function_tool
def list_files(path: str = "", limit: int = 20, offset: int = 0) -> str:
    """List files and directories in the brand directory.

    Args:
        path: Relative path within brand directory. Empty string for root.
            Examples: "", "assets/", "assets/logo/"
        limit: Maximum number of items to return (1-100, default 20).
        offset: Number of items to skip for pagination (default 0).

    Returns:
        Formatted list of files and directories with pagination info,
        or error message.
    """
    return _impl_list_files(path, limit, offset)


@function_tool
def load_brand(
    slug: str | None = None,
    detail_level: Literal["summary", "full"] = "summary",
) -> str:
    """Load brand identity and context.

    If no slug is provided, loads the currently active brand.
    Sets the brand as active for subsequent tool calls.

    Args:
        slug: Brand slug to load. If not provided, uses active brand.
            Available brands can be found in ~/.sip-videogen/brands/
        detail_level: Level of detail to return:
            - "summary" (default): Quick overview (~500 chars) with name,
              tagline, category, tone, primary colors, and asset count.
            - "full": Complete brand context (~2000 chars) including full
              visual identity, voice guidelines, audience profile, and positioning.

    Returns:
        Formatted brand context as markdown. Use "full" detail_level when
        you need complete information for creative work.

        Or error message if brand not found.
    """
    return _impl_load_brand(slug, detail_level)


@function_tool
def list_products() -> str:
    """List all products for the active brand.

    Returns a formatted list of products with their names, slugs, attribute counts,
    and primary images. Use this to explore available products before getting details
    or using them in image generation.

    Products can be used with generate_image(product_slug="...") to automatically
    use their primary image (plus any additional product images) as references
    for consistent generation.

    Returns:
        Formatted markdown list of products, or error message if no brand is active.

    Example output:
        Products for brand 'coffee-co':

        - **Night Cream** (`night-cream`), 5 attributes
          A luxurious night cream for deep hydration...
        - **Day Serum** (`day-serum`), 3 attributes
          Lightweight serum for daytime protection...
    """
    return _impl_list_products()


@function_tool
def list_projects() -> str:
    """List all projects/campaigns for the active brand.

    Returns a formatted list of projects with their names, slugs, status,
    and asset counts. Active projects are marked with a star.

    When a project is active, generated images are automatically tagged with
    that project's slug for organization and filtering.

    Returns:
        Formatted markdown list of projects, or error message if no brand is active.

    Example output:
        Projects for brand 'coffee-co':

        - **Christmas Campaign** (`christmas-campaign`) [active], 12 assets ★ ACTIVE
        - **Summer Sale** (`summer-sale`) [archived], 8 assets
    """
    return _impl_list_projects()


@function_tool
def get_product_detail(product_slug: str) -> str:
    """Get detailed information about a specific product.

    Use this when you need more information than what's provided by list_products,
    such as full descriptions, all attributes, or complete image lists.

    Args:
        product_slug: The product's slug identifier (e.g., "night-cream").

    Returns:
        Formatted markdown with:
        - Product name and slug
        - Full description
        - All attributes (key, category, value)
        - All images with primary marker
        - Creation and update timestamps

        Or error message if product not found.
    """
    return _impl_get_product_detail(product_slug)


@function_tool
def get_project_detail(project_slug: str) -> str:
    """Get detailed information about a specific project/campaign.

    Use this when you need the project's instructions or want to see
    what assets have been generated for it.

    Args:
        project_slug: The project's slug identifier (e.g., "christmas-campaign").

    Returns:
        Formatted markdown with:
        - Project name, slug, and status (with active marker if applicable)
        - Full instructions markdown
        - List of generated assets (first 10)
        - Creation and update timestamps

        Or error message if project not found.
    """
    return _impl_get_project_detail(project_slug)


@function_tool
def update_memory(
    key: str,
    value: str,
    display_message: str,
) -> str:
    """Record a user preference or learning for future reference.

    Use this when the user expresses a preference, gives feedback,
    or makes a decision that should be remembered for future interactions.

    Examples:
    - User says "I prefer minimalist designs" → remember style preference
    - User says "Don't use red" → remember color restriction
    - User picks a direction → remember that preference

    Args:
        key: Short identifier (e.g., "style_preference", "color_avoid")
        value: The actual preference/learning to store
        display_message: User-friendly confirmation (e.g., "Noted: You prefer minimalist designs")

    Returns:
        Confirmation of memory update.
    """
    global _pending_memory_update
    import json
    from datetime import datetime

    brand_slug = get_active_brand()
    if not brand_slug:
        return "No active brand - cannot save memory"

    memory_path = get_brand_dir(brand_slug) / "memory.json"
    memory = {}
    if memory_path.exists():
        try:
            memory = json.loads(memory_path.read_text())
        except json.JSONDecodeError:
            memory = {}

    memory[key] = {
        "value": value,
        "updated_at": datetime.utcnow().isoformat(),
    }

    write_atomically(memory_path,json.dumps(memory, indent=2))
    _pending_memory_update = {"message": display_message}

    return f"Memory updated: {key}"


@function_tool
def create_product(
    name: str,
    description: str = "",
    attributes: list[AttributeInput] | None = None,
) -> str:
    """Create a new product for the active brand.

    Use this to add products to the brand's product catalog. Products can have
    images added separately using add_product_image().

    Args:
        name: Product name (e.g., "Night Cream", "Summer Collection T-Shirt").
            A URL-safe slug will be generated from this name.
        description: Optional product description. Keep it concise but informative.
        attributes: Optional list of product attributes. Each attribute has:
            - key: Attribute name (e.g., "dimensions", "material", "weight")
            - value: Attribute value (e.g., "50ml", "organic cotton", "200g")
            - category: Optional category (default: "general"). Common categories:
              "measurements", "texture", "use_case", "ingredients"
            Attributes are appended to the description in an "Attributes" block for manual editing.

    Returns:
        Success message with product name and slug, or error message.

    Example:
        create_product(
            name="Restorative Night Cream",
            description="A luxurious cream for overnight skin rejuvenation",
            attributes=[
                {"key": "size", "value": "50ml", "category": "measurements"},
                {"key": "texture", "value": "rich, creamy", "category": "texture"},
                {"key": "key_ingredients", "value": "retinol, hyaluronic acid"},
            ]
        )
        # Returns: "Created product **Restorative Night Cream** (`restorative-night-cream`)."
    """
    return _impl_create_product(name, description, attributes)


@function_tool
def add_product_image(
    product_slug: str,
    image_path: str,
    set_as_primary: bool = False,
    allow_non_reference: bool = False,
) -> str:
    """Add an image to a product from the uploads folder.

    Use this after a user uploads an image (which goes to uploads/) to associate
    it with a product. The image will be copied to the product's images folder.

    Args:
        product_slug: The product's slug identifier (e.g., "night-cream").
            Use list_products() to see available products.
        image_path: Path to the image within the brand directory.
            MUST be within the uploads/ folder (e.g., "uploads/product-photo.png").
            Use list_files("uploads") to see available uploaded images.
        set_as_primary: If True, set this image as the product's primary image.
            The primary image is used first for generate_image(product_slug=...),
            with additional product images included as supplemental references.
        allow_non_reference: If True, allow adding images that were classified as screenshots,
            documents, or otherwise not suitable as product reference images. Prefer leaving this
            False so product images remain clean reference photos.

    Returns:
        Success message with the added filename, or error message.

    Example:
        # After user uploads an image, add it to a product:
        add_product_image(
            product_slug="night-cream",
            image_path="uploads/cream-photo.jpg",
            set_as_primary=True
        )
        # Returns: "Added image `cream-photo.jpg` to product **Night Cream**
        #          and set as primary image."
    """
    return _impl_add_product_image(product_slug, image_path, set_as_primary, allow_non_reference)


@function_tool
def update_product(
    product_slug: str,
    name: str | None = None,
    description: str | None = None,
    attributes: list[AttributeInput] | None = None,
    replace_attributes: bool = False,
) -> str:
    """Update an existing product's details. Attributes merge by default.

    Use this to modify product information without creating a new product.
    Attributes are merged by (category, key) case-insensitively by default.
    To replace all attributes, set replace_attributes=True.

    Args:
        product_slug: The product's slug identifier (e.g., "night-cream").
            Use list_products() to see available products.
        name: Optional new product name.
        description: Optional new product description.
        attributes: Optional list of product attributes to merge or replace.
            Each attribute has:
            - key: Attribute name (e.g., "dimensions", "material")
            - value: Attribute value (e.g., "50ml", "organic cotton")
            - category: Optional category (default: "general")
        replace_attributes: If True, replace all existing attributes with the provided list.
            If False (default), merge existing attributes by (category, key).
            Resulting attributes are appended to the description in an "Attributes" block.

    Returns:
        Success message with the updated product name and slug, or error message.

    Example:
        # Merge attributes (default behavior)
        update_product(
            product_slug="night-cream",
            description="A richer formula for overnight rejuvenation",
            attributes=[
                {"key": "texture", "value": "ultra-creamy", "category": "texture"},
                {"key": "new_feature", "value": "vitamin C", "category": "ingredients"},
            ]
        )

        # Replace all attributes
        update_product(
            product_slug="night-cream",
            replace_attributes=True,
            attributes=[
                {"key": "size", "value": "30ml"},
                {"key": "skin_type", "value": "dry"},
            ]
        )
    """
    return _impl_update_product(product_slug, name, description, attributes, replace_attributes)


@function_tool
def delete_product(
    product_slug: str,
    confirm: bool = False,
) -> str:
    """Delete a product and all its files. Requires confirm=True.

    Use this to remove products from the brand's catalog. This operation is
    destructive and cannot be undone. Requires explicit confirmation.

    Args:
        product_slug: The product's slug identifier (e.g., "night-cream").
            Use list_products() to see available products.
        confirm: Must be True to actually delete the product. If False,
            returns a warning message with product name and image count.

    Returns:
        Success message or error/warning.

    Example:
        # First call to see what will be deleted
        delete_product(product_slug="old-product")
        # Returns: "This will permanently delete **Old Product** and all 3 images.
        #          To confirm, call `delete_product(product_slug, confirm=True)`."

        # Second call to confirm deletion
        delete_product(product_slug="old-product", confirm=True)
        # Returns: "Deleted product **Old Product** (`old-product`)."
    """
    return _impl_delete_product(product_slug, confirm)


@function_tool
def set_product_primary_image(
    product_slug: str,
    image_path: str,
) -> str:
    """Set the primary image for a product.

    Use this to designate which image should be used first for
    generate_image(product_slug=...). Additional product images are included
    as supplemental references. The primary image is also displayed
    prominently in the product catalog.

    Args:
        product_slug: The product's slug identifier (e.g., "night-cream").
            Use list_products() to see available products.
        image_path: Path to the image within the product's images list.
            Use get_product_detail(product_slug) to see available images.

    Returns:
        Success message or error message.

    Example:
        # First see what images are available
        get_product_detail(product_slug="night-cream")
        # Shows: images: ["images/main.png", "images/alt.png"]

        # Then set the primary image
        set_product_primary_image(
            product_slug="night-cream",
            image_path="images/main.png"
        )
        # Returns: "Set `images/main.png` as primary image for product **Night Cream** "
        #          (`night-cream`)."
    """
    return _impl_set_product_primary_image(product_slug, image_path)


# =============================================================================
# Brand Memory Tools (migrated from brands.tools)
# =============================================================================


def _impl_fetch_brand_detail(
    detail_type: Literal[
        "visual_identity",
        "voice_guidelines",
        "audience_profile",
        "positioning",
        "full_identity",
    ],
) -> str:
    """Implementation of fetch_brand_detail."""
    from sip_videogen.brands.memory import get_brand_detail
    slug = get_active_brand()
    if not slug:
        return "Error: No brand context set. Cannot fetch brand details."
    logger.info("Agent fetching brand detail: %s for %s", detail_type, slug)
    return get_brand_detail(slug, detail_type)


def _impl_browse_brand_assets(category: str | None = None) -> str:
    """Implementation of browse_brand_assets."""
    import json

    from sip_videogen.brands.memory import list_brand_assets
    slug = get_active_brand()
    if not slug:
        return "Error: No brand context set. Cannot browse assets."
    logger.info("Agent browsing brand assets: category=%s for %s", category, slug)
    assets = list_brand_assets(slug, category)
    if not assets:
        return f"No assets found{' in category ' + category if category else ''}."
    return json.dumps(assets, indent=2)


@function_tool
def fetch_brand_detail(
    detail_type: Literal[
        "visual_identity",
        "voice_guidelines",
        "audience_profile",
        "positioning",
        "full_identity",
    ],
) -> str:
    """Fetch detailed brand information.
    Use this tool to get comprehensive information about a specific aspect
    of the brand before making creative decisions.
    Args:
        detail_type: The type of detail to fetch:
            - "visual_identity": Colors, typography, imagery guidelines
            - "voice_guidelines": Tone, messaging, copy examples
            - "audience_profile": Target audience demographics and psychographics
            - "positioning": Market position and competitive differentiation
            - "full_identity": Complete brand identity (use sparingly)
    Returns:
        JSON string containing the requested brand details.
    """
    return _impl_fetch_brand_detail(detail_type)


@function_tool
def browse_brand_assets(category: str | None = None) -> str:
    """Browse existing brand assets.
    Use this tool to see what assets have already been generated for the brand.
    This helps maintain consistency and avoid recreating existing work.
    Args:
        category: Optional category filter. One of:
            - "logo": Brand logos
            - "packaging": Product packaging images
            - "lifestyle": Lifestyle/in-use photography
            - "mascot": Brand mascot images
            - "marketing": Marketing materials
            - None: Return all assets
    Returns:
        JSON string listing available assets with paths and metadata.
    """
    return _impl_browse_brand_assets(category)


@function_tool
def get_recent_generated_images(limit: int = 5) -> str:
    """Get the most recently generated images, sorted by newest first.

    Use this tool when you need to find a concept image you just generated,
    especially when following up on a user's request to generate a video
    from a previously created concept image.

    Args:
        limit: Maximum number of images to return. Defaults to 5.

    Returns:
        JSON array of recent images with path, filename, and modified time.
        Paths can be passed directly to generate_video_clip as concept_image_path.
    """
    return _impl_get_recent_generated_images(limit)


def _impl_get_recent_generated_images(limit: int = 5) -> str:
    """Implementation of get_recent_generated_images."""
    import os
    slug = get_active_brand()
    if not slug:
        return "Error: No brand context set."
    brand_dir = get_brand_dir(slug)
    gen_dir = brand_dir / "assets" / "generated"
    if not gen_dir.exists():
        return "[]"
    #Get all image files with modification time
    images = []
    for fp in gen_dir.glob("*"):
        if fp.is_file() and fp.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            mtime = fp.stat().st_mtime
            images.append({"path": str(fp), "filename": fp.name, "modified": mtime})
    #Sort by modification time (newest first) and limit
    images.sort(key=lambda x: x["modified"], reverse=True)
    result = images[:limit]
    #Format modified time for readability
    from datetime import datetime
    for img in result:
        img["modified"] = datetime.fromtimestamp(img["modified"]).isoformat()
    return json.dumps(result, indent=2)


# =============================================================================
# URL Content Fetching (FireCrawl)
# =============================================================================
from time import time as _time
import os as _os
#URL content cache (10 min TTL)
_url_cache:dict[str,tuple[str,float]]={}
_CACHE_TTL=600
def _impl_fetch_url_content(url:str)->str:
    """Fetch URL content as LLM-friendly markdown with caching."""
    logger.info(f"fetch_url_content called with url={url}")
    #Check cache
    if url in _url_cache:
        content,ts=_url_cache[url]
        if _time()-ts<_CACHE_TTL:
            logger.info("Returning cached content")
            return content
    try:
        from firecrawl import Firecrawl
    except ImportError:
        logger.error("firecrawl-py not installed")
        return "Error: firecrawl-py not installed. Run: pip install firecrawl-py"
    #Get API key directly from environment (settings may be cached)
    api_key=_os.environ.get("FIRECRAWL_API_KEY","")
    logger.info(f"FIRECRAWL_API_KEY from env: {'set ('+api_key[:8]+'...)' if api_key else 'NOT SET'}")
    if not api_key:
        return "Error: FireCrawl API key not configured. Please add your key in Brand Studio Settings (gear icon in sidebar)."
    try:
        logger.info("Calling FireCrawl API...")
        fc=Firecrawl(api_key=api_key)
        r=fc.scrape(url=url,formats=['markdown'],only_main_content=True)
        #FireCrawl returns a Document object (Pydantic model), not a dict
        md=getattr(r,'markdown','')or''
        meta=getattr(r,'metadata',None)
        title=meta.get('title','')if isinstance(meta,dict)else getattr(meta,'title','')if meta else''
        if md:
            content=f"# {title}\n\n{md}" if title else md
            _url_cache[url]=(content,_time())
            logger.info(f"Successfully fetched {len(content)} chars from {url}")
            return content
        logger.warning(f"No markdown content returned for {url}")
        return f"Error: No content returned from URL"
    except Exception as e:
        logger.error(f"Exception in fetch_url_content: {e}")
        return f"Error fetching URL: {e}"

@function_tool
def fetch_url_content(url:str)->str:
    """Fetch content from a URL and return as markdown.
    Use when user shares a URL and wants you to read or analyze its content.
    The content is automatically converted to clean markdown suitable for analysis.
    Args:
        url: The full URL to fetch (must include https://)
    Returns:
        Clean markdown content from the webpage, or error message if fetch fails.
    """
    return _impl_fetch_url_content(url)


# =============================================================================
# Template Management Tools
# =============================================================================
import asyncio
import json
from datetime import datetime as _dt

def _impl_list_templates()->str:
    """List all templates for active brand."""
    logger.info("list_templates called")
    slug=get_active_brand()
    if not slug:return "Error: No brand context set."
    templates=storage_list_templates(slug)
    if not templates:return "No templates found for this brand."
    lines=["**Templates:**"]
    for t in templates:
        img_count=1 if t.primary_image else 0
        lines.append(f"- **{t.name}** (`{t.slug}`) - {img_count} image(s)")
    return "\n".join(lines)

def _impl_get_template_detail(template_slug:str)->str:
    """Get detailed template info including analysis."""
    logger.info(f"get_template_detail called with template_slug={template_slug}")
    slug=get_active_brand()
    if not slug:return "Error: No brand context set."
    t=load_template(slug,template_slug)
    if not t:return f"Error: Template '{template_slug}' not found."
    lines=[f"# {t.name}",f"**Slug:** `{t.slug}`",f"**Description:** {t.description or '(none)'}",
           f"**Default Strict:** {t.default_strict}",f"**Images:** {len(t.images)}"]
    if t.primary_image:lines.append(f"**Primary Image:** {t.primary_image}")
    if t.analysis:
        lines.append("\n## Analysis")
        if hasattr(t.analysis,'copywriting'):
            lines.append("**V2 Semantic Analysis Available**")
            if t.analysis.copywriting:
                cw=t.analysis.copywriting
                if cw.headline:lines.append(f"- Headline: \"{cw.headline}\"")
                if cw.cta:lines.append(f"- CTA: \"{cw.cta}\"")
        else:lines.append("**V1 Geometry Analysis Available**")
    return "\n".join(lines)

async def _generate_template_name(image_path:Path)->str:
    """Generate descriptive template name from image using Gemini."""
    try:
        from google import genai
        from google.genai import types
        settings=get_settings()
        client=genai.Client(api_key=settings.gemini_api_key)
        img_bytes=image_path.read_bytes()
        prompt="Analyze this design template image and suggest a short descriptive name (2-4 words) that captures its layout style. Examples: 'Hero Centered Product', 'Split Two-Column', 'Minimalist Product Card'. Reply with ONLY the name, nothing else."
        resp=client.models.generate_content(model="gemini-2.0-flash",contents=[types.Part.from_bytes(data=img_bytes,mime_type="image/png"),prompt])
        name=resp.text.strip().strip('"').strip("'")
        return name if name else "New Template"
    except Exception as e:
        logger.warning(f"Failed to generate template name: {e}")
        return "New Template"

async def _impl_create_template_async(name:str,description:str="",image_path:str|None=None,default_strict:bool=True)->str:
    """Create a new template."""
    logger.info(f"create_template called with name={name}")
    slug=get_active_brand()
    if not slug:return "Error: No brand context set."
    #Generate slug from name
    template_slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
    if not template_slug:return "Error: Invalid template name."
    #Check if exists
    existing=load_template_summary(slug,template_slug)
    if existing:return f"Error: Template '{template_slug}' already exists."
    #Create template
    now=_dt.utcnow()
    template=TemplateFull(slug=template_slug,name=name,description=description,images=[],primary_image="",default_strict=default_strict,analysis=None,created_at=now,updated_at=now)
    try:storage_create_template(slug,template)
    except Exception as e:return f"Error creating template: {e}"
    #Add image if provided
    if image_path:
        result=await _impl_add_template_image_async(template_slug,image_path,reanalyze=True)
        if result.startswith("Error"):return f"Created template but failed to add image: {result}"
    return f"Created template **{name}** (`{template_slug}`)."

async def _impl_create_templates_from_images_async(image_paths:list[str],default_strict:bool=True)->str:
    """Create one template per image with auto-generated names."""
    logger.info(f"create_templates_from_images called with {len(image_paths)} images")
    slug=get_active_brand()
    if not slug:return "Error: No brand context set."
    brand_dir=get_brand_dir(slug)
    created=[]
    errors=[]
    for img_path in image_paths:
        #Validate path
        if not img_path.startswith("uploads/"):
            errors.append(f"{img_path}: must be in uploads/ folder")
            continue
        full_path=brand_dir/img_path
        if not full_path.exists():
            errors.append(f"{img_path}: file not found")
            continue
        #Generate name from image
        name=await _generate_template_name(full_path)
        #Make slug unique
        base_slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")or"template"
        template_slug=base_slug
        counter=1
        while load_template_summary(slug,template_slug):
            template_slug=f"{base_slug}-{counter}"
            counter+=1
        #Create template
        now=_dt.utcnow()
        template=TemplateFull(slug=template_slug,name=name,description="",images=[],primary_image="",default_strict=default_strict,analysis=None,created_at=now,updated_at=now)
        try:
            storage_create_template(slug,template)
            #Add image and analyze
            img_bytes=full_path.read_bytes()
            storage_add_template_image(slug,template_slug,full_path.name,img_bytes)
            #Reload and analyze
            t=load_template(slug,template_slug)
            if t and t.images:
                img_full=brand_dir/t.images[0]
                analysis=await analyze_template_v2([img_full])
                if analysis:
                    t.analysis=analysis
                    t.updated_at=_dt.utcnow()
                    storage_save_template(slug,t)
            created.append(f"**{name}** (`{template_slug}`)")
        except Exception as e:
            errors.append(f"{img_path}: {e}")
    result_lines=[]
    if created:result_lines.append(f"Created {len(created)} template(s):\n"+"\n".join(f"- {c}" for c in created))
    if errors:result_lines.append(f"\nErrors:\n"+"\n".join(f"- {e}" for e in errors))
    return "\n".join(result_lines)if result_lines else "No templates created."


def _impl_update_template(template_slug:str,name:str|None=None,description:str|None=None,default_strict:bool|None=None)->str:
    """Update template metadata."""
    logger.info(f"update_template called with template_slug={template_slug}")
    slug=get_active_brand()
    if not slug:return "Error: No brand context set."
    t=load_template(slug,template_slug)
    if not t:return f"Error: Template '{template_slug}' not found."
    if name is not None:t.name=name
    if description is not None:t.description=description
    if default_strict is not None:t.default_strict=default_strict
    t.updated_at=_dt.utcnow()
    try:storage_save_template(slug,t)
    except Exception as e:return f"Error updating template: {e}"
    return f"Updated template **{t.name}** (`{template_slug}`)."

async def _impl_add_template_image_async(template_slug:str,image_path:str,reanalyze:bool=True)->str:
    """Add image to template from uploads folder."""
    logger.info(f"add_template_image called with template_slug={template_slug}, image_path={image_path}")
    slug=get_active_brand()
    if not slug:return "Error: No brand context set."
    t=load_template(slug,template_slug)
    if not t:return f"Error: Template '{template_slug}' not found."
    #Validate path
    if not image_path.startswith("uploads/"):return "Error: image_path must be within uploads/ folder."
    brand_dir=get_brand_dir(slug)
    full_path=brand_dir/image_path
    if not full_path.exists():return f"Error: File not found: {image_path}"
    #Add image
    try:
        img_bytes=full_path.read_bytes()
        storage_add_template_image(slug,template_slug,full_path.name,img_bytes)
    except Exception as e:return f"Error adding image: {e}"
    #Reanalyze if requested
    if reanalyze:
        result=await _impl_reanalyze_template_async(template_slug)
        if result.startswith("Error"):return f"Added image but reanalysis failed: {result}"
    return f"Added image `{full_path.name}` to template **{t.name}**."

async def _impl_reanalyze_template_async(template_slug:str)->str:
    """Re-run V2 analysis on template images."""
    logger.info(f"reanalyze_template called with template_slug={template_slug}")
    slug=get_active_brand()
    if not slug:return "Error: No brand context set."
    t=load_template(slug,template_slug)
    if not t:return f"Error: Template '{template_slug}' not found."
    if not t.images:return f"Error: Template has no images to analyze."
    brand_dir=get_brand_dir(slug)
    img_paths=[brand_dir/img for img in t.images[:2]]
    try:
        analysis=await analyze_template_v2(img_paths)
        if not analysis:return "Error: Analysis failed - no result returned."
        t.analysis=analysis
        t.updated_at=_dt.utcnow()
        storage_save_template(slug,t)
        return f"Re-analyzed template **{t.name}** with V2 semantic analysis."
    except Exception as e:return f"Error during analysis: {e}"

def _impl_delete_template(template_slug:str,confirm:bool=False)->str:
    """Delete template. Requires confirm=True."""
    logger.info(f"delete_template called with template_slug={template_slug}, confirm={confirm}")
    slug=get_active_brand()
    if not slug:return "Error: No brand context set."
    t=load_template(slug,template_slug)
    if not t:return f"Error: Template '{template_slug}' not found."
    if not confirm:
        return f"This will permanently delete **{t.name}** and {len(t.images)} image(s). To confirm, call `delete_template(template_slug, confirm=True)`."
    try:
        storage_delete_template(slug,template_slug)
        return f"Deleted template **{t.name}** (`{template_slug}`)."
    except Exception as e:return f"Error deleting template: {e}"

#Wrapped template tools
@function_tool
def list_templates()->str:
    """List all templates for the active brand.
    Returns:
        Formatted list of templates with name, slug, and image count.
    """
    return _impl_list_templates()

@function_tool
def get_template_detail(template_slug:str)->str:
    """Get detailed template information including analysis.
    Args:
        template_slug: The template's slug identifier. Use list_templates() to see available templates.
    Returns:
        Template details including name, description, images, and analysis summary.
    """
    return _impl_get_template_detail(template_slug)

@function_tool
async def create_template(name:str,description:str="",image_path:str|None=None,default_strict:bool=True)->str:
    """Create a new template for reusable layouts.
    Args:
        name: Template name (e.g., "Hero Centered Product", "Split Banner").
        description: Optional template description.
        image_path: Optional path to image within uploads/ folder.
        default_strict: Default strict mode for this template (default True).
    Returns:
        Success message with template slug, or error message.
    """
    return await _impl_create_template_async(name,description,image_path,default_strict)

@function_tool
async def create_templates_from_images(image_paths:list[str],default_strict:bool=True)->str:
    """Create one template per image with auto-generated names.
    Use this when user drops multiple images and wants a template for each.
    The template name is auto-generated by analyzing each image's layout.
    Args:
        image_paths: List of paths within uploads/ folder. Each creates a separate template.
        default_strict: Default strict mode for created templates (default True).
    Returns:
        Summary of created templates and any errors.
    Example:
        create_templates_from_images(["uploads/banner1.png", "uploads/card.png"])
    """
    return await _impl_create_templates_from_images_async(image_paths,default_strict)

@function_tool
def update_template(template_slug:str,name:str|None=None,description:str|None=None,default_strict:bool|None=None)->str:
    """Update template metadata.
    Args:
        template_slug: The template's slug identifier.
        name: Optional new name.
        description: Optional new description.
        default_strict: Optional new default strict mode.
    Returns:
        Success message or error.
    """
    return _impl_update_template(template_slug,name,description,default_strict)

@function_tool
async def add_template_image(template_slug:str,image_path:str,reanalyze:bool=True)->str:
    """Add an image to a template from uploads folder.
    Args:
        template_slug: The template's slug identifier.
        image_path: Path within uploads/ folder (e.g., "uploads/design.png").
        reanalyze: Re-run V2 analysis after adding image (default True).
    Returns:
        Success message or error.
    """
    return await _impl_add_template_image_async(template_slug,image_path,reanalyze)

@function_tool
async def reanalyze_template(template_slug:str)->str:
    """Re-run V2 Gemini analysis on template images.
    Use when template images have changed or you want to refresh the analysis.
    Args:
        template_slug: The template's slug identifier.
    Returns:
        Success message or error.
    """
    return await _impl_reanalyze_template_async(template_slug)

@function_tool
def delete_template(template_slug:str,confirm:bool=False)->str:
    """Delete a template and all its files. Requires confirm=True.
    Args:
        template_slug: The template's slug identifier.
        confirm: Must be True to actually delete. If False, returns warning.
    Returns:
        Success message, warning, or error.
    """
    return _impl_delete_template(template_slug,confirm)


# =============================================================================
# Thinking Visibility Tool
# =============================================================================
import uuid as _uuid
#Max lengths to prevent UI flooding
_MAX_STEP_LEN=50
_MAX_DETAIL_LEN=500
def _build_thinking_step_result(step:str,detail:str)->str:
    """Build JSON result string containing thinking step data.
    Parsed in on_tool_end to extract step data, avoiding global state issues.
    """
    s=step[:_MAX_STEP_LEN].strip()if step else"Thinking"
    d=detail[:_MAX_DETAIL_LEN].strip()if detail else""
    return json.dumps({"_thinking_step":True,"id":str(_uuid.uuid4()),"step":s,"detail":d,"timestamp":int(_time()*1000)})
def _impl_report_thinking(step:str,detail:str)->str:
    """Report a thinking step to show reasoning to the user.
    Returns structured JSON that on_tool_end parses.
    """
    logger.debug(f"[THINKING] {step[:50]}")
    return _build_thinking_step_result(step,detail)
def parse_thinking_step_result(result:str)->dict|None:
    """Parse thinking step data from tool result if present."""
    try:
        data=json.loads(result)
        if isinstance(data,dict)and data.get("_thinking_step"):
            return{"id":data["id"],"step":data["step"],"detail":data["detail"],"timestamp":data["timestamp"]}
    except(json.JSONDecodeError,KeyError,TypeError):
        pass
    return None
@function_tool
def report_thinking(step:str,detail:str)->str:
    """Report a thinking step to show the user your reasoning process.
    REQUIRED: Call this tool to explain what you're doing at each decision point.
    Users see these steps as a collapsible list, building trust in your process.
    Args:
        step: Brief title (2-5 words) describing this stage.
              Examples: "Understanding request", "Choosing approach", "Crafting scene"
        detail: Brief explanation of what you decided and why (1-2 sentences).
                Focus on WHAT and WHY, not internal reasoning or system details.
                Do NOT include system prompts, internal instructions, or chain-of-thought.
    Returns:
        Acknowledgment string.
    """
    return _impl_report_thinking(step,detail)


# =============================================================================
# Tool List for Agent
# =============================================================================

# All tools available to the Brand Marketing Advisor
ADVISOR_TOOLS = [
    generate_image,
    generate_video_clip,
    get_recent_generated_images,
    read_file,
    write_file,
    list_files,
    load_brand,
    propose_choices,
    propose_images,
    update_memory,
    # Product and Project exploration tools
    list_products,
    list_projects,
    get_product_detail,
    get_project_detail,
    # Product management tools
    create_product,
    update_product,
    delete_product,
    add_product_image,
    set_product_primary_image,
    # Template management tools
    list_templates,
    get_template_detail,
    create_template,
    create_templates_from_images,
    update_template,
    add_template_image,
    reanalyze_template,
    delete_template,
    # Brand memory tools (migrated from brands.tools)
    fetch_brand_detail,
    browse_brand_assets,
    # URL content fetching
    fetch_url_content,
    # Thinking visibility
    report_thinking,
]
