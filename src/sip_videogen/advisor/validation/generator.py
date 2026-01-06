"""Generation with validation - retry loops for reference-validated image generation."""

from __future__ import annotations

import hashlib
import io
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sip_videogen.advisor.tools import emit_tool_thinking
from sip_videogen.config.logging import get_logger
from sip_videogen.config.settings import get_settings

from .metrics import (
    GenerationMetrics,
    ProductMetric,
    _cleanup_attempt_files,
    _generate_request_id,
    _write_metrics,
)
from .models import (
    MultiValidationAttempt,
    MultiValidationGenerationResult,
    ValidationAttempt,
    ValidationGenerationResult,
    _validation_model_dump,
)
from .prompts import _improve_multi_product_prompt, _improve_prompt_for_identity
from .validator import validate_multi_product_identity, validate_reference_identity

if TYPE_CHECKING:
    from google.genai import Client
logger = get_logger(__name__)


async def generate_with_validation(
    client: "Client",
    prompt: str,
    reference_image_bytes: bytes,
    output_dir: Path,
    filename: str,
    aspect_ratio: str = "1:1",
    max_retries: int = 3,
    reference_images_bytes: list[bytes] | None = None,
) -> ValidationGenerationResult | str:
    """Generate image with reference and validate for identity preservation.
    This function implements a retry loop that:
    1. Generates an image using the reference
    2. Validates it against the reference using GPT-4o vision
    3. If validation fails, improves the prompt and retries
    4. Returns the best attempt if all retries are exhausted
    Args:
            client: Gemini API client.
            prompt: Generation prompt.
            reference_image_bytes: Primary reference image bytes (used for validation).
            reference_images_bytes: Optional list of reference image bytes to guide
                    generation (primary first). When omitted, uses the primary only.
            output_dir: Directory to save output.
            filename: Base filename (without extension).
            aspect_ratio: Image aspect ratio.
            max_retries: Maximum validation attempts.
    Returns:
            ValidationGenerationResult with path and attempt details, or an error string.
    """
    from google.genai import types
    from PIL import Image as PILImage

    attempts: list[ValidationAttempt] = []
    attempts_meta: list[dict] = []
    best: ValidationAttempt | None = None
    cp = prompt
    for an in range(max_retries):
        anum = an + 1
        logger.info(f"Reference generation attempt {anum}/{max_retries}")
        try:
            # Build contents with reference image(s)
            ibl = reference_images_bytes or [reference_image_bytes]
            if reference_image_bytes not in ibl:
                ibl = [reference_image_bytes, *ibl]
            rpils = [PILImage.open(io.BytesIO(ib)) for ib in ibl]
            contents = [cp, *rpils]
            # Emit baby steps to show sophisticated prompt engineering
            emit_tool_thinking(
                "I'm crafting the perfect prompt...",
                "Adding your brand's visual identity",
                expertise="Image Generation",
            )
            emit_tool_thinking(
                "I'm generating your image now...",
                "This might take a moment",
                expertise="Image Generation",
            )
            # Generate image
            resp = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size="4K"),
                ),
            )
            # Extract and save generated image
            afn = f"{filename}_attempt{anum}.png"
            ap = output_dir / afn
            gb: bytes | None = None
            for part in resp.parts or []:
                if part.inline_data:
                    img = part.as_image()
                    if img:
                        img.save(str(ap))
                    # Read bytes back for validation
                    gb = ap.read_bytes()
                    break
            if not gb:
                logger.warning(f"No image generated on attempt {anum}")
                attempts_meta.append(
                    {
                        "attempt_number": anum,
                        "prompt": cp,
                        "image_path": str(ap),
                        "error": "No image generated in response",
                    }
                )
                continue
            # Validate against reference
            logger.info(f"Validating attempt {anum} against reference...")
            val = await validate_reference_identity(
                reference_image_bytes=reference_image_bytes,
                generated_image_bytes=gb,
                original_prompt=cp,
            )
            att = ValidationAttempt(
                attempt_number=anum,
                prompt_used=cp,
                image_path=str(ap),
                similarity_score=val.similarity_score,
                is_identical=val.is_identical,
                improvement_suggestions=val.improvement_suggestions,
            )
            attempts.append(att)
            # Track best attempt by similarity score
            if best is None or att.similarity_score > best.similarity_score:
                best = att
            # Log proportion status
            ps = "OK" if val.proportions_match else "FAIL"
            if val.proportions_notes:
                logger.info(f"  Proportions [{ps}]: {val.proportions_notes}")
            # Phase 3: Check both identity AND proportions
            st = get_settings()
            vp = val.is_identical and (val.proportions_match or not st.sip_proportion_validation)
            attempts_meta.append(
                {
                    "attempt_number": anum,
                    "prompt": cp,
                    "image_path": str(ap),
                    "validation": _validation_model_dump(val),
                    "validation_passed": vp,
                }
            )
            if vp:
                # Success - rename to final filename
                fp = output_dir / f"{filename}.png"
                ap.rename(fp)
                logger.info(
                    f"Validation passed on attempt {anum} (score: {val.similarity_score:.2f}, proportions: {ps})"
                )
                return ValidationGenerationResult(
                    path=str(fp),
                    attempts=attempts_meta,
                    final_prompt=cp,
                    final_attempt_number=anum,
                    validation_passed=True,
                )
            # Improve prompt for next attempt
            # Get proportion notes for prompt improvement if proportions failed
            pn = ""
            if not val.proportions_match:
                pn = val.proportions_notes
            cp = _improve_prompt_for_identity(
                original_prompt=prompt,
                suggestions=val.improvement_suggestions,
                attempt_number=anum,
                proportions_notes=pn,
            )
            logger.info(
                f"Validation failed (score: {val.similarity_score:.2f}, proportions: {ps}), improving prompt for retry"
            )
        except Exception as e:
            logger.warning(f"Generation attempt {anum} failed: {e}")
            attempts_meta.append({"attempt_number": anum, "prompt": cp, "error": str(e)})
            continue
    # All attempts exhausted - use best attempt as fallback
    if best:
        bp = Path(best.image_path)
        fp = output_dir / f"{filename}.png"
        if bp.exists():
            bp.rename(fp)
        # Clean up other attempt files
        for att in attempts:
            atp = Path(att.image_path)
            if atp.exists() and atp != fp:
                try:
                    atp.unlink()
                except Exception:
                    pass
        logger.warning(
            f"Validation loop exhausted after {max_retries} attempts. Using best attempt (score: {best.similarity_score:.2f}). Note: Generated image may not be identical to reference."
        )
        warn = f"[Warning: Object identity validation did not pass after {max_retries} attempts. Best similarity score: {best.similarity_score:.2f}. The generated image may differ from the reference.]"
        return ValidationGenerationResult(
            path=str(fp),
            attempts=attempts_meta,
            final_prompt=best.prompt_used,
            final_attempt_number=best.attempt_number,
            validation_passed=False,
            warning=warn,
        )
    return "Error: All generation attempts failed."


