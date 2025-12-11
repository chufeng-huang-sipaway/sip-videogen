"""Gemini Image Generator for creating reference images.

This module provides image generation functionality using Google's Gemini API
to create reference images for shared visual elements.
"""

import asyncio
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

    def __init__(self, api_key: str, model: str = "gemini-3-pro-image-preview"):
        """Initialize the image generator.

        Args:
            api_key: Google Gemini API key.
            model: Model to use for image generation. Defaults to gemini-3-pro-image-preview
                   which supports high-quality image generation.
        """
        # Explicitly use API key authentication, NOT Vertex AI
        # This is important because GOOGLE_GENAI_USE_VERTEXAI env var may be set
        # for VEO video generation, but Gemini image gen works with API keys
        self.client = genai.Client(api_key=api_key, vertexai=False)
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
                        image_size="2K",
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
        max_concurrent: int = 3,
    ) -> list[GeneratedAsset]:
        """Generate reference images for all shared elements in parallel.

        Args:
            elements: List of SharedElements to generate images for.
            output_dir: Directory to save the generated images.
            max_concurrent: Maximum number of concurrent image generations. Defaults to 3.

        Returns:
            List of GeneratedAssets for all successfully generated images.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Generating {len(elements)} reference images in parallel "
            f"(max concurrent: {max_concurrent})"
        )

        # Results container
        results: list[GeneratedAsset | None] = [None] * len(elements)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(idx: int, element: SharedElement) -> None:
            """Generate a single image with semaphore control."""
            async with semaphore:
                aspect_ratio = self._get_aspect_ratio_for_element(element)
                try:
                    asset = await self.generate_reference_image(
                        element=element,
                        output_dir=output_dir,
                        aspect_ratio=aspect_ratio,
                    )
                    results[idx] = asset
                except ImageGenerationError as e:
                    logger.warning(f"Skipping element {element.id} due to error: {e}")

        # Create and run all tasks in parallel
        tasks = [generate_with_semaphore(idx, element) for idx, element in enumerate(elements)]
        await asyncio.gather(*tasks)

        # Filter successful results
        assets = [r for r in results if r is not None]
        logger.info(f"Successfully generated {len(assets)}/{len(elements)} reference images")
        return assets

    def _build_prompt(self, element: SharedElement) -> str:
        """Build a generation prompt for a shared element.

        Always generates photorealistic style images for consistency with VEO video output.
        Constructs highly detailed prompts to maximize generation quality and reduce
        rejection rates during quality review.

        Args:
            element: The SharedElement to build a prompt for.

        Returns:
            A detailed prompt string for image generation.
        """
        description = element.visual_description
        element_type = element.element_type.value
        name = element.name

        # Start with a clear subject declaration
        prompt_parts = []

        if element_type == "character":
            # Include role descriptor if available for additional context
            role_context = f" ({element.role_descriptor})" if element.role_descriptor else ""
            prompt_parts.extend([
                f"A photorealistic studio portrait photograph of {name}{role_context}.",
                f"Subject description: {description}",
                "",
                "CRITICAL REQUIREMENTS:",
                "- Single person only, no other people or figures in the image",
                "- Face must be clearly visible, sharp, and well-defined",
                "- Front-facing or slight three-quarter angle for clear facial features",
                "- Upper body or head-and-shoulders framing, centered in frame",
                "- Plain neutral background (solid gray, white, or soft gradient)",
                "- Professional studio lighting: soft key light, subtle fill, clean shadows",
                "- Sharp focus on the subject, no motion blur",
                "- Natural skin tones, realistic proportions",
                "- Clothing and accessories as described, no extra items",
                "",
                "STYLE: Professional headshot photography, magazine quality, "
                "high-end commercial portrait. 8K resolution, extremely detailed, "
                "natural lighting simulation, subtle catchlights in eyes.",
            ])

        elif element_type == "environment":
            prompt_parts.extend([
                f"A photorealistic establishing shot photograph of {name}.",
                f"Location description: {description}",
                "",
                "CRITICAL REQUIREMENTS:",
                "- Wide angle establishing shot showing the full environment",
                "- NO people, characters, or human figures in the frame",
                "- Clear visibility of key architectural and environmental features",
                "- Balanced composition with clear focal point",
                "- Natural ambient lighting appropriate to the setting",
                "- Sharp focus throughout, deep depth of field",
                "- Clean and uncluttered scene, no distracting elements",
                "- Weather and time of day as appropriate to the description",
                "",
                "STYLE: Professional location photography, cinematic framing, "
                "high-end real estate or film location scout quality. "
                "8K resolution, HDR dynamic range, vivid but natural colors.",
            ])

        elif element_type == "prop":
            prompt_parts.extend([
                f"A photorealistic product photograph of {name}.",
                f"Object description: {description}",
                "",
                "CRITICAL REQUIREMENTS:",
                "- Single object only, isolated on neutral seamless background",
                "- Object perfectly centered in frame with adequate padding",
                "- NO people, hands, or other objects in the image",
                "- Full visibility of the object's key features and details",
                "- Three-quarter angle or straight-on view for clear identification",
                "- Professional product lighting: soft diffused light, minimal shadows",
                "- Sharp focus on the entire object, no blur",
                "- Accurate colors and materials as described",
                "- Correct scale and proportions",
                "",
                "STYLE: Professional product photography, e-commerce or catalog quality. "
                "8K resolution, studio lighting, pristine presentation, "
                "white or light gray seamless backdrop.",
            ])

        # Universal quality and technical requirements
        prompt_parts.extend([
            "",
            "TECHNICAL SPECIFICATIONS:",
            "- Photorealistic rendering, indistinguishable from a real photograph",
            "- High resolution with fine detail throughout",
            "- No text, watermarks, signatures, or logos",
            "- No split-screen, collage, or multiple panels",
            "- No artistic filters, no illustration style, no cartoon elements",
            "- Clean image without artifacts, distortions, or anomalies",
            "- Professional color grading with natural tones",
        ])

        return "\n".join(prompt_parts)

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
