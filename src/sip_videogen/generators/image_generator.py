"""Gemini Image Generator for creating reference images.

This module provides image generation functionality using Google's Gemini API
to create reference images for shared visual elements.
"""

from pathlib import Path

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from sip_videogen.config.logging import get_logger
from sip_videogen.models.assets import AssetType, GeneratedAsset
from sip_videogen.models.script import SharedElement

logger = get_logger(__name__)


class ImageGenerationError(Exception):
    """Raised when image generation fails."""

    pass


class ImageGenerator:
    """Generates reference images using Google Gemini API.

    This class handles the generation of reference images for SharedElements
    that need visual consistency across video scenes.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-image"):
        """Initialize the image generator.

        Args:
            api_key: Google Gemini API key.
            model: Model to use for image generation. Defaults to gemini-2.5-flash-image.
                   Use gemini-3-pro-image-preview for higher quality.
        """
        self.client = genai.Client(api_key=api_key)
        self.model = model
        logger.debug(f"Initialized ImageGenerator with model: {model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    async def generate_reference_image(
        self,
        element: SharedElement,
        output_dir: Path,
        aspect_ratio: str = "1:1",
    ) -> GeneratedAsset:
        """Generate a reference image for a shared element.

        Args:
            element: The SharedElement to generate an image for.
            output_dir: Directory to save the generated image.
            aspect_ratio: Image aspect ratio. Defaults to 1:1 (square) for character references.
                         Options: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9

        Returns:
            GeneratedAsset with the local path to the saved image.

        Raises:
            ImageGenerationError: If image generation fails after retries.
        """
        logger.info(f"Generating reference image for: {element.name} ({element.id})")

        # Build the prompt for image generation
        prompt = self._build_prompt(element)
        logger.debug(f"Image prompt: {prompt}")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    ),
                ),
            )

            # Extract and save the image
            for part in response.parts:
                if part.inline_data:
                    image = part.as_image()
                    image_path = output_dir / f"{element.id}.png"
                    image.save(str(image_path))
                    logger.info(f"Saved reference image to: {image_path}")

                    return GeneratedAsset(
                        asset_type=AssetType.REFERENCE_IMAGE,
                        element_id=element.id,
                        local_path=str(image_path),
                    )

            # No image was generated
            raise ImageGenerationError(
                f"No image generated for element: {element.id}. "
                "The response did not contain image data."
            )

        except Exception as e:
            logger.error(f"Failed to generate image for {element.id}: {e}")
            raise ImageGenerationError(
                f"Failed to generate reference image for {element.name}: {e}"
            ) from e

    async def generate_all_reference_images(
        self,
        elements: list[SharedElement],
        output_dir: Path,
    ) -> list[GeneratedAsset]:
        """Generate reference images for all shared elements.

        Args:
            elements: List of SharedElements to generate images for.
            output_dir: Directory to save the generated images.

        Returns:
            List of GeneratedAssets for all successfully generated images.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Generating {len(elements)} reference images to: {output_dir}")

        assets: list[GeneratedAsset] = []

        for element in elements:
            # Determine aspect ratio based on element type
            aspect_ratio = self._get_aspect_ratio_for_element(element)

            try:
                asset = await self.generate_reference_image(
                    element=element,
                    output_dir=output_dir,
                    aspect_ratio=aspect_ratio,
                )
                assets.append(asset)
            except ImageGenerationError as e:
                # Log error but continue with other elements
                logger.warning(f"Skipping element {element.id} due to error: {e}")

        logger.info(f"Successfully generated {len(assets)}/{len(elements)} reference images")
        return assets

    def _build_prompt(self, element: SharedElement) -> str:
        """Build a generation prompt for a shared element.

        Args:
            element: The SharedElement to build a prompt for.

        Returns:
            A detailed prompt string for image generation.
        """
        # Start with the visual description
        prompt_parts = [element.visual_description]

        # Add context based on element type
        type_context = {
            "character": "Full body character reference, clear details, neutral pose, professional illustration style.",
            "environment": "Establishing shot, wide view, atmospheric lighting, cinematic composition.",
            "prop": "Detailed object reference, clear view, clean background, product photography style.",
        }

        context = type_context.get(element.element_type.value, "")
        if context:
            prompt_parts.append(context)

        # Add quality modifiers
        prompt_parts.append("High quality, detailed, suitable for video production reference.")

        return " ".join(prompt_parts)

    def _get_aspect_ratio_for_element(self, element: SharedElement) -> str:
        """Determine the best aspect ratio for an element type.

        Args:
            element: The SharedElement to determine aspect ratio for.

        Returns:
            Aspect ratio string (e.g., "1:1", "16:9").
        """
        # Use square for characters (good for consistency)
        # Use wide for environments (establishes scene)
        # Use square for props (clear detail)
        aspect_ratios = {
            "character": "1:1",
            "environment": "16:9",
            "prop": "1:1",
        }
        return aspect_ratios.get(element.element_type.value, "1:1")
