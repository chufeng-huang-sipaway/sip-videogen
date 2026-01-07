"""Tests for video generation pipeline API."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_studio.generators import VideoProvider
from sip_studio.models.assets import AssetType, GeneratedAsset
from sip_studio.models.music import GeneratedMusic
from sip_studio.models.script import VideoScript
from sip_studio.video import (
    PipelineConfig,
    PipelineError,
    PipelineResult,
    VideoPipeline,
    generate_video,
)


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_default_values(self) -> None:
        """Test PipelineConfig has sensible defaults."""
        config = PipelineConfig(idea="Test idea")

        assert config.idea == "Test idea"
        assert config.num_scenes == 3
        assert config.output_dir is None
        assert config.enable_music is True
        assert config.music_volume == 0.4
        assert config.provider is None
        assert config.dry_run is False
        assert config.existing_script is None
        assert config.project_id is None

    def test_custom_values(self, sample_video_script: VideoScript) -> None:
        """Test PipelineConfig accepts custom values."""
        config = PipelineConfig(
            idea="Custom idea",
            num_scenes=5,
            output_dir=Path("/custom/path"),
            enable_music=False,
            music_volume=0.8,
            provider=VideoProvider.KLING,
            dry_run=True,
            existing_script=sample_video_script,
            project_id="custom_project_123",
        )

        assert config.idea == "Custom idea"
        assert config.num_scenes == 5
        assert config.output_dir == Path("/custom/path")
        assert config.enable_music is False
        assert config.music_volume == 0.8
        assert config.provider == VideoProvider.KLING
        assert config.dry_run is True
        assert config.existing_script == sample_video_script
        assert config.project_id == "custom_project_123"


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_minimal_result(self, sample_video_script: VideoScript, tmp_path: Path) -> None:
        """Test PipelineResult with minimal fields."""
        result = PipelineResult(
            project_id="test_123",
            project_dir=tmp_path,
            script=sample_video_script,
        )

        assert result.project_id == "test_123"
        assert result.project_dir == tmp_path
        assert result.script == sample_video_script
        assert result.reference_images == []
        assert result.video_clips == []
        assert result.music is None
        assert result.final_video_path is None
        assert result.stages_completed == []

    def test_full_result(
        self,
        sample_video_script: VideoScript,
        sample_reference_image_asset: GeneratedAsset,
        sample_video_clip_asset: GeneratedAsset,
        tmp_path: Path,
    ) -> None:
        """Test PipelineResult with all fields populated."""
        mock_music = MagicMock(spec=GeneratedMusic)
        mock_music.duration_seconds = 30.0

        result = PipelineResult(
            project_id="test_456",
            project_dir=tmp_path,
            script=sample_video_script,
            reference_images=[sample_reference_image_asset],
            video_clips=[sample_video_clip_asset],
            music=mock_music,
            final_video_path=tmp_path / "final.mp4",
            stages_completed=["script_development", "reference_images", "video_clips", "assembly"],
        )

        assert len(result.reference_images) == 1
        assert len(result.video_clips) == 1
        assert result.music is not None
        assert result.final_video_path == tmp_path / "final.mp4"
        assert len(result.stages_completed) == 4


class TestVideoPipeline:
    """Tests for VideoPipeline class."""

    def test_init(self) -> None:
        """Test VideoPipeline initialization."""
        config = PipelineConfig(idea="Test idea")
        pipeline = VideoPipeline(config)

        assert pipeline.config == config
        assert pipeline.on_progress is None

    def test_progress_callback(self) -> None:
        """Test progress callback registration."""
        config = PipelineConfig(idea="Test idea")
        pipeline = VideoPipeline(config)

        progress_events: list[tuple[str, str]] = []

        def on_progress(stage: str, message: str) -> None:
            progress_events.append((stage, message))

        pipeline.on_progress = on_progress
        pipeline._emit_progress("test_stage", "Test message")

        assert len(progress_events) == 1
        assert progress_events[0] == ("test_stage", "Test message")

    def test_generate_project_id(self) -> None:
        """Test project ID generation."""
        project_id = VideoPipeline._generate_project_id()

        assert project_id.startswith("sip_")
        assert len(project_id) > 20  # timestamp + uuid
        # Format: sip_YYYYMMDD_HHMMSS_xxxxxxxx
        parts = project_id.split("_")
        assert len(parts) == 4

    @pytest.mark.asyncio
    async def test_dry_run_returns_script_only(
        self,
        sample_video_script: VideoScript,
        tmp_path: Path,
    ) -> None:
        """Test dry run mode returns script without generating video."""
        config = PipelineConfig(
            idea="Test idea",
            existing_script=sample_video_script,
            dry_run=True,
            output_dir=tmp_path,
        )
        pipeline = VideoPipeline(config)

        result = await pipeline.run()

        assert result.script == sample_video_script
        assert result.stages_completed == ["script_development"]
        assert result.reference_images == []
        assert result.video_clips == []
        assert result.final_video_path is None

        # Verify script was saved
        script_files = list(tmp_path.rglob("script.json"))
        assert len(script_files) == 1

    @pytest.mark.asyncio
    async def test_uses_existing_script(
        self,
        sample_video_script: VideoScript,
        tmp_path: Path,
    ) -> None:
        """Test pipeline uses existing script when provided."""
        config = PipelineConfig(
            idea="This idea should be ignored",
            existing_script=sample_video_script,
            dry_run=True,
            output_dir=tmp_path,
        )
        pipeline = VideoPipeline(config)

        result = await pipeline.run()

        # Should use the provided script, not develop a new one
        assert result.script.title == sample_video_script.title
        assert result.script.logline == sample_video_script.logline

    @pytest.mark.asyncio
    async def test_custom_project_id(
        self,
        sample_video_script: VideoScript,
        tmp_path: Path,
    ) -> None:
        """Test custom project ID is used."""
        config = PipelineConfig(
            idea="Test",
            existing_script=sample_video_script,
            dry_run=True,
            output_dir=tmp_path,
            project_id="my_custom_project",
        )
        pipeline = VideoPipeline(config)

        result = await pipeline.run()

        assert result.project_id == "my_custom_project"
        assert result.project_dir == tmp_path / "my_custom_project"

    @pytest.mark.asyncio
    async def test_script_development_error_raises_pipeline_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that script development failures raise PipelineError."""
        config = PipelineConfig(
            idea="Test idea",
            output_dir=tmp_path,
            dry_run=True,
        )
        pipeline = VideoPipeline(config)

        with patch(
            "sip_studio.video.pipeline.develop_script",
            new_callable=AsyncMock,
        ) as mock_develop:
            mock_develop.side_effect = Exception("Script development failed")

            with pytest.raises(PipelineError) as exc_info:
                await pipeline.run()

            assert "Script development failed" in str(exc_info.value)


