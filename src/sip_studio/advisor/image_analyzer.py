"""Image analyzer for extracting product information using Gemini Vision.
This module provides functionality to analyze product images and extract
structured information (name, measurements, colors, materials) before
sending to the Brand Advisor agent.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from google import genai
from google.genai import types
from PIL import Image as PILImage

from sip_studio.config.logging import get_logger
from sip_studio.config.settings import get_settings
from sip_studio.studio.services.rate_limiter import rate_limited_generate_content

logger = get_logger(__name__)


class ExtractedAttribute(TypedDict):
    """Single extracted attribute from an image."""

    key: str
    value: str
    category: str  # measurements, texture, surface, appearance, distinguishers


class ImageAnalysisResult(TypedDict):
    """Result of analyzing a product image."""

    product_name: str | None
    image_type: str  # product_photo, screenshot, document, label
    is_suitable_reference: bool  # True if clean product photo
    attributes: list[ExtractedAttribute]
    description: str
    visible_text: str


_ANALYSIS_PROMPT = """Analyze this image and extract all visible product information.

Return a JSON object with this exact structure:
{
  "product_name": "Name of the product if visible, or null if not clear",
  "image_type": "product_photo" | "screenshot" | "document" | "label",
  "is_suitable_reference": true/false,
  "attributes": [
    {"key": "...", "value": "...", "category": "..."}
  ],
  "description": "Brief description of what's shown",
  "visible_text": "Key text/numbers visible in the image"
}

Classification rules for image_type:
- "product_photo": Clean shot of a product, suitable for reference
- "screenshot": Screenshot of a webpage, app, or e-commerce page
- "document": Text-heavy document, spec sheet, or manual
- "label": Nutrition label, ingredient list, or product specifications

is_suitable_reference should be TRUE only if:
- The image shows the COMPLETE product
- The product is the primary subject (not part of a webpage)
- Clean angle suitable for AI image generation reference

For attributes, extract with these categories:
- measurements: dimensions, weight, volume (e.g., "50ml", "2.5 lb", "150mm tall")
- texture: materials visible (e.g., "glass jar", "plastic bottle", "fabric bag")
- surface: finish visible (e.g., "matte", "glossy", "frosted")
- appearance: colors (e.g., "deep blue", "rose gold", "transparent")
- distinguishers: distinctive features (e.g., "pump dispenser", "twist cap", "embossed logo")

Be precise with measurements and use specific color names when visible.
Return ONLY valid JSON, no markdown formatting."""


async def analyze_image(image_path: Path) -> ImageAnalysisResult | None:
    """Analyze an image to extract product information.

    Args:
        image_path: Path to the image file to analyze.

    Returns:
        ImageAnalysisResult with extracted information, or None if analysis fails.
    """
    try:
        settings = get_settings()

        # Initialize Gemini client
        client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)

        # Load image
        pil_image = PILImage.open(image_path)
        logger.debug(f"Analyzing image: {image_path.name} ({pil_image.size})")

        # Call Gemini Vision (rate-limited)
        response = rate_limited_generate_content(
            client,
            "gemini-2.0-flash",
            [_ANALYSIS_PROMPT, pil_image],
            types.GenerateContentConfig(temperature=0.1),
        )

        # Parse response
        response_text = (response.text or "").strip()

        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            # Remove markdown code fences
            lines = response_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines)

        result = json.loads(response_text)
        logger.info(
            f"Image analysis complete: {image_path.name} -> "
            f"type={result.get('image_type')}, "
            f"suitable_ref={result.get('is_suitable_reference')}, "
            f"attrs={len(result.get('attributes', []))}"
        )

        return ImageAnalysisResult(
            product_name=result.get("product_name"),
            image_type=result.get("image_type", "unknown"),
            is_suitable_reference=result.get("is_suitable_reference", False),
            attributes=result.get("attributes", []),
            description=result.get("description", ""),
            visible_text=result.get("visible_text", ""),
        )

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse Gemini response as JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"Image analysis failed for {image_path}: {e}")
        return None


_PACKAGING_TEXT_PROMPT_BASE = """Analyze text on this product packaging like a graphic designer explaining to another designer.
Return JSON with:
- summary: Brief overview of text layout and visual hierarchy
- elements: Array of text elements, each with:
  - text: Exact literal characters only (no explanations here)
  - notes: Disambiguation if needed, e.g. "letter O not zero", "lowercase L not one"
  - role: brand_name|product_name|tagline|instructions|legal|decorative|other
  - typography: serif|sans-serif|script|decorative|handwritten|geometric|monospace
  - size: large|medium|small|tiny (relative to package)
  - color: Specific color description
  - position: Where on package (front-center, top-left, cap, etc.)
  - emphasis: bold|italic|all-caps|embossed|engraved|foil|metallic|printed
