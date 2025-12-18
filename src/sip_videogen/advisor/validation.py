"""Reference image validation for Brand Advisor image generation.

This module provides validation functionality to ensure generated images
maintain object identity with provided reference images. Uses GPT-4o vision
to compare images and assess whether the same object appears in both.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from sip_videogen.config.logging import get_logger

if TYPE_CHECKING:
    from google.genai import Client

logger = get_logger(__name__)


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


class ProductValidationResult(BaseModel):
    """Result of validating a single product within a multi-product image."""

    product_name: str = Field(description="Name of the product being validated")
    is_present: bool = Field(
        description="Whether this product is visible in the generated image"
    )
    is_accurate: bool = Field(
        description="Whether this product's appearance matches the reference"
    )
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity score from 0.0 (completely different) to 1.0 (identical)",
    )
    issues: str = Field(
        default="",
        description="Specific issues found (wrong material, color mismatch, etc.)",
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


@dataclass
class ValidationAttempt:
    """Record of a single generation + validation attempt."""

    attempt_number: int
    prompt_used: str
    image_path: str
    similarity_score: float
    is_identical: bool
    improvement_suggestions: str


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

## Improvement Suggestions

When not identical, provide SPECIFIC suggestions:
- Which features are missing or wrong
- What the prompt should emphasize
- How to better describe the specific object

Examples:
- "The logo text is different - emphasize 'EXACT logo placement and text'"
- "Color is off - specify 'same shade of blue (#1234AB)'"
- "Shape altered - add 'preserve original proportions exactly'"
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

## Output

Provide individual scores for EACH product and an overall assessment.
Be STRICT about material and color accuracy - these are critical.
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
        image_content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{ref_b64}",
            "detail": "high",
        })

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
    input_content.append({  # Generated image last
        "type": "input_image",
        "image_url": f"data:image/png;base64,{gen_b64}",
        "detail": "high",
    })

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
) -> str:
    """Generate image with reference and validate for identity preservation.

    This function implements a retry loop that:
    1. Generates an image using the reference
    2. Validates it against the reference using GPT-4o vision
    3. If validation fails, improves the prompt and retries
    4. Returns the best attempt if all retries are exhausted

    Args:
        client: Gemini API client.
        prompt: Generation prompt.
        reference_image_bytes: Reference image bytes.
        output_dir: Directory to save output.
        filename: Base filename (without extension).
        aspect_ratio: Image aspect ratio.
        max_retries: Maximum validation attempts.

    Returns:
        Path to generated image. If validation failed after all retries,
        includes a warning message.
    """
    from google.genai import types
    from PIL import Image as PILImage

    attempts: list[ValidationAttempt] = []
    best_attempt: ValidationAttempt | None = None
    current_prompt = prompt

    for attempt_num in range(max_retries):
        attempt_number = attempt_num + 1
        logger.info(f"Reference generation attempt {attempt_number}/{max_retries}")

        try:
            # Build contents with reference image
            ref_pil = PILImage.open(io.BytesIO(reference_image_bytes))
            contents = [current_prompt, ref_pil]

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
                    # Gemini Image.save() only accepts a file path, not buffer
                    image.save(str(attempt_path))
                    # Read bytes back for validation
                    generated_bytes = attempt_path.read_bytes()
                    break

            if not generated_bytes:
                logger.warning(f"No image generated on attempt {attempt_number}")
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

            if validation.is_identical:
                # Success - rename to final filename
                final_path = output_dir / f"{filename}.png"
                attempt_path.rename(final_path)
                logger.info(
                    f"Validation passed on attempt {attempt_number} "
                    f"(score: {validation.similarity_score:.2f})"
                )
                return str(final_path)

            # Improve prompt for next attempt
            current_prompt = _improve_prompt_for_identity(
                original_prompt=prompt,
                suggestions=validation.improvement_suggestions,
                attempt_number=attempt_number,
            )
            logger.info(
                f"Validation failed (score: {validation.similarity_score:.2f}), "
                f"improving prompt for retry"
            )

        except Exception as e:
            logger.warning(f"Generation attempt {attempt_number} failed: {e}")
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
        return (
            f"{final_path}\n\n"
            f"[Warning: Object identity validation did not pass after {max_retries} attempts. "
            f"Best similarity score: {best_attempt.similarity_score:.2f}. "
            f"The generated image may differ from the reference.]"
        )

    return "Error: All generation attempts failed."


def _improve_prompt_for_identity(
    original_prompt: str,
    suggestions: str,
    attempt_number: int,
) -> str:
    """Improve generation prompt to better preserve object identity.

    Args:
        original_prompt: Original user prompt.
        suggestions: Improvement suggestions from validator.
        attempt_number: Current attempt number.

    Returns:
        Improved prompt.
    """
    improvements = [
        "CRITICAL: The generated image MUST show the EXACT SAME object from the reference image.",
        "Preserve all distinctive features: brand logos, specific colors, shapes, and markings.",
        "This is NOT about style - it's about showing the SAME physical object.",
    ]

    if suggestions:
        improvements.append(f"Specific feedback: {suggestions}")

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
) -> str:
    """Generate image with multiple products and validate each one.

    This function implements a retry loop that:
    1. Generates an image using all product reference images
    2. Validates each product individually using GPT-4o vision
    3. If any product fails validation, improves the prompt and retries
    4. Returns the best attempt if all retries are exhausted

    Args:
        client: Gemini API client.
        prompt: Generation prompt (should mention all products).
        product_references: List of (product_name, image_bytes) tuples.
        output_dir: Directory to save output.
        filename: Base filename (without extension).
        aspect_ratio: Image aspect ratio.
        max_retries: Maximum validation attempts.

    Returns:
        Path to generated image. If validation failed after all retries,
        includes a warning message with per-product scores.
    """
    from google.genai import types
    from PIL import Image as PILImage

    attempts: list[MultiValidationAttempt] = []
    best_attempt: MultiValidationAttempt | None = None
    current_prompt = prompt

    for attempt_num in range(max_retries):
        attempt_number = attempt_num + 1
        logger.info(
            f"Multi-product generation attempt {attempt_number}/{max_retries} "
            f"({len(product_references)} products)"
        )

        try:
            # Build contents with all reference images
            contents: list = [current_prompt]
            for name, ref_bytes in product_references:
                ref_pil = PILImage.open(io.BytesIO(ref_bytes))
                contents.append(ref_pil)

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
                continue

            # Validate all products
            logger.info(
                f"Validating attempt {attempt_number} "
                f"against {len(product_references)} products..."
            )
            validation = await validate_multi_product_identity(
                product_references=product_references,
                generated_image_bytes=generated_bytes,
                original_prompt=current_prompt,
            )

            # Build product scores dict
            product_scores = {
                pr.product_name: pr.similarity_score
                for pr in validation.product_results
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

            # Track best attempt by overall score
            if best_attempt is None or attempt.overall_score > best_attempt.overall_score:
                best_attempt = attempt

            # Log per-product results
            for pr in validation.product_results:
                status = "PASS" if pr.is_accurate else "FAIL"
                logger.info(
                    f"  {pr.product_name}: {pr.similarity_score:.2f} [{status}] "
                    f"{'- ' + pr.issues if pr.issues else ''}"
                )

            if validation.all_products_accurate:
                # Success - all products validated
                final_path = output_dir / f"{filename}.png"
                attempt_path.rename(final_path)
                logger.info(
                    f"Multi-product validation passed on attempt {attempt_number} "
                    f"(overall score: {validation.overall_score:.2f})"
                )
                return str(final_path)

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
            continue

    # All attempts exhausted - use best attempt as fallback
    if best_attempt:
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

        # Build per-product score summary
        score_summary = ", ".join(
            f"{name}: {score:.2f}"
            for name, score in best_attempt.product_scores.items()
        )

        logger.warning(
            f"Multi-product validation loop exhausted after {max_retries} attempts. "
            f"Using best attempt (overall: {best_attempt.overall_score:.2f}). "
            f"Per-product scores: {score_summary}"
        )
        return (
            f"{final_path}\n\n"
            f"[Warning: Multi-product validation did not pass after {max_retries} attempts. "
            f"Overall score: {best_attempt.overall_score:.2f}. "
            f"Per-product scores: {score_summary}. "
            f"Some products may not match their reference images exactly.]"
        )

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
    ]

    # Add specific feedback for each failed product
    failed_products = []
    for pr in validation_result.product_results:
        if not pr.is_accurate and pr.issues:
            failed_products.append(f"  * {pr.product_name}: {pr.issues}")

    if failed_products:
        improvements.append("SPECIFIC ISSUES TO FIX:")
        improvements.extend(failed_products)

    if validation_result.suggestions:
        improvements.append(f"Overall feedback: {validation_result.suggestions}")

    return (
        f"{original_prompt}\n\n"
        f"[MULTI-PRODUCT ACCURACY - Attempt {attempt_number + 1}]\n"
        + "\n".join(f"- {imp}" if not imp.startswith("  ") else imp for imp in improvements)
    )
