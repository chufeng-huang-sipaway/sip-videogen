"""Reference image validation for Brand Advisor image generation.

This module provides validation functionality to ensure generated images
maintain object identity with provided reference images. Uses GPT-4o vision
to compare images and assess whether the same object appears in both.

Phase 0: Includes metrics logging and debug artifact retention.
Phase 3: Includes proportion/measurement validation.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from sip_videogen.advisor.tools import emit_tool_thinking
from sip_videogen.config.logging import get_logger
from sip_videogen.config.settings import get_settings

if TYPE_CHECKING:
    from google.genai import Client

logger = get_logger(__name__)


# =============================================================================
# Phase 0: Generation Metrics
# =============================================================================


@dataclass
class ProductMetric:
    """Metrics for a single product in a generation."""

    product_name: str
    similarity_score: float
    is_present: bool
    is_accurate: bool
    proportions_match: bool = True  # Phase 3
    issues: str = ""
    failure_reason: str = ""  # "identity", "proportion", "missing", or ""


@dataclass
class GenerationMetrics:
    """Comprehensive metrics for a single generation request."""

    # Request metadata
    request_id: str
    timestamp: str
    prompt_hash: str
    original_prompt: str
    aspect_ratio: str

    # Product context
    product_slugs: list[str]
    product_names: list[str]

    # Attempt tracking
    total_attempts: int
    successful_attempt: int | None  # None if all failed

    # Per-attempt details
    attempts: list[dict] = field(default_factory=list)

    # Final outcome
    final_score: float = 0.0
    passed: bool = False
    failure_category: str = ""  # "identity", "proportion", "missing", "error"
    best_attempt_reason: str = ""

    def add_attempt(
        self,
        attempt_number: int,
        prompt_used: str,
        overall_score: float,
        passed: bool,
        product_metrics: list[ProductMetric],
        improvement_suggestions: str = "",
    ) -> None:
        """Record a single attempt's metrics."""
        self.attempts.append(
            {
                "attempt_number": attempt_number,
                "prompt_hash": hashlib.sha256(prompt_used.encode()).hexdigest()[:12],
                "overall_score": overall_score,
                "passed": passed,
                "product_metrics": [asdict(pm) for pm in product_metrics],
                "improvement_suggestions": improvement_suggestions,
            }
        )


def _generate_request_id() -> str:
    """Generate a unique request ID."""
    import uuid

    return f"gen_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _get_metrics_dir(output_dir: Path) -> Path:
    """Get the metrics directory, creating if needed."""
    metrics_dir = output_dir / "_metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    return metrics_dir


def _write_metrics(metrics: GenerationMetrics, output_dir: Path) -> None:
    """Write metrics to JSONL file if enabled."""
    settings = get_settings()
    if not settings.sip_generation_metrics_enabled:
        return

    metrics_dir = _get_metrics_dir(output_dir)
    metrics_file = metrics_dir / f"generation_metrics_{datetime.utcnow().strftime('%Y%m')}.jsonl"

    try:
        with open(metrics_file, "a") as f:
            f.write(json.dumps(asdict(metrics)) + "\n")
        logger.debug(f"Wrote generation metrics to {metrics_file}")
    except Exception as e:
        logger.warning(f"Failed to write metrics: {e}")


def _cleanup_attempt_files(
    attempts: list,
    best_attempt_path: Path | None,
    final_path: Path,
    output_dir: Path,
) -> None:
    """Clean up attempt files based on debug mode setting."""
    settings = get_settings()

    for attempt in attempts:
        attempt_path = Path(attempt.image_path) if hasattr(attempt, "image_path") else None
        if attempt_path is None:
            continue

        if attempt_path.exists() and attempt_path != final_path:
            if settings.sip_generation_debug_mode:
                # In debug mode, keep files but rename to _debug_attempt
                debug_name = attempt_path.stem + "_debug" + attempt_path.suffix
                debug_path = output_dir / debug_name
                try:
                    attempt_path.rename(debug_path)
                    logger.debug(f"Kept debug artifact: {debug_path}")
                except Exception:
                    pass
            else:
                # Normal mode: delete attempt files
                try:
                    attempt_path.unlink()
                except Exception:
                    pass