class TestVideoPipelineFullRun:
    """Tests for full pipeline execution with mocks."""

    @pytest.mark.asyncio
    async def test_happy_path_with_mocks(
        self,
        sample_video_script: VideoScript,
        tmp_path: Path,
    ) -> None:
        """Test full pipeline run with all stages mocked."""
        config = PipelineConfig(
            idea="Test idea",
            existing_script=sample_video_script,
            output_dir=tmp_path,
            enable_music=False,  # Disable music for simpler test
        )
        pipeline = VideoPipeline(config)

        # Track progress events
        progress_events: list[tuple[str, str]] = []
        pipeline.on_progress = lambda stage, msg: progress_events.append((stage, msg))

        # Mock reference image generation
        mock_ref_image = GeneratedAsset(
            asset_type=AssetType.REFERENCE_IMAGE,
            element_id="char_protagonist",
            local_path=str(tmp_path / "ref_char.png"),
        )

        # Mock video clip
        mock_clip = GeneratedAsset(
            asset_type=AssetType.VIDEO_CLIP,
            scene_number=1,
            local_path=str(tmp_path / "scene_001.mp4"),
        )

        # Create actual files so assembly works
        (tmp_path / "ref_char.png").write_bytes(b"fake png")
        (tmp_path / "scene_001.mp4").write_bytes(b"fake mp4")

        with (
            patch.object(
                pipeline,
                "_generate_reference_images",
                new_callable=AsyncMock,
            ) as mock_gen_images,
            patch.object(
                pipeline,
                "_generate_video_clips",
                new_callable=AsyncMock,
            ) as mock_gen_clips,
            patch.object(
                pipeline,
                "_assemble_video",
                new_callable=AsyncMock,
            ) as mock_assemble,
        ):
            mock_gen_images.return_value = [mock_ref_image]
            mock_gen_clips.return_value = [mock_clip]
            mock_assemble.return_value = tmp_path / "final.mp4"

            result = await pipeline.run()

            # Verify result
            assert result.script == sample_video_script
            assert len(result.reference_images) == 1
            assert len(result.video_clips) == 1
            assert result.final_video_path == tmp_path / "final.mp4"
            assert "script_development" in result.stages_completed
            assert "reference_images" in result.stages_completed
            assert "video_clips" in result.stages_completed
            assert "assembly" in result.stages_completed

            # Verify methods were called
            mock_gen_images.assert_called_once()
            mock_gen_clips.assert_called_once()
            mock_assemble.assert_called_once()

        # Verify progress was emitted
        stages = [event[0] for event in progress_events]
        assert "init" in stages
        assert "script" in stages


