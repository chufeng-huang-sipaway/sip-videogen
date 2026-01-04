"""Style reference analyzer for extracting layout using Gemini Vision.
V1: Geometry-focused (deprecated)
V2: Semantic-focused - verbatim copywriting, prose layout, visual treatments
"""

import json
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image as PILImage
from tenacity import retry, stop_after_attempt, wait_exponential

from sip_videogen.brands.models import StyleReferenceAnalysis, StyleReferenceAnalysisV2
from sip_videogen.config.logging import get_logger
from sip_videogen.config.settings import get_settings

logger = get_logger(__name__)
# V1 geometry-focused analysis prompt
_STYLE_ANALYSIS_PROMPT = """Analyze this style reference image and extract its complete layout specification.
Return a JSON object with this exact structure:
{
  "version": "1.0",
  "canvas": {
    "aspect_ratio": "1:1" | "16:9" | "9:16" | "4:5" | "...",
    "background": "description of background (color, gradient, texture)",
    "width": null,
    "height": null
  },
  "message": {
    "intent": "primary message intent (e.g., 'product launch', 'sale promotion')",
    "audience": "target audience description",
    "key_claims": ["claim1", "claim2"]
  },
  "style": {
    "palette": ["#hex1", "#hex2"],
    "lighting": "lighting style description",
    "mood": "overall mood/aesthetic",
    "materials": ["material1", "material2"]
  },
  "elements": [
    {
      "id": "unique_id",
      "type": "image" | "text" | "shape" | "product",
      "role": "semantic role (e.g., 'headline', 'logo', 'background', 'hero_image')",
      "geometry": {
        "x": 0.0 to 1.0 (fraction of canvas width from left),
        "y": 0.0 to 1.0 (fraction of canvas height from top),
        "width": 0.0 to 1.0 (fraction of canvas width),
        "height": 0.0 to 1.0 (fraction of canvas height),
        "rotation": 0,
        "z_index": 0
      },
      "appearance": {
        "fill": "color or gradient",
        "stroke": "border color if any",
        "opacity": 1.0,
        "blur": 0.0,
        "shadow": "shadow description if any"
      },
      "content": {
        "text": "text content if text element",
        "font_family": "font if identifiable",
        "font_size": "relative size (small/medium/large/xlarge)",
        "font_weight": "normal/bold/...",
        "alignment": "left/center/right",
        "image_description": "description of image content"
      },
      "constraints": {
        "locked_position": true/false,
        "locked_size": true/false,
        "locked_aspect": true/false,
        "min_margin": 0.0,
        "semantic_role": "role for strict mode preservation"
      }
    }
  ],
  "product_slot": {
    "id": "product_main",
    "geometry": {
      "x": 0.0 to 1.0,
      "y": 0.0 to 1.0,
      "width": 0.0 to 1.0,
      "height": 0.0 to 1.0,
      "rotation": 0,
      "z_index": 0
    },
    "appearance": {
      "fill": "",
      "stroke": "",
      "opacity": 1.0,
      "blur": 0.0,
      "shadow": "shadow if product has shadow"
    },
    "interaction": {
      "replacement_mode": "replace" | "overlay",
      "preserve_shadow": true/false,
      "preserve_reflection": false,
      "scale_mode": "fit" | "fill" | "stretch"
    }
  }
}

Analysis Instructions:
1. Identify the aspect ratio by measuring the image dimensions
2. Locate ALL visual elements (text, images, shapes, logos)
3. For each element, estimate position/size as fractions (0-1) of canvas
4. Identify the product area - where a product image should be placed
5. Extract colors from the palette (use hex codes)
6. Note the overall style, mood, and lighting

If multiple images are provided, analyze them together to find the CONSENSUS layout pattern.
Set product_slot to null if no clear product placement area exists.
Return ONLY valid JSON, no markdown formatting."""  # noqa: E501
_MULTI_IMAGE_PROMPT = (
    """Analyze these style reference images together.
They represent variations of the same layout style.
Identify the COMMON layout pattern across all images.
"""
    + _STYLE_ANALYSIS_PROMPT
)