class ReferenceValidationResult(BaseModel):
    """Result of validating generated image against reference."""

    is_identical: bool = Field(
        description="Whether the object in generated image is identical to reference"
    )
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity score from 0.0 (completely different) to 1.0 (identical)",
    )
    reasoning: str = Field(description="Explanation of the assessment")
    improvement_suggestions: str = Field(
        default="",
        description="If not identical, suggestions to improve the generation prompt",
    )
    # Phase 3: Proportion validation
    proportions_match: bool = Field(
        default=True,
        description="Whether the object proportions match the reference (height:width ratio)",
    )
    proportions_notes: str = Field(
        default="",
        description="Notes about proportion accuracy - squashed, stretched, or correct",
    )


class ProductValidationResult(BaseModel):
    """Result of validating a single product within a multi-product image."""

    product_name: str = Field(description="Name of the product being validated")
    is_present: bool = Field(description="Whether this product is visible in the generated image")
    is_accurate: bool = Field(description="Whether this product's appearance matches the reference")
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity score from 0.0 (completely different) to 1.0 (identical)",
    )
    issues: str = Field(
        default="",
        description="Specific issues found (wrong material, color mismatch, etc.)",
    )
    # Phase 3: Proportion validation
    proportions_match: bool = Field(
        default=True,
        description="Whether this product's proportions match the reference",
    )
    proportions_notes: str = Field(
        default="",
        description="Notes about proportion accuracy for this product",
    )


class MultiProductValidationResult(BaseModel):
    """Result of validating multiple products in a single generated image."""

    product_results: list[ProductValidationResult] = Field(
        description="Validation results for each individual product"
    )
    all_products_present: bool = Field(
        description="Whether ALL products are visible in the generated image"
    )
    all_products_accurate: bool = Field(
        description="Whether ALL products accurately match their references"
    )
    overall_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Average similarity score across all products",
    )
    suggestions: str = Field(
        default="",
        description="Overall improvement suggestions for the generation prompt",
    )
    # Phase 3: Proportion validation
    all_proportions_match: bool = Field(
        default=True,
        description="Whether ALL products have correct proportions",
    )


@dataclass
class ValidationAttempt:
    """Record of a single generation + validation attempt."""

    attempt_number: int
    prompt_used: str
    image_path: str
    similarity_score: float
    is_identical: bool
    improvement_suggestions: str


@dataclass
class ValidationGenerationResult:
    """Result of a reference-validated image generation run."""

    path: str
    attempts: list[dict]
    final_prompt: str
    final_attempt_number: int
    validation_passed: bool
    warning: str | None = None


@dataclass
class MultiValidationGenerationResult:
    """Result of a multi-product validated image generation run."""

    path: str
    attempts: list[dict]
    final_prompt: str
    final_attempt_number: int
    validation_passed: bool
    warning: str | None = None


def _validation_model_dump(model: BaseModel) -> dict:
    """Return a JSON-serializable dict from a pydantic model."""
    return model.model_dump()


_VALIDATOR_PROMPT = """# Reference Image Identity Validator

You are an expert at comparing images to determine if they show the SAME object/product.

## Your Task

Compare a reference image with a generated image and determine if the SAME object appears in both.

## What "Identical Object" Means

IDENTICAL means:
- Same specific product/item (not just same category)
- Same brand, model, design
- Distinctive features preserved (logos, markings, colors, shape)
- Someone would recognize it as THE SAME thing

IDENTICAL does NOT require:
- Same angle or perspective
- Same lighting or shadows
- Same background
- Same artistic style

## Scoring Guide

- 1.0: Perfect - exact same object, all features match
- 0.8-0.9: Very close - same object, minor details differ
- 0.6-0.7: Similar - same type of object, some features match
- 0.4-0.5: Somewhat similar - same category, different specific item
- 0.0-0.3: Different - clearly different object

## When to Mark as Identical (is_identical=True)

Mark as identical if score >= 0.8 AND the core object identity is preserved.

## Proportion Validation (CRITICAL)

Check if the object's proportions are preserved:
- Compare the height:width ratio of the object in both images
- Look for signs of squashing (too short/wide) or stretching (too tall/narrow)
- Set proportions_match=False if the object looks distorted
- Allow ±15% tolerance for perspective differences

Examples of proportion issues:
- "Bottle appears squashed - height:width ratio is ~1:1 but should be ~2:1"
- "Product stretched vertically - appears elongated vs reference"

Set proportions_notes to explain any mismatch.

## Improvement Suggestions

When not identical, provide SPECIFIC suggestions:
- Which features are missing or wrong
- What the prompt should emphasize
- How to better describe the specific object
- If proportions are wrong, specify the correct ratio

Examples:
- "The logo text is different - emphasize 'EXACT logo placement and text'"
- "Color is off - specify 'same shade of blue (#1234AB)'"
- "Shape altered - add 'preserve original proportions exactly'"
- "Object is squashed - add 'maintain 2:1 height-to-width ratio'"
"""


