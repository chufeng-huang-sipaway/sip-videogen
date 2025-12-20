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

from pathlib import Path
from typing import Literal

from agents import function_tool

from sip_videogen.brands.storage import (
    get_active_brand,
    get_active_project,
    get_brand_dir,
    get_brands_dir,
    load_product,
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
from sip_videogen.config.logging import get_logger
from sip_videogen.config.settings import get_settings

logger = get_logger(__name__)


# =============================================================================
# Image Generation Metadata
# =============================================================================

from dataclasses import asdict, dataclass, field


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
        contents_lines = ['[', f'    """{prompt_escaped}""",']
        img_idx = 1
        for product_name, paths in grouped_reference_images:
            img_count = len(paths)
            plural = "s" if img_count > 1 else ""
            # Add the label that's sent to Gemini
            label = f"[Reference images for {product_name} ({img_count} image{plural}):]"
            contents_lines.append(f'    "{label}",')
            # Add all images for this product
            for ref_path in paths:
                ref_comment = f'  # Loaded from: {ref_path}'
                contents_lines.append(
                    f'    PILImage.open(io.BytesIO(reference_image_bytes_{img_idx})),'
                    f'{ref_comment}'
                )
                img_idx += 1
        contents_lines.append(']')
        contents_repr = "\n".join(contents_lines)
    elif reference_images:
        # Legacy flat list (for single product or backward compatibility)
        reference_images = [path for path in reference_images if path]
        contents_lines = ['[', f'    """{prompt_escaped}""",']
        for idx, ref_path in enumerate(reference_images, start=1):
            ref_comment = f'  # Loaded from: {ref_path}'
            contents_lines.append(
                f'    PILImage.open(io.BytesIO(reference_image_bytes_{idx})),{ref_comment}'
            )
        contents_lines.append(']')
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


def store_image_metadata(path: str, metadata: ImageGenerationMetadata) -> None:
    """Store metadata for a generated image."""
    _image_metadata[path] = asdict(metadata)


def get_image_metadata(path: str) -> dict | None:
    """Get and remove metadata for a generated image."""
    return _image_metadata.pop(path, None)


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
# Interaction + Memory State (captured via hooks)
# =============================================================================

# Stored between tool calls and cleared when hooks read them
_pending_interaction: dict | None = None
_pending_memory_update: dict | None = None


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
    validate_identity: bool = False,
    max_retries: int = 3,
) -> str:
    """Implementation of generate_image tool with optional reference-based generation.

    Args:
        prompt: Text description for image generation.
        aspect_ratio: Image aspect ratio.
        filename: Optional output filename (without extension).
        reference_image: Optional path to reference image within brand directory.
        product_slug: Optional product slug - auto-loads product's primary image as reference.
        product_slugs: Optional list of product slugs for multi-product generation.
            When provided with 2+ products, uses multi-product validation.
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

    # Handle multi-product generation with validation
    if product_slugs and len(product_slugs) >= 2:
        if not brand_slug:
            return "Error: No active brand - cannot load products"

        # Load ALL reference images per product (no per-product limit)
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

            # Get ALL images for this product (primary first, then additional)
            product_images: list[str] = []
            if product.primary_image:
                product_images.append(product.primary_image)

            # Add all additional images
            if product.images:
                for img in product.images:
                    if img != product.primary_image:
                        product_images.append(img)

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
                        return (
                            f"Error: Reference image not found for product '{slug}': "
                            f"{img_path}"
                        )
                    else:
                        logger.warning(f"Additional image not found, skipping: {img_path}")
                        continue

                try:
                    ref_bytes = ref_path.read_bytes()
                    current_product_images.append(ref_bytes)  # Add to this product's bytes
                    current_product_paths.append(img_path)  # Add to this product's paths
                    generation_image_paths.append(img_path)
                    role = "primary" if img_path == product.primary_image else "additional"
                    used_for = "generation+validation" if role == "primary" else "generation"
                    reference_images_detail.append({
                        "path": img_path,
                        "product_slug": slug,
                        "role": role,
                        "used_for": used_for,
                    })
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
                        logger.warning(f"Failed to read additional image: {e}")
                        continue

            # Add ONE entry per product to validation refs (primary only)
            if primary_bytes:
                product_references.append((product.name, primary_bytes))

            # Add grouped images for this product (for Gemini generation with labels)
            if current_product_images:
                grouped_generation_images.append((product.name, current_product_images))
                grouped_reference_image_paths.append((product.name, current_product_paths))

            if images_loaded > 1:
                logger.info(
                    f"Loaded {images_loaded} reference images for '{product.name}' (multi-angle)"
                )

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

        # Use multi-product validation
        from sip_videogen.advisor.validation import generate_with_multi_validation

        total_gen_images = sum(len(imgs) for _, imgs in grouped_generation_images)
        logger.info(
            f"Generating multi-product image with {len(product_references)} products, "
            f"{total_gen_images} total reference images (max {max_retries} retries)..."
        )

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

    # Auto-load product's primary image as reference if product_slug provided (single product)
    generation_prompt = prompt  # Will be modified if specs injection is enabled
    if product_slug and not reference_image:
        if not brand_slug:
            return "Error: No active brand - cannot load product"
        product = load_product(brand_slug, product_slug)
        if product is None:
            return f"Error: Product not found: {product_slug}"
        if product.primary_image:
            # primary_image is brand-relative (e.g., "products/night-cream/images/main.png")
            # Pass directly - _resolve_brand_path will handle it
            reference_image = product.primary_image
            # Enable identity validation for product consistency
            validate_identity = True
            logger.info(
                f"Using product '{product_slug}' primary image as reference: {reference_image}"
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
        else:
            logger.warning(f"Product '{product_slug}' has no primary image")

    # Resolve and load reference image if provided
    reference_image_bytes: bytes | None = None
    if reference_image:
        reference_path = _resolve_brand_path(reference_image)
        if reference_path is None:
            return f"Error: No active brand or invalid path: {reference_image}"
        if not reference_path.exists():
            return f"Error: Reference image not found: {reference_image}"
        try:
            reference_image_bytes = reference_path.read_bytes()
            logger.info(
                f"Loaded reference image: {reference_image} ({len(reference_image_bytes)} bytes)"
            )
        except Exception as e:
            return f"Error reading reference image: {e}"

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

            reference_images = [reference_image] if reference_image else []
            reference_images_detail = []
            if reference_image:
                role = "primary" if product_slug else "reference"
                used_for = "generation+validation" if validate_identity else "generation"
                reference_images_detail.append({
                    "path": reference_image,
                    "product_slug": product_slug,
                    "role": role,
                    "used_for": used_for,
                })

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
        if reference_image_bytes:
            # Include reference image in contents
            ref_pil = PILImage.open(io.BytesIO(reference_image_bytes))
            contents = [generation_prompt, ref_pil]  # Phase 1: Use specs-injected prompt
            logger.info(f"Generating image with reference: {generation_prompt[:100]}...")
        else:
            contents = generation_prompt
            logger.info(f"Generating image: {generation_prompt[:100]}...")

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
                reference_images = [reference_image] if reference_image else []
                reference_images_detail = []
                if reference_image:
                    role = "primary" if product_slug else "reference"
                    reference_images_detail.append({
                        "path": reference_image,
                        "product_slug": product_slug,
                        "role": role,
                        "used_for": "generation",
                    })

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
                attempts = [{
                    "attempt_number": 1,
                    "prompt": generation_prompt,
                    "validation_passed": None,
                    "api_call_code": final_api_call,
                    "request_payload": final_request_payload,
                }]
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
        # Create parent directories
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        resolved.write_text(content, encoding="utf-8")

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
        return f"No products found for brand '{brand_slug}'. Use the bridge to create products."

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

    lines = [f"# Product: {product.name}"]
    lines.append(f"*Slug: `{product.slug}`*\n")

    # Description
    if product.description:
        lines.append("## Description")
        lines.append(product.description)
        lines.append("")

    # Attributes
    if product.attributes:
        lines.append("## Attributes")
        for attr in product.attributes:
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
            automatically loads the product's primary image as reference and enables
            identity validation. Use this when generating images featuring a specific
            product - the product's actual appearance will be preserved.
        product_slugs: Optional list of product slugs for MULTI-PRODUCT images.
            Use this when the user wants to generate an image featuring 2-3 products.
            Each product's primary image will be used as reference, and multi-product
            validation ensures EVERY product appears accurately. The prompt should
            describe each product with specific details (materials, colors, etc.).
            Example: product_slugs=["night-cream", "day-serum", "toner"]
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
        validate_identity,
        max_retries,
    )


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
    use their primary image as a reference for consistent generation.

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

    memory_path.write_text(json.dumps(memory, indent=2))
    _pending_memory_update = {"message": display_message}

    return f"Memory updated: {key}"


# =============================================================================
# Tool List for Agent
# =============================================================================

# All tools available to the Brand Marketing Advisor
ADVISOR_TOOLS = [
    generate_image,
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
]
