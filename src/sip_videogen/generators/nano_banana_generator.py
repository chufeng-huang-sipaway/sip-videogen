"""Nano Banana Pro image generator adapter (Gemini-based).

This reuses the same Google Gemini image generation approach used for
reference images, but is configured for the "Nano Banana Pro" model
name expected by the brand kit workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from google import genai
from google.genai import types
from PIL import Image as PILImage

from sip_videogen.config.logging import get_logger

logger = get_logger(__name__)


class NanoBananaImageGenerator:
    """Wrapper around Google's image generation API for Nano Banana Pro."""

    def __init__(self, api_key: str, model: str = "gemini-3-pro-image-preview"):
        # Use explicit API key auth (not Vertex)
        self.client = genai.Client(api_key=api_key, vertexai=False)
        self.model = model

    def generate_images(
        self,
        prompt: str,
        output_dir: Path,
        n: int = 1,
        aspect_ratio: str = "1:1",
        filename_prefix: str = "asset",
        reference_image_path: str | None = None,
    ) -> List[str]:
        """Generate images for a prompt and save them to disk.

        Args:
            prompt: Text prompt to send to the model.
            output_dir: Directory to save generated images.
            n: Number of images to request.
            aspect_ratio: Image aspect ratio to request (1:1, 3:4, 4:5, 16:9, 9:16).
            filename_prefix: Prefix for output filenames.
            reference_image_path: Optional path to a reference image for consistency.

        Returns:
            List of local file paths to the generated images.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []

        # Build contents list - supports mixed text + image
        contents: list = [prompt]
        if reference_image_path:
            ref_img = PILImage.open(reference_image_path)
            contents.append(ref_img)
            logger.debug("Using reference image: %s", reference_image_path)

        for idx in range(n):
            logger.debug(
                "Calling model '%s' (attempt %s/%s) with aspect_ratio=%s",
                self.model,
                idx + 1,
                n,
                aspect_ratio,
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size="2K",
                    ),
                ),
            )

            saved = False
            for part in response.parts:
                if part.inline_data:
                    image = part.as_image()
                    filename = (
                        f"{filename_prefix}_{idx + 1}.png" if n > 1 else f"{filename_prefix}.png"
                    )
                    file_path = output_dir / filename
                    image.save(str(file_path))
                    paths.append(str(file_path))
                    logger.debug("Saved generated image: %s", file_path)
                    saved = True
                    break

            if not saved:
                logger.warning("No image data returned for %s (index %s)", filename_prefix, idx + 1)

        return paths
