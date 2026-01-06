"""Image generation tools."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from agents import function_tool

from sip_videogen.config.logging import get_logger

from . import _common
from .memory_tools import emit_tool_thinking
from .metadata import (
    ImageGenerationMetadata,
    _build_api_call_code,
    _build_attempts_metadata,
    _build_request_payload,
    store_image_metadata,
)
from .session import get_active_aspect_ratio

logger = get_logger(__name__)


def _generate_output_filename(project_slug: str | None = None) -> str:
    """Generate a filename with optional project prefix."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hash_suffix = uuid.uuid4().hex[:8]
    if project_slug:
        return f"{project_slug}__{timestamp}_{hash_suffix}"
    else:
        return f"{timestamp}_{hash_suffix}"


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
    """Implementation of generate_image tool with optional reference-based generation."""
    import io
    import time

    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    logger.info(
        "[generate_image] PARAMS: slug=%s, slugs=%s, ref_img=%s, template_slug=%s, strict=%s, validate=%s",
        product_slug,
        product_slugs,
        reference_image,
        template_slug,
        strict,
        validate_identity,
    )
    settings = _common.get_settings()
    brand_slug = _common.get_active_brand()
    model = "gemini-3-pro-image-preview"
    image_size = "4K"
    if brand_slug:
        output_dir = _common.get_brand_dir(brand_slug) / "assets" / "generated"
    else:
        output_dir = _common.get_brands_dir() / "_temp"
    output_dir.mkdir(parents=True, exist_ok=True)
    active_project = _common.get_active_project(brand_slug) if brand_slug else None
    if active_project:
        generated_filename = _generate_output_filename(active_project)
        if filename:
            logger.debug(
                f"Overriding filename '{filename}' with '{generated_filename}' for project"
            )
        filename = generated_filename
        logger.info(f"Tagging generated image with project: {active_project}")
    elif not filename:
        filename = _generate_output_filename(None)
    output_path = output_dir / f"{filename}.png"
    template_constraints = ""
    if template_slug:
        if not brand_slug:
            return "Error: No active brand - cannot load style reference"
        style_ref = _common.load_style_reference(brand_slug, template_slug)
        if style_ref is None:
            return f"Error: Style reference not found: {template_slug}"
        if style_ref.analysis is None:
            return f"Error: Style reference '{template_slug}' has no analysis"
        is_v2 = getattr(style_ref.analysis, "version", "1.0") == "2.0"
        if is_v2:
            from sip_videogen.advisor.style_reference_prompt import (
                build_style_reference_constraints_v2,
            )

            template_constraints = build_style_reference_constraints_v2(
                style_ref.analysis, strict=strict, include_usage=False
            )
        else:
            from sip_videogen.advisor.style_reference_prompt import (
                build_style_reference_constraints,
            )

            template_constraints = build_style_reference_constraints(
                style_ref.analysis, strict=strict, include_usage=False
            )
        template_aspect_ratio = style_ref.analysis.canvas.aspect_ratio
        allowed_aspects = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"}
        if template_aspect_ratio and template_aspect_ratio in allowed_aspects:
            if template_aspect_ratio != aspect_ratio:
                logger.info(
                    "Template aspect ratio override: %s -> %s", aspect_ratio, template_aspect_ratio
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
        max_total_images = 16
        product_references: list[tuple[str, bytes]] = []
        grouped_generation_images: list[tuple[str, list[bytes]]] = []
        grouped_reference_image_paths: list[tuple[str, list[str]]] = []
        generation_image_paths: list[str] = []
        reference_images_detail: list[dict] = []
        total_images_loaded = 0
        for slug in product_slugs:
            product = _common.load_product(brand_slug, slug)
            if product is None:
                return f"Error: Product not found: {slug}"
            if not product.primary_image:
                return f"Error: Product '{slug}' has no primary image for reference"
            product_images: list[str] = []
            if product.primary_image:
                product_images.append(product.primary_image)
            if product.images:
                for img in product.images:
                    if img != product.primary_image:
                        product_images.append(img)
            max_refs = min(settings.sip_product_ref_images_per_product, len(product_images))
            if max_refs < len(product_images):
                n = len(product_images)
                logger.info(f"Limiting '{product.name}' refs to {max_refs} of {n} available")
                product_images = product_images[:max_refs]
            images_loaded = 0
            primary_bytes: bytes | None = None
            current_product_images: list[bytes] = []
            current_product_paths: list[str] = []
            for img_path in product_images:
                if total_images_loaded >= max_total_images and images_loaded > 0:
                    pn = product.name
                    logger.warning(f"Image cap ({max_total_images}) reached, skip rest for '{pn}'")
                    break
                ref_path = _resolve_brand_path(img_path)
                if ref_path is None or not ref_path.exists():
                    if images_loaded == 0:
                        return f"Error: Reference image not found for product '{slug}': {img_path}"
                    else:
                        logger.warning(f"Image not found for '{product.name}': {img_path}")
                        continue
                try:
                    ref_bytes = ref_path.read_bytes()
                    current_product_images.append(ref_bytes)
                    current_product_paths.append(img_path)
                    generation_image_paths.append(img_path)
                    role = "primary" if img_path == product.primary_image else "additional"
                    used_for = "generation+validation" if role == "primary" else "generation"
                    reference_images_detail.append(
                        {"path": img_path, "product_slug": slug, "role": role, "used_for": used_for}
                    )
                    if images_loaded == 0:
                        primary_bytes = ref_bytes
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
                        logger.warning(f"Failed to read image for '{product.name}': {e}")
                        continue
            if primary_bytes:
                product_references.append((product.name, primary_bytes))
            if current_product_images:
                grouped_generation_images.append((product.name, current_product_images))
                grouped_reference_image_paths.append((product.name, current_product_paths))
            logger.info(f"Loaded {images_loaded}/{len(product_images)} images for '{product.name}'")
            if images_loaded != len(product_images):
                exp, got = len(product_images), images_loaded
                logger.warning(f"Load partial for '{product.name}': {got}/{exp}")
        generation_prompt = prompt
        if settings.sip_product_specs_injection:
            from sip_videogen.advisor.product_specs import inject_specs_into_prompt

            generation_prompt = inject_specs_into_prompt(
                prompt=prompt, brand_slug=brand_slug, product_slugs=product_slugs
            )
            logger.info(f"Injected product specs for {len(product_slugs)} products")
        generation_prompt = _apply_template_constraints(generation_prompt)
        from sip_videogen.advisor.validation import generate_with_multi_validation

        total_gen_images = sum(len(imgs) for _, imgs in grouped_generation_images)
        expected_images = 0
        for slug in product_slugs:
            product = _common.load_product(brand_slug, slug)
            if not product:
                continue
            expected_images += min(len(product.images), settings.sip_product_ref_images_per_product)
        if total_gen_images < expected_images:
            logger.warning(
                f"Reference image mismatch: expected {expected_images} total images, but only loaded {total_gen_images}. Some images may have failed to load."
            )
        logger.info(
            f"Generating multi-product image with {len(product_references)} products, {total_gen_images} total reference images (max {max_retries} retries)..."
        )
        start_time = time.time()
        mp_step_id = emit_tool_thinking(
            "I'm gathering your product images...",
            f"Preparing {len(product_references)} products for the shot",
            expertise="Image Generation",
            status="pending",
        )
        try:
            client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)
            result = await generate_with_multi_validation(
                client=client,
                prompt=generation_prompt,
                product_references=product_references,
                grouped_generation_images=grouped_generation_images,
                output_dir=output_dir,
                filename=filename,
                aspect_ratio=aspect_ratio,
                max_retries=max_retries,
                product_slugs=product_slugs,
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
            # Mark setup complete and emit new completion step
            emit_tool_thinking(
                "I'm gathering your product images...",
                "All set!",
                expertise="Image Generation",
                status="complete",
                step_id=mp_step_id,
            )
            emit_tool_thinking(
                "Your image is ready!",
                "Take a look at what I created",
                expertise="Image Generation",
                status="complete",
            )
            return return_value
        except Exception as e:
            logger.error(f"Multi-product image generation failed: {e}")
            emit_tool_thinking(
                "I ran into an issue...",
                str(e)[:100],
                expertise="Image Generation",
                status="failed",
                step_id=mp_step_id,
            )
            return f"Error generating multi-product image: {str(e)}"
    # Single-product reference handling
    generation_prompt = prompt
    reference_candidates: list[dict] = []
    reference_images: list[str] = []
    reference_images_detail: list[dict] = []
    reference_images_bytes: list[bytes] = []
    reference_image_bytes: bytes | None = None
    original_reference_image = reference_image
    if product_slug:
        if not brand_slug:
            return "Error: No active brand - cannot load product"
        product = _common.load_product(brand_slug, product_slug)
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
                    f"Limiting '{product_slug}' reference images to {max_refs} of {len(product_images)} available"
                )
            if original_reference_image:
                reference_candidates.append(
                    {
                        "path": original_reference_image,
                        "product_slug": product_slug,
                        "role": "edit-source",
                        "used_for": "generation+validation",
                        "is_primary": True,
                    }
                )
                for img_path in selected_images:
                    if img_path != original_reference_image:
                        reference_candidates.append(
                            {
                                "path": img_path,
                                "product_slug": product_slug,
                                "role": "product-reference",
                                "used_for": "generation",
                                "is_primary": False,
                            }
                        )
                validate_identity = True
                logger.info(
                    f"Quick Edit mode: edit-source={original_reference_image}, product refs={selected_images}"
                )
            else:
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
            if settings.sip_product_specs_injection:
                from sip_videogen.advisor.product_specs import inject_specs_into_prompt

                generation_prompt = inject_specs_into_prompt(
                    prompt=prompt, brand_slug=brand_slug, product_slugs=[product_slug]
                )
                logger.info(
                    f"[generate_image] SPECS INJECTED for '{product_slug}', prompt_len={len(generation_prompt)}"
                )
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
            logger.warning(f"Failed to read reference image {img_path}: {type(e).__name__}: {e}")
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
    start_time = time.time()
    step_id = emit_tool_thinking(
        "I'm preparing your references...",
        "Loading your brand assets",
        expertise="Image Generation",
        status="pending",
    )
    try:
        client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)
        if validate_identity and reference_image_bytes:
            from sip_videogen.advisor.validation import generate_with_validation

            logger.info(f"Generating with validation (max {max_retries} retries)...")
            result = await generate_with_validation(
                client=client,
                prompt=generation_prompt,
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
            # Mark setup complete and emit new completion step
            emit_tool_thinking(
                "I'm preparing your references...",
                "All set!",
                expertise="Image Generation",
                status="complete",
                step_id=step_id,
            )
            emit_tool_thinking(
                "Your image is ready!",
                "Take a look at what I created",
                expertise="Image Generation",
                status="complete",
            )
            return return_value
        # Standard generation
        if reference_images_bytes:
            ref_pils = [
                PILImage.open(io.BytesIO(ref_bytes)) for ref_bytes in reference_images_bytes
            ]
            contents = [generation_prompt, *ref_pils]
            logger.info(
                f"Generating image with {len(reference_images_bytes)} reference image(s): {generation_prompt[:100]}..."
            )
        else:
            contents = generation_prompt
            logger.info(f"Generating image: {generation_prompt[:100]}...")
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size=image_size),
            ),
        )
        for part in response.parts:
            if part.inline_data:
                image = part.as_image()
                image.save(str(output_path))
                logger.info(f"Saved image to: {output_path}")
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
                # Mark setup complete and emit new completion step
                emit_tool_thinking(
                    "I'm preparing your references...",
                    "All set!",
                    expertise="Image Generation",
                    status="complete",
                    step_id=step_id,
                )
                emit_tool_thinking(
                    "Your image is ready!",
                    "Take a look at what I created",
                    expertise="Image Generation",
                    status="complete",
                )
                return str(output_path)
        emit_tool_thinking(
            "Something went wrong",
            "Couldn't generate the image",
            expertise="Image Generation",
            status="failed",
            step_id=step_id,
        )
        return "Error: No image generated in response"
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        emit_tool_thinking(
            "I ran into an issue...",
            str(e)[:100],
            expertise="Image Generation",
            status="failed",
            step_id=step_id,
        )
        return f"Error generating image: {str(e)}"


