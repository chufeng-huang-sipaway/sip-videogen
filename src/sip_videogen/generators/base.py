"""Base classes and protocols for video generators.

This module defines the common interface for video generators,
allowing different providers (VEO, Kling, etc.) to be used interchangeably.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sip_videogen.models.assets import GeneratedAsset
    from sip_videogen.models.script import SceneAction, VideoScript


class VideoProvider(str, Enum):
    """Supported video generation providers."""

    VEO = "veo"
    KLING = "kling"


class VideoGenerationError(Exception):
    """Base exception for video generation errors."""

    pass


class PromptSafetyError(VideoGenerationError):
    """Raised when a prompt is rejected for safety/policy reasons."""

    pass


class ServiceAgentNotReadyError(VideoGenerationError):
    """Raised when the service is still being provisioned."""

    pass


class BaseVideoGenerator(ABC):
    """Abstract base class for video generators.

    All video generator implementations must inherit from this class
    and implement the required methods.
    """

    # Provider-specific constraints (to be overridden by subclasses)
    PROVIDER_NAME: str = "base"
    VALID_DURATIONS: list[int] = []
    MAX_REFERENCE_IMAGES: int = 0

    @abstractmethod
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
        """Generate a single video clip for a scene.

        Args:
            scene: The scene to generate video for.
            output_path: Output path (GCS URI for VEO, local dir for Kling).
            reference_images: Optional reference images for visual consistency.
            aspect_ratio: Video aspect ratio (e.g., "16:9", "9:16").
            generate_audio: Whether to generate audio.
            total_scenes: Total number of scenes for flow context.
            script: Full VideoScript for element lookups.
            signed_url_generator: Function to generate signed URLs (for Kling).

        Returns:
            GeneratedAsset with path to the generated video.

        Raises:
            VideoGenerationError: If generation fails.
            PromptSafetyError: If the prompt is rejected for safety reasons.
        """
        ...

    @abstractmethod
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
            output_path: Output path prefix (GCS URI for VEO, local dir for Kling).
            reference_images: Optional reference images for visual consistency.
            max_concurrent: Maximum concurrent generations.
            show_progress: Whether to show progress bar.
            signed_url_generator: Function to generate signed URLs (for Kling).

        Returns:
            List of GeneratedAssets for all successfully generated clips.

        Raises:
            VideoGenerationError: If generation fails for all scenes.
        """
        ...

    def map_duration(self, requested_seconds: int) -> int:
        """Map requested duration to the nearest valid duration for this provider.

        Args:
            requested_seconds: Requested duration in seconds.

        Returns:
            Valid duration for this provider.
        """
        if not self.VALID_DURATIONS:
            return requested_seconds

        # Find the nearest valid duration
        return min(self.VALID_DURATIONS, key=lambda d: abs(d - requested_seconds))
