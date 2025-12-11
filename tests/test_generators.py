"""Tests for generator modules in sip-videogen."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_videogen.generators.image_generator import (
    ImageGenerationError,
    ImageGenerator,
)
from sip_videogen.generators import VideoGenerator
from sip_videogen.models.assets import AssetType
from sip_videogen.models.script import ElementType, SceneAction, SharedElement


class TestImageGenerator:
    """Tests for ImageGenerator class."""

    def test_init_default_model(self) -> None:
        """Test ImageGenerator initializes with default model."""
        with patch("sip_videogen.generators.image_generator.genai.Client"):
            generator = ImageGenerator(api_key="test-key")
            assert generator.model == "gemini-3-pro-image-preview"

    def test_init_custom_model(self) -> None:
        """Test ImageGenerator with custom model."""
        with patch("sip_videogen.generators.image_generator.genai.Client"):
            generator = ImageGenerator(
                api_key="test-key", model="gemini-3-pro-image-preview"
            )
            assert generator.model == "gemini-3-pro-image-preview"

    def test_build_prompt_character(self, sample_shared_element: SharedElement) -> None:
        """Test prompt building for character elements."""
        with patch("sip_videogen.generators.image_generator.genai.Client"):
            generator = ImageGenerator(api_key="test-key")
            prompt = generator._build_prompt(sample_shared_element)

            assert sample_shared_element.visual_description in prompt
            assert "portrait" in prompt.lower()
            assert "photorealistic" in prompt.lower()

    def test_build_prompt_environment(
        self, sample_environment_element: SharedElement
    ) -> None:
        """Test prompt building for environment elements."""
        with patch("sip_videogen.generators.image_generator.genai.Client"):
            generator = ImageGenerator(api_key="test-key")
            prompt = generator._build_prompt(sample_environment_element)

            assert sample_environment_element.visual_description in prompt
            assert "establishing shot" in prompt.lower()

    def test_build_prompt_prop(self, sample_prop_element: SharedElement) -> None:
        """Test prompt building for prop elements."""
        with patch("sip_videogen.generators.image_generator.genai.Client"):
            generator = ImageGenerator(api_key="test-key")
            prompt = generator._build_prompt(sample_prop_element)

            assert sample_prop_element.visual_description in prompt
            assert "product photograph" in prompt.lower()

    def test_get_aspect_ratio_character(
        self, sample_shared_element: SharedElement
    ) -> None:
        """Test aspect ratio for character elements is 1:1."""
        with patch("sip_videogen.generators.image_generator.genai.Client"):
            generator = ImageGenerator(api_key="test-key")
            ratio = generator._get_aspect_ratio_for_element(sample_shared_element)
            assert ratio == "1:1"

    def test_get_aspect_ratio_environment(
        self, sample_environment_element: SharedElement
    ) -> None:
        """Test aspect ratio for environment elements is 16:9."""
        with patch("sip_videogen.generators.image_generator.genai.Client"):
            generator = ImageGenerator(api_key="test-key")
            ratio = generator._get_aspect_ratio_for_element(sample_environment_element)
            assert ratio == "16:9"

    def test_get_aspect_ratio_prop(self, sample_prop_element: SharedElement) -> None:
        """Test aspect ratio for prop elements is 1:1."""
        with patch("sip_videogen.generators.image_generator.genai.Client"):
            generator = ImageGenerator(api_key="test-key")
            ratio = generator._get_aspect_ratio_for_element(sample_prop_element)
            assert ratio == "1:1"

    @pytest.mark.asyncio
    async def test_generate_reference_image_success(
        self, sample_shared_element: SharedElement, tmp_path: Path
    ) -> None:
        """Test successful image generation."""
        # Create mock image data
        mock_image = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data = True
        mock_part.as_image.return_value = mock_image

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch(
            "sip_videogen.generators.image_generator.genai.Client",
            return_value=mock_client,
        ):
            generator = ImageGenerator(api_key="test-key")
            asset = await generator.generate_reference_image(
                element=sample_shared_element,
                output_dir=tmp_path,
            )

            assert asset.asset_type == AssetType.REFERENCE_IMAGE
            assert asset.element_id == sample_shared_element.id
            assert sample_shared_element.id in asset.local_path
            mock_image.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_reference_image_no_image_in_response(
        self, sample_shared_element: SharedElement, tmp_path: Path
    ) -> None:
        """Test handling when no image is in response."""
        mock_response = MagicMock()
        mock_response.parts = []  # No parts

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch(
            "sip_videogen.generators.image_generator.genai.Client",
            return_value=mock_client,
        ):
            generator = ImageGenerator(api_key="test-key")

            with pytest.raises(ImageGenerationError) as exc_info:
                await generator.generate_reference_image(
                    element=sample_shared_element,
                    output_dir=tmp_path,
                )

            assert "No image generated" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_reference_image_api_error(
        self, sample_shared_element: SharedElement, tmp_path: Path
    ) -> None:
        """Test handling of API errors."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")

        with patch(
            "sip_videogen.generators.image_generator.genai.Client",
            return_value=mock_client,
        ):
            generator = ImageGenerator(api_key="test-key")

            # Disable retries for faster test
            generator.generate_reference_image.retry.stop = (
                lambda *args, **kwargs: True
            )

            with pytest.raises(ImageGenerationError) as exc_info:
                await generator.generate_reference_image(
                    element=sample_shared_element,
                    output_dir=tmp_path,
                )

            assert "Failed to generate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_all_reference_images(
        self,
        sample_shared_element: SharedElement,
        sample_environment_element: SharedElement,
        tmp_path: Path,
    ) -> None:
        """Test generating multiple reference images."""
        # Create mock image data
        mock_image = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data = True
        mock_part.as_image.return_value = mock_image

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch(
            "sip_videogen.generators.image_generator.genai.Client",
            return_value=mock_client,
        ):
            generator = ImageGenerator(api_key="test-key")
            assets = await generator.generate_all_reference_images(
                elements=[sample_shared_element, sample_environment_element],
                output_dir=tmp_path,
            )

            assert len(assets) == 2
            assert all(a.asset_type == AssetType.REFERENCE_IMAGE for a in assets)

    @pytest.mark.asyncio
    async def test_generate_all_reference_images_partial_failure(
        self,
        sample_shared_element: SharedElement,
        sample_environment_element: SharedElement,
        tmp_path: Path,
    ) -> None:
        """Test partial failure in batch image generation."""
        # First call succeeds, second fails
        mock_image = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data = True
        mock_part.as_image.return_value = mock_image

        mock_response_success = MagicMock()
        mock_response_success.parts = [mock_part]

        mock_response_fail = MagicMock()
        mock_response_fail.parts = []  # No image

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            mock_response_success,
            mock_response_fail,
        ]

        with patch(
            "sip_videogen.generators.image_generator.genai.Client",
            return_value=mock_client,
        ):
            generator = ImageGenerator(api_key="test-key")

            # Disable retries
            original_retry = generator.generate_reference_image
            generator.generate_reference_image = AsyncMock(
                side_effect=[
                    await original_retry.__wrapped__(
                        generator, sample_shared_element, tmp_path
                    ),
                    ImageGenerationError("No image"),
                ]
            )

            assets = await generator.generate_all_reference_images(
                elements=[sample_shared_element, sample_environment_element],
                output_dir=tmp_path,
            )

            # Only one should succeed
            assert len(assets) == 1