def _strip_md(txt: str) -> str:
    """Strip markdown code fences from response."""
    if txt.startswith("```"):
        ln = txt.split("\n")
        if ln[0].startswith("```"):
            ln = ln[1:]
        if ln and ln[-1].strip() == "```":
            ln = ln[:-1]
        return "\n".join(ln)
    return txt


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60), reraise=True)
async def analyze_style_reference(images: list[Path | bytes]) -> StyleReferenceAnalysis | None:
    """Analyze style reference image(s) to extract layout specification.
    Args:
        images: List of image paths or raw bytes (1-2 images).
    Returns:
        StyleReferenceAnalysis with extracted layout, or None if analysis fails.
    """
    if not images:
        logger.warning("No images provided for style reference analysis")
        return None
    try:
        settings = get_settings()
        client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)
        # Load images
        pil_imgs = []
        for img in images:
            if isinstance(img, bytes):
                import io

                pil_imgs.append(PILImage.open(io.BytesIO(img)))
            else:
                pil_imgs.append(PILImage.open(img))
        img_info = ", ".join(f"{i.size[0]}x{i.size[1]}" for i in pil_imgs)
        logger.debug(f"Analyzing {len(pil_imgs)} style reference image(s): {img_info}")
        # Build content
        prompt = _MULTI_IMAGE_PROMPT if len(pil_imgs) > 1 else _STYLE_ANALYSIS_PROMPT
        contents = [prompt] + pil_imgs
        # Call Gemini Vision
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.1),
        )
        txt = _strip_md(resp.text.strip())
        data = json.loads(txt)
        analysis = StyleReferenceAnalysis(**data)
        c, e, s = (
            analysis.canvas.aspect_ratio,
            len(analysis.elements),
            analysis.product_slot is not None,
        )
        logger.info(f"Style reference analysis complete: canvas={c}, elements={e}, has_slot={s}")
        return analysis
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse Gemini response as JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"Style reference analysis failed: {e}")
        return None


async def analyze_style_reference_from_paths(
    image_paths: list[str],
) -> StyleReferenceAnalysis | None:
    """Convenience wrapper accepting string paths.
    Args:
        image_paths: List of file path strings.
    Returns:
        StyleReferenceAnalysis or None.
    """
    return await analyze_style_reference([Path(p) for p in image_paths])


