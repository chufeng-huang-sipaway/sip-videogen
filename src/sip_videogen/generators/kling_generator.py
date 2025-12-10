"""Kling AI Video Generator for creating video clips.

This module provides video generation functionality using Kling AI's official API
to create video clips for each scene in the script.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx
from pydantic import BaseModel, Field
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn

from sip_videogen.generators.base import (
    BaseVideoGenerator,
    PromptSafetyError,
    VideoGenerationError,
)
from sip_videogen.models.assets import AssetType, GeneratedAsset
from sip_videogen.models.script import SceneAction, VideoScript

logger = logging.getLogger(__name__)


class KlingConfig(BaseModel):
    """Configuration for Kling AI video generation."""

    model_version: str = Field(
        default="1.6",
        description=(
            "Kling model version: 1.0, 1.5, 1.6, 2.0, 2.1, 2.1-master, 2.5 "
            "(Note: 2.0 and 2.1-master require pro mode)"
        ),
    )
    mode: str = Field(
        default="std",
        description="Generation mode: 'std' (standard, faster) or 'pro' (higher quality)",
    )
    camera_control: dict | None = Field(
        default=None,
        description="Optional camera control parameters",
    )


@dataclass
class KlingGenerationResult:
    """Result of Kling video generation for multiple scenes."""

    successful: list[GeneratedAsset]
    failed_scenes: list[int]
    total_scenes: int

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        return len(self.successful) / self.total_scenes * 100 if self.total_scenes > 0 else 0.0

    @property
    def all_succeeded(self) -> bool:
        """Check if all scenes were generated successfully."""
        return len(self.failed_scenes) == 0


class KlingVideoGenerator(BaseVideoGenerator):
    """Generates video clips using Kling AI API.

    This class handles the generation of video clips for each scene,
    optionally using reference images for visual consistency.
    """

    PROVIDER_NAME = "kling"
    VALID_DURATIONS = [5, 10]
    MAX_REFERENCE_IMAGES = 1  # Kling supports 1 image for image-to-video
    # Official Kling API v1 base URL (supports all models including 2.6 with audio)
    API_BASE_URL = "https://api.klingai.com/v1"
    POLL_INTERVAL_SECONDS = 10
    MAX_POLL_TIME_SECONDS = 600  # 10 minutes max wait per video

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        config: KlingConfig | None = None,
    ):
        """Initialize the Kling video generator.

        Args:
            access_key: Kling API access key.
            secret_key: Kling API secret key.
            config: Optional Kling-specific configuration.
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.config = config or KlingConfig()
        self._client: httpx.AsyncClient | None = None

        logger.debug(
            "Initialized KlingVideoGenerator with model: %s, mode: %s",
            self.config.model_version,
            self.config.mode,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _generate_jwt_token(self) -> str:
        """Generate JWT token for Kling API authentication.

        Returns:
            JWT token string.
        """
        import jwt

        now = int(time.time())
        payload = {
            "iss": self.access_key,
            "exp": now + 1800,  # 30 minutes
            "nbf": now - 5,  # Allow 5 seconds clock skew
        }

        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def _get_headers(self) -> dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self._generate_jwt_token()}",
            "Content-Type": "application/json",
        }

    def map_duration(self, requested_seconds: int) -> int:
        """Map requested duration to nearest Kling-supported duration.

        Args:
            requested_seconds: Requested duration in seconds.

        Returns:
            5 or 10 seconds (Kling's supported durations).
        """
        # Kling only supports 5 or 10 seconds
        if requested_seconds <= 7:
            return 5
        return 10

    async def generate_video_clip(
        self,
        scene: SceneAction,
        output_path: str,
        reference_images: list[GeneratedAsset] | None = None,
        aspect_ratio: str = "16:9",
        generate_audio: bool = True,
        total_scenes: int | None = None,
        script: VideoScript | None = None,
        signed_url_generator: Callable[[str], str] | None = None,
    ) -> GeneratedAsset:
        """Generate a video clip using Kling API.

        Args:
            scene: The scene to generate video for.
            output_path: Local directory to save downloaded video.
            reference_images: Optional reference images (will use signed URLs).
            aspect_ratio: Video aspect ratio (e.g., "16:9", "9:16", "1:1").
            generate_audio: Whether to generate audio (Kling always includes audio).
            total_scenes: Total number of scenes for flow context.
            script: Full VideoScript for element lookups.
            signed_url_generator: Function to generate signed URLs from GCS URIs.

        Returns:
            GeneratedAsset with path to the generated video.

        Raises:
            VideoGenerationError: If generation fails.
            PromptSafetyError: If the prompt is rejected for safety reasons.
        """
        prompt = self._build_prompt(scene, total_scenes, reference_images, script)
        duration = self.map_duration(scene.duration_seconds)

        logger.info(
            "Generating video for scene %d with Kling (duration: %ds, mode: %s)",
            scene.scene_number,
            duration,
            self.config.mode,
        )

        # Build request payload and endpoint
        endpoint, payload, _ = self._build_request_payload(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            reference_images=reference_images,
            signed_url_generator=signed_url_generator,
        )

        # Submit generation request to v1 API
        client = await self._get_client()
        response = await client.post(
            endpoint,
            headers=self._get_headers(),
            json=payload,
        )

        if response.status_code != 200:
            self._handle_error_response(response, scene.scene_number)

        task_data = response.json()
        task_id = (
            task_data.get("data", {}).get("task_id")
            if isinstance(task_data, dict)
            else None
        )
        if not task_id:
            task_id = task_data.get("task_id") if isinstance(task_data, dict) else None

        if not task_id:
            raise VideoGenerationError(
                f"No task_id in Kling response for scene {scene.scene_number}"
            )

        logger.debug("Kling task created: %s for scene %d", task_id, scene.scene_number)

        # Poll for completion
        video_url = await self._poll_for_completion(task_id, scene.scene_number)

        # Download video from CDN
        local_path = await self._download_video(
            video_url, output_path, scene.scene_number
        )

        return GeneratedAsset(
            asset_type=AssetType.VIDEO_CLIP,
            scene_number=scene.scene_number,
            local_path=str(local_path),
            gcs_uri=None,  # Kling videos are downloaded locally
        )

    def _build_request_payload(
        self,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        reference_images: list[GeneratedAsset] | None = None,
        signed_url_generator: Callable[[str], str] | None = None,
    ) -> tuple[str, dict, list[str]]:
        """Build the request payload and endpoint for Kling API.

        All models use the v1 API endpoint.

        Returns:
            (endpoint, payload, candidate_paths) tuple. candidate_paths is empty
            as we only use the v1 endpoint.
        """
        model_name = self._resolve_model_name(self.config.model_version)
        logger.info("Kling model_name resolved to: %s", model_name)

        # Build payload - all models use the same v1 structure
        payload: dict = {
            "model_name": model_name,
            "prompt": prompt,
            "mode": self.config.mode,  # std or pro
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
            "cfg_scale": 0.5,  # Default creativity vs prompt adherence
        }

        image_url = self._get_image_url(reference_images, signed_url_generator)
        if image_url:
            payload["image"] = image_url
            logger.debug("Using image-to-video mode with reference image")

        if self.config.camera_control:
            payload["camera_control"] = self.config.camera_control

        endpoint = f"{self.API_BASE_URL}/videos/text2video"
        return endpoint, payload, []

    def _resolve_model_name(self, version: str) -> str:
        """Map friendly version strings to Kling API model names.

        Supported models (official API at api.klingai.com):
        - kling-v1, kling-v1-5, kling-v1-6
        - kling-v2-master (pro mode only)
        - kling-v2-1, kling-v2-1-master (pro mode only)
        - kling-v2-5-turbo (2.5 turbo, use mode="pro" for pro quality)
        - kling-v2.6 (2.6 with native audio)
        """
        if not version:
            return "kling-v1-6"

        normalized = version.strip().lower()
        normalized = normalized.replace("kling-", "")
        normalized = normalized.replace("_", "-")
        if normalized.startswith("v"):
            normalized = normalized[1:]

        # Version 2.6 (latest with native audio)
        if normalized in {"2.6", "2-6", "v2.6", "v2-6"}:
            return "kling-v2.6"

        # Version 2.5 (turbo) - use mode="pro" in request body for pro quality
        if normalized in {"2.5-turbo", "2-5-turbo", "v2.5-turbo", "v2-5-turbo", "2.5", "2-5"}:
            return "kling-v2-5-turbo"

        # Version 2.1
        if normalized in {"2.1-master", "2-1-master"}:
            return "kling-v2-1-master"
        if normalized in {"2.1", "2-1"}:
            return "kling-v2-1"

        # Version 2.0
        if normalized in {"2.0-master", "2-0-master", "2-master"}:
            return "kling-v2-master"
        if normalized in {"2.0", "2", "2-0"}:
            return "kling-v2"

        # Version 1.x
        if normalized in {"1.6", "1-6"}:
            return "kling-v1-6"
        if normalized in {"1.5", "1-5"}:
            return "kling-v1-5"
        if normalized in {"1.0", "1", "1-0"}:
            return "kling-v1"

        # Fallback to v1.6 (most stable)
        logger.warning("Unknown Kling version '%s', falling back to kling-v1-6", version)
        return "kling-v1-6"

    def _get_image_url(
        self,
        reference_images: list[GeneratedAsset] | None,
        signed_url_generator: Callable[[str], str] | None,
    ) -> str | None:
        """Get a publicly accessible URL for the reference image.

        Tries multiple strategies:
        1. Use signed URL generator if available
        2. Use local_path to read and upload (future)
        3. Skip if no viable option

        Args:
            reference_images: Optional reference images.
            signed_url_generator: Function to generate signed URLs.

        Returns:
            Public URL string, or None if unavailable.
        """
        if not reference_images:
            return None

        ref_image = reference_images[0]  # Kling supports 1 reference image

        # Try signed URL first
        if ref_image.gcs_uri and signed_url_generator:
            try:
                return signed_url_generator(ref_image.gcs_uri)
            except Exception as e:
                logger.warning("Failed to generate signed URL for reference image: %s", e)

        # If local path exists, we could upload directly to Kling in the future
        # For now, skip and use text-to-video
        if ref_image.local_path:
            logger.info(
                "Reference image has local path but no signed URL - "
                "falling back to text-to-video mode"
            )

        return None

    async def _poll_for_completion(self, task_id: str, scene_number: int) -> str:
        """Poll Kling API until video generation completes.

        Args:
            task_id: The Kling task ID.
            scene_number: Scene number for logging.

        Returns:
            URL of the generated video.

        Raises:
            VideoGenerationError: If generation fails or times out.
        """
        client = await self._get_client()
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.MAX_POLL_TIME_SECONDS:
                raise VideoGenerationError(
                    f"Kling generation timed out for scene {scene_number} "
                    f"after {self.MAX_POLL_TIME_SECONDS}s"
                )

            response = await client.get(
                f"{self.API_BASE_URL}/videos/text2video/{task_id}",
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                logger.warning(
                    "Kling status check failed for scene %d: %s",
                    scene_number,
                    response.text,
                )
                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
                continue

            data = response.json()
            task_status = data.get("data", {}).get("task_status", "")

            if task_status == "succeed":
                videos = data.get("data", {}).get("task_result", {}).get("videos", [])
                if videos and "url" in videos[0]:
                    return videos[0]["url"]
                raise VideoGenerationError(
                    f"No video URL in Kling success response for scene {scene_number}"
                )

            elif task_status == "failed":
                error_msg = data.get("data", {}).get("task_status_msg", "Unknown error")
                raise VideoGenerationError(
                    f"Kling generation failed for scene {scene_number}: {error_msg}"
                )

            logger.debug(
                "Scene %d status: %s (%.0fs elapsed)",
                scene_number,
                task_status,
                elapsed,
            )
            await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

    async def _download_video(
        self,
        url: str,
        output_dir: str,
        scene_number: int,
    ) -> Path:
        """Download video from Kling CDN.

        Args:
            url: URL of the video to download.
            output_dir: Local directory to save the video.
            scene_number: Scene number for filename.

        Returns:
            Path to the downloaded video file.

        Raises:
            VideoGenerationError: If download fails.
        """
        output_path = Path(output_dir) / f"scene_{scene_number:03d}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        client = await self._get_client()

        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            output_path.write_bytes(response.content)
            logger.info("Downloaded video for scene %d to %s", scene_number, output_path)
            return output_path

        except httpx.HTTPError as e:
            raise VideoGenerationError(
                f"Failed to download video for scene {scene_number}: {e}"
            ) from e

    def _handle_error_response(
        self,
        response: httpx.Response,
        scene_number: int,
    ) -> None:
        """Handle API error responses.

        Args:
            response: The HTTP response.
            scene_number: Scene number for error context.

        Raises:
            PromptSafetyError: If the prompt was rejected for safety reasons.
            VideoGenerationError: For other errors.
        """
        try:
            error_text = response.text
            try:
                error_data = response.json()
            except Exception:
                error_data = {}

            error_code = (
                error_data.get("code")
                or error_data.get("error_code")
                or error_data.get("statusCode")
            )
            error_msg = (
                error_data.get("message")
                or error_data.get("error_message")
                or error_data.get("msg")
                or "Unknown error"
            )

            # Check for content policy violations
            # Kling error codes for content violations (approximate - adjust based on actual API)
            safety_error_codes = [1004, 1005, 1006, 1007]
            if error_code in safety_error_codes:
                raise PromptSafetyError(
                    f"Kling rejected prompt for scene {scene_number}: {error_msg}"
                )

            raise VideoGenerationError(
                f"Kling API error for scene {scene_number} "
                f"(code {error_code}): {error_msg}. Raw response: {error_text}"
            )

        except (KeyError, ValueError):
            raise VideoGenerationError(
                f"Kling API error for scene {scene_number}: "
                f"HTTP {response.status_code} - {response.text}"
            )

    def _build_prompt(
        self,
        scene: SceneAction,
        total_scenes: int | None = None,
        reference_images: list[GeneratedAsset] | None = None,
        script: VideoScript | None = None,
    ) -> str:
        """Build a generation prompt from scene details.

        Args:
            scene: The SceneAction to build a prompt for.
            total_scenes: Total number of scenes in the video (for flow context).
            reference_images: Optional reference images (not used in prompt for Kling).
            script: Optional VideoScript for element lookups.

        Returns:
            A detailed prompt string for video generation.
        """
        parts = []

        # Add scene flow context for continuity
        flow_context = self._build_flow_context(scene, total_scenes)
        if flow_context:
            parts.append(flow_context)

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
            parts.append(f"Dialogue: \"{scene.dialogue}\"")

        # Kling has a 2500 character limit
        prompt = ". ".join(parts)
        if len(prompt) > 2500:
            prompt = prompt[:2497] + "..."

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
        output_path: str,
        reference_images: list[GeneratedAsset] | None = None,
        max_concurrent: int = 3,
        show_progress: bool = True,
        signed_url_generator: Callable[[str], str] | None = None,
    ) -> list[GeneratedAsset]:
        """Generate video clips for all scenes in the script.

        Args:
            script: The VideoScript containing all scenes.
            output_path: Local directory to save videos.
            reference_images: Optional reference images for visual consistency.
            max_concurrent: Maximum concurrent generations (Kling limit is typically 5).
            show_progress: Whether to show progress bar.
            signed_url_generator: Function to generate signed URLs from GCS URIs.

        Returns:
            List of GeneratedAssets for all successfully generated clips.
        """
        scenes = script.scenes
        total_scenes = len(scenes)
        results: list[GeneratedAsset] = []
        failed_scenes: list[int] = []

        # Build scene-to-reference-image mapping
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
                        output_path=output_path,
                        reference_images=refs,
                        total_scenes=total_scenes,
                        script=script,
                        signed_url_generator=signed_url_generator,
                    )
                    if progress and task_id is not None:
                        progress.update(task_id, advance=1)
                    return asset

                except Exception as e:
                    logger.error("Failed to generate video for scene %d: %s", scene.scene_number, e)
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
                    f"[cyan]Generating {total_scenes} video clips (Kling)...",
                    total=total_scenes,
                )

                tasks = [
                    generate_with_semaphore(scene, task_id, progress)
                    for scene in scenes
                ]
                generated = await asyncio.gather(*tasks)

        else:
            tasks = [
                generate_with_semaphore(scene, None, None)
                for scene in scenes
            ]
            generated = await asyncio.gather(*tasks)

        # Filter out None results (failed generations)
        results = [asset for asset in generated if asset is not None]

        # Sort by scene number
        results.sort(key=lambda a: a.scene_number or 0)

        logger.info(
            "Kling generation complete: %d/%d successful",
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

        For Kling, we use at most 1 reference image per scene.

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
            img.element_id: img
            for img in reference_images
            if img.element_id
        }

        # Build scene to references mapping
        scene_refs: dict[int, list[GeneratedAsset]] = {}

        for scene in script.scenes:
            refs_for_scene = []
            for element_id in scene.shared_element_ids:
                if element_id in element_to_image:
                    refs_for_scene.append(element_to_image[element_id])
                    # Kling only supports 1 reference image
                    break

            if refs_for_scene:
                scene_refs[scene.scene_number] = refs_for_scene

        return scene_refs
