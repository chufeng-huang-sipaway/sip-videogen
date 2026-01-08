"""Tests for AssetService."""

import base64
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from sip_studio.studio.services.asset_service import AssetService
from sip_studio.studio.state import BridgeState


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def state():
    """Create fresh BridgeState."""
    return BridgeState()


@pytest.fixture
def service(state):
    """Create AssetService with state."""
    return AssetService(state)


@pytest.fixture
def mock_brand_dir(tmp_path) -> Path:
    """Create mock brand directory with assets folder."""
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    assets_dir = brand_dir / "assets"
    assets_dir.mkdir()
    for cat in ["logo", "generated", "video"]:
        (assets_dir / cat).mkdir()
    return brand_dir


# =============================================================================
# get_assets tests
# =============================================================================
class TestGetAssets:
    """Tests for get_assets method."""

    def test_returns_asset_tree(self, service):
        """Should return asset tree for brand."""
        mock_assets = [{"filename": "logo.png", "path": "/tmp/test.png", "type": "image"}]
        with patch(
            "sip_studio.studio.services.asset_service.list_brand_assets",
            return_value=mock_assets,
        ):
            with patch("pathlib.Path.stat", return_value=MagicMock(st_size=1024)):
                with patch("pathlib.Path.exists", return_value=True):
                    result = service.get_assets("test")
        assert result["success"]
        assert "tree" in result["data"]

    def test_uses_provided_slug(self, service):
        """Should use provided slug instead of active brand."""
        with patch(
            "sip_studio.studio.services.asset_service.list_brand_assets", return_value=[]
        ) as mock_list:
            with patch("sip_studio.studio.services.asset_service.ASSET_CATEGORIES", ["logo"]):
                service.get_assets("custom-brand")
        mock_list.assert_called_with("custom-brand", category="logo")

    def test_error_when_no_brand(self, service):
        """Should return error when no brand selected."""
        result = service.get_assets()
        assert not result["success"]
        assert "No brand selected" in result["error"]


# =============================================================================
# get_asset_thumbnail tests
# =============================================================================
class TestGetAssetThumbnail:
    """Tests for get_asset_thumbnail method."""

    def test_returns_thumbnail_for_svg(self, service, state, mock_brand_dir):
        """Should return base64-encoded SVG directly."""
        svg_path = mock_brand_dir / "assets" / "logo" / "icon.svg"
        svg_path.write_text("<svg></svg>")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_asset_thumbnail("logo/icon.svg")
        assert result["success"]
        assert "dataUrl" in result["data"]
        assert "image/svg+xml" in result["data"]["dataUrl"]

    def test_error_when_no_brand(self, service, state):
        """Should return error when no brand dir."""
        state.get_brand_dir = MagicMock(return_value=(None, "No brand selected"))
        result = service.get_asset_thumbnail("logo/test.png")
        assert not result["success"]
        assert "No brand selected" in result["error"]

    def test_error_for_missing_file(self, service, state, mock_brand_dir):
        """Should return error when file doesn't exist."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_asset_thumbnail("logo/missing.png")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_error_for_unsupported_type(self, service, state, mock_brand_dir):
        """Should reject unsupported file types."""
        bad_file = mock_brand_dir / "assets" / "logo" / "test.exe"
        bad_file.write_text("binary")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_asset_thumbnail("logo/test.exe")
        assert not result["success"]
        assert "Unsupported" in result["error"]


# =============================================================================
# get_asset_full tests
# =============================================================================
class TestGetAssetFull:
    """Tests for get_asset_full method."""

    def test_returns_full_image(self, service, state, mock_brand_dir):
        """Should return base64-encoded full image."""
        # Create a minimal valid PNG (1x1 pixel)
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        png_path = mock_brand_dir / "assets" / "logo" / "test.png"
        png_path.write_bytes(png_data)
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_asset_full("logo/test.png")
        assert result["success"]
        assert "dataUrl" in result["data"]
        assert "image/png" in result["data"]["dataUrl"]

    def test_error_for_missing_file(self, service, state, mock_brand_dir):
        """Should return error when file doesn't exist."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_asset_full("logo/missing.png")
        assert not result["success"]
        assert "not found" in result["error"]


