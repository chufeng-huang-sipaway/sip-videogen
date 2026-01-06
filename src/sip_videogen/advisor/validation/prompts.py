"""Prompt templates for validation and prompt improvement."""

from __future__ import annotations

from .models import MultiProductValidationResult

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


def _improve_prompt_for_identity(
    original_prompt: str, suggestions: str, attempt_number: int, proportions_notes: str = ""
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
    imps = [
        "CRITICAL: The generated image MUST show the EXACT SAME object from the reference image.",
        "Preserve all distinctive features: brand logos, specific colors, shapes, and markings.",
        "This is NOT about style - it's about showing the SAME physical object.",
        "PRESERVE EXACT PROPORTIONS - do not squash or stretch the object.",
    ]
    if suggestions:
        imps.append(f"Specific feedback: {suggestions}")
    if proportions_notes:
        imps.append(f"PROPORTION FIX NEEDED: {proportions_notes}")
    return (
        f"{original_prompt}\n\n[IDENTITY REQUIREMENT - Attempt {attempt_number + 1}]\n"
        + "\n".join(f"- {i}" for i in imps)
    )


def _improve_multi_product_prompt(
    original_prompt: str, validation_result: MultiProductValidationResult, attempt_number: int
) -> str:
    """Improve generation prompt based on multi-product validation feedback.
    Args:
            original_prompt: Original user prompt.
            validation_result: Validation results with per-product issues.
            attempt_number: Current attempt number.
    Returns:
            Improved prompt with specific fixes for failed products.
    """
    imps = [
        "CRITICAL: EVERY product must appear EXACTLY as shown in its reference image.",
        "Preserve ALL distinctive features: materials, colors, shapes, textures, logos.",
        "Each product must be CLEARLY DISTINGUISHABLE - do not merge or confuse products.",
        "PRESERVE EXACT PROPORTIONS - do not squash or stretch any product.",
    ]
    # Add specific feedback for each failed product
    failed = []
    prop_issues = []
    for pr in validation_result.product_results:
        if not pr.is_accurate and pr.issues:
            failed.append(f"  * {pr.product_name}: {pr.issues}")
        # Phase 3: Include proportion-specific feedback
        if not pr.proportions_match and pr.proportions_notes:
            prop_issues.append(f"  * {pr.product_name}: {pr.proportions_notes}")
    if failed:
        imps.append("IDENTITY ISSUES TO FIX:")
        imps.extend(failed)
    if prop_issues:
        imps.append("PROPORTION ISSUES TO FIX:")
        imps.extend(prop_issues)
    if validation_result.suggestions:
        imps.append(f"Overall feedback: {validation_result.suggestions}")
    return (
        f"{original_prompt}\n\n[MULTI-PRODUCT ACCURACY - Attempt {attempt_number + 1}]\n"
        + "\n".join(f"- {i}" if not i.startswith("  ") else i for i in imps)
    )