async def generate_with_multi_validation(
    client: "Client",
    prompt: str,
    product_references: list[tuple[str, bytes]],
    output_dir: Path,
    filename: str,
    aspect_ratio: str = "1:1",
    max_retries: int = 3,
    product_slugs: list[str] | None = None,
    grouped_generation_images: list[tuple[str, list[bytes]]] | None = None,
) -> MultiValidationGenerationResult | str:
    """Generate image with multiple products and validate each one.
    This function implements a retry loop that:
    1. Generates an image using all reference images with explicit product labels
    2. Validates each product individually using GPT-4o vision (primary refs only)
    3. If any product fails validation, improves the prompt and retries
    4. Returns the best attempt if all retries are exhausted
    Args:
            client: Gemini API client.
            prompt: Generation prompt (should mention all products).
            product_references: List of (product_name, image_bytes) tuples for VALIDATION.
                    Should contain exactly one entry per product (primary image).
            output_dir: Directory to save output.
            filename: Base filename (without extension).
            aspect_ratio: Image aspect ratio.
            max_retries: Maximum validation attempts.
            product_slugs: Optional list of product slugs for metrics.
            grouped_generation_images: Optional list of (product_name, [image_bytes, ...]) tuples
                    for GENERATION. Groups images by product so we can add explicit labels in the
                    API call. If None, uses product_references (one image per product).
    Returns:
            MultiValidationGenerationResult with path and attempt details, or an error string.
    """
    from google.genai import types
    from PIL import Image as PILImage

    st = get_settings()
    # If grouped_generation_images not provided, extract from product_references
    if grouped_generation_images is None:
        grouped_generation_images = [(n, [ib]) for n, ib in product_references]
    # Count total images for logging
    ti = sum(len(imgs) for _, imgs in grouped_generation_images)
    attempts: list[MultiValidationAttempt] = []
    attempts_meta: list[dict] = []
    best: MultiValidationAttempt | None = None
    cp = prompt
    # Phase 0: Initialize metrics
    met = GenerationMetrics(
        request_id=_generate_request_id(),
        timestamp=datetime.utcnow().isoformat(),
        prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:12],
        original_prompt=prompt[:500],
        aspect_ratio=aspect_ratio,
        product_slugs=product_slugs or [],
        product_names=[n for n, _ in product_references],
        total_attempts=0,
        successful_attempt=None,
    )
    for an in range(max_retries):
        anum = an + 1
        met.total_attempts = anum
        logger.info(
            f"Multi-product generation attempt {anum}/{max_retries} ({len(product_references)} products, {ti} reference images)"
        )
        try:
            # Build contents with interleaved text labels and images
            # This helps Gemini understand which images belong to which product
            contents: list = [cp]
            for pn, pimgs in grouped_generation_images:
                ic = len(pimgs)
                # Add explicit label before this product's images
                pl = "s" if ic > 1 else ""
                lbl = f"[Reference images for {pn} ({ic} image{pl}):]"
                contents.append(lbl)
                # Add all images for this product
                for rb in pimgs:
                    rp = PILImage.open(io.BytesIO(rb))
                    contents.append(rp)
            # Emit baby steps to show sophisticated prompt engineering
            emit_tool_thinking(
                "I'm crafting the perfect prompt...",
                "Balancing all your products in the scene",
                expertise="Image Generation",
            )
            emit_tool_thinking(
                "I'm generating your image now...",
                "This might take a moment",
                expertise="Image Generation",
            )
            # Generate image
            resp = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size="4K"),
                ),
            )
            # Extract and save generated image
            afn = f"{filename}_attempt{anum}.png"
            ap = output_dir / afn
            gb: bytes | None = None
            for part in resp.parts:
                if part.inline_data:
                    img = part.as_image()
                    img.save(str(ap))
                    gb = ap.read_bytes()
                    break
            if not gb:
                logger.warning(f"No image generated on attempt {anum}")
                attempts_meta.append(
                    {
                        "attempt_number": anum,
                        "prompt": cp,
                        "image_path": str(ap),
                        "error": "No image generated in response",
                    }
                )
                continue
            # Validate all products
            logger.info(f"Validating attempt {anum} against {len(product_references)} products...")
            val = await validate_multi_product_identity(
                product_references=product_references, generated_image_bytes=gb, original_prompt=cp
            )
            # Build product scores dict
            psc = {pr.product_name: pr.similarity_score for pr in val.product_results}
            att = MultiValidationAttempt(
                attempt_number=anum,
                prompt_used=cp,
                image_path=str(ap),
                overall_score=val.overall_score,
                all_accurate=val.all_products_accurate,
                product_scores=psc,
                suggestions=val.suggestions,
            )
            attempts.append(att)
            # Phase 0: Record attempt metrics
            pmets = [
                ProductMetric(
                    product_name=pr.product_name,
                    similarity_score=pr.similarity_score,
                    is_present=pr.is_present,
                    is_accurate=pr.is_accurate,
                    proportions_match=pr.proportions_match,
                    issues=pr.issues,
                    failure_reason="missing"
                    if not pr.is_present
                    else "proportion"
                    if not pr.proportions_match
                    else "identity"
                    if not pr.is_accurate
                    else "",
                )
                for pr in val.product_results
            ]
            # Determine if attempt passed (respecting proportion validation setting)
            apassed = val.all_products_accurate and (
                val.all_proportions_match or not st.sip_proportion_validation
            )
            attempts_meta.append(
                {
                    "attempt_number": anum,
                    "prompt": cp,
                    "image_path": str(ap),
                    "validation": _validation_model_dump(val),
                    "validation_passed": apassed,
                }
            )
            met.add_attempt(
                attempt_number=anum,
                prompt_used=cp,
                overall_score=val.overall_score,
                passed=apassed,
                product_metrics=pmets,
                improvement_suggestions=val.suggestions,
            )
            # Track best attempt by overall score
            if best is None or att.overall_score > best.overall_score:
                best = att
            # Log per-product results
            for pr in val.product_results:
                # Status respects proportion validation setting
                pok = pr.proportions_match or not st.sip_proportion_validation
                status = "PASS" if pr.is_accurate and pok else "FAIL"
                pn = ""
                if st.sip_proportion_validation:
                    pn = f" [PROPORTIONS: {'OK' if pr.proportions_match else 'FAIL'}]"
                logger.info(
                    f"  {pr.product_name}: {pr.similarity_score:.2f} [{status}]{pn} {'- ' + pr.issues if pr.issues else ''}"
                )
            # Phase 3: Check both accuracy AND proportions
            vp = val.all_products_accurate and (
                val.all_proportions_match or not st.sip_proportion_validation
            )
            if vp:
                # Success - all products validated
                fp = output_dir / f"{filename}.png"
                ap.rename(fp)
                logger.info(
                    f"Multi-product validation passed on attempt {anum} (overall score: {val.overall_score:.2f})"
                )
                # Phase 0: Record success metrics
                met.successful_attempt = anum
                met.final_score = val.overall_score
                met.passed = True
                _write_metrics(met, output_dir)
                # Clean up attempt files
                _cleanup_attempt_files(attempts, None, fp, output_dir)
                return MultiValidationGenerationResult(
                    path=str(fp),
                    attempts=attempts_meta,
                    final_prompt=cp,
                    final_attempt_number=anum,
                    validation_passed=True,
                )
            # Improve prompt for next attempt
            cp = _improve_multi_product_prompt(
                original_prompt=prompt, validation_result=val, attempt_number=anum
            )
            logger.info(
                f"Multi-product validation failed (score: {val.overall_score:.2f}), improving prompt for retry"
            )
        except Exception as e:
            logger.warning(f"Multi-product generation attempt {anum} failed: {e}")
            attempts_meta.append({"attempt_number": anum, "prompt": cp, "error": str(e)})
            continue
    # All attempts exhausted - use best attempt as fallback
    if best:
        bp = Path(best.image_path)
        fp = output_dir / f"{filename}.png"
        if bp.exists():
            bp.rename(fp)
        # Phase 0: Clean up attempt files (respects debug mode)
        _cleanup_attempt_files(attempts, bp, fp, output_dir)
        # Build per-product score summary
        ss = ", ".join(f"{n}: {s:.2f}" for n, s in best.product_scores.items())
        # Phase 0: Determine failure category and record metrics
        fc = "identity"  # Default
        if met.attempts:
            la = met.attempts[-1]
            for pm in la.get("product_metrics", []):
                if not pm.get("is_present", True):
                    fc = "missing"
                    break
                if not pm.get("proportions_match", True):
                    fc = "proportion"
                    break
        met.final_score = best.overall_score
        met.passed = False
        met.failure_category = fc
        met.best_attempt_reason = f"Highest overall score: {best.overall_score:.2f}"
        _write_metrics(met, output_dir)
        logger.warning(
            f"Multi-product validation loop exhausted after {max_retries} attempts. Using best attempt (overall: {best.overall_score:.2f}). Per-product scores: {ss}"
        )
        warn = f"[Warning: Multi-product validation did not pass after {max_retries} attempts. Overall score: {best.overall_score:.2f}. Per-product scores: {ss}. Some products may not match their reference images exactly.]"
        return MultiValidationGenerationResult(
            path=str(fp),
            attempts=attempts_meta,
            final_prompt=best.prompt_used,
            final_attempt_number=best.attempt_number,
            validation_passed=False,
            warning=warn,
        )
    # Phase 0: Record failure metrics
    met.passed = False
    met.failure_category = "error"
    _write_metrics(met, output_dir)
    return "Error: All multi-product generation attempts failed."
