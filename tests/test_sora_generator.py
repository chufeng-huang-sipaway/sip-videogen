"""Tests for Sora video generator."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_videogen.generators.base import PromptSafetyError, VideoGenerationError
from sip_videogen.generators.sora_generator import (
    SoraConfig,
    SoraGenerationResult,
    SoraVideoGenerator,
)
from sip_videogen.models.assets import AssetType, GeneratedAsset
from sip_videogen.models.script import SceneAction, VideoScript


class TestSoraConfig:
    """Tests for SoraConfig."""

    def test_default_values(self) -> None:
        """Test default config values."""
        config = SoraConfig()
        assert config.model == "sora-2"
        assert config.resolution == "1080p"

    def test_custom_values(self) -> None:
        """Test custom config values."""
        config = SoraConfig(model="sora-2-pro", resolution="720p")
        assert config.model == "sora-2-pro"
        assert config.resolution == "720p"


class TestSoraGenerationResult:
    """Tests for SoraGenerationResult."""

    def test_success_rate_all_success(self) -> None:
        """Test success rate when all scenes succeed."""
        result = SoraGenerationResult(
            successful=[MagicMock(), MagicMock(), MagicMock()],
            failed_scenes=[],
            total_scenes=3,
        )
        assert result.success_rate == 100.0
        assert result.all_succeeded is True

    def test_success_rate_partial(self) -> None:
        """Test success rate with some failures."""
        result = SoraGenerationResult(
            successful=[MagicMock(), MagicMock()],
            failed_scenes=[3],
            total_scenes=3,
        )
        assert result.success_rate == pytest.approx(66.67, rel=0.01)
        assert result.all_succeeded is False

    def test_success_rate_all_failed(self) -> None:
        """Test success rate when all fail."""
        result = SoraGenerationResult(
            successful=[],
            failed_scenes=[1, 2, 3],
            total_scenes=3,
        )
        assert result.success_rate == 0.0
        assert result.all_succeeded is False

    def test_success_rate_empty(self) -> None:
        """Test success rate with no scenes."""
        result = SoraGenerationResult(
            successful=[],
            failed_scenes=[],
            total_scenes=0,
        )
        assert result.success_rate == 0.0
        assert result.all_succeeded is True


class TestSoraVideoGenerator:
    """Tests for SoraVideoGenerator class."""

    def test_init_default_config(self) -> None:
        """Test SoraVideoGenerator initializes with default config."""
        generator = SoraVideoGenerator(api_key="test-key")
        assert generator.config.model == "sora-2"
        assert generator.config.resolution == "1080p"
        assert generator.api_key == "test-key"

    def test_init_custom_config(self) -> None:
        """Test SoraVideoGenerator with custom config."""
        config = SoraConfig(model="sora-2-pro", resolution="720p")
        generator = SoraVideoGenerator(api_key="test-key", config=config)
        assert generator.config.model == "sora-2-pro"
        assert generator.config.resolution == "720p"

    def test_provider_constants(self) -> None:
        """Test provider constants are correctly set."""
        generator = SoraVideoGenerator(api_key="test-key")
        assert generator.PROVIDER_NAME == "sora"
        assert generator.VALID_DURATIONS == [4, 8, 12]
        assert generator.MAX_REFERENCE_IMAGES == 1

    def test_map_duration_short(self) -> None:
        """Test duration mapping for short durations."""
        generator = SoraVideoGenerator(api_key="test-key")
        # <= 6 seconds maps to 4
        assert generator.map_duration(1) == 4
        assert generator.map_duration(4) == 4
        assert generator.map_duration(5) == 4
        assert generator.map_duration(6) == 4

    def test_map_duration_medium(self) -> None:
        """Test duration mapping for medium durations."""
        generator = SoraVideoGenerator(api_key="test-key")
        # 7-10 seconds maps to 8
        assert generator.map_duration(7) == 8
        assert generator.map_duration(8) == 8
        assert generator.map_duration(10) == 8

    def test_map_duration_long(self) -> None:
        """Test duration mapping for long durations."""
        generator = SoraVideoGenerator(api_key="test-key")
        # > 10 seconds maps to 12
        assert generator.map_duration(11) == 12
        assert generator.map_duration(12) == 12
        assert generator.map_duration(15) == 12

    def test_map_aspect_ratio_landscape_1080p(self) -> None:
        """Test aspect ratio mapping for landscape at 1080p."""
        generator = SoraVideoGenerator(api_key="test-key")
        size = generator._map_aspect_ratio_to_size("16:9")
        # Sora uses 1792x1024 for high-res landscape (closest to 1080p)
        assert size == "1792x1024"

    def test_map_aspect_ratio_portrait_1080p(self) -> None:
        """Test aspect ratio mapping for portrait at 1080p."""
        generator = SoraVideoGenerator(api_key="test-key")
        size = generator._map_aspect_ratio_to_size("9:16")
        # Sora uses 1024x1792 for high-res portrait (closest to 1080p)
        assert size == "1024x1792"

    def test_map_aspect_ratio_landscape_720p(self) -> None:
        """Test aspect ratio with 720p resolution."""
        config = SoraConfig(resolution="720p")
        generator = SoraVideoGenerator(api_key="test-key", config=config)
        assert generator._map_aspect_ratio_to_size("16:9") == "1280x720"

    def test_map_aspect_ratio_portrait_720p(self) -> None:
        """Test aspect ratio for portrait at 720p."""
        config = SoraConfig(resolution="720p")
        generator = SoraVideoGenerator(api_key="test-key", config=config)
        assert generator._map_aspect_ratio_to_size("9:16") == "720x1280"

    def test_build_flow_context_first_scene(self) -> None:
        """Test flow context for first scene."""
        generator = SoraVideoGenerator(api_key="test-key")
        scene = SceneAction(
            scene_number=1,
            duration_seconds=4,
            setting_description="A forest",
            action_description="Hero walks through trees",
            dialogue="",
            camera_direction="Wide shot",
            shared_element_ids=[],
        )
        context = generator._build_flow_context(scene, total_scenes=3)

        assert context is not None
        assert "Scene 1/3" in context
        assert "Opening scene" in context

    def test_build_flow_context_middle_scene(self) -> None:
        """Test flow context for middle scene."""
        generator = SoraVideoGenerator(api_key="test-key")
        scene = SceneAction(
            scene_number=2,
            duration_seconds=4,
            setting_description="A room",
            action_description="Something happens",
            dialogue="",
            camera_direction="Medium shot",
            shared_element_ids=[],
        )
        context = generator._build_flow_context(scene, total_scenes=3)

        assert context is not None
        assert "Scene 2/3" in context
        assert "Middle scene" in context

    def test_build_flow_context_last_scene(self) -> None:
        """Test flow context for last scene."""
        generator = SoraVideoGenerator(api_key="test-key")
        scene = SceneAction(
            scene_number=3,
            duration_seconds=4,
            setting_description="A sunset",
            action_description="Hero walks away",
            dialogue="",
            camera_direction="Wide shot",
            shared_element_ids=[],
        )
        context = generator._build_flow_context(scene, total_scenes=3)

        assert context is not None
        assert "Scene 3/3" in context
        assert "Final scene" in context

    def test_build_flow_context_single_scene(self) -> None:
        """Test flow context returns None for single-scene videos."""
        generator = SoraVideoGenerator(api_key="test-key")
        scene = SceneAction(
            scene_number=1,
            duration_seconds=4,
            setting_description="A room",
            action_description="Something happens",
            dialogue="",
            camera_direction="Medium shot",
            shared_element_ids=[],
        )
        context = generator._build_flow_context(scene, total_scenes=1)
        assert context is None

    def test_build_flow_context_none_total(self) -> None:
        """Test flow context returns None when total_scenes is None."""
        generator = SoraVideoGenerator(api_key="test-key")
        scene = SceneAction(
            scene_number=1,
            duration_seconds=4,
            setting_description="A room",
            action_description="Something happens",
            dialogue="",
            camera_direction="Medium shot",
            shared_element_ids=[],
        )
        context = generator._build_flow_context(scene, total_scenes=None)
        assert context is None

    def test_build_scene_reference_map_empty(self) -> None:
        """Test reference map with no images."""
        generator = SoraVideoGenerator(api_key="test-key")
        script = MagicMock(spec=VideoScript)
        script.scenes = []

        result = generator._build_scene_reference_map(script, None)
        assert result == {}

        result = generator._build_scene_reference_map(script, [])
        assert result == {}

    def test_build_scene_reference_map_with_images(self) -> None:
        """Test reference map maps images to scenes correctly."""
        generator = SoraVideoGenerator(api_key="test-key")

        # Create mock script with scenes
        scene1 = MagicMock(spec=SceneAction)
        scene1.scene_number = 1
        scene1.shared_element_ids = ["char_1", "env_1"]

        scene2 = MagicMock(spec=SceneAction)
        scene2.scene_number = 2
        scene2.shared_element_ids = ["char_1"]

        script = MagicMock(spec=VideoScript)
        script.scenes = [scene1, scene2]

        # Create mock reference images
        img1 = MagicMock(spec=GeneratedAsset)
        img1.element_id = "char_1"

        img2 = MagicMock(spec=GeneratedAsset)
        img2.element_id = "env_1"

        reference_images = [img1, img2]

        result = generator._build_scene_reference_map(script, reference_images)

        # Sora only uses 1 image per scene
        assert len(result.get(1, [])) == 1
        assert len(result.get(2, [])) == 1

    @pytest.mark.asyncio
    async def test_generate_video_clip_success(self, tmp_path: Path) -> None:
        """Test successful video generation."""
        # Create mock video response (from create_and_poll)
        mock_video = MagicMock()
        mock_video.id = "video_123"
        mock_video.status = "completed"
        mock_video.error = None

        # Mock download response
        mock_download_response = MagicMock()
        mock_download_response.content = b"fake video content"

        mock_client = AsyncMock()
        mock_client.videos.create_and_poll = AsyncMock(return_value=mock_video)
        mock_client.videos.download_content = AsyncMock(return_value=mock_download_response)

        with patch(
            "sip_videogen.generators.sora_generator.AsyncOpenAI",
            return_value=mock_client,
        ):
            generator = SoraVideoGenerator(api_key="test-key")
            generator._client = mock_client

            scene = SceneAction(
                scene_number=1,
                duration_seconds=4,
                setting_description="A forest",
                action_description="Hero walks",
                dialogue="",
                camera_direction="Wide shot",
                shared_element_ids=[],
            )

            asset = await generator.generate_video_clip(
                scene=scene,
                output_dir=str(tmp_path),
            )

            assert asset.asset_type == AssetType.VIDEO_CLIP
            assert asset.scene_number == 1
            assert "scene_001.mp4" in asset.local_path
            # Verify the file was created
            assert (tmp_path / "scene_001.mp4").exists()

    @pytest.mark.asyncio
    async def test_generate_video_clip_safety_error(self, tmp_path: Path) -> None:
        """Test that safety errors are converted to PromptSafetyError."""
        mock_client = AsyncMock()
        mock_client.videos.create_and_poll = AsyncMock(
            side_effect=Exception("Content policy violation: safety filter triggered")
        )

        with patch(
            "sip_videogen.generators.sora_generator.AsyncOpenAI",
            return_value=mock_client,
        ):
            generator = SoraVideoGenerator(api_key="test-key")
            generator._client = mock_client

            scene = SceneAction(
                scene_number=1,
                duration_seconds=4,
                setting_description="A scene",
                action_description="Something happens",
                dialogue="",
                camera_direction="Shot",
                shared_element_ids=[],
            )

            with pytest.raises(PromptSafetyError):
                await generator.generate_video_clip(
                    scene=scene,
                    output_dir=str(tmp_path),
                )

    @pytest.mark.asyncio
    async def test_generate_video_clip_access_error(self, tmp_path: Path) -> None:
        """Test that access errors include helpful message."""
        mock_client = AsyncMock()
        mock_client.videos.create_and_poll = AsyncMock(
            side_effect=Exception("Unauthorized: You don't have access to this model")
        )

        with patch(
            "sip_videogen.generators.sora_generator.AsyncOpenAI",
            return_value=mock_client,
        ):
            generator = SoraVideoGenerator(api_key="test-key")
            generator._client = mock_client

            scene = SceneAction(
                scene_number=1,
                duration_seconds=4,
                setting_description="A scene",
                action_description="Something happens",
                dialogue="",
                camera_direction="Shot",
                shared_element_ids=[],
            )

            with pytest.raises(VideoGenerationError) as exc_info:
                await generator.generate_video_clip(
                    scene=scene,
                    output_dir=str(tmp_path),
                )

            assert "platform.openai.com" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_video_clip_failed_status(self, tmp_path: Path) -> None:
        """Test error when video generation fails."""
        mock_error = MagicMock()
        mock_error.message = "Generation failed due to content policy"

        mock_video = MagicMock()
        mock_video.id = "video_123"
        mock_video.status = "failed"
        mock_video.error = mock_error

        mock_client = AsyncMock()
        mock_client.videos.create_and_poll = AsyncMock(return_value=mock_video)

        with patch(
            "sip_videogen.generators.sora_generator.AsyncOpenAI",
            return_value=mock_client,
        ):
            generator = SoraVideoGenerator(api_key="test-key")
            generator._client = mock_client

            scene = SceneAction(
                scene_number=1,
                duration_seconds=4,
                setting_description="A scene",
                action_description="Something happens",
                dialogue="",
                camera_direction="Shot",
                shared_element_ids=[],
            )

            with pytest.raises(VideoGenerationError) as exc_info:
                await generator.generate_video_clip(
                    scene=scene,
                    output_dir=str(tmp_path),
                )

            assert "failed" in str(exc_info.value).lower()