# V2 Semantic Analysis - focuses on meaning, not geometry
_STYLE_ANALYSIS_PROMPT_V2 = """Analyze this style reference image and extract its SEMANTIC structure.
Focus on MEANING and REPRODUCTION, not pixel coordinates.

Return a JSON object with this exact structure:
{
  "version": "2.0",
  "canvas": {
    "aspect_ratio": "1:1" | "16:9" | "9:16" | "4:5" | "...",
    "background": "description of background (color, gradient, texture)"
  },
  "style": {
    "palette": ["#hex1", "#hex2", ...],
    "lighting": "lighting style description",
    "mood": "overall mood/aesthetic",
    "materials": ["material1", "material2"]
  },
  "layout": {
    "structure": "Prose layout description (e.g., 'Two-column split: text left, image right')",
    "zones": ["headline zone", "benefits area", "product hero", "footer"],
    "hierarchy": "What draws the eye first, second, third? Describe the visual flow.",
    "alignment": "Alignment pattern: 'left-aligned text, right-aligned imagery' or 'centered'"
  },
  "copywriting": {
    "headline": "EXACT headline text, CHARACTER-FOR-CHARACTER as shown in image",
    "subheadline": "EXACT subheadline if present, CHARACTER-FOR-CHARACTER",
    "body_texts": ["Each line of body copy EXACTLY as written, preserve punctuation"],
    "benefits": ["Each benefit statement EXACTLY as written, preserve asterisks/daggers"],
    "cta": "Call-to-action text EXACTLY as written",
    "disclaimer": "Any fine print or disclaimers EXACTLY as written, preserve line breaks",
    "tagline": "Brand tagline if visible"
  },
  "visual_scene": {
    "scene_description": "Describe the overall visual scene in detail",
    "product_placement": "How does the product appear? (e.g., 'Product centered on marble surface')",
    "lifestyle_elements": ["female hands", "blender with ingredients", "marble countertop"],
    "visual_treatments": ["rounded pill badges", "soft drop shadow", "gradient overlay"],
    "photography_style": "lifestyle with human interaction | clean studio shot | flat lay"
  },
  "constraints": {
    "non_negotiables": [
      "All copywriting text must appear VERBATIM",
      "Benefit statements must appear in exact order shown",
      "Layout structure must be preserved",
      "Visual treatments must be replicated"
    ],
    "creative_freedom": [
      "Background scene details can vary",
      "Exact colors can shift within palette family",
      "Specific lifestyle props can change"
    ],
    "product_integration": "How to place the product in the layout"
  }
}

CRITICAL INSTRUCTIONS:
1. **VERBATIM TEXT**: Extract ALL text CHARACTER-FOR-CHARACTER. Include asterisks, daggers, etc.
2. **PROSE LAYOUT**: Describe layout in words ('left half', 'right third'), NOT coordinates
3. **VISUAL TREATMENTS**: Name specific design techniques ('rounded pill badges', 'soft shadow')
4. **NON-NEGOTIABLES**: Identify what makes this style work
5. **BENEFITS ORDER**: If there are ordered benefit statements, preserve their exact order

Return ONLY valid JSON, no markdown formatting."""  # noqa: E501

_MULTI_IMAGE_PROMPT_V2 = (
    """Analyze these style reference images together.
They represent variations of the same layout style.
Identify the COMMON semantic pattern across all images.
"""
    + _STYLE_ANALYSIS_PROMPT_V2
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60), reraise=True)
async def analyze_style_reference_v2(images: list[Path | bytes]) -> StyleReferenceAnalysisV2 | None:
    """Analyze style reference image(s) using V2 semantic analysis.
    Args:
        images: List of image paths or raw bytes (1-2 images).
    Returns:
        StyleReferenceAnalysisV2 with semantic layout, or None if analysis fails.
    """
    if not images:
        logger.warning("No images provided for style reference analysis")
        return None
    try:
        settings = get_settings()
        client = genai.Client(api_key=settings.gemini_api_key, vertexai=False)
        pil_imgs = []
        for img in images:
            if isinstance(img, bytes):
                import io

                pil_imgs.append(PILImage.open(io.BytesIO(img)))
            else:
                pil_imgs.append(PILImage.open(img))
        img_info = ", ".join(f"{i.size[0]}x{i.size[1]}" for i in pil_imgs)
        logger.debug(f"Analyzing {len(pil_imgs)} style reference image(s) with V2: {img_info}")
        prompt = _MULTI_IMAGE_PROMPT_V2 if len(pil_imgs) > 1 else _STYLE_ANALYSIS_PROMPT_V2
        contents = [prompt] + pil_imgs
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.1),
        )
        txt = _strip_md(resp.text.strip())
        data = json.loads(txt)
        analysis = StyleReferenceAnalysisV2(**data)
        c = analysis.canvas.aspect_ratio
        b = len(analysis.copywriting.benefits)
        t = len(analysis.visual_scene.visual_treatments)
        logger.info(f"V2 analysis complete: canvas={c}, copywriting_items={b}, treatments={t}")
        return analysis
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse V2 Gemini response as JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"V2 style reference analysis failed: {e}")
        return None


async def analyze_style_reference_v2_from_paths(
    image_paths: list[str],
) -> StyleReferenceAnalysisV2 | None:
    """Convenience wrapper for V2 accepting string paths."""
    return await analyze_style_reference_v2([Path(p) for p in image_paths])