class TestImageGenerationError:
    """Tests for ImageGenerationError exception."""

    def test_error_message(self) -> None:
        """Test error message is preserved."""
        error = ImageGenerationError("Test error message")
        assert str(error) == "Test error message"

    def test_error_with_cause(self) -> None:
        """Test error with underlying cause."""
        cause = ValueError("Original error")
        error = ImageGenerationError("Wrapped error")
        error.__cause__ = cause

        assert error.__cause__ == cause


class TestVideoGeneratorSceneFlow:
    """Tests for VideoGenerator scene flow context."""

    def test_build_flow_context_first_scene(self) -> None:
        """Test flow context for first scene includes opening guidance."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            generator = VideoGenerator(project="test", location="us-central1")
            scene = SceneAction(
                scene_number=1,
                setting_description="A forest",
                action_description="Hero walks through trees",
            )
            context = generator._build_flow_context(scene, total_scenes=3)

            assert context is not None
            assert "scene 1 of 3" in context
            assert "opening scene" in context
            assert "Do NOT end with" in context
            assert "continues into the next scene" in context

    def test_build_flow_context_middle_scene(self) -> None:
        """Test flow context for middle scene requires seamless flow."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            generator = VideoGenerator(project="test", location="us-central1")
            scene = SceneAction(
                scene_number=2,
                setting_description="A forest path",
                action_description="Hero continues walking",
            )
            context = generator._build_flow_context(scene, total_scenes=3)

            assert context is not None
            assert "scene 2 of 3" in context
            assert "middle scene" in context
            assert "NO opening pause" in context
            assert "NO closing pause" in context
            assert "NO looking at camera" in context

    def test_build_flow_context_last_scene(self) -> None:
        """Test flow context for last scene allows conclusion."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            generator = VideoGenerator(project="test", location="us-central1")
            scene = SceneAction(
                scene_number=3,
                setting_description="A clearing",
                action_description="Hero reaches destination",
            )
            context = generator._build_flow_context(scene, total_scenes=3)

            assert context is not None
            assert "scene 3 of 3" in context
            assert "final scene" in context
            assert "begin mid-action" in context
            assert "natural conclusion" in context

    def test_build_flow_context_single_scene_returns_none(self) -> None:
        """Test flow context returns None for single-scene videos."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            generator = VideoGenerator(project="test", location="us-central1")
            scene = SceneAction(
                scene_number=1,
                setting_description="A room",
                action_description="Something happens",
            )
            context = generator._build_flow_context(scene, total_scenes=1)

            assert context is None

    def test_build_flow_context_none_total_scenes(self) -> None:
        """Test flow context returns None when total_scenes is None."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            generator = VideoGenerator(project="test", location="us-central1")
            scene = SceneAction(
                scene_number=1,
                setting_description="A room",
                action_description="Something happens",
            )
            context = generator._build_flow_context(scene, total_scenes=None)

            assert context is None

    def test_build_prompt_includes_flow_context(self) -> None:
        """Test that _build_prompt includes flow context when total_scenes provided."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            generator = VideoGenerator(project="test", location="us-central1")
            scene = SceneAction(
                scene_number=2,
                setting_description="A forest",
                action_description="Hero walks",
            )
            prompt = generator._build_prompt(scene, total_scenes=3)

            assert "scene 2 of 3" in prompt
            assert "middle scene" in prompt
            assert "Hero walks" in prompt

    def test_build_prompt_without_flow_context(self) -> None:
        """Test that _build_prompt works without total_scenes (backward compat)."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            generator = VideoGenerator(project="test", location="us-central1")
            scene = SceneAction(
                scene_number=1,
                setting_description="A forest",
                action_description="Hero walks",
            )
            prompt = generator._build_prompt(scene)  # No total_scenes

            # Should still work, just without flow context
            assert "Hero walks" in prompt
            assert "Setting: A forest" in prompt
            # Flow context should NOT be present
            assert "scene 1 of" not in prompt

    def test_build_prompt_includes_all_scene_fields(self) -> None:
        """Test that _build_prompt includes all scene fields with flow context."""
        with patch("sip_videogen.generators.video_generator.genai.Client"):
            generator = VideoGenerator(project="test", location="us-central1")
            scene = SceneAction(
                scene_number=2,
                setting_description="Dark alley",
                action_description="Detective searches for clues",
                camera_direction="Slow pan right",
                dialogue="Where could it be?",
            )
            prompt = generator._build_prompt(scene, total_scenes=4)

            # Flow context should be present
            assert "scene 2 of 4" in prompt
            # All scene fields should be present
            assert "Setting: Dark alley" in prompt
            assert "Detective searches for clues" in prompt
            # Camera direction is now at the beginning without "Camera:" prefix
            assert "Slow pan right" in prompt
            # Dialogue is now integrated with action using quotes
            assert '"Where could it be?"' in prompt