class TestVideoGeneratorFactoryIntegration:
    """Tests for VideoGeneratorFactory usage in pipeline."""

    @pytest.mark.asyncio
    async def test_provider_selection_veo(
        self,
        sample_video_script: VideoScript,
        tmp_path: Path,
    ) -> None:
        """Test VEO provider is selected and used correctly."""
        # Modify script to have no shared elements (skip ref images)
        sample_video_script.shared_elements = []

        config = PipelineConfig(
            idea="Test idea",
            existing_script=sample_video_script,
            output_dir=tmp_path,
            provider=VideoProvider.VEO,
            enable_music=False,
        )
        pipeline = VideoPipeline(config)

        mock_generator = MagicMock()
        mock_generator.generate_all_video_clips = AsyncMock(return_value=[])

        with (
            patch(
                "sip_studio.video.pipeline.VideoGeneratorFactory.create",
                return_value=mock_generator,
            ) as mock_factory,
            patch.object(
                pipeline,
                "_assemble_video",
                new_callable=AsyncMock,
            ) as mock_assemble,
        ):
            # VideoGenerationError when no clips generated
            from sip_studio.generators import VideoGenerationError

            mock_generator.generate_all_video_clips.side_effect = VideoGenerationError("Test error")

            with pytest.raises(VideoGenerationError):
                await pipeline.run()

            # Verify factory was called with VEO provider
            mock_factory.assert_called_once_with(VideoProvider.VEO)

    @pytest.mark.asyncio
    async def test_provider_selection_kling(
        self,
        sample_video_script: VideoScript,
        tmp_path: Path,
    ) -> None:
        """Test Kling provider is selected correctly."""
        sample_video_script.shared_elements = []

        config = PipelineConfig(
            idea="Test idea",
            existing_script=sample_video_script,
            output_dir=tmp_path,
            provider=VideoProvider.KLING,
            enable_music=False,
        )
        pipeline = VideoPipeline(config)

        mock_generator = MagicMock()
        mock_generator.generate_all_video_clips = AsyncMock(return_value=[])

        with (
            patch(
                "sip_studio.video.pipeline.VideoGeneratorFactory.create",
                return_value=mock_generator,
            ) as mock_factory,
            patch(
                "sip_studio.video.pipeline.UserPreferences.load",
            ),
        ):
            from sip_studio.generators import VideoGenerationError

            mock_generator.generate_all_video_clips.side_effect = VideoGenerationError("Test error")

            with pytest.raises(VideoGenerationError):
                await pipeline.run()

            mock_factory.assert_called_once_with(VideoProvider.KLING)

    @pytest.mark.asyncio
    async def test_provider_from_user_preferences(
        self,
        sample_video_script: VideoScript,
        tmp_path: Path,
    ) -> None:
        """Test provider is loaded from user preferences when not specified."""
        sample_video_script.shared_elements = []

        config = PipelineConfig(
            idea="Test idea",
            existing_script=sample_video_script,
            output_dir=tmp_path,
            provider=None,  # Not specified - should use preferences
            enable_music=False,
        )
        pipeline = VideoPipeline(config)

        mock_generator = MagicMock()
        mock_generator.generate_all_video_clips = AsyncMock(return_value=[])

        mock_prefs = MagicMock()
        mock_prefs.default_video_provider = VideoProvider.SORA

        with (
            patch(
                "sip_studio.video.pipeline.VideoGeneratorFactory.create",
                return_value=mock_generator,
            ) as mock_factory,
            patch(
                "sip_studio.video.pipeline.UserPreferences.load",
                return_value=mock_prefs,
            ),
        ):
            from sip_studio.generators import VideoGenerationError

            mock_generator.generate_all_video_clips.side_effect = VideoGenerationError("Test error")

            with pytest.raises(VideoGenerationError):
                await pipeline.run()

            # Should use SORA from preferences
            mock_factory.assert_called_once_with(VideoProvider.SORA)


class TestGenerateVideoConvenience:
    """Tests for the generate_video convenience function."""

    @pytest.mark.asyncio
    async def test_generate_video_creates_pipeline(
        self,
        sample_video_script: VideoScript,
        tmp_path: Path,
    ) -> None:
        """Test generate_video convenience function."""
        with patch("sip_studio.video.pipeline.VideoPipeline") as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.run = AsyncMock(
                return_value=PipelineResult(
                    project_id="test",
                    project_dir=tmp_path,
                    script=sample_video_script,
                )
            )
            mock_pipeline_class.return_value = mock_pipeline

            result = await generate_video(
                idea="Test idea",
                num_scenes=5,
                output_dir=tmp_path,
                enable_music=False,
                dry_run=True,
                provider=VideoProvider.VEO,
            )

            # Verify pipeline was created with correct config
            call_args = mock_pipeline_class.call_args
            config = call_args[0][0]
            assert config.idea == "Test idea"
            assert config.num_scenes == 5
            assert config.output_dir == tmp_path
            assert config.enable_music is False
            assert config.dry_run is True
            assert config.provider == VideoProvider.VEO

            # Verify result
            assert result.project_id == "test"


class TestPipelineError:
    """Tests for PipelineError exception."""

    def test_error_message(self) -> None:
        """Test error message is preserved."""
        error = PipelineError("Test error message")
        assert str(error) == "Test error message"

    def test_error_with_cause(self) -> None:
        """Test error with underlying cause."""
        cause = ValueError("Original error")
        error = PipelineError("Wrapped error")
        error.__cause__ = cause

        assert error.__cause__ == cause