async def validate_reference_identity(
    reference_image_bytes: bytes,
    generated_image_bytes: bytes,
    original_prompt: str,
) -> ReferenceValidationResult:
    """Validate that generated image maintains object identity with reference.

    Uses GPT-4o vision to compare the generated image against the reference
    and assess whether the key object/subject is identical.

    Args:
        reference_image_bytes: Original reference image bytes.
        generated_image_bytes: Generated image bytes to validate.
        original_prompt: The prompt used for generation (for context).

    Returns:
        ReferenceValidationResult with identity assessment.
    """
    from agents import Agent, Runner

    # Create validation agent
    validator_agent = Agent(
        name="Reference Image Validator",
        instructions=_VALIDATOR_PROMPT,
        model="gpt-4o",
        output_type=ReferenceValidationResult,
    )

    # Encode images
    ref_b64 = base64.b64encode(reference_image_bytes).decode("utf-8")
    gen_b64 = base64.b64encode(generated_image_bytes).decode("utf-8")

    # Build validation request
    validation_prompt = f"""Compare these two images:

**Image 1 (Reference)**: The original product/object that should be reproduced.
**Image 2 (Generated)**: An AI-generated image that should contain the SAME object.

**Generation Prompt Used**: {original_prompt}

Your task:
1. Identify the main object/subject in the reference image
2. Check if the SAME object appears in the generated image (not just similar - IDENTICAL)
3. Assess object identity, NOT creative execution (lighting, angle, background can differ)

Focus on:
- Is it the same specific product/item (same brand, model, design)?
- Are distinctive features preserved (logo, shape, color, markings)?
- Would someone recognize it as the exact same object?

Be strict about object identity but flexible about creative presentation.
"""

    # Create input with images for vision model
    input_message = {
        "role": "user",
        "content": [
            {"type": "input_text", "text": validation_prompt},
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{ref_b64}",
                "detail": "high",
            },
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{gen_b64}",
                "detail": "high",
            },
        ],
    }

    result = await Runner.run(validator_agent, [input_message])
    return result.final_output


_MULTI_PRODUCT_VALIDATOR_PROMPT = """# Multi-Product Image Validator

You are an expert at validating generated images containing MULTIPLE products.

## Your Task

Given a generated image and MULTIPLE reference images, determine if EACH product appears correctly.

## Validation Criteria

For EACH product, check:
1. **Is it PRESENT?** - Can you clearly identify this product in the generated image?
2. **Is it ACCURATE?** - Does it match the reference image in:
   - Material (glass, metal, ceramic, plastic, etc.)
   - Color (exact shade and finish - glossy, matte, frosted)
   - Shape and proportions
   - Distinctive features (logos, patterns, textures)
3. **Are PROPORTIONS correct?** - Check height:width ratio matches reference

## Scoring Guide (per product)

- 1.0: Perfect match - identical to reference
- 0.8-0.9: Very close - same product, minor details differ
- 0.6-0.7: Similar - same type but noticeable differences
- 0.4-0.5: Poor - significant material/color changes
- 0.0-0.3: Wrong - clearly different product

## Key Issues to Catch

- Material changed (e.g., glass became plastic)
- Color shifted (e.g., copper became gold)
- Texture lost (e.g., frosted became clear)
- Products merged or confused with each other
- Product missing entirely
- **PROPORTIONS WRONG** (e.g., bottle squashed, jar stretched)

## Proportion Validation (CRITICAL)

For EACH product:
- Compare the height:width ratio against its reference
- Set proportions_match=False if product looks squashed or stretched
- Allow ±15% tolerance for perspective differences
- Set proportions_notes to describe any mismatch

Examples:
- "Bottle appears squashed - height:width is ~1:1 but should be ~2:1"
- "Jar stretched vertically - appears taller than reference"

Set all_proportions_match=False if ANY product has wrong proportions.

## Output

Provide individual scores for EACH product and an overall assessment.
Be STRICT about material, color, AND proportion accuracy - these are critical.
"""


