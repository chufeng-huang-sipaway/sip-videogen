"""Tests for single-clip video generation feature."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestImageMetadataPersistence:
    """Tests for image metadata persistence to disk."""

    def test_store_image_metadata_writes_json(self, tmp_path: Path) -> None:
        """Test that store_image_metadata writes a .meta.json file."""
        from sip_studio.advisor.tools import ImageGenerationMetadata, store_image_metadata

        img_path = tmp_path / "test_image.png"
        img_path.write_bytes(b"fake png")
        meta = ImageGenerationMetadata(
            prompt="A test prompt",
            original_prompt="A test prompt",
            model="gemini-3-pro",
            aspect_ratio="1:1",
            image_size="4K",
            reference_image=None,
            product_slugs=[],
            validate_identity=False,
            validation_passed=None,
            validation_warning=None,
            validation_attempts=None,
            final_attempt_number=1,
            attempts=None,
            request_payload=None,
            generated_at="2025-01-01T00:00:00",
            generation_time_ms=1000,
            api_call_code="",
            reference_images=[],
            reference_images_detail=[],
        )
        store_image_metadata(str(img_path), meta)
        meta_path = tmp_path / "test_image.meta.json"
        assert meta_path.exists()
        data = json.loads(meta_path.read_text())
        assert data["prompt"] == "A test prompt"
        assert data["model"] == "gemini-3-pro"

    def test_load_image_metadata_reads_json(self, tmp_path: Path) -> None:
        """Test that load_image_metadata reads from .meta.json file."""
        from sip_studio.advisor.tools import load_image_metadata

        img_path = tmp_path / "test_image.png"
        meta_path = tmp_path / "test_image.meta.json"
        img_path.write_bytes(b"fake png")
        meta_path.write_text(json.dumps({"prompt": "Loaded prompt", "model": "test-model"}))
        result = load_image_metadata(str(img_path))
        assert result is not None
        assert result["prompt"] == "Loaded prompt"
        assert result["model"] == "test-model"

    def test_load_image_metadata_returns_none_if_missing(self, tmp_path: Path) -> None:
        """Test that load_image_metadata returns None if .meta.json doesn't exist."""
        from sip_studio.advisor.tools import load_image_metadata

        img_path = tmp_path / "no_meta.png"
        img_path.write_bytes(b"fake png")
        result = load_image_metadata(str(img_path))
        assert result is None


class TestVideoMetadataPersistence:
    """Tests for video metadata persistence."""

    def test_store_video_metadata_writes_json(self, tmp_path: Path) -> None:
        """Test that store_video_metadata writes a .meta.json file."""
        from sip_studio.advisor.tools import store_video_metadata

        vid_path = tmp_path / "test_video.mp4"
        vid_path.write_bytes(b"fake mp4")
        meta = {"prompt": "Video prompt", "duration": 8, "provider": "veo"}
        store_video_metadata(str(vid_path), meta)
        meta_path = tmp_path / "test_video.meta.json"
        assert meta_path.exists()
        data = json.loads(meta_path.read_text())
        assert data["prompt"] == "Video prompt"
        assert data["duration"] == 8

    def test_load_video_metadata_reads_json(self, tmp_path: Path) -> None:
        """Test that load_video_metadata reads from .meta.json file."""
        from sip_studio.advisor.tools import load_video_metadata

        vid_path = tmp_path / "test_video.mp4"
        meta_path = tmp_path / "test_video.meta.json"
        vid_path.write_bytes(b"fake mp4")
        meta_path.write_text(json.dumps({"prompt": "Loaded video prompt", "duration": 6}))
        result = load_video_metadata(str(vid_path))
        assert result is not None
        assert result["prompt"] == "Loaded video prompt"
        assert result["duration"] == 6

    def test_load_video_metadata_returns_none_if_missing(self, tmp_path: Path) -> None:
        """Test that load_video_metadata returns None if .meta.json doesn't exist."""
        from sip_studio.advisor.tools import load_video_metadata

        vid_path = tmp_path / "no_meta.mp4"
        vid_path.write_bytes(b"fake mp4")
        result = load_video_metadata(str(vid_path))
        assert result is None


