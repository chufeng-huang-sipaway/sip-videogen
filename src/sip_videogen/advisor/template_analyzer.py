"""Template analyzer for extracting layout using Gemini Vision.
V1: Geometry-focused (deprecated)
V2: Semantic-focused - verbatim copywriting, prose layout, visual treatments
"""
import json
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image as PILImage
from tenacity import retry,stop_after_attempt,wait_exponential
from sip_videogen.config.logging import get_logger
from sip_videogen.config.settings import get_settings
from sip_videogen.brands.models import TemplateAnalysis,TemplateAnalysisV2
logger=get_logger(__name__)
_ANALYSIS_PROMPT="""Analyze this template image and extract its complete layout specification.
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
Return ONLY valid JSON, no markdown formatting."""
_MULTI_IMAGE_PROMPT="""Analyze these template images together.
They represent variations of the same layout template.
Identify the COMMON layout pattern across all images.
"""+_ANALYSIS_PROMPT
def _strip_md(txt:str)->str:
    """Strip markdown code fences from response."""
    if txt.startswith("```"):
        ln=txt.split("\n")
        if ln[0].startswith("```"):ln=ln[1:]
        if ln and ln[-1].strip()=="```":ln=ln[:-1]
        return "\n".join(ln)
    return txt
@retry(stop=stop_after_attempt(3),wait=wait_exponential(multiplier=1,min=4,max=60),reraise=True)
async def analyze_template(images:list[Path|bytes])->TemplateAnalysis|None:
    """Analyze template image(s) to extract layout specification.
    Args:
        images: List of image paths or raw bytes (1-2 images).
    Returns:
        TemplateAnalysis with extracted layout, or None if analysis fails.
    """
    if not images:
        logger.warning("No images provided for template analysis")
        return None
    try:
        settings=get_settings()
        client=genai.Client(api_key=settings.gemini_api_key,vertexai=False)
        #Load images
        pil_imgs=[]
        for img in images:
            if isinstance(img,bytes):
                import io
                pil_imgs.append(PILImage.open(io.BytesIO(img)))
            else:
                pil_imgs.append(PILImage.open(img))
        img_info=", ".join(f"{i.size[0]}x{i.size[1]}" for i in pil_imgs)
        logger.debug(f"Analyzing {len(pil_imgs)} template image(s): {img_info}")
        #Build content
        prompt=_MULTI_IMAGE_PROMPT if len(pil_imgs)>1 else _ANALYSIS_PROMPT
        contents=[prompt]+pil_imgs
        #Call Gemini Vision
        resp=client.models.generate_content(model="gemini-2.0-flash",contents=contents,config=types.GenerateContentConfig(temperature=0.1))
        txt=_strip_md(resp.text.strip())
        data=json.loads(txt)
        analysis=TemplateAnalysis(**data)
        logger.info(f"Template analysis complete: canvas={analysis.canvas.aspect_ratio}, elements={len(analysis.elements)}, has_slot={analysis.product_slot is not None}")
        return analysis
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse Gemini response as JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"Template analysis failed: {e}")
        return None
async def analyze_template_from_paths(image_paths:list[str])->TemplateAnalysis|None:
    """Convenience wrapper accepting string paths.
    Args:
        image_paths: List of file path strings.
    Returns:
        TemplateAnalysis or None.
    """
    return await analyze_template([Path(p) for p in image_paths])