async def validate_multi_product_identity(
    product_references: list[tuple[str, bytes]],
    generated_image_bytes: bytes,
    original_prompt: str,
) -> MultiProductValidationResult:
    """Validate that ALL products appear correctly in a generated image.

    Uses GPT-4o vision to compare the generated image against multiple reference
    images and assess whether each product is present and accurately reproduced.

    Args:
        product_references: List of (product_name, reference_image_bytes) tuples.
        generated_image_bytes: Generated image bytes to validate.
        original_prompt: The prompt used for generation (for context).

    Returns:
        MultiProductValidationResult with per-product assessments.
    """
    from agents import Agent, Runner

    # Create multi-product validation agent
    validator_agent = Agent(
        name="Multi-Product Validator",
        instructions=_MULTI_PRODUCT_VALIDATOR_PROMPT,
        model="gpt-4o",
        output_type=MultiProductValidationResult,
    )

    # Encode generated image
    gen_b64 = base64.b64encode(generated_image_bytes).decode("utf-8")

    # Build product reference descriptions and encode images
    product_descriptions = []
    image_content = []

    for idx, (name, ref_bytes) in enumerate(product_references, 1):
        product_descriptions.append(f"- Product {idx}: {name}")
        ref_b64 = base64.b64encode(ref_bytes).decode("utf-8")
        image_content.append(
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{ref_b64}",
                "detail": "high",
            }
        )

    products_list = "\n".join(product_descriptions)

    # Build validation request
    num_products = len(product_references)
    validation_prompt = f"""Validate this generated image against {num_products} product references.

**Products to find:**
{products_list}

**Generation Prompt Used:** {original_prompt}

**Reference images** (in order): Images 1-{num_products} are the product references.
**Generated image**: Image {num_products + 1} is the AI-generated result.

For EACH product:
1. Find it in the generated image
2. Compare to its reference image
3. Check material, color, shape, and texture accuracy
4. Score it from 0.0 to 1.0

Be STRICT about material and color accuracy.
If a glass bottle became plastic, that's a major issue.
If products are present but with wrong materials/colors,
mark is_accurate=False even if is_present=True.
"""

    # Build input message with all images
    input_content = [{"type": "input_text", "text": validation_prompt}]
    input_content.extend(image_content)  # Reference images
    input_content.append(
        {  # Generated image last
            "type": "input_image",
            "image_url": f"data:image/png;base64,{gen_b64}",
            "detail": "high",
        }
    )

    input_message = {"role": "user", "content": input_content}

    result = await Runner.run(validator_agent, [input_message])
    return result.final_output


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
    attempts_metadata: list[dict] = []
    best_attempt: ValidationAttempt | None = None
    current_prompt = prompt

    for attempt_num in range(max_retries):
        attempt_number = attempt_num + 1
        logger.info(f"Reference generation attempt {attempt_number}/{max_retries}")

        try:
            # Build contents with reference image(s)
            image_bytes_list = reference_images_bytes or [reference_image_bytes]
            if reference_image_bytes not in image_bytes_list:
                image_bytes_list = [reference_image_bytes, *image_bytes_list]

            ref_pils = [PILImage.open(io.BytesIO(img_bytes)) for img_bytes in image_bytes_list]
            contents = [current_prompt, *ref_pils]
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
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=contents,  # type: ignore[arg-type]
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size="4K",
                    ),
                ),
            )

            # Extract and save generated image
            attempt_filename = f"{filename}_attempt{attempt_number}.png"
            attempt_path = output_dir / attempt_filename
            generated_bytes: bytes | None = None

            for part in response.parts or []:
                if part.inline_data:
                    image = part.as_image()
                    if image:
                        # Gemini Image.save() only accepts a file path, not buffer
                        image.save(str(attempt_path))
                    # Read bytes back for validation
                    generated_bytes = attempt_path.read_bytes()
                    break

            if not generated_bytes:
                logger.warning(f"No image generated on attempt {attempt_number}")
                attempts_metadata.append(
                    {
                        "attempt_number": attempt_number,
                        "prompt": current_prompt,
                        "image_path": str(attempt_path),
                        "error": "No image generated in response",
                    }
                )
                continue

            # Validate against reference
            logger.info(f"Validating attempt {attempt_number} against reference...")
            validation = await validate_reference_identity(
                reference_image_bytes=reference_image_bytes,
                generated_image_bytes=generated_bytes,
                original_prompt=current_prompt,
            )

            attempt = ValidationAttempt(
                attempt_number=attempt_number,
                prompt_used=current_prompt,
                image_path=str(attempt_path),
                similarity_score=validation.similarity_score,
                is_identical=validation.is_identical,
                improvement_suggestions=validation.improvement_suggestions,
            )
            attempts.append(attempt)

            # Track best attempt by similarity score
            if best_attempt is None or attempt.similarity_score > best_attempt.similarity_score:
                best_attempt = attempt

            # Log proportion status
            prop_status = "OK" if validation.proportions_match else "FAIL"
            if validation.proportions_notes:
                logger.info(f"  Proportions [{prop_status}]: {validation.proportions_notes}")

            # Phase 3: Check both identity AND proportions
            settings = get_settings()
            validation_passed = validation.is_identical and (
                validation.proportions_match or not settings.sip_proportion_validation
            )

            attempts_metadata.append(
                {
                    "attempt_number": attempt_number,
                    "prompt": current_prompt,
                    "image_path": str(attempt_path),
                    "validation": _validation_model_dump(validation),
                    "validation_passed": validation_passed,
                }
            )

            if validation_passed:
                # Success - rename to final filename
                final_path = output_dir / f"{filename}.png"
                attempt_path.rename(final_path)
                logger.info(
                    f"Validation passed on attempt {attempt_number} "
                    f"(score: {validation.similarity_score:.2f}, proportions: {prop_status})"
                )
                return ValidationGenerationResult(
                    path=str(final_path),
                    attempts=attempts_metadata,
                    final_prompt=current_prompt,
                    final_attempt_number=attempt_number,
                    validation_passed=True,
                )

            # Improve prompt for next attempt
            # Get proportion notes for prompt improvement if proportions failed
            prop_notes = ""
            if not validation.proportions_match:
                prop_notes = validation.proportions_notes
            current_prompt = _improve_prompt_for_identity(
                original_prompt=prompt,
                suggestions=validation.improvement_suggestions,
                attempt_number=attempt_number,
                proportions_notes=prop_notes,
            )
            logger.info(
                f"Validation failed (score: {validation.similarity_score:.2f}, "
                f"proportions: {prop_status}), improving prompt for retry"
            )

        except Exception as e:
            logger.warning(f"Generation attempt {attempt_number} failed: {e}")
            attempts_metadata.append(
                {
                    "attempt_number": attempt_number,
                    "prompt": current_prompt,
                    "error": str(e),
                }
            )
            continue

    # All attempts exhausted - use best attempt as fallback
    if best_attempt:
        # Rename best attempt to final filename
        best_path = Path(best_attempt.image_path)
        final_path = output_dir / f"{filename}.png"
        if best_path.exists():
            best_path.rename(final_path)

        # Clean up other attempt files
        for attempt in attempts:
            attempt_path = Path(attempt.image_path)
            if attempt_path.exists() and attempt_path != final_path:
                try:
                    attempt_path.unlink()
                except Exception:
                    pass

        logger.warning(
            f"Validation loop exhausted after {max_retries} attempts. "
            f"Using best attempt (score: {best_attempt.similarity_score:.2f}). "
            f"Note: Generated image may not be identical to reference."
        )
        warning = (
            f"[Warning: Object identity validation did not pass after {max_retries} attempts. "
            f"Best similarity score: {best_attempt.similarity_score:.2f}. "
            f"The generated image may differ from the reference.]"
        )
        return ValidationGenerationResult(
            path=str(final_path),
            attempts=attempts_metadata,
            final_prompt=best_attempt.prompt_used,
            final_attempt_number=best_attempt.attempt_number,
            validation_passed=False,
            warning=warning,
        )

    return "Error: All generation attempts failed."