class TestGenerateVideoClip:
    """Tests for _impl_generate_video_clip function."""

    def test_no_active_brand_returns_error(self) -> None:
        """Test that generating video with no active brand returns error."""
        import asyncio

        from sip_studio.advisor.tools import _impl_generate_video_clip

        with patch(
            "sip_studio.advisor.tools.video_tools._common.get_active_brand", return_value=None
        ):
            result = asyncio.run(_impl_generate_video_clip(prompt="Test prompt"))
        assert "No active brand selected" in result

    def test_unsupported_provider_returns_error(self, tmp_path: Path) -> None:
        """Test that unsupported provider returns error."""
        import asyncio

        from sip_studio.advisor.tools import _impl_generate_video_clip

        with (
            patch(
                "sip_studio.advisor.tools.video_tools._common.get_active_brand",
                return_value="test-brand",
            ),
            patch(
                "sip_studio.advisor.tools.video_tools._common.get_brand_dir",
                return_value=tmp_path,
            ),
            patch(
                "sip_studio.advisor.tools.video_tools._common.get_settings",
                return_value=MagicMock(gemini_api_key="fake"),
            ),
        ):
            result = asyncio.run(_impl_generate_video_clip(prompt="Test", provider="kling"))
        assert "not supported" in result

    def test_no_prompt_no_concept_image_returns_error(self, tmp_path: Path) -> None:
        """Test that calling without prompt or concept_image_path returns error."""
        import asyncio

        from sip_studio.advisor.tools import _impl_generate_video_clip

        with (
            patch(
                "sip_studio.advisor.tools.video_tools._common.get_active_brand",
                return_value="test-brand",
            ),
            patch(
                "sip_studio.advisor.tools.video_tools._common.get_brand_dir",
                return_value=tmp_path,
            ),
            patch(
                "sip_studio.advisor.tools.video_tools._common.get_settings",
                return_value=MagicMock(gemini_api_key="fake"),
            ),
        ):
            result = asyncio.run(_impl_generate_video_clip())
        assert "required" in result.lower()

    def test_concept_image_not_found_returns_error(self, tmp_path: Path) -> None:
        """Test that non-existent concept image returns error."""
        import asyncio

        from sip_studio.advisor.tools import _impl_generate_video_clip

        with (
            patch(
                "sip_studio.advisor.tools.video_tools._common.get_active_brand",
                return_value="test-brand",
            ),
            patch(
                "sip_studio.advisor.tools.video_tools._common.get_brand_dir",
                return_value=tmp_path,
            ),
            patch(
                "sip_studio.advisor.tools.video_tools._common.get_settings",
                return_value=MagicMock(gemini_api_key="fake"),
            ),
        ):
            result = asyncio.run(_impl_generate_video_clip(concept_image_path="nonexistent.png"))
        assert "not found" in result.lower()


class TestVideoConstants:
    """Tests for video-related constants."""

    def test_allowed_video_exts_defined(self) -> None:
        """Test that ALLOWED_VIDEO_EXTS is defined and contains expected extensions."""
        from sip_studio.constants import ALLOWED_VIDEO_EXTS

        assert ".mp4" in ALLOWED_VIDEO_EXTS
        assert ".mov" in ALLOWED_VIDEO_EXTS
        assert ".webm" in ALLOWED_VIDEO_EXTS

    def test_video_mime_types_defined(self) -> None:
        """Test that VIDEO_MIME_TYPES is defined."""
        from sip_studio.constants import VIDEO_MIME_TYPES

        assert VIDEO_MIME_TYPES[".mp4"] == "video/mp4"
        assert VIDEO_MIME_TYPES[".mov"] == "video/quicktime"
        assert VIDEO_MIME_TYPES[".webm"] == "video/webm"

    def test_video_category_in_asset_categories(self) -> None:
        """Test that 'video' is in ASSET_CATEGORIES."""
        from sip_studio.constants import ASSET_CATEGORIES

        assert "video" in ASSET_CATEGORIES


class TestBrandMemoryVideoListing:
    """Tests for video listing in brand memory."""

    def test_list_brand_assets_includes_videos(self, tmp_path: Path) -> None:
        """Test that list_brand_assets includes video files."""
        from sip_studio.brands.memory import list_brand_assets

        # Set up brand directory with video
        brand_dir = tmp_path / "test-brand"
        video_dir = brand_dir / "assets" / "video"
        video_dir.mkdir(parents=True)
        vid_file = video_dir / "clip.mp4"
        vid_file.write_bytes(b"fake mp4")
        with (
            patch("sip_studio.brands.memory.get_brand_dir", return_value=brand_dir),
        ):
            assets = list_brand_assets("test-brand", category="video")
        assert len(assets) == 1
        assert assets[0]["filename"] == "clip.mp4"
        assert assets[0]["type"] == "video"

    def test_list_brand_videos_filters_only_videos(self, tmp_path: Path) -> None:
        """Test that list_brand_videos returns only video assets."""
        from sip_studio.brands.memory import list_brand_videos

        # Set up brand directory with video
        brand_dir = tmp_path / "test-brand"
        video_dir = brand_dir / "assets" / "video"
        video_dir.mkdir(parents=True)
        vid_file = video_dir / "clip.mp4"
        vid_file.write_bytes(b"fake mp4")
        with (
            patch("sip_studio.brands.memory.get_brand_dir", return_value=brand_dir),
        ):
            videos = list_brand_videos("test-brand")
        assert len(videos) == 1
        assert videos[0]["type"] == "video"


class TestVideoPromptEngineeringSkill:
    """Tests for video prompt engineering skill."""

    def test_skill_file_exists(self) -> None:
        """Test that the video prompt engineering skill file exists."""
        from pathlib import Path

        skill_path = (
            Path(__file__).parent.parent
            / "src"
            / "sip_studio"
            / "advisor"
            / "skills"
            / "video_prompt_engineering"
            / "SKILL.md"
        )
        assert skill_path.exists()

    def test_skill_has_video_triggers(self) -> None:
        """Test that the skill has video-related triggers."""
        from pathlib import Path

        skill_path = (
            Path(__file__).parent.parent
            / "src"
            / "sip_studio"
            / "advisor"
            / "skills"
            / "video_prompt_engineering"
            / "SKILL.md"
        )
        content = skill_path.read_text()
        assert "video" in content.lower()
        assert "generate_video_clip" in content
