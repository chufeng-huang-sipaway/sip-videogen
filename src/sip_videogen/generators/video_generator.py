"""VEO 3.1 Video Generator for creating video clips.

This module provides video generation functionality using Google's VEO 3.1 API
via Vertex AI to create video clips for each scene in the script.
"""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai.types import GenerateVideosConfig, Image, VideoGenerationReferenceImage
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from sip_videogen.config.logging import get_logger
from sip_videogen.models.assets import AssetType, GeneratedAsset
from sip_videogen.models.script import SceneAction, VideoScript

logger = get_logger(__name__)


class VideoGenerationError(Exception):
    """Raised when video generation fails."""

    pass


class PromptSafetyError(VideoGenerationError):
    """Raised when Vertex AI rejects a prompt for safety/policy reasons."""

    pass


class ServiceAgentNotReadyError(VideoGenerationError):
    """Raised when Vertex AI service agents are still being provisioned."""

    pass


class VideoGenerator:
    """Generates video clips using Google VEO 3.1 via Vertex AI.

    This class handles the generation of video clips for each scene,
    optionally using reference images for visual consistency.
    """

    # VEO 3.1 constraints
    MAX_REFERENCE_IMAGES = 3
    VALID_DURATIONS = [4, 6, 8]
    FORCED_DURATION_WITH_REFS = 8  # VEO forces 8s when using reference images
    POLL_INTERVAL_SECONDS = 15

    def __init__(
        self,
        project: str,
        location: str = "us-central1",
        model: str = "veo-3.1-generate-preview",
    ):
        """Initialize the video generator with Vertex AI.

        Args:
            project: Google Cloud project ID.
            location: Google Cloud region. Defaults to us-central1.
            model: Model to use for video generation. Defaults to veo-3.1-generate-preview.
        """
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        self.model = model
        self.project = project
        self.location = location
        logger.debug(
            f"Initialized VideoGenerator with model: {model}, "
            f"project: {project}, location: {location}"
        )

    @retry(
        retry=retry_if_exception(lambda e: not isinstance(e, PromptSafetyError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    async def generate_video_clip(
        self,
        scene: SceneAction,
        output_gcs_uri: str,
        reference_images: list[GeneratedAsset] | None = None,
        aspect_ratio: str = "16:9",
        generate_audio: bool = True,
    ) -> GeneratedAsset:
        """Generate a video clip for a scene.

        Args:
            scene: The SceneAction to generate a video for.
            output_gcs_uri: GCS URI prefix for output (e.g., gs://bucket/prefix).
            reference_images: Optional list of reference images for visual consistency.
                             Maximum 3 images allowed.
            aspect_ratio: Video aspect ratio. Defaults to 16:9. Options: 16:9, 9:16.
            generate_audio: Whether to generate audio. Defaults to True.

        Returns:
            GeneratedAsset with the GCS URI to the generated video.

        Raises:
            VideoGenerationError: If video generation fails after retries.
        """
        logger.info(f"Generating video clip for scene {scene.scene_number}")

        # Build reference image configs (max 3)
        ref_configs = None
        if reference_images:
            ref_configs = self._build_reference_configs(reference_images)
            logger.debug(f"Using {len(ref_configs)} reference images")

        # Determine duration (forced to 8s when using reference images)
        duration = self._get_duration(scene, has_references=bool(ref_configs))

        # Build the prompt
        prompt = self._build_prompt(scene)
        logger.debug(f"Video prompt: {prompt}")

        try:
            # Start video generation
            operation = self.client.models.generate_videos(
                model=self.model,
                prompt=prompt,
                config=GenerateVideosConfig(
                    reference_images=ref_configs,
                    duration_seconds=duration,
                    aspect_ratio=aspect_ratio,
                    output_gcs_uri=output_gcs_uri,
                    generate_audio=generate_audio,
                    person_generation="allow_adult",
                ),
            )

            logger.info(
                f"Started video generation for scene {scene.scene_number}, "
                f"polling for completion..."
            )

            # Poll for completion
            while not operation.done:
                time.sleep(self.POLL_INTERVAL_SECONDS)
                operation = self.client.operations.get(operation)
                logger.debug(f"Scene {scene.scene_number} generation in progress...")

            # Check for errors in the operation
            if hasattr(operation, 'error') and operation.error:
                error_raw = operation.error
                error_msg = str(error_raw)
                logger.error(f"VEO operation error: {error_msg}")

                # Try to infer an error code from the error object or message
                error_code = getattr(error_raw, "code", None)
                if error_code is None:
                    if "'code': 3" in error_msg or '"code": 3' in error_msg:
                        error_code = 3
                    elif "'code': 9" in error_msg or '"code": 9' in error_msg:
                        error_code = 9

                # Prompt/policy violation – do not retry
                if error_code == 3 or "usage guidelines" in error_msg:
                    raise PromptSafetyError(
                        "Vertex AI rejected the prompt because it may violate "
                        "usage guidelines (for example, real-person names, brands, "
                        "or other sensitive terms). Please simplify or anonymize "
                        f"the description for scene {scene.scene_number}. "
                        f"Raw error: {error_msg}"
                    )

                # Service agents not ready – advise user to wait and retry CLI later
                if error_code == 9 or "Service agents are being provisioned" in error_msg:
                    raise ServiceAgentNotReadyError(
                        "Vertex AI service agents for your project are still being "
                        "provisioned and cannot read from Cloud Storage yet. "
                        "Wait a few minutes after enabling Vertex AI and try again. "
                        f"Raw error: {error_msg}"
                    )

                raise VideoGenerationError(
                    f"Video generation failed for scene {scene.scene_number}: {error_msg}"
                )

            # Check for response
            if not operation.response:
                # Try to get more details
                details = ""
                if hasattr(operation, 'metadata'):
                    details = f" Metadata: {operation.metadata}"
                raise VideoGenerationError(
                    f"Video generation failed for scene {scene.scene_number}: "
                    f"No response received.{details}"
                )

            # Extract video URI
            video_uri = operation.result.generated_videos[0].video.uri
            logger.info(
                f"Video clip for scene {scene.scene_number} generated: {video_uri}"
            )

            return GeneratedAsset(
                asset_type=AssetType.VIDEO_CLIP,
                scene_number=scene.scene_number,
                local_path="",  # Will be set after download
                gcs_uri=video_uri,
            )

        except (PromptSafetyError, ServiceAgentNotReadyError):
            # Already logged with specific guidance, just propagate
            raise
        except Exception as e:
            logger.error(f"Failed to generate video for scene {scene.scene_number}: {e}")
            raise VideoGenerationError(
                f"Failed to generate video clip for scene {scene.scene_number}: {e}"
            ) from e

    def _build_reference_configs(
        self,
        reference_images: list[GeneratedAsset],
    ) -> list[VideoGenerationReferenceImage]:
        """Build reference image configurations for VEO.

        Args:
            reference_images: List of GeneratedAssets with GCS URIs.

        Returns:
            List of VideoGenerationReferenceImage configs.
        """
        configs = []
        for asset in reference_images[: self.MAX_REFERENCE_IMAGES]:
            if not asset.gcs_uri:
                logger.warning(
                    f"Skipping reference image {asset.element_id}: no GCS URI"
                )
                continue

            # Determine mime type from path
            mime_type = self._get_mime_type(asset.gcs_uri)

            configs.append(
                VideoGenerationReferenceImage(
                    image=Image(
                        gcs_uri=asset.gcs_uri,
                        mime_type=mime_type,
                    ),
                    reference_type="asset",  # VEO 3.1 only supports "asset"
                )
            )

        return configs

    def _build_prompt(self, scene: SceneAction) -> str:
        """Build a generation prompt from scene details.

        Args:
            scene: The SceneAction to build a prompt for.

        Returns:
            A detailed prompt string for video generation.
        """
        parts = []

        # Add setting context
        if scene.setting_description:
            parts.append(f"Setting: {scene.setting_description}")

        # Add the main action (most important)
        parts.append(scene.action_description)

        # Add camera direction if specified
        if scene.camera_direction:
            parts.append(f"Camera: {scene.camera_direction}")

        # Add dialogue context if present
        if scene.dialogue:
            parts.append(f"Dialogue: {scene.dialogue}")

        raw_prompt = ". ".join(parts)
        return self._sanitize_prompt_for_vertex(raw_prompt)

    def _sanitize_prompt_for_vertex(self, prompt: str) -> str:
        """Sanitize prompts to better align with Vertex AI usage guidelines.

        This avoids directly naming real public figures or specific brands in
        the prompts sent to the video model by replacing them with more
        generic descriptors. This helps reduce prompt rejections while
        keeping the creative intent.
        """
        sanitized = prompt

        replacements = {
            # Public figures – replace with generic descriptors
            "Elon Musk": "a charismatic tech spokesperson",
            "Elon": "the charismatic tech spokesperson",
            # Brand names – replace with generic location descriptions
            "Dunkin’ Donuts": "a popular neon-lit donut shop",
            "Dunkin' Donuts": "a popular neon-lit donut shop",
        }

        for original, replacement in replacements.items():
            if original in sanitized:
                logger.debug(
                    f"Sanitizing prompt for Vertex AI: replacing '{original}' "
                    f"with '{replacement}'"
                )
                sanitized = sanitized.replace(original, replacement)

        return sanitized

    def _get_duration(self, scene: SceneAction, has_references: bool) -> int:
        """Get the video duration, respecting VEO constraints.

        Args:
            scene: The SceneAction with requested duration.
            has_references: Whether reference images are being used.

        Returns:
            Duration in seconds (4, 6, or 8).
        """
        if has_references:
            # VEO forces 8 seconds when using reference images
            return self.FORCED_DURATION_WITH_REFS

        # Validate and normalize to nearest valid duration
        requested = scene.duration_seconds
        if requested in self.VALID_DURATIONS:
            return requested

        # Find nearest valid duration
        nearest = min(self.VALID_DURATIONS, key=lambda x: abs(x - requested))
        logger.debug(
            f"Adjusted duration from {requested}s to {nearest}s "
            f"(valid: {self.VALID_DURATIONS})"
        )
        return nearest

    def _get_mime_type(self, path: str) -> str:
        """Determine mime type from file path.

        Args:
            path: File path or GCS URI.

        Returns:
            MIME type string.
        """
        path_lower = path.lower()
        if path_lower.endswith(".png"):
            return "image/png"
        elif path_lower.endswith(".jpg") or path_lower.endswith(".jpeg"):
            return "image/jpeg"
        elif path_lower.endswith(".webp"):
            return "image/webp"
        else:
            # Default to PNG for unknown
            return "image/png"

    async def generate_all_video_clips(
        self,
        script: VideoScript,
        output_gcs_prefix: str,
        reference_images: list[GeneratedAsset] | None = None,
        max_concurrent: int = 3,
        inter_request_delay: float = 2.0,
        show_progress: bool = True,
    ) -> list[GeneratedAsset]:
        """Generate video clips for all scenes in parallel with progress tracking.

        This method generates video clips for all scenes in the script,
        managing concurrency and rate limits while displaying progress.

        Args:
            script: The VideoScript containing scenes to generate videos for.
            output_gcs_prefix: GCS URI prefix for outputs (e.g., gs://bucket/project).
            reference_images: Optional list of reference images for visual consistency.
            max_concurrent: Maximum number of concurrent video generations. Defaults to 3.
            inter_request_delay: Delay in seconds between starting new requests. Defaults to 2.0.
            show_progress: Whether to display a Rich progress bar. Defaults to True.

        Returns:
            List of GeneratedAssets for all successfully generated video clips,
            sorted by scene number.
        """
        scenes = script.scenes
        if not scenes:
            logger.warning("No scenes to generate video clips for")
            return []

        logger.info(
            f"Starting parallel video generation for {len(scenes)} scenes "
            f"(max concurrent: {max_concurrent})"
        )

        # Build a mapping of scene elements to reference images
        scene_references = self._build_scene_reference_map(script, reference_images)

        # Create results container
        results: list[GeneratedAsset | None] = [None] * len(scenes)
        errors: list[tuple[int, Exception]] = []

        # Semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(
            idx: int,
            scene: SceneAction,
            progress: Progress | None,
            task_id: TaskID | None,
        ) -> None:
            """Generate a single video clip with semaphore control."""
            async with semaphore:
                # Add delay between requests to respect rate limits
                if idx > 0:
                    await asyncio.sleep(inter_request_delay)

                try:
                    # Get reference images for this scene
                    scene_refs = scene_references.get(scene.scene_number, [])

                    # Generate GCS output URI for this scene
                    scene_output_uri = f"{output_gcs_prefix}/scene_{scene.scene_number:03d}"

                    result = await self.generate_video_clip(
                        scene=scene,
                        output_gcs_uri=scene_output_uri,
                        reference_images=scene_refs,
                    )
                    results[idx] = result

                    if progress and task_id is not None:
                        progress.update(
                            task_id,
                            advance=1,
                            description=f"[green]Scene {scene.scene_number} ✓",
                        )

                except Exception as e:
                    errors.append((scene.scene_number, e))
                    logger.error(f"Failed to generate video for scene {scene.scene_number}: {e}")

                    if progress and task_id is not None:
                        progress.update(
                            task_id,
                            advance=1,
                            description=f"[red]Scene {scene.scene_number} ✗",
                        )

        if show_progress:
            # Use Rich progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
            ) as progress:
                task_id = progress.add_task(
                    "[cyan]Generating videos...",
                    total=len(scenes),
                )

                # Create all tasks
                tasks = [
                    generate_with_semaphore(idx, scene, progress, task_id)
                    for idx, scene in enumerate(scenes)
                ]

                # Run all tasks concurrently
                await asyncio.gather(*tasks)
        else:
            # No progress bar
            tasks = [
                generate_with_semaphore(idx, scene, None, None)
                for idx, scene in enumerate(scenes)
            ]
            await asyncio.gather(*tasks)

        # Filter out None results and sort by scene number
        successful_results = [r for r in results if r is not None]
        successful_results.sort(key=lambda x: x.scene_number or 0)

        logger.info(
            f"Video generation complete: {len(successful_results)}/{len(scenes)} clips generated"
        )

        if errors:
            logger.warning(f"Failed scenes: {[e[0] for e in errors]}")

        return successful_results

    def _build_scene_reference_map(
        self,
        script: VideoScript,
        reference_images: list[GeneratedAsset] | None,
    ) -> dict[int, list[GeneratedAsset]]:
        """Build a mapping of scene numbers to their reference images.

        Args:
            script: The VideoScript with scene and element information.
            reference_images: List of generated reference image assets.

        Returns:
            Dictionary mapping scene numbers to lists of relevant reference images.
        """
        if not reference_images:
            return {}

        # Build element ID to reference image mapping
        element_to_ref: dict[str, GeneratedAsset] = {}
        for ref in reference_images:
            if ref.element_id:
                element_to_ref[ref.element_id] = ref

        # Build scene to reference images mapping
        scene_refs: dict[int, list[GeneratedAsset]] = {}
        for scene in script.scenes:
            refs = []
            for element_id in scene.shared_element_ids:
                if element_id in element_to_ref:
                    refs.append(element_to_ref[element_id])

            # Limit to MAX_REFERENCE_IMAGES per scene
            if refs:
                scene_refs[scene.scene_number] = refs[: self.MAX_REFERENCE_IMAGES]

        return scene_refs


@dataclass
class VideoGenerationResult:
    """Result of parallel video generation."""

    successful: list[GeneratedAsset]
    failed_scenes: list[int]
    total_scenes: int

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_scenes == 0:
            return 0.0
        return len(self.successful) / self.total_scenes * 100

    @property
    def all_succeeded(self) -> bool:
        """Check if all scenes were generated successfully."""
        return len(self.successful) == self.total_scenes
