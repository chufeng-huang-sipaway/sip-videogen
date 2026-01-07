"""Image Production tool for generating and reviewing reference images.

This module provides functionality to generate reference images with
quality review and automatic retry capability. It integrates the
ImageGenerator with the ImageReviewer agent to ensure quality control.
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from sip_studio.agents.image_reviewer import review_image
from sip_studio.config.logging import get_logger
from sip_studio.generators.image_generator import ImageGenerationError, ImageGenerator
from sip_studio.models.image_review import (
    ImageGenerationAttempt,
    ImageGenerationResult,
    ReviewDecision,
)

if TYPE_CHECKING:
    from sip_studio.models.script import SharedElement

logger = get_logger(__name__)

# Maximum number of retries for image generation (2 retries = 3 total attempts)
MAX_RETRIES = 2
# Default concurrency limits
_IMAGE_GEN_MAX_CONCURRENT = 8  # Generation limit (Gemini ~300 RPM)
_REVIEW_MAX_CONCURRENT = 4  # Review limit (separate semaphore)
_review_semaphore: asyncio.Semaphore | None = None


def _get_review_semaphore() -> asyncio.Semaphore:
    """Get or create the review semaphore (lazy init, module-level)."""
    global _review_semaphore
    if _review_semaphore is None:
        _review_semaphore = asyncio.Semaphore(_REVIEW_MAX_CONCURRENT)
    return _review_semaphore


class ImageProductionManager:
    """Manages image generation with quality review and retry capability.

    This class coordinates between the ImageGenerator and ImageReviewer
    to produce high-quality reference images with automatic retry on
    rejection.
    """

    def __init__(
        self,
        gemini_api_key: str,
        output_dir: Path,
        max_retries: int = MAX_RETRIES,
    ):
        """Initialize the image production manager.

        Args:
            gemini_api_key: API key for Gemini image generation.
            output_dir: Directory to save generated images.
            max_retries: Maximum number of retry attempts (default 2).
        """
        self.generator = ImageGenerator(api_key=gemini_api_key)
        self.output_dir = Path(output_dir)
        self.max_retries = max_retries
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_with_review(
        self,
        element: SharedElement,
        *,
        skip_review: bool = False,
    ) -> ImageGenerationResult:
        """Generate a reference image with review and automatic retry.
        This method:
        1. Generates an image using the ImageGenerator
        2. Sends it to the ImageReviewer for quality assessment (unless skip_review=True)
        3. If rejected, improves the prompt and retries (up to max_retries)
        4. If all attempts fail, keeps the last generated image as fallback
        5. Returns the final result with all attempt history
        Args:
            element: The SharedElement to generate an image for.
            skip_review: If True, skip quality review and return immediately (status="unreviewed").
        Returns:
            ImageGenerationResult with status, path, and attempt history.
        """
        if skip_review:
            return await self._generate_without_review(element)
        attempts: list[ImageGenerationAttempt] = []
        current_prompt = element.visual_description
        last_generated_path: str = ""  # Track last successfully generated image
        last_prompt_used: str = current_prompt

        for attempt_num in range(self.max_retries + 1):
            attempt_number = attempt_num + 1
            max_attempts = self.max_retries + 1
            is_last_attempt = attempt_num == self.max_retries
            logger.info(
                f"Generating image for {element.id} (attempt {attempt_number}/{max_attempts})"
            )

            # Create a working copy of the element with potentially improved prompt
            working_element = element.model_copy()
            working_element.visual_description = current_prompt

            try:
                # Generate the image
                aspect_ratio = self.generator._get_aspect_ratio_for_element(element)
                asset = await self.generator.generate_reference_image(
                    element=working_element,
                    output_dir=self.output_dir,
                    aspect_ratio=aspect_ratio,
                )

                # Track this as our latest generated image
                image_path = Path(asset.local_path)
                last_generated_path = asset.local_path
                last_prompt_used = current_prompt

                # Read image for review
                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")

                # Review the image (with semaphore to limit concurrent OpenAI calls)
                logger.info(f"Reviewing generated image for {element.id}")
                async with _get_review_semaphore():
                    review_result = await review_image(
                        element_id=element.id,
                        element_type=element.element_type.value,
                        element_name=element.name,
                        visual_description=current_prompt,
                        image_base64=image_data,
                    )

                if review_result.decision == ReviewDecision.ACCEPT:
                    # Image accepted
                    logger.info(f"Image accepted for {element.id}: {review_result.reasoning}")
                    attempts.append(
                        ImageGenerationAttempt(
                            attempt_number=attempt_number,
                            prompt_used=current_prompt,
                            outcome="success",
                        )
                    )
                    return ImageGenerationResult(
                        element_id=element.id,
                        status="success",
                        local_path=asset.local_path,
                        attempts=attempts,
                        final_prompt=current_prompt,
                    )
                else:
                    # Image rejected
                    logger.info(f"Image rejected for {element.id}: {review_result.reasoning}")
                    attempts.append(
                        ImageGenerationAttempt(
                            attempt_number=attempt_number,
                            prompt_used=current_prompt,
                            outcome="rejected",
                            rejection_reason=review_result.reasoning,
                        )
                    )

                    # Only delete rejected image if NOT the last attempt
                    # Keep the last one as fallback
                    if not is_last_attempt:
                        if image_path.exists():
                            image_path.unlink()
                            logger.debug(f"Deleted rejected image: {image_path}")

                        # Improve prompt for next attempt
                        current_prompt = self._improve_prompt(
                            original_prompt=current_prompt,
                            suggestions=review_result.improvement_suggestions,
                        )
                        logger.info(f"Improved prompt for retry: {current_prompt[:100]}...")
                    else:
                        logger.info(
                            f"Keeping last generated image for {element.id} as fallback "
                            f"(better than nothing)"
                        )

            except ImageGenerationError as e:
                logger.warning(f"Generation error for {element.id}: {e}")
                attempts.append(
                    ImageGenerationAttempt(
                        attempt_number=attempt_number,
                        prompt_used=current_prompt,
                        outcome="error",
                        error_message=str(e),
                    )
                )

        # All attempts exhausted - check if we have a fallback image
        if last_generated_path and Path(last_generated_path).exists():
            logger.warning(
                f"Using fallback image for {element.id} after "
                f"{self.max_retries + 1} attempts (image not ideal but usable)"
            )
            return ImageGenerationResult(
                element_id=element.id,
                status="fallback",
                local_path=last_generated_path,
                attempts=attempts,
                final_prompt=last_prompt_used,
            )

        # Complete failure - no image generated at all
        logger.warning(
            f"Failed to generate any image for {element.id} after {self.max_retries + 1} attempts"
        )
        return ImageGenerationResult(
            element_id=element.id,
            status="failed",
            local_path="",
            attempts=attempts,
            final_prompt=current_prompt,
        )

    def _improve_prompt(self, original_prompt: str, suggestions: str) -> str:
        """Improve the generation prompt based on review suggestions.

        Args:
            original_prompt: The original visual description prompt.
            suggestions: Improvement suggestions from the reviewer.

        Returns:
            Improved prompt incorporating the suggestions.
        """
        if not suggestions:
            return original_prompt

        # Extract key improvements from suggestions
        improvements = []

        # Common improvement patterns
        suggestion_lower = suggestions.lower()

        if "background" in suggestion_lower:
            improvements.append("plain neutral background")
        if "face" in suggestion_lower or "visible" in suggestion_lower:
            improvements.append("face clearly visible, front-facing")
        if "detail" in suggestion_lower or "sharp" in suggestion_lower:
            improvements.append("high detail, sharp focus")
        if "center" in suggestion_lower:
            improvements.append("centered in frame")
        if "lighting" in suggestion_lower:
            improvements.append("soft studio lighting")
        if "color" in suggestion_lower or "colour" in suggestion_lower:
            # Try to extract color-specific mentions
            if "red" in suggestion_lower:
                improvements.append("bright red coloring")
            elif "blue" in suggestion_lower:
                improvements.append("blue coloring")
            # Add more colors as needed
        if "clean" in suggestion_lower or "artifact" in suggestion_lower:
            improvements.append("clean image without artifacts")

        # If no specific patterns matched, append the full suggestions
        if not improvements and suggestions.strip():
            # Add a simplified version of the suggestions
            improvements.append(suggestions.strip()[:100])

        if improvements:
            return f"{original_prompt}. {', '.join(improvements)}."
        return original_prompt

    async def _generate_without_review(self, element: SharedElement) -> ImageGenerationResult:
        """Generate image without quality review (skip_review mode)."""
        logger.info(f"Generating image for {element.id} (skip_review mode)")
        try:
            aspect_ratio = self.generator._get_aspect_ratio_for_element(element)
            asset = await self.generator.generate_reference_image(
                element=element, output_dir=self.output_dir, aspect_ratio=aspect_ratio
            )
            return ImageGenerationResult(
                element_id=element.id,
                status="unreviewed",
                local_path=asset.local_path,
                attempts=[
                    ImageGenerationAttempt(
                        attempt_number=1, prompt_used=element.visual_description, outcome="success"
                    )
                ],
                final_prompt=element.visual_description,
            )
        except ImageGenerationError as e:
            logger.warning(f"Generation error for {element.id}: {e}")
            return ImageGenerationResult(
                element_id=element.id,
                status="failed",
                local_path="",
                attempts=[
                    ImageGenerationAttempt(
                        attempt_number=1,
                        prompt_used=element.visual_description,
                        outcome="error",
                        error_message=str(e),
                    )
                ],
                final_prompt=element.visual_description,
            )

    async def generate_with_variants(
        self, element: SharedElement, *, num_variants: int = 2, skip_review: bool = False
    ) -> ImageGenerationResult:
        """Generate multiple variants and use early-exit review strategy.
        Generates num_variants images in parallel, then reviews them one-by-one until
        one is accepted. Unused variants are cleaned up immediately.
        Args:
            element: The SharedElement to generate images for.
            num_variants: Number of variants to generate (default 2, max 4).
            skip_review: If True, skip review and return first variant (with warning).
        Returns:
            ImageGenerationResult with status and path.
        """
        if skip_review:
            logger.warning(f"skip_review + num_variants: using first variant for {element.id}")
            return await self._generate_without_review(element)
        num_variants = min(max(num_variants, 1), 4)
        logger.info(f"Generating {num_variants} variants for {element.id} with early-exit review")
        # Generate all variants in parallel
        variant_paths = await self.generator.generate_reference_image_variants(
            element, self.output_dir, num_variants
        )
        if not variant_paths:
            logger.warning(f"No variants generated for {element.id}")
            return ImageGenerationResult(
                element_id=element.id,
                status="failed",
                local_path="",
                attempts=[
                    ImageGenerationAttempt(
                        attempt_number=1,
                        prompt_used=element.visual_description,
                        outcome="error",
                        error_message="All variant generations failed",
                    )
                ],
                final_prompt=element.visual_description,
            )
        attempts: list[ImageGenerationAttempt] = []
        accepted_path: str = ""
        final_path = self.output_dir / f"{element.id}.png"
        # Review variants one-by-one (early exit on accept)
        for idx, vpath in enumerate(variant_paths):
            attempt_num = idx + 1
            try:
                with open(vpath, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")
                logger.info(
                    f"Reviewing variant {attempt_num}/{len(variant_paths)} for {element.id}"
                )
                async with _get_review_semaphore():
                    review_result = await review_image(
                        element_id=element.id,
                        element_type=element.element_type.value,
                        element_name=element.name,
                        visual_description=element.visual_description,
                        image_base64=image_data,
                    )
                if review_result.decision == ReviewDecision.ACCEPT:
                    logger.info(
                        f"Variant {attempt_num} accepted for {element.id}: {review_result.reasoning}"
                    )
                    attempts.append(
                        ImageGenerationAttempt(
                            attempt_number=attempt_num,
                            prompt_used=element.visual_description,
                            outcome="success",
                        )
                    )
                    accepted_path = vpath
                    break
                else:
                    logger.info(
                        f"Variant {attempt_num} rejected for {element.id}: {review_result.reasoning}"
                    )
                    attempts.append(
                        ImageGenerationAttempt(
                            attempt_number=attempt_num,
                            prompt_used=element.visual_description,
                            outcome="rejected",
                            rejection_reason=review_result.reasoning,
                        )
                    )
            except Exception as e:
                logger.warning(f"Error reviewing variant {attempt_num} for {element.id}: {e}")
                attempts.append(
                    ImageGenerationAttempt(
                        attempt_number=attempt_num,
                        prompt_used=element.visual_description,
                        outcome="error",
                        error_message=str(e),
                    )
                )
        # Determine which path to keep (accepted or last as fallback)
        keep_path = accepted_path
        if not keep_path and variant_paths:
            # Find last existing variant for fallback
            for vp in reversed(variant_paths):
                if Path(vp).exists():
                    keep_path = vp
                    break
        # Cleanup unused variants
        for vp in variant_paths:
            vp_path = Path(vp)
            if vp != keep_path and vp_path.exists():
                vp_path.unlink()
                logger.debug(f"Cleaned up unused variant: {vp}")
        if accepted_path:
            Path(accepted_path).rename(final_path)
            logger.info(f"Renamed accepted variant to: {final_path}")
            return ImageGenerationResult(
                element_id=element.id,
                status="success",
                local_path=str(final_path),
                attempts=attempts,
                final_prompt=element.visual_description,
            )
        # No variant accepted - use last as fallback
        if keep_path and Path(keep_path).exists():
            Path(keep_path).rename(final_path)
            logger.warning(f"Using last variant as fallback for {element.id}")
            return ImageGenerationResult(
                element_id=element.id,
                status="fallback",
                local_path=str(final_path),
                attempts=attempts,
                final_prompt=element.visual_description,
            )
        return ImageGenerationResult(
            element_id=element.id,
            status="failed",
            local_path="",
            attempts=attempts,
            final_prompt=element.visual_description,
        )

    async def generate_all_with_review(
        self,
        elements: list[SharedElement],
    ) -> list[ImageGenerationResult]:
        """Generate reference images for all elements with review.

        Processes elements sequentially to allow for proper review flow.

        Args:
            elements: List of SharedElements to generate images for.

        Returns:
            List of ImageGenerationResult for all elements.
        """
        results: list[ImageGenerationResult] = []

        for element in elements:
            result = await self.generate_with_review(element)
            results.append(result)

        # Log summary
        successful = sum(1 for r in results if r.status == "success")
        fallback = sum(1 for r in results if r.status == "fallback")
        failed = sum(1 for r in results if r.status == "failed")

        logger.info(
            f"Image production complete: {successful} accepted, "
            f"{fallback} fallback, {failed} failed (total: {len(elements)})"
        )

        return results

    async def generate_all_with_review_parallel(
        self,
        elements: list[SharedElement],
        max_concurrent: int = _IMAGE_GEN_MAX_CONCURRENT,
        on_complete: Callable[[str, ImageGenerationResult], None] | None = None,
        *,
        skip_review: bool = False,
        num_variants: int = 1,
    ) -> list[ImageGenerationResult]:
        """Generate reference images for all elements in parallel with review.
        Each element's full generate→review→retry cycle runs independently
        and concurrently, controlled by a semaphore.
        Args:
            elements: List of SharedElements to generate images for.
            max_concurrent: Maximum number of concurrent generations (default 8).
            on_complete: Optional callback called when each element completes.
                         Receives (element_id, result).
            skip_review: If True, skip quality review (status="unreviewed").
            num_variants: Number of variants per element (default 1). If >1, uses
                         early-exit review strategy. Max 4.
        Returns:
            List of ImageGenerationResult for all elements, in the same order
            as the input elements list.
        """
        if not elements:
            return []
        semaphore = asyncio.Semaphore(max_concurrent)
        results: dict[str, ImageGenerationResult] = {}
        use_variants = num_variants > 1

        async def generate_single(element: SharedElement) -> None:
            """Generate a single element with semaphore control."""
            async with semaphore:
                logger.info(f"Starting parallel generation for {element.id}")
                if use_variants:
                    result = await self.generate_with_variants(
                        element, num_variants=num_variants, skip_review=skip_review
                    )
                else:
                    result = await self.generate_with_review(element, skip_review=skip_review)
                results[element.id] = result
                if on_complete:
                    try:
                        on_complete(element.id, result)
                    except Exception as e:
                        logger.warning(f"on_complete callback error: {e}")

        # Create tasks for all elements
        tasks = [generate_single(element) for element in elements]

        # Run all tasks concurrently
        await asyncio.gather(*tasks)

        # Return results in original element order
        ordered_results = [results[element.id] for element in elements]

        # Log summary
        successful = sum(1 for r in ordered_results if r.status == "success")
        fallback = sum(1 for r in ordered_results if r.status == "fallback")
        failed = sum(1 for r in ordered_results if r.status == "failed")
        unreviewed = sum(1 for r in ordered_results if r.status == "unreviewed")
        if unreviewed:
            logger.info(
                f"Parallel image production complete: {unreviewed} unreviewed, {failed} failed (total: {len(elements)}, max_concurrent: {max_concurrent})"
            )
        else:
            logger.info(
                f"Parallel image production complete: {successful} accepted, {fallback} fallback, {failed} failed (total: {len(elements)}, max_concurrent: {max_concurrent})"
            )
        return ordered_results


async def generate_reference_images_with_review(
    elements: list[SharedElement],
    output_dir: Path,
    gemini_api_key: str,
    max_retries: int = MAX_RETRIES,
) -> list[ImageGenerationResult]:
    """Generate reference images for shared elements with quality review.

    This is a convenience function that creates an ImageProductionManager
    and generates all images with review.

    Args:
        elements: List of SharedElements to generate images for.
        output_dir: Directory to save generated images.
        gemini_api_key: API key for Gemini image generation.
        max_retries: Maximum number of retry attempts (default 2).

    Returns:
        List of ImageGenerationResult for all elements.
    """
    manager = ImageProductionManager(
        gemini_api_key=gemini_api_key,
        output_dir=output_dir,
        max_retries=max_retries,
    )
    return await manager.generate_all_with_review(elements)