- layout_notes: How text elements relate spatially
Guidelines:
- Keep "text" field literal - put clarifications in "notes"
- List elements in visual hierarchy order (most prominent first)
- Include special finishes: embossing, foil stamping, metallic ink
- If text is partially visible, describe what's readable
- Skip very long text (ingredients, legal disclaimers)
Return ONLY valid JSON, no markdown formatting."""


def _build_packaging_prompt(
    brand_context: str | None = None, product_context: str | None = None
) -> str:
    """Build packaging text prompt with optional brand/product context."""
    prompt = _PACKAGING_TEXT_PROMPT_BASE
    if brand_context or product_context:
        prompt += "\n---\nBackground context (for disambiguation only, do not invent text):"
        if brand_context:
            prompt += f"\nBrand: {brand_context}"
        if product_context:
            prompt += f"\nProduct: {product_context}"
    return prompt


async def analyze_packaging_text(
    image_path: Path, brand_context: str | None = None, product_context: str | None = None
):
    """Analyze packaging text from a product image using Gemini Vision.
    Args:
     image_path: Path to the image file to analyze.
     brand_context: Optional brand info for disambiguation (e.g. "Summit Coffee - Premium artisan coffee").
     product_context: Optional product info for disambiguation (e.g. "Ethiopian Single Origin - Single-origin beans").
    Returns:
     PackagingTextDescription with extracted text elements, or None if analysis fails.
    """
    from sip_studio.brands.models import PackagingTextDescription, PackagingTextElement

    try:
        settings = get_settings()
        client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)
        pil_image = PILImage.open(image_path)
        prompt = _build_packaging_prompt(brand_context, product_context)
        logger.debug(f"Analyzing packaging text: {image_path.name} ({pil_image.size})")
        response = rate_limited_generate_content(
            client,
            "gemini-3-pro-image-preview",
            [prompt, pil_image],
            types.GenerateContentConfig(temperature=0.1),
        )
        response_text = (response.text or "").strip()
        # Handle potential markdown code blocks (reuse existing pattern)
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines)
        data = json.loads(response_text)
        elements = [PackagingTextElement(**e) for e in data.get("elements", [])]
        result = PackagingTextDescription(
            summary=data.get("summary", ""),
            elements=elements,
            layout_notes=data.get("layout_notes", ""),
            source_image=str(image_path),
            generated_at=datetime.now(timezone.utc),
        )
        logger.info(
            f"Packaging text analysis complete: {image_path.name} -> {len(elements)} elements"
        )
        return result
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse packaging text response as JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"Packaging text analysis failed for {image_path}: {e}")
        return None


def format_analysis_for_message(
    analyses: list[tuple[str, str, ImageAnalysisResult | None]],
) -> str:
    """Format multiple image analyses as markdown for the agent message.

    Args:
        analyses: List of (filename, rel_path, analysis_result) tuples.

    Returns:
        Markdown-formatted string with extracted information.
    """
    if not analyses:
        return ""

    sections = []
    attachment_paths = []
    reference_candidates: list[str] = []
    info_only_attachments: list[str] = []
    unknown_attachments: list[str] = []
    has_any_analysis = False

    for filename, rel_path, result in analyses:
        entry = f"- {filename} (path: {rel_path})"
        attachment_paths.append(entry)

        if result is None:
            unknown_attachments.append(entry)
            continue

        has_any_analysis = True
        type_label = {
            "product_photo": "clean product image",
            "screenshot": "screenshot",
            "document": "document",
            "label": "product label/specs",
        }.get(result["image_type"], result["image_type"])

        is_reference_candidate = bool(result.get("is_suitable_reference")) and (
            result.get("image_type") == "product_photo"
        )
        if is_reference_candidate:
            reference_candidates.append(entry)
        else:
            info_only_attachments.append(entry)

        if is_reference_candidate:
            ref_note = " - **suitable as product reference image**"
        else:
            ref_note = " - **NOT suitable as product reference image (info-only)**"

        lines = [f"**From: {filename}** ({type_label}{ref_note})"]

        if result["product_name"]:
            lines.append(f"- Product Name: {result['product_name']}")

        # Group attributes by category for cleaner output
        for attr in result["attributes"]:
            key = attr.get("key", "")
            value = attr.get("value", "")
            if key and value:
                lines.append(f"- {key.title()}: {value}")

        if result["description"]:
            lines.append(f"- Description: {result['description']}")

        sections.append("\n".join(lines))

    # Build final output
    output_parts = []

    # Provide an explicit, easy-to-follow summary to reduce accidental misuse of screenshots/docs
    output_parts.append("## Attachment Summary (Gemini Vision)\n")
    output_parts.append("Reference-ready images (OK to store in product images):")
    output_parts.append("\n".join(reference_candidates) if reference_candidates else "- (none)")
    output_parts.append("")
    output_parts.append("Info-only attachments (extract info, but DO NOT store in product images):")
    output_parts.append("\n".join(info_only_attachments) if info_only_attachments else "- (none)")
    if unknown_attachments:
        output_parts.append("")
        output_parts.append("Other attachments (not analyzed):")
        output_parts.append("\n".join(unknown_attachments))
    output_parts.append("")

    if has_any_analysis:
        output_parts.append("## Product Information Extracted from Attachments\n")
        output_parts.append("\n\n".join(sections))
        output_parts.append("")

    output_parts.append("Attachments provided (paths are relative to the brand folder):")
    output_parts.append("\n".join(attachment_paths))

    return "\n".join(output_parts)
