"""Core validation functions using GPT-4o vision."""

from __future__ import annotations

import base64

from .models import MultiProductValidationResult, ReferenceValidationResult
from .prompts import _MULTI_PRODUCT_VALIDATOR_PROMPT, _VALIDATOR_PROMPT


async def validate_reference_identity(
    reference_image_bytes: bytes, generated_image_bytes: bytes, original_prompt: str
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
    va = Agent(
        name="Reference Image Validator",
        instructions=_VALIDATOR_PROMPT,
        model="gpt-4o",
        output_type=ReferenceValidationResult,
    )
    # Encode images
    rb = base64.b64encode(reference_image_bytes).decode("utf-8")
    gb = base64.b64encode(generated_image_bytes).decode("utf-8")
    # Build validation request
    vp = f"""Compare these two images:

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
    im = {
        "role": "user",
        "content": [
            {"type": "input_text", "text": vp},
            {"type": "input_image", "image_url": f"data:image/png;base64,{rb}", "detail": "high"},
            {"type": "input_image", "image_url": f"data:image/png;base64,{gb}", "detail": "high"},
        ],
    }
    r = await Runner.run(va, [im])
    return r.final_output


async def validate_multi_product_identity(
    product_references: list[tuple[str, bytes]], generated_image_bytes: bytes, original_prompt: str
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
    va = Agent(
        name="Multi-Product Validator",
        instructions=_MULTI_PRODUCT_VALIDATOR_PROMPT,
        model="gpt-4o",
        output_type=MultiProductValidationResult,
    )
    # Encode generated image
    gb = base64.b64encode(generated_image_bytes).decode("utf-8")
    # Build product reference descriptions and encode images
    pd = []
    ic = []
    for idx, (name, rb) in enumerate(product_references, 1):
        pd.append(f"- Product {idx}: {name}")
        b64 = base64.b64encode(rb).decode("utf-8")
        ic.append(
            {"type": "input_image", "image_url": f"data:image/png;base64,{b64}", "detail": "high"}
        )
    pl = "\n".join(pd)
    # Build validation request
    np = len(product_references)
    vp = f"""Validate this generated image against {np} product references.

**Products to find:**
{pl}

**Generation Prompt Used:** {original_prompt}

**Reference images** (in order): Images 1-{np} are the product references.
**Generated image**: Image {np + 1} is the AI-generated result.

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
    cnt = [{"type": "input_text", "text": vp}]
    cnt.extend(ic)  # Reference images
    cnt.append(
        {"type": "input_image", "image_url": f"data:image/png;base64,{gb}", "detail": "high"}
    )  # Generated image last
    im = {"role": "user", "content": cnt}
    r = await Runner.run(va, [im])
    return r.final_output