@function_tool
async def generate_image(
    prompt: str,
    aspect_ratio: Literal["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9"]
    | None = None,
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
    Creates a high-quality image from a text prompt. Use for brand assets like logos, mascots, lifestyle photos, and marketing materials.
    Args:
        prompt: Detailed description of the image to generate.
        aspect_ratio: Image aspect ratio. Uses session context if not specified.
        filename: Optional filename to save as (without extension).
        reference_image: Optional path to a reference image within the brand directory.
        product_slug: Optional product slug. Automatically loads product's images and enables identity validation.
        product_slugs: Optional list of product slugs for MULTI-PRODUCT images.
        template_slug: Optional template slug. When provided, applies template layout constraints.
        strict: When True with template_slug, enforces exact layout reproduction.
        validate_identity: When True AND reference_image is provided, enables validation loop.
        max_retries: Maximum attempts for validation loop (default 3).
    Returns:
        Path to the saved image file, or error message.
    """
    effective_ratio = aspect_ratio or get_active_aspect_ratio()
    return await _impl_generate_image(
        prompt,
        effective_ratio,
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
def propose_images(question: str, image_paths: list[str], labels: list[str] | None = None) -> str:
    """Present images for the user to select from.
    Args:
        question: The question (e.g., "Which logo do you prefer?")
        image_paths: List of image file paths.
        labels: Optional short labels for each image.
    Returns:
        Confirmation that image selection is being presented.
    """
    import sip_videogen.advisor.tools.memory_tools as mem

    if len(image_paths) < 2:
        return "Error: Please provide at least 2 images to choose from"
    brand_slug = _common.get_active_brand()
    if brand_slug:
        assets_dir = (_common.get_brand_dir(brand_slug) / "assets").resolve()
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
                continue
        image_paths = normalized
        if len(image_paths) < 2:
            return "Error: Please provide at least 2 images within the brand assets folder"
    mem._pending_interaction = {
        "type": "image_select",
        "question": question,
        "image_paths": image_paths,
        "labels": labels or [f"Option {i + 1}" for i in range(len(image_paths))],
    }
    return f"[Presenting {len(image_paths)} images for user to select]"


def _impl_get_recent_generated_images(limit: int = 5) -> str:
    """Implementation of get_recent_generated_images."""
    import json

    slug = _common.get_active_brand()
    if not slug:
        return "Error: No brand context set."
    brand_dir = _common.get_brand_dir(slug)
    gen_dir = brand_dir / "assets" / "generated"
    if not gen_dir.exists():
        return "[]"
    images = []
    for fp in gen_dir.glob("*"):
        if fp.is_file() and fp.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            mtime = fp.stat().st_mtime
            images.append({"path": str(fp), "filename": fp.name, "modified": mtime})
    images.sort(key=lambda x: x["modified"], reverse=True)
    result = images[:limit]
    for img in result:
        img["modified"] = datetime.fromtimestamp(img["modified"]).isoformat()
    return json.dumps(result, indent=2)


@function_tool
def get_recent_generated_images(limit: int = 5) -> str:
    """Get the most recently generated images, sorted by newest first.
    Args:
        limit: Maximum number of images to return. Defaults to 5.
    Returns:
        JSON array of recent images with path, filename, and modified time.
    """
    return _impl_get_recent_generated_images(limit)