def _improve_prompt_for_identity(
    original_prompt: str,
    suggestions: str,
    attempt_number: int,
    proportions_notes: str = "",
) -> str:
    """Improve generation prompt to better preserve object identity.

    Args:
        original_prompt: Original user prompt.
        suggestions: Improvement suggestions from validator.
        attempt_number: Current attempt number.
        proportions_notes: Notes about proportion issues to fix.

    Returns:
        Improved prompt.
    """
    improvements = [
        "CRITICAL: The generated image MUST show the EXACT SAME object from the reference image.",
        "Preserve all distinctive features: brand logos, specific colors, shapes, and markings.",
        "This is NOT about style - it's about showing the SAME physical object.",
        "PRESERVE EXACT PROPORTIONS - do not squash or stretch the object.",
    ]

    if suggestions:
        improvements.append(f"Specific feedback: {suggestions}")

    if proportions_notes:
        improvements.append(f"PROPORTION FIX NEEDED: {proportions_notes}")

    return (
        f"{original_prompt}\n\n"
        f"[IDENTITY REQUIREMENT - Attempt {attempt_number + 1}]\n"
        + "\n".join(f"- {imp}" for imp in improvements)
    )


@dataclass
class MultiValidationAttempt:
    """Record of a single multi-product generation + validation attempt."""

    attempt_number: int
    prompt_used: str
    image_path: str
    overall_score: float
    all_accurate: bool
    product_scores: dict[str, float]  # product_name -> score
    suggestions: str


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

    settings = get_settings()

    # If grouped_generation_images not provided, extract from product_references
    if grouped_generation_images is None:
        grouped_generation_images = [(name, [img_bytes]) for name, img_bytes in product_references]

    # Count total images for logging
    total_images = sum(len(imgs) for _, imgs in grouped_generation_images)

    attempts: list[MultiValidationAttempt] = []
    attempts_metadata: list[dict] = []
    best_attempt: MultiValidationAttempt | None = None
    current_prompt = prompt

    # Phase 0: Initialize metrics
    metrics = GenerationMetrics(
        request_id=_generate_request_id(),
        timestamp=datetime.utcnow().isoformat(),
        prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:12],
        original_prompt=prompt[:500],  # Truncate for storage
        aspect_ratio=aspect_ratio,
        product_slugs=product_slugs or [],
        product_names=[name for name, _ in product_references],
        total_attempts=0,
        successful_attempt=None,
    )

    for attempt_num in range(max_retries):
        attempt_number = attempt_num + 1
        metrics.total_attempts = attempt_number
        logger.info(
            f"Multi-product generation attempt {attempt_number}/{max_retries} "
            f"({len(product_references)} products, {total_images} reference images)"
        )

        try:
            # Build contents with interleaved text labels and images
            # This helps Gemini understand which images belong to which product
            contents: list = [current_prompt]

            for product_name, product_images in grouped_generation_images:
                img_count = len(product_images)
                # Add explicit label before this product's images
                plural = "s" if img_count > 1 else ""
                label = f"[Reference images for {product_name} ({img_count} image{plural}):]"
                contents.append(label)
                # Add all images for this product
                for ref_bytes in product_images:
                    ref_pil = PILImage.open(io.BytesIO(ref_bytes))
                    contents.append(ref_pil)
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
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size="4K",
                    ),
                ),
            )

            # Extract and save generated image
            attempt_filename = f"{filename}_attempt{attempt_number}.png"
            attempt_path = output_dir / attempt_filename
            generated_bytes: bytes | None = None

            for part in response.parts:
                if part.inline_data:
                    image = part.as_image()
                    image.save(str(attempt_path))
                    generated_bytes = attempt_path.read_bytes()
                    break

            if not generated_bytes:
                logger.warning(f"No image generated on attempt {attempt_number}")
                attempts_metadata.append(
                    {
                        "attempt_number": attempt_number,
                        "prompt": current_prompt,
                        "image_path": str(attempt_path),
                        "error": "No image generated in response",
                    }
                )
                continue

            # Validate all products
            logger.info(
                f"Validating attempt {attempt_number} against {len(product_references)} products..."
            )
            validation = await validate_multi_product_identity(
                product_references=product_references,
                generated_image_bytes=generated_bytes,
                original_prompt=current_prompt,
            )

            # Build product scores dict
            product_scores = {
                pr.product_name: pr.similarity_score for pr in validation.product_results
            }

            attempt = MultiValidationAttempt(
                attempt_number=attempt_number,
                prompt_used=current_prompt,
                image_path=str(attempt_path),
                overall_score=validation.overall_score,
                all_accurate=validation.all_products_accurate,
                product_scores=product_scores,
                suggestions=validation.suggestions,
            )
            attempts.append(attempt)

            # Phase 0: Record attempt metrics
            product_metrics = [
                ProductMetric(
                    product_name=pr.product_name,
                    similarity_score=pr.similarity_score,
                    is_present=pr.is_present,
                    is_accurate=pr.is_accurate,
                    proportions_match=pr.proportions_match,
                    issues=pr.issues,
                    failure_reason=(
                        "missing"
                        if not pr.is_present
                        else "proportion"
                        if not pr.proportions_match
                        else "identity"
                        if not pr.is_accurate
                        else ""
                    ),
                )
                for pr in validation.product_results
            ]
            # Determine if attempt passed (respecting proportion validation setting)
            attempt_passed = validation.all_products_accurate and (
                validation.all_proportions_match or not settings.sip_proportion_validation
            )
            attempts_metadata.append(
                {
                    "attempt_number": attempt_number,
                    "prompt": current_prompt,
                    "image_path": str(attempt_path),
                    "validation": _validation_model_dump(validation),
                    "validation_passed": attempt_passed,
                }
            )
            metrics.add_attempt(
                attempt_number=attempt_number,
                prompt_used=current_prompt,
                overall_score=validation.overall_score,
                passed=attempt_passed,
                product_metrics=product_metrics,
                improvement_suggestions=validation.suggestions,
            )

            # Track best attempt by overall score
            if best_attempt is None or attempt.overall_score > best_attempt.overall_score:
                best_attempt = attempt

            # Log per-product results
            for pr in validation.product_results:
                # Status respects proportion validation setting
                prop_ok = pr.proportions_match or not settings.sip_proportion_validation
                status = "PASS" if pr.is_accurate and prop_ok else "FAIL"
                prop_note = ""
                if settings.sip_proportion_validation:
                    prop_note = f" [PROPORTIONS: {'OK' if pr.proportions_match else 'FAIL'}]"
                logger.info(
                    f"  {pr.product_name}: {pr.similarity_score:.2f} [{status}]{prop_note} "
                    f"{'- ' + pr.issues if pr.issues else ''}"
                )

            # Phase 3: Check both accuracy AND proportions
            validation_passed = validation.all_products_accurate and (
                validation.all_proportions_match or not settings.sip_proportion_validation
            )

            if validation_passed:
                # Success - all products validated
                final_path = output_dir / f"{filename}.png"
                attempt_path.rename(final_path)
                logger.info(
                    f"Multi-product validation passed on attempt {attempt_number} "
                    f"(overall score: {validation.overall_score:.2f})"
                )

                # Phase 0: Record success metrics
                metrics.successful_attempt = attempt_number
                metrics.final_score = validation.overall_score
                metrics.passed = True
                _write_metrics(metrics, output_dir)

                # Clean up attempt files
                _cleanup_attempt_files(attempts, None, final_path, output_dir)

                return MultiValidationGenerationResult(
                    path=str(final_path),
                    attempts=attempts_metadata,
                    final_prompt=current_prompt,
                    final_attempt_number=attempt_number,
                    validation_passed=True,
                )

            # Improve prompt for next attempt
            current_prompt = _improve_multi_product_prompt(
                original_prompt=prompt,
                validation_result=validation,
                attempt_number=attempt_number,
            )
            logger.info(
                f"Multi-product validation failed (score: {validation.overall_score:.2f}), "
                f"improving prompt for retry"
            )

        except Exception as e:
            logger.warning(f"Multi-product generation attempt {attempt_number} failed: {e}")
            attempts_metadata.append(
                {
                    "attempt_number": attempt_number,
                    "prompt": current_prompt,
                    "error": str(e),
                }
            )
            continue

    # All attempts exhausted - use best attempt as fallback
    if best_attempt:
        best_path = Path(best_attempt.image_path)
        final_path = output_dir / f"{filename}.png"
        if best_path.exists():
            best_path.rename(final_path)

        # Phase 0: Clean up attempt files (respects debug mode)
        _cleanup_attempt_files(attempts, best_path, final_path, output_dir)

        # Build per-product score summary
        score_summary = ", ".join(
            f"{name}: {score:.2f}" for name, score in best_attempt.product_scores.items()
        )

        # Phase 0: Determine failure category and record metrics
        failure_category = "identity"  # Default
        if metrics.attempts:
            last_attempt = metrics.attempts[-1]
            for pm in last_attempt.get("product_metrics", []):
                if not pm.get("is_present", True):
                    failure_category = "missing"
                    break
                if not pm.get("proportions_match", True):
                    failure_category = "proportion"
                    break

        metrics.final_score = best_attempt.overall_score
        metrics.passed = False
        metrics.failure_category = failure_category
        metrics.best_attempt_reason = f"Highest overall score: {best_attempt.overall_score:.2f}"
        _write_metrics(metrics, output_dir)

        logger.warning(
            f"Multi-product validation loop exhausted after {max_retries} attempts. "
            f"Using best attempt (overall: {best_attempt.overall_score:.2f}). "
            f"Per-product scores: {score_summary}"
        )
        warning = (
            f"[Warning: Multi-product validation did not pass after {max_retries} attempts. "
            f"Overall score: {best_attempt.overall_score:.2f}. "
            f"Per-product scores: {score_summary}. "
            f"Some products may not match their reference images exactly.]"
        )
        return MultiValidationGenerationResult(
            path=str(final_path),
            attempts=attempts_metadata,
            final_prompt=best_attempt.prompt_used,
            final_attempt_number=best_attempt.attempt_number,
            validation_passed=False,
            warning=warning,
        )

    # Phase 0: Record failure metrics
    metrics.passed = False
    metrics.failure_category = "error"
    _write_metrics(metrics, output_dir)

    return "Error: All multi-product generation attempts failed."