# =============================================================================
# upload_asset tests
# =============================================================================
class TestUploadAsset:
    """Tests for upload_asset method."""

    def test_uploads_asset(self, service):
        """Should upload asset successfully."""
        content = base64.b64encode(b"test content").decode()
        with patch(
            "sip_studio.studio.services.asset_service.get_active_brand", return_value="test"
        ):
            with patch(
                "sip_studio.studio.services.asset_service.storage_save_asset",
                return_value=("generated/test.png", None),
            ):
                result = service.upload_asset("test.png", content, "generated")
        assert result["success"]
        assert result["data"]["path"] == "generated/test.png"

    def test_error_when_no_brand(self, service):
        """Should return error when no brand selected."""
        with patch("sip_studio.studio.services.asset_service.get_active_brand", return_value=None):
            result = service.upload_asset("test.png", "base64data", "logo")
        assert not result["success"]
        assert "No brand selected" in result["error"]

    def test_returns_storage_error(self, service):
        """Should return storage error message."""
        with patch(
            "sip_studio.studio.services.asset_service.get_active_brand", return_value="test"
        ):
            with patch(
                "sip_studio.studio.services.asset_service.storage_save_asset",
                return_value=(None, "Write failed"),
            ):
                result = service.upload_asset("test.png", base64.b64encode(b"x").decode(), "logo")
        assert not result["success"]
        assert "Write failed" in result["error"]


# =============================================================================
# delete_asset tests
# =============================================================================
class TestDeleteAsset:
    """Tests for delete_asset method."""

    def test_deletes_asset(self, service, state, mock_brand_dir):
        """Should delete asset by moving to trash."""
        png_path = mock_brand_dir / "assets" / "generated" / "test.png"
        png_path.write_bytes(b"test")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        with patch("sip_studio.studio.services.asset_service._move_to_trash", return_value=True):
            result = service.delete_asset("generated/test.png")
        assert result["success"]

    def test_error_when_no_brand(self, service, state):
        """Should return error when no brand dir."""
        state.get_brand_dir = MagicMock(return_value=(None, "No brand selected"))
        result = service.delete_asset("logo/test.png")
        assert not result["success"]

    def test_error_for_missing_file(self, service, state, mock_brand_dir):
        """Should return error when file doesn't exist."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.delete_asset("logo/missing.png")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_error_for_folders(self, service, state, mock_brand_dir):
        """Should reject folder deletion."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.delete_asset("logo")
        assert not result["success"]
        assert "folder" in result["error"].lower()

    def test_error_for_unsupported_type(self, service, state, mock_brand_dir):
        """Should reject unsupported file types."""
        bad_file = mock_brand_dir / "assets" / "logo" / "test.exe"
        bad_file.write_text("binary")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.delete_asset("logo/test.exe")
        assert not result["success"]
        assert "Unsupported" in result["error"]


# =============================================================================
# rename_asset tests
# =============================================================================
class TestRenameAsset:
    """Tests for rename_asset method."""

    def test_renames_asset(self, service, state, mock_brand_dir):
        """Should rename asset successfully."""
        old_path = mock_brand_dir / "assets" / "logo" / "old.png"
        old_path.write_bytes(b"test")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.rename_asset("logo/old.png", "new.png")
        assert result["success"]
        assert result["data"]["newPath"] == "logo/new.png"

    def test_error_when_no_brand(self, service, state):
        """Should return error when no brand dir."""
        state.get_brand_dir = MagicMock(return_value=(None, "No brand selected"))
        result = service.rename_asset("logo/old.png", "new.png")
        assert not result["success"]

    def test_error_for_missing_file(self, service, state, mock_brand_dir):
        """Should return error when file doesn't exist."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.rename_asset("logo/missing.png", "new.png")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_rejects_path_in_filename(self, service, state, mock_brand_dir):
        """Should reject filenames with path separators."""
        old_path = mock_brand_dir / "assets" / "logo" / "old.png"
        old_path.write_bytes(b"test")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.rename_asset("logo/old.png", "../new.png")
        assert not result["success"]
        assert "Invalid filename" in result["error"]

    def test_rejects_unsupported_extension(self, service, state, mock_brand_dir):
        """Should reject rename to unsupported extension."""
        old_path = mock_brand_dir / "assets" / "logo" / "old.png"
        old_path.write_bytes(b"test")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.rename_asset("logo/old.png", "new.exe")
        assert not result["success"]
        assert "Unsupported" in result["error"]

    def test_error_when_target_exists(self, service, state, mock_brand_dir):
        """Should error when target already exists."""
        old_path = mock_brand_dir / "assets" / "logo" / "old.png"
        old_path.write_bytes(b"test1")
        new_path = mock_brand_dir / "assets" / "logo" / "new.png"
        new_path.write_bytes(b"test2")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.rename_asset("logo/old.png", "new.png")
        assert not result["success"]
        assert "already exists" in result["error"]


# =============================================================================
# open_asset_in_finder tests
# =============================================================================
class TestOpenAssetInFinder:
    """Tests for open_asset_in_finder method."""

    def test_opens_asset(self, service, state, mock_brand_dir):
        """Should reveal asset in finder."""
        png_path = mock_brand_dir / "assets" / "logo" / "test.png"
        png_path.write_bytes(b"test")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        with patch(
            "sip_studio.studio.services.asset_service.reveal_in_file_manager"
        ) as mock_reveal:
            result = service.open_asset_in_finder("logo/test.png")
        assert result["success"]
        mock_reveal.assert_called_once()

    def test_error_for_missing_file(self, service, state, mock_brand_dir):
        """Should return error when file doesn't exist."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.open_asset_in_finder("logo/missing.png")
        assert not result["success"]
        assert "not found" in result["error"]


