"""Video generation pipeline - non-interactive API for programmatic use.

This module provides a clean, non-interactive API for video generation
that can be called programmatically without CLI dependencies.

The pipeline orchestrates:
1. Script development via agent team (Showrunner)
2. Reference image generation with quality review
3. Video clip generation via provider (VEO, Kling, Sora)
4. Optional background music generation
5. Final assembly via FFmpeg

Example usage:
    from sip_studio.video import VideoPipeline, PipelineConfig

    config = PipelineConfig(
        idea="A cat playing piano in a jazz club",
        num_scenes=3,
    )
    pipeline = VideoPipeline(config)
    result = await pipeline.run()
    print(f"Video created: {result.final_video_path}")
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from sip_studio.agents import (
    AgentProgress,
    ImageProductionManager,
    develop_script,
)
from sip_studio.assembler import FFmpegAssembler, FFmpegError
from sip_studio.config.settings import get_settings
from sip_studio.config.user_preferences import UserPreferences
from sip_studio.generators import (
    MusicGenerationError,
    MusicGenerator,
    VideoGenerationError,
    VideoGeneratorFactory,
    VideoProvider,
)
from sip_studio.models import (
    AssetType,
    GeneratedAsset,
    GeneratedMusic,
    ProductionPackage,
    VideoScript,
)
from sip_studio.utils.file_utils import write_atomically

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Exception raised for pipeline-level errors."""


@dataclass
class PipelineConfig:
    """Configuration for the video generation pipeline.
    Attributes:
        idea: The video concept/idea to generate.
        num_scenes: Target number of scenes (default: 3).
        output_dir: Base output directory. If None, uses settings default.
        enable_music: Whether to generate background music (default: True).
        music_volume: Music volume level 0.0-1.0 (default: 0.4).
        provider: Video provider to use. If None, uses user preference.
        dry_run: If True, only generate script without video (default: False).
        existing_script: Pre-existing script to use (skips script development).
        project_id: Custom project ID. If None, auto-generated.
        image_max_concurrent: Max concurrent image generations (default: 8).
        skip_image_review: Skip image quality review for faster drafts (default: False).
        image_variants_per_request: Number of image variants per element (default: 1).
            If >1, generates multiple variants and uses early-exit review. Max 4.
    """

    idea: str
    num_scenes: int = 3
    output_dir: Path | None = None
    enable_music: bool = True
    music_volume: float = 0.4
    provider: VideoProvider | None = None
    dry_run: bool = False
    existing_script: VideoScript | None = None
    project_id: str | None = None
    image_max_concurrent: int = 8
    skip_image_review: bool = False
    image_variants_per_request: int = 1


@dataclass
class PipelineResult:
    """Result of a video generation pipeline run.

    Attributes:
        project_id: Unique identifier for this run.
        project_dir: Directory containing all generated assets.
        script: The generated or provided video script.
        reference_images: List of generated reference images.
        video_clips: List of generated video clips.
        music: Generated background music (if enabled).
        final_video_path: Path to the assembled final video (if not dry_run).
        stages_completed: List of completed stage names.
    """

    project_id: str
    project_dir: Path
    script: VideoScript
    reference_images: list[GeneratedAsset] = field(default_factory=list)
    video_clips: list[GeneratedAsset] = field(default_factory=list)
    music: GeneratedMusic | None = None
    final_video_path: Path | None = None
    stages_completed: list[str] = field(default_factory=list)


# Type alias for progress callbacks
ProgressCallback = Callable[[str, str], None]