def _improve_multi_product_prompt(
    original_prompt: str,
    validation_result: MultiProductValidationResult,
    attempt_number: int,
) -> str:
    """Improve generation prompt based on multi-product validation feedback.

    Args:
        original_prompt: Original user prompt.
        validation_result: Validation results with per-product issues.
        attempt_number: Current attempt number.

    Returns:
        Improved prompt with specific fixes for failed products.
    """
    improvements = [
        "CRITICAL: EVERY product must appear EXACTLY as shown in its reference image.",
        "Preserve ALL distinctive features: materials, colors, shapes, textures, logos.",
        "Each product must be CLEARLY DISTINGUISHABLE - do not merge or confuse products.",
        "PRESERVE EXACT PROPORTIONS - do not squash or stretch any product.",
    ]

    # Add specific feedback for each failed product
    failed_products = []
    proportion_issues = []
    for pr in validation_result.product_results:
        if not pr.is_accurate and pr.issues:
            failed_products.append(f"  * {pr.product_name}: {pr.issues}")
        # Phase 3: Include proportion-specific feedback
        if not pr.proportions_match and pr.proportions_notes:
            proportion_issues.append(f"  * {pr.product_name}: {pr.proportions_notes}")

    if failed_products:
        improvements.append("IDENTITY ISSUES TO FIX:")
        improvements.extend(failed_products)

    if proportion_issues:
        improvements.append("PROPORTION ISSUES TO FIX:")
        improvements.extend(proportion_issues)

    if validation_result.suggestions:
        improvements.append(f"Overall feedback: {validation_result.suggestions}")

    return (
        f"{original_prompt}\n\n"
        f"[MULTI-PRODUCT ACCURACY - Attempt {attempt_number + 1}]\n"
        + "\n".join(f"- {imp}" if not imp.startswith("  ") else imp for imp in improvements)
    )
