"""Template analyzer for extracting layout geometry using Gemini Vision.
Analyzes template images to extract: canvas specs, layout elements, visual style, message intent, product slot.
"""
import json
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image as PILImage
from tenacity import retry,stop_after_attempt,wait_exponential
from sip_videogen.config.logging import get_logger
from sip_videogen.config.settings import get_settings
from sip_videogen.brands.models import TemplateAnalysis
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
