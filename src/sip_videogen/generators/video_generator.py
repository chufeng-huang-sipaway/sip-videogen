"""VEO 3.1 Video Generator for creating video clips.

This module provides video generation functionality using Google's VEO 3.1 API
via Vertex AI to create video clips for each scene in the script.
"""

import time
from pathlib import Path

from google import genai
from google.genai.types import GenerateVideosConfig, Image, VideoGenerationReferenceImage
from tenacity import retry, stop_after_attempt, wait_exponential

from sip_videogen.config.logging import get_logger
from sip_videogen.models.assets import AssetType, GeneratedAsset
from sip_videogen.models.script import SceneAction

logger = get_logger(__name__)


class VideoGenerationError(Exception):
    """Raised when video generation fails."""

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
                    number_of_videos=1,
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

            # Check for errors
            if not operation.response:
                raise VideoGenerationError(
                    f"Video generation failed for scene {scene.scene_number}: "
                    "No response received"
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

        return ". ".join(parts)

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
