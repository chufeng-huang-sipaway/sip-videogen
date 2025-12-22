"""OpenAI Sora 2 Video Generator for creating video clips.

This module provides video generation functionality using OpenAI's Sora 2 API
to create video clips for each scene in the script.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from sip_videogen.generators.base import (
    BaseVideoGenerator,
    PromptSafetyError,
    VideoGenerationError,
)
from sip_videogen.generators.prompt_builder import (
    DEFAULT_MAX_PROMPT_CHARS,
    build_structured_scene_prompt,
)
from sip_videogen.models.assets import AssetType, GeneratedAsset
from sip_videogen.models.script import SceneAction, VideoScript

logger = logging.getLogger(__name__)


class SoraConfig(BaseModel):
    """Configuration for Sora video generation."""

    model: str = Field(
        default="sora-2",
        description="Sora model: 'sora-2' (faster, cheaper) or 'sora-2-pro' (higher quality)",
    )
    resolution: str = Field(
        default="1080p",
        description="Video resolution: '720p' (1280x720) or '1080p' (1920x1080)",
    )


@dataclass
class SoraGenerationResult:
    """Result of Sora video generation for multiple scenes."""

    successful: list[GeneratedAsset]
    failed_scenes: list[int]
    total_scenes: int

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        return (
            len(self.successful) / self.total_scenes * 100
            if self.total_scenes > 0
            else 0.0
        )

    @property
    def all_succeeded(self) -> bool:
        """Check if all scenes were generated successfully."""
        return len(self.failed_scenes) == 0


class SoraVideoGenerator(BaseVideoGenerator):
    """Generates video clips using OpenAI Sora 2 API.

    This class handles the generation of video clips for each scene,
    optionally using a reference image as the first frame.
    """

    PROVIDER_NAME = "sora"
    VALID_DURATIONS = [4, 8, 12]  # Sora supports 4, 8, or 12 seconds
    MAX_REFERENCE_IMAGES = 1  # Sora supports 1 image (acts as first frame)
    POLL_INTERVAL_SECONDS = 10
    MAX_POLL_TIME_SECONDS = 600  # 10 minutes max wait per video

    # Resolution mappings - Sora only supports specific sizes:
    # 720x1280, 1280x720, 1024x1792, 1792x1024
    RESOLUTION_MAP_LANDSCAPE = {
        "720p": "1280x720",
        "1080p": "1792x1024",  # Closest to 1080p landscape
    }
    RESOLUTION_MAP_PORTRAIT = {
        "720p": "720x1280",
        "1080p": "1024x1792",  # Closest to 1080p portrait
    }

    def __init__(
        self,
        api_key: str,
        config: SoraConfig | None = None,
    ):
        """Initialize the Sora video generator.

        Args:
            api_key: OpenAI API key.
            config: Optional Sora-specific configuration.
        """
        self.api_key = api_key
        self.config = config or SoraConfig()
        self._client: AsyncOpenAI | None = None

        logger.debug(
            "Initialized SoraVideoGenerator with model: %s, resolution: %s",
            self.config.model,
            self.config.resolution,
        )

    async def _get_client(self) -> AsyncOpenAI:
        """Get or create the async OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def close(self) -> None:
        """Close the client (cleanup)."""
        if self._client:
            await self._client.close()
            self._client = None

    def _map_aspect_ratio_to_size(self, aspect_ratio: str) -> str:
        """Map aspect ratio to Sora size parameter.

        Sora only supports: 720x1280, 1280x720, 1024x1792, 1792x1024

        Args:
            aspect_ratio: Aspect ratio string (e.g., "16:9", "9:16").

        Returns:
            Size string for Sora API.
        """
        resolution = self.config.resolution

        if aspect_ratio == "9:16":  # Portrait
            return self.RESOLUTION_MAP_PORTRAIT.get(resolution, "720x1280")
        else:  # 16:9 landscape (default)
            return self.RESOLUTION_MAP_LANDSCAPE.get(resolution, "1280x720")

    def map_duration(self, requested_seconds: int) -> int:
        """Map requested duration to nearest Sora-supported duration.

        Args:
            requested_seconds: Requested duration in seconds.

        Returns:
            4, 8, or 12 seconds (Sora's supported durations).
        """
        # Sora supports 4, 8, or 12 seconds
        if requested_seconds <= 6:
            return 4
        elif requested_seconds <= 10:
            return 8
        return 12

    async def generate_video_clip(
        self,
        scene: SceneAction,
        output_dir: str,
        reference_images: list[GeneratedAsset] | None = None,
        aspect_ratio: str = "16:9",
        generate_audio: bool = True,
        total_scenes: int | None = None,
        script: VideoScript | None = None,
        constraints_context: str | None = None,
    ) -> GeneratedAsset:
        """Generate a video clip using Sora API.

        Args:
            scene: The scene to generate video for.
            output_dir: Local directory to save downloaded video.
            reference_images: Optional reference images (max 1, acts as first frame).
            aspect_ratio: Video aspect ratio (e.g., "16:9", "9:16").
            generate_audio: Whether to generate audio (Sora includes audio).
            total_scenes: Total number of scenes for flow context.
            script: Full VideoScript for element lookups.
            constraints_context: Optional constraints block to append to the prompt.

        Returns:
            GeneratedAsset with path to the generated video.

        Raises:
            VideoGenerationError: If generation fails.
            PromptSafetyError: If the prompt is rejected for safety reasons.
        """
        prompt = self._build_prompt(
            scene, total_scenes, reference_images, script, constraints_context
        )
        duration = self.map_duration(scene.duration_seconds)
        size = self._map_aspect_ratio_to_size(aspect_ratio)

        logger.info(
            "Generating video for scene %d with Sora (model: %s, duration: %ds, size: %s)",
            scene.scene_number,
            self.config.model,
            duration,
            size,
        )

        client = await self._get_client()

        try:
            # Use create_and_poll which handles polling automatically
            # Parameters: prompt (str), model, seconds (str like "4"), size
            video = await client.videos.create_and_poll(
                prompt=prompt,
                model=self.config.model,
                seconds=str(duration),  # Must be "4", "8", or "12"
                size=size,
            )

            # Check if generation succeeded
            if video.status != "completed":
                error_msg = video.error.message if video.error else "Unknown error"
                raise VideoGenerationError(
                    f"Sora generation failed for scene {scene.scene_number}: {error_msg}"
                )

            # Download the video content using the video ID
            local_path = await self._download_video_by_id(
                client, video.id, output_dir, scene.scene_number
            )

            return GeneratedAsset(
                asset_type=AssetType.VIDEO_CLIP,
                scene_number=scene.scene_number,
                local_path=str(local_path),
                gcs_uri=None,
            )

        except Exception as e:
            error_msg = str(e).lower()

            # Check for safety/policy violations
            if any(
                term in error_msg
                for term in ["safety", "policy", "content", "moderation", "rejected"]
            ):
                raise PromptSafetyError(
                    f"Sora rejected prompt for scene {scene.scene_number}: {e}"
                ) from e

            # Check for access errors
            if any(term in error_msg for term in ["access", "permission", "unauthorized"]):
                raise VideoGenerationError(
                    f"Sora API access error for scene {scene.scene_number}. "
                    "Ensure you have API access to Sora 2. "
                    "Visit platform.openai.com to verify your access. "
                    f"Original error: {e}"
                ) from e

            raise VideoGenerationError(
                f"Sora generation failed for scene {scene.scene_number}: {e}"
            ) from e

    async def _download_video_by_id(
        self,
        client: AsyncOpenAI,
        video_id: str,
        output_dir: str,
        scene_number: int,
    ) -> Path:
        """Download video content using the OpenAI API.

        Args:
            client: OpenAI async client.
            video_id: The Sora video ID.
            output_dir: Local directory to save the video.
            scene_number: Scene number for filename.

        Returns:
            Path to the downloaded video file.

        Raises:
            VideoGenerationError: If download fails.
        """
        output_path = Path(output_dir) / f"scene_{scene_number:03d}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Use the SDK's download_content method
            response = await client.videos.download_content(video_id)

            # Write the video content to file
            output_path.write_bytes(response.content)
            logger.info(
                "Downloaded video for scene %d to %s", scene_number, output_path
            )
            return output_path

        except Exception as e:
            raise VideoGenerationError(
                f"Failed to download video for scene {scene_number}: {e}"
            ) from e

    def _build_prompt(
        self,
        scene: SceneAction,
        total_scenes: int | None = None,
        reference_images: list[GeneratedAsset] | None = None,
        script: VideoScript | None = None,
        constraints_context: str | None = None,
    ) -> str:
        """Build a generation prompt from scene details.

        Args:
            scene: The SceneAction to build a prompt for.
            total_scenes: Total number of scenes in the video (for flow context).
            reference_images: Optional reference images (not used in prompt for Sora).
            script: Optional VideoScript for element lookups.
            constraints_context: Optional constraints block to append to the prompt.

        Returns:
            A detailed prompt string for video generation.
        """
        flow_context = self._build_flow_context(scene, total_scenes)

        prompt = build_structured_scene_prompt(
            scene=scene,
            script=script,
            flow_context=flow_context,
            reference_context=None,  # Sora uses first-frame image, not text reference
            audio_instruction=None,  # Sora always generates audio
            constraints_context=constraints_context,
            max_length=DEFAULT_MAX_PROMPT_CHARS,
        )

        return prompt

    def _build_flow_context(
        self,
        scene: SceneAction,
        total_scenes: int | None,
    ) -> str | None:
        """Build scene flow context for continuity between clips.

        Args:
            scene: The SceneAction being processed.
            total_scenes: Total number of scenes in the video sequence.

        Returns:
            Flow context string, or None if context cannot be determined.
        """
        if total_scenes is None or total_scenes <= 1:
            return None

        scene_num = scene.scene_number
        is_first = scene_num == 1
        is_last = scene_num == total_scenes

        if is_first:
            return (
                f"Scene {scene_num}/{total_scenes}: Opening scene. "
                "End with action continuing into the next scene"
            )
        elif is_last:
            return (
                f"Scene {scene_num}/{total_scenes}: Final scene. "
                "Begin mid-action, natural conclusion appropriate"
            )
        else:
            return (
                f"Scene {scene_num}/{total_scenes}: Middle scene. "
                "Seamless flow - begin and end mid-action"
            )

    async def generate_all_video_clips(
        self,
        script: VideoScript,
        output_dir: str,
        reference_images: list[GeneratedAsset] | None = None,
        max_concurrent: int = 3,
        show_progress: bool = True,
    ) -> list[GeneratedAsset]:
        """Generate video clips for all scenes in the script.

        Args:
            script: The VideoScript containing all scenes.
            output_dir: Local directory to save videos.
            reference_images: Optional reference images (Sora uses max 1 per scene).
            max_concurrent: Maximum concurrent generations.
            show_progress: Whether to show progress bar.

        Returns:
            List of GeneratedAssets for all successfully generated clips.
        """
        scenes = script.scenes
        total_scenes = len(scenes)
        results: list[GeneratedAsset] = []
        failed_scenes: list[int] = []

        # Build scene-to-reference-image mapping (Sora uses max 1 per scene)
        scene_refs = self._build_scene_reference_map(script, reference_images)

        # Semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(
            scene: SceneAction,
            task_id: TaskID | None,
            progress: Progress | None,
        ) -> GeneratedAsset | None:
            async with semaphore:
                try:
                    refs = scene_refs.get(scene.scene_number, [])
                    asset = await self.generate_video_clip(
                        scene=scene,
                        output_dir=output_dir,
                        reference_images=refs,
                        total_scenes=total_scenes,
                        script=script,
                    )
                    if progress and task_id is not None:
                        progress.update(task_id, advance=1)
                    return asset

                except Exception as e:
                    logger.error(
                        "Failed to generate video for scene %d: %s",
                        scene.scene_number,
                        e,
                    )
                    failed_scenes.append(scene.scene_number)
                    if progress and task_id is not None:
                        progress.update(task_id, advance=1)
                    return None

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task_id = progress.add_task(
                    f"[cyan]Generating {total_scenes} video clips (Sora)...",
                    total=total_scenes,
                )

                tasks = [
                    generate_with_semaphore(scene, task_id, progress)
                    for scene in scenes
                ]
                generated = await asyncio.gather(*tasks)

        else:
            tasks = [
                generate_with_semaphore(scene, None, None) for scene in scenes
            ]
            generated = await asyncio.gather(*tasks)

        # Filter out None results (failed generations)
        results = [asset for asset in generated if asset is not None]

        # Sort by scene number
        results.sort(key=lambda a: a.scene_number or 0)

        logger.info(
            "Sora generation complete: %d/%d successful",
            len(results),
            total_scenes,
        )

        if failed_scenes:
            logger.warning("Failed scenes: %s", failed_scenes)

        return results

    def _build_scene_reference_map(
        self,
        script: VideoScript,
        reference_images: list[GeneratedAsset] | None,
    ) -> dict[int, list[GeneratedAsset]]:
        """Build a mapping of scene numbers to their reference images.

        For Sora, we use at most 1 reference image per scene (acts as first frame).

        Args:
            script: The VideoScript with scene definitions.
            reference_images: List of all reference images.

        Returns:
            Dict mapping scene_number to list of reference images.
        """
        if not reference_images:
            return {}

        # Build element_id to image mapping
        element_to_image = {
            img.element_id: img for img in reference_images if img.element_id
        }

        # Build scene to references mapping
        scene_refs: dict[int, list[GeneratedAsset]] = {}

        for scene in script.scenes:
            refs_for_scene = []
            for element_id in scene.shared_element_ids:
                if element_id in element_to_image:
                    refs_for_scene.append(element_to_image[element_id])
                    # Sora only supports 1 reference image
                    break

            if refs_for_scene:
                scene_refs[scene.scene_number] = refs_for_scene

        return scene_refs