class VideoPipeline:
    """Non-interactive video generation pipeline.

    Orchestrates the full video generation workflow:
    1. Script development (via Showrunner agent team)
    2. Reference image generation (via ImageProductionManager)
    3. Video clip generation (via selected provider)
    4. Background music generation (optional)
    5. Final assembly (via FFmpeg)

    Example:
        config = PipelineConfig(idea="A day in the life of a robot")
        pipeline = VideoPipeline(config)

        # Optional: register progress callback
        pipeline.on_progress = lambda stage, msg: print(f"[{stage}] {msg}")

        result = await pipeline.run()
    """

    def __init__(self, config: PipelineConfig):
        """Initialize the video pipeline.

        Args:
            config: Pipeline configuration.
        """
        self.config = config
        self.settings = get_settings()
        self.on_progress: ProgressCallback | None = None
        self._package: ProductionPackage | None = None

    def _emit_progress(self, stage: str, message: str) -> None:
        """Emit a progress update if callback is registered."""
        logger.info("[%s] %s", stage, message)
        if self.on_progress:
            self.on_progress(stage, message)

    async def run(self) -> PipelineResult:
        """Run the full video generation pipeline.

        Returns:
            PipelineResult with all generated assets and paths.

        Raises:
            PipelineError: If a critical stage fails.
            VideoGenerationError: If video generation fails.
            FFmpegError: If video assembly fails.
        """
        # Generate project ID
        project_id = self.config.project_id or self._generate_project_id()

        # Setup output directory
        output_dir = self.config.output_dir or self.settings.ensure_output_dir()
        project_dir = output_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Starting pipeline run: %s", project_id)
        self._emit_progress("init", f"Starting pipeline in {project_dir}")

        stages_completed: list[str] = []

        # Stage 1: Script development
        script = await self._develop_script()
        stages_completed.append("script_development")

        # Save script atomically
        script_path = project_dir / "script.json"
        write_atomically(script_path, script.model_dump_json(indent=2))
        self._emit_progress("script", f"Script saved to {script_path}")

        # Early return for dry run
        if self.config.dry_run:
            self._emit_progress("complete", "Dry run complete - script only")
            return PipelineResult(
                project_id=project_id,
                project_dir=project_dir,
                script=script,
                stages_completed=stages_completed,
            )

        # Stage 2: Reference images
        reference_images = await self._generate_reference_images(
            script=script,
            output_dir=project_dir / "reference_images",
        )
        stages_completed.append("reference_images")

        # Stage 3: Video clips
        video_clips = await self._generate_video_clips(
            script=script,
            reference_images=reference_images,
            output_dir=project_dir / "clips",
        )
        stages_completed.append("video_clips")

        # Stage 4: Background music (optional)
        music: GeneratedMusic | None = None
        if self.config.enable_music and script.music_brief:
            music = await self._generate_music(
                script=script,
                output_dir=project_dir / "music",
            )
            if music:
                stages_completed.append("music")

        # Stage 5: Assembly
        final_video_path = await self._assemble_video(
            script=script,
            video_clips=video_clips,
            music=music,
            output_dir=project_dir,
        )
        stages_completed.append("assembly")

        self._emit_progress("complete", f"Pipeline complete: {final_video_path}")

        return PipelineResult(
            project_id=project_id,
            project_dir=project_dir,
            script=script,
            reference_images=reference_images,
            video_clips=video_clips,
            music=music,
            final_video_path=final_video_path,
            stages_completed=stages_completed,
        )

    async def _develop_script(self) -> VideoScript:
        """Develop video script via agent team.

        Returns:
            Generated VideoScript.

        Raises:
            PipelineError: If script development fails.
        """
        if self.config.existing_script:
            self._emit_progress("script", "Using provided script")
            return self.config.existing_script

        self._emit_progress("script", "Developing script via agent team...")

        def on_agent_progress(progress: AgentProgress) -> None:
            """Forward agent progress to pipeline progress."""
            self._emit_progress("script", f"[{progress.event_type}] {progress.message}")

        try:
            script = await develop_script(
                self.config.idea,
                self.config.num_scenes,
                progress_callback=on_agent_progress,
            )
            self._emit_progress("script", f"Script developed: {script.title}")
            return script
        except Exception as e:
            raise PipelineError(f"Script development failed: {e}") from e

    async def _generate_reference_images(
        self,
        script: VideoScript,
        output_dir: Path,
    ) -> list[GeneratedAsset]:
        """Generate reference images for shared elements.

        Args:
            script: Video script with shared elements.
            output_dir: Directory to save images.

        Returns:
            List of generated image assets.
        """
        if not script.shared_elements:
            self._emit_progress("images", "No shared elements - skipping images")
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        self._emit_progress(
            "images",
            f"Generating {len(script.shared_elements)} reference images...",
        )

        image_production = ImageProductionManager(
            gemini_api_key=self.settings.gemini_api_key,
            output_dir=output_dir,
            max_retries=2,
        )

        generated_assets: list[GeneratedAsset] = []

        def on_complete(element_id: str, result) -> None:
            status = "✓" if result.status in ("success", "fallback", "unreviewed") else "✗"
            self._emit_progress("images", f"{status} {element_id}")

        results = await image_production.generate_all_with_review_parallel(
            elements=script.shared_elements,
            max_concurrent=self.config.image_max_concurrent,
            on_complete=on_complete,
            skip_review=self.config.skip_image_review,
            num_variants=self.config.image_variants_per_request,
        )
        for result in results:
            if result.status in ("success", "fallback", "unreviewed"):
                asset = GeneratedAsset(
                    asset_type=AssetType.REFERENCE_IMAGE,
                    element_id=result.element_id,
                    local_path=result.local_path,
                )
                generated_assets.append(asset)

        self._emit_progress(
            "images",
            f"Generated {len(generated_assets)}/{len(script.shared_elements)} images",
        )
        return generated_assets

    async def _generate_video_clips(
        self,
        script: VideoScript,
        reference_images: list[GeneratedAsset],
        output_dir: Path,
    ) -> list[GeneratedAsset]:
        """Generate video clips for each scene.

        Args:
            script: Video script with scenes.
            reference_images: Reference images for visual consistency.
            output_dir: Directory to save video clips.

        Returns:
            List of generated video clip assets.

        Raises:
            VideoGenerationError: If video generation fails.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine provider
        prefs = UserPreferences.load()
        provider = self.config.provider or prefs.default_video_provider

        self._emit_progress("video", f"Using {provider.value} video generator")

        video_generator = VideoGeneratorFactory.create(provider)

        # Generate clips
        self._emit_progress("video", f"Generating {len(script.scenes)} video clips...")

        if provider == VideoProvider.VEO:
            video_clips = await video_generator.generate_all_video_clips(
                script=script,
                output_dir=str(output_dir),
                reference_images=reference_images,
                show_progress=False,  # We handle progress ourselves
            )
        else:
            # Non-VEO providers may not support reference images
            if reference_images:
                logger.warning(
                    "Reference images not fully supported for %s",
                    provider.value,
                )
            video_clips = await video_generator.generate_all_video_clips(
                script=script,
                output_dir=str(output_dir),
                reference_images=None,
                show_progress=False,
            )

        if not video_clips:
            raise VideoGenerationError("No video clips were generated")

        self._emit_progress(
            "video",
            f"Generated {len(video_clips)}/{len(script.scenes)} clips",
        )
        return video_clips

    async def _generate_music(
        self,
        script: VideoScript,
        output_dir: Path,
    ) -> GeneratedMusic | None:
        """Generate background music for the video.

        Args:
            script: Video script with music brief.
            output_dir: Directory to save music file.

        Returns:
            Generated music or None if generation fails/skipped.
        """
        if not script.music_brief:
            self._emit_progress("music", "No music brief - skipping")
            return None

        if not self.settings.google_cloud_project:
            self._emit_progress(
                "music",
                "GOOGLE_CLOUD_PROJECT not set - skipping music",
            )
            return None

        output_dir.mkdir(parents=True, exist_ok=True)

        mood = script.music_brief.mood.value
        genre = script.music_brief.genre.value
        self._emit_progress("music", f"Generating {mood} {genre} music...")

        try:
            music_generator = MusicGenerator(
                project_id=self.settings.google_cloud_project,
                location="us-central1",
            )
            generated_music = await music_generator.generate(
                brief=script.music_brief,
                output_dir=output_dir,
            )
            self._emit_progress(
                "music",
                f"Generated music: {generated_music.duration_seconds:.0f}s",
            )
            return generated_music
        except MusicGenerationError as e:
            logger.warning("Music generation failed: %s", e)
            self._emit_progress("music", f"Music generation failed: {e}")
            return None

    async def _assemble_video(
        self,
        script: VideoScript,
        video_clips: list[GeneratedAsset],
        music: GeneratedMusic | None,
        output_dir: Path,
    ) -> Path:
        """Assemble video clips into final video.

        Args:
            script: Video script for naming.
            video_clips: Video clips to concatenate.
            music: Optional background music to overlay.
            output_dir: Directory to save final video.

        Returns:
            Path to the final assembled video.

        Raises:
            FFmpegError: If assembly fails.
            PipelineError: If no clips available.
        """
        clips_with_paths = [c for c in video_clips if c.local_path]
        if not clips_with_paths:
            raise PipelineError("No clips available for assembly")

        self._emit_progress("assembly", f"Assembling {len(clips_with_paths)} clips...")

        try:
            assembler = FFmpegAssembler()
        except FFmpegError as e:
            raise PipelineError(f"FFmpeg not available: {e}") from e

        # Sort clips by scene number
        clip_paths = sorted(
            [Path(c.local_path) for c in clips_with_paths],
            key=lambda p: int(p.stem.split("_")[-1]) if "_" in p.stem else 0,
        )

        # Generate output filename
        safe_title = script.title.replace(" ", "_").lower()[:50]
        final_video_path = output_dir / f"{safe_title}_final.mp4"

        if music:
            self._emit_progress("assembly", "Assembling with background music...")
            assembler.assemble_with_music(
                clip_paths=clip_paths,
                music=music,
                output_path=final_video_path,
                music_volume=self.config.music_volume,
            )
        else:
            self._emit_progress("assembly", "Concatenating clips...")
            assembler.concatenate_clips(clip_paths, final_video_path)

        self._emit_progress("assembly", f"Final video: {final_video_path}")
        return final_video_path

    @staticmethod
    def _generate_project_id() -> str:
        """Generate a unique project identifier."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = uuid.uuid4().hex[:8]
        return f"sip_{timestamp}_{suffix}"


# Convenience function for simple usage
async def generate_video(
    idea: str,
    num_scenes: int = 3,
    output_dir: Path | None = None,
    enable_music: bool = True,
    dry_run: bool = False,
    provider: VideoProvider | None = None,
) -> PipelineResult:
    """Convenience function to generate a video from an idea.

    This is a simple wrapper around VideoPipeline for quick usage.

    Args:
        idea: The video concept/idea.
        num_scenes: Target number of scenes.
        output_dir: Output directory (uses default if None).
        enable_music: Whether to generate background music.
        dry_run: If True, only generate script.
        provider: Video provider to use.

    Returns:
        PipelineResult with all generated assets.

    Example:
        result = await generate_video("A sunset over the ocean")
        print(f"Video: {result.final_video_path}")
    """
    config = PipelineConfig(
        idea=idea,
        num_scenes=num_scenes,
        output_dir=output_dir,
        enable_music=enable_music,
        dry_run=dry_run,
        provider=provider,
    )
    pipeline = VideoPipeline(config)
    return await pipeline.run()
