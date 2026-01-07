"""Smoke tests for video backend infrastructure.

These tests verify that the video generation backend remains importable
and properly configured after the CLI removal. They serve as a safety net
to ensure video generation capabilities are preserved.

Note: These are lightweight import and instantiation tests that don't
require actual API credentials. They use mocked settings.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from sip_studio.generators import VideoProvider


class TestVideoBackendImports:
    """Verify all video backend modules are importable."""

    def test_import_video_pipeline_module(self) -> None:
        """Test sip_studio.video.pipeline is importable."""
        from sip_studio.video import pipeline

        assert hasattr(pipeline, "VideoPipeline")
        assert hasattr(pipeline, "PipelineConfig")
        assert hasattr(pipeline, "PipelineResult")
        assert hasattr(pipeline, "PipelineError")
        assert hasattr(pipeline, "generate_video")

    def test_import_video_package_exports(self) -> None:
        """Test sip_studio.video package exports all expected classes."""
        from sip_studio.video import (
            PipelineConfig,
            PipelineError,
            PipelineResult,
            VideoPipeline,
            generate_video,
        )

        assert PipelineConfig is not None
        assert PipelineResult is not None
        assert PipelineError is not None
        assert VideoPipeline is not None
        assert generate_video is not None

    def test_import_generators_module(self) -> None:
        """Test sip_studio.generators is importable with all providers."""
        from sip_studio.generators import (
            BaseVideoGenerator,
            KlingVideoGenerator,
            SoraVideoGenerator,
            VEOVideoGenerator,
            VideoGeneratorFactory,
            VideoProvider,
        )

        assert BaseVideoGenerator is not None
        assert VideoGeneratorFactory is not None
        assert VideoProvider is not None
        assert VEOVideoGenerator is not None
        assert KlingVideoGenerator is not None
        assert SoraVideoGenerator is not None

    def test_import_assembler_module(self) -> None:
        """Test sip_studio.assembler is importable."""
        from sip_studio.assembler import FFmpegAssembler, FFmpegError

        assert FFmpegAssembler is not None
        assert FFmpegError is not None

    def test_import_models_module(self) -> None:
        """Test video-related models are importable."""
        from sip_studio.models import (
            AssetType,
            GeneratedAsset,
            GeneratedMusic,
            VideoScript,
        )

        assert VideoScript is not None
        assert GeneratedAsset is not None
        assert GeneratedMusic is not None
        assert AssetType is not None


class TestVideoGeneratorFactorySmoke:
    """Smoke tests for VideoGeneratorFactory with mocked credentials."""

    def test_create_veo_generator(self) -> None:
        """Test VEO generator can be instantiated with mocked settings."""
        mock_settings = MagicMock()
        mock_settings.gemini_api_key = "test-gemini-api-key"

        with (
            patch(
                "sip_studio.generators.factory.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "sip_studio.config.user_preferences.UserPreferences.load",
            ),
        ):
            from sip_studio.generators import VideoGeneratorFactory

            generator = VideoGeneratorFactory.create(VideoProvider.VEO)

            assert generator is not None
            assert generator.__class__.__name__ == "VEOVideoGenerator"

    def test_create_kling_generator(self) -> None:
        """Test Kling generator can be instantiated with mocked settings."""
        mock_settings = MagicMock()
        mock_settings.kling_access_key = "test-access-key"
        mock_settings.kling_secret_key = "test-secret-key"

        mock_prefs = MagicMock()
        mock_prefs.kling.model_version = "kling-v2-master"
        mock_prefs.kling.mode = "std"

        with (
            patch(
                "sip_studio.generators.factory.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "sip_studio.config.user_preferences.UserPreferences.load",
                return_value=mock_prefs,
            ),
        ):
            from sip_studio.generators import VideoGeneratorFactory

            generator = VideoGeneratorFactory.create(VideoProvider.KLING)

            assert generator is not None
            assert generator.__class__.__name__ == "KlingVideoGenerator"

    def test_create_sora_generator(self) -> None:
        """Test Sora generator can be instantiated with mocked settings."""
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-openai-api-key"

        mock_prefs = MagicMock()
        mock_prefs.sora.model = "sora"
        mock_prefs.sora.resolution = "1080p"

        with (
            patch(
                "sip_studio.generators.factory.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "sip_studio.config.user_preferences.UserPreferences.load",
                return_value=mock_prefs,
            ),
        ):
            from sip_studio.generators import VideoGeneratorFactory

            generator = VideoGeneratorFactory.create(VideoProvider.SORA)

            assert generator is not None
            assert generator.__class__.__name__ == "SoraVideoGenerator"

    def test_get_available_providers_method_exists(self) -> None:
        """Test that get_available_providers method is available."""
        from sip_studio.generators import VideoGeneratorFactory

        assert hasattr(VideoGeneratorFactory, "get_available_providers")
        assert callable(VideoGeneratorFactory.get_available_providers)

    def test_is_provider_available_method_exists(self) -> None:
        """Test that is_provider_available method is available."""
        from sip_studio.generators import VideoGeneratorFactory

        assert hasattr(VideoGeneratorFactory, "is_provider_available")
        assert callable(VideoGeneratorFactory.is_provider_available)


class TestVideoPipelineSmoke:
    """Smoke tests for VideoPipeline class."""

    def test_pipeline_instantiation(self) -> None:
        """Test VideoPipeline can be instantiated."""
        from sip_studio.video import PipelineConfig, VideoPipeline

        config = PipelineConfig(idea="Test video idea")
        pipeline = VideoPipeline(config)

        assert pipeline is not None
        assert pipeline.config == config
        assert pipeline.on_progress is None

    def test_pipeline_config_dataclass(self) -> None:
        """Test PipelineConfig accepts all expected parameters."""
        from sip_studio.video import PipelineConfig

        config = PipelineConfig(
            idea="A cat playing piano",
            num_scenes=5,
            enable_music=False,
            dry_run=True,
            provider=VideoProvider.VEO,
        )

        assert config.idea == "A cat playing piano"
        assert config.num_scenes == 5
        assert config.enable_music is False
        assert config.dry_run is True
        assert config.provider == VideoProvider.VEO

    def test_pipeline_result_dataclass(self, tmp_path) -> None:
        """Test PipelineResult can be constructed."""
        from sip_studio.models import VideoScript
        from sip_studio.video import PipelineResult

        # Minimal script for testing
        mock_script = MagicMock(spec=VideoScript)
        mock_script.title = "Test"

        result = PipelineResult(
            project_id="smoke_test_123",
            project_dir=tmp_path,
            script=mock_script,
            stages_completed=["script_development"],
        )

        assert result.project_id == "smoke_test_123"
        assert result.project_dir == tmp_path
        assert result.reference_images == []
        assert result.video_clips == []


class TestVideoProviderEnum:
    """Smoke tests for VideoProvider enum."""

    def test_all_providers_exist(self) -> None:
        """Test all expected video providers are defined."""
        assert VideoProvider.VEO is not None
        assert VideoProvider.KLING is not None
        assert VideoProvider.SORA is not None

    def test_provider_values(self) -> None:
        """Test provider enum values are strings."""
        assert VideoProvider.VEO.value == "veo"
        assert VideoProvider.KLING.value == "kling"
        assert VideoProvider.SORA.value == "sora"

    def test_provider_iteration(self) -> None:
        """Test all providers can be iterated."""
        providers = list(VideoProvider)
        assert len(providers) >= 3
        assert VideoProvider.VEO in providers
        assert VideoProvider.KLING in providers
        assert VideoProvider.SORA in providers