# =============================================================================
# get_video_path tests
# =============================================================================
class TestGetVideoPath:
    """Tests for get_video_path method."""

    def test_returns_video_path(self, service, state, mock_brand_dir):
        """Should return absolute video path."""
        video_path = mock_brand_dir / "assets" / "video" / "test.mp4"
        video_path.write_bytes(b"fake video")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_video_path("video/test.mp4")
        assert result["success"]
        assert "path" in result["data"]
        assert "test.mp4" in result["data"]["path"]

    def test_error_for_missing_video(self, service, state, mock_brand_dir):
        """Should return error when video doesn't exist."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_video_path("video/missing.mp4")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_error_for_wrong_type(self, service, state, mock_brand_dir):
        """Should reject non-video files."""
        png_path = mock_brand_dir / "assets" / "video" / "test.png"
        png_path.write_bytes(b"image")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_video_path("video/test.png")
        assert not result["success"]
        assert "Unsupported" in result["error"]


# =============================================================================
# get_video_data tests
# =============================================================================
class TestGetVideoData:
    """Tests for get_video_data method."""

    def test_returns_video_data(self, service, state, mock_brand_dir):
        """Should return base64-encoded video data."""
        video_path = mock_brand_dir / "assets" / "video" / "test.mp4"
        video_path.write_bytes(b"fake video content")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_video_data("video/test.mp4")
        assert result["success"]
        assert "dataUrl" in result["data"]
        assert "video/mp4" in result["data"]["dataUrl"]

    def test_error_for_missing_video(self, service, state, mock_brand_dir):
        """Should return error when video doesn't exist."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_video_data("video/missing.mp4")
        assert not result["success"]
        assert "not found" in result["error"]


# =============================================================================
# get_image_metadata tests
# =============================================================================
# Create mock for sip_studio.advisor.tools to avoid import chain issues
_mock_tools = ModuleType("sip_studio.advisor.tools")
_mock_tools.load_image_metadata = MagicMock()


class TestGetImageMetadata:
    """Tests for get_image_metadata method."""

    @pytest.fixture(autouse=True)
    def mock_tools_module(self):
        """Mock the tools module to avoid PIL import chain."""
        sys.modules["sip_studio.advisor.tools"] = _mock_tools
        yield
        # Cleanup after test
        if "sip_studio.advisor.tools" in sys.modules:
            if sys.modules["sip_studio.advisor.tools"] is _mock_tools:
                del sys.modules["sip_studio.advisor.tools"]

    def test_returns_metadata_when_exists(self, service, state, mock_brand_dir):
        """Metadata file exists with product_slugs → returns dict."""
        gen_dir = mock_brand_dir / "assets" / "generated"
        img = gen_dir / "test.png"
        img.write_bytes(b"fake png")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        mock_meta = {"product_slugs": ["product-a"], "prompt": "test"}
        _mock_tools.load_image_metadata.return_value = mock_meta
        result = service.get_image_metadata(str(img))
        assert result["success"]
        assert result["data"]["product_slugs"] == ["product-a"]

    def test_returns_none_when_no_metadata(self, service, state, mock_brand_dir):
        """Image exists but no .meta.json → returns None (not error)."""
        gen_dir = mock_brand_dir / "assets" / "generated"
        img = gen_dir / "test.png"
        img.write_bytes(b"fake png")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        _mock_tools.load_image_metadata.return_value = None
        result = service.get_image_metadata(str(img))
        assert result["success"]
        assert result["data"] is None

    def test_returns_none_for_corrupt_metadata(self, service, state, mock_brand_dir):
        """Corrupt .meta.json → load_image_metadata returns None → returns None."""
        gen_dir = mock_brand_dir / "assets" / "generated"
        img = gen_dir / "test.png"
        img.write_bytes(b"fake png")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        # load_image_metadata handles corrupt JSON by returning None
        _mock_tools.load_image_metadata.return_value = None
        result = service.get_image_metadata(str(img))
        assert result["success"]
        assert result["data"] is None

    def test_returns_error_for_path_resolution_failure(self, service, state):
        """Path resolution fails → returns error."""
        state.get_brand_dir = MagicMock(return_value=(None, "No brand selected"))
        result = service.get_image_metadata("/some/path.png")
        assert not result["success"]
        assert "No brand selected" in result["error"]

    def test_returns_error_for_nonexistent_image(self, service, state, mock_brand_dir):
        """Path resolves but file doesn't exist → returns error."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.get_image_metadata(
            str(mock_brand_dir / "assets" / "generated" / "nonexistent.png")
        )
        assert not result["success"]
        assert "not found" in result["error"].lower()