#V2 Semantic Analysis - focuses on meaning, not geometry
_ANALYSIS_PROMPT_V2="""Analyze this template image and extract its SEMANTIC structure.
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
    "structure": "Prose description of layout. Examples: 'Two-column split: text content stacked on left half, lifestyle photography on right half', 'Hero-centered: large product centered with headline above and benefits below', 'Full-bleed background with text overlay in bottom third'",
    "zones": ["List named zones: 'headline zone', 'benefits area', 'product hero', 'footer'"],
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
    "scene_description": "Describe the overall visual scene: What is depicted? What's the setting? What's the atmosphere? Be specific about what the viewer sees.",
    "product_placement": "How does the product appear? Examples: 'Product jar held in hands over a blender', 'Product centered on marble surface', 'Product floating with ingredients around it'",
    "lifestyle_elements": ["List contextual elements: 'female hands', 'blender with ingredients', 'marble countertop', 'morning light through window'"],
    "visual_treatments": ["List specific design treatments: 'rounded pill badges for benefit list', 'soft drop shadow under product', 'gradient overlay on background image', 'white rounded rectangles behind each benefit'"],
    "photography_style": "Photography style: 'lifestyle with human interaction', 'clean studio shot', 'flat lay overhead', 'environmental product shot'"
  },
  "constraints": {
    "non_negotiables": [
      "All copywriting text must appear VERBATIM - exact wording, punctuation, symbols",
      "Benefit statements must appear in exact order shown",
      "Layout structure (e.g., 'two-column split') must be preserved",
      "Visual treatments (e.g., 'pill badges for benefits') must be replicated"
    ],
    "creative_freedom": [
      "Background scene details can vary (different setting, different props)",
      "Exact colors can shift within palette family",
      "Human model styling can change",
      "Specific lifestyle props can change (different blender, different surface)"
    ],
    "product_integration": "How to place the product: 'Product replaces existing product in the hero area on right side, maintaining similar scale and orientation'"
  }
}

CRITICAL INSTRUCTIONS:
1. **VERBATIM TEXT**: Extract ALL text CHARACTER-FOR-CHARACTER. Include asterisks (*), daggers (†), trademark symbols (®), etc. Do NOT paraphrase. Do NOT summarize.
2. **PROSE LAYOUT**: Describe layout in words ('left half', 'right third'), NOT coordinates (x=0.33)
3. **VISUAL TREATMENTS**: Name specific design techniques ('rounded pill badges', 'soft shadow', 'gradient overlay')
4. **NON-NEGOTIABLES**: Identify what makes this template work - what MUST be preserved for it to look like the original
5. **BENEFITS ORDER**: If there are numbered or ordered benefit statements, preserve their exact order

Return ONLY valid JSON, no markdown formatting."""

_MULTI_IMAGE_PROMPT_V2="""Analyze these template images together.
They represent variations of the same layout template.
Identify the COMMON semantic pattern across all images.
"""+_ANALYSIS_PROMPT_V2


@retry(stop=stop_after_attempt(3),wait=wait_exponential(multiplier=1,min=4,max=60),reraise=True)
async def analyze_template_v2(images:list[Path|bytes])->TemplateAnalysisV2|None:
    """Analyze template image(s) using V2 semantic analysis.
    Args:
        images: List of image paths or raw bytes (1-2 images).
    Returns:
        TemplateAnalysisV2 with semantic layout, or None if analysis fails.
    """
    if not images:
        logger.warning("No images provided for template analysis")
        return None
    try:
        settings=get_settings()
        client=genai.Client(api_key=settings.gemini_api_key,vertexai=False)
        pil_imgs=[]
        for img in images:
            if isinstance(img,bytes):
                import io
                pil_imgs.append(PILImage.open(io.BytesIO(img)))
            else:
                pil_imgs.append(PILImage.open(img))
        img_info=", ".join(f"{i.size[0]}x{i.size[1]}" for i in pil_imgs)
        logger.debug(f"Analyzing {len(pil_imgs)} template image(s) with V2: {img_info}")
        prompt=_MULTI_IMAGE_PROMPT_V2 if len(pil_imgs)>1 else _ANALYSIS_PROMPT_V2
        contents=[prompt]+pil_imgs
        resp=client.models.generate_content(model="gemini-2.0-flash",contents=contents,config=types.GenerateContentConfig(temperature=0.1))
        txt=_strip_md(resp.text.strip())
        data=json.loads(txt)
        analysis=TemplateAnalysisV2(**data)
        logger.info(f"V2 analysis complete: canvas={analysis.canvas.aspect_ratio}, copywriting_items={len(analysis.copywriting.benefits)}, treatments={len(analysis.visual_scene.visual_treatments)}")
        return analysis
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse V2 Gemini response as JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"V2 template analysis failed: {e}")
        return None


async def analyze_template_v2_from_paths(image_paths:list[str])->TemplateAnalysisV2|None:
    """Convenience wrapper for V2 accepting string paths."""
    return await analyze_template_v2([Path(p) for p in image_paths])
