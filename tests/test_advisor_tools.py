"""Tests for the Brand Marketing Advisor tools."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestReadFile:
    """Tests for _impl_read_file function."""

    def test_read_text_file(self, tmp_path: Path) -> None:
        """Test reading a text file."""
        from sip_videogen.advisor.tools import _impl_read_file

        # Set up brand directory structure
        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "test.txt"
        test_file.write_text("Hello, World!")

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _impl_read_file("test.txt")

        assert result == "Hello, World!"

    def test_read_json_file(self, tmp_path: Path) -> None:
        """Test reading a JSON file."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "identity.json"
        test_file.write_text('{"name": "Test Brand"}')

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _impl_read_file("identity.json")

        assert '{"name": "Test Brand"}' in result

    def test_read_binary_file(self, tmp_path: Path) -> None:
        """Test reading a binary file returns size info."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "image.png"
        test_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _impl_read_file("image.png")

        assert "Binary file exists" in result
        assert "108 bytes" in result

    def test_read_file_not_found(self, tmp_path: Path) -> None:
        """Test reading non-existent file returns error."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _impl_read_file("nonexistent.txt")

        assert "Error: File not found" in result

    def test_read_file_no_active_brand(self) -> None:
        """Test reading file with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_read_file

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_read_file("test.txt")

        assert "No active brand selected" in result


class TestWriteFile:
    """Tests for _impl_write_file function."""

    def test_write_text_file(self, tmp_path: Path) -> None:
        """Test writing a text file."""
        from sip_videogen.advisor.tools import _impl_write_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _impl_write_file("test.txt", "Hello, World!")

        assert "Successfully wrote" in result
        assert (brand_dir / "test.txt").read_text() == "Hello, World!"

    def test_write_creates_directories(self, tmp_path: Path) -> None:
        """Test that _impl_write_file creates parent directories."""
        from sip_videogen.advisor.tools import _impl_write_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _impl_write_file("subdir/deep/file.txt", "Content")

        assert "Successfully wrote" in result
        assert (brand_dir / "subdir" / "deep" / "file.txt").read_text() == "Content"

    def test_write_file_no_active_brand(self) -> None:
        """Test writing file with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_write_file

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_write_file("test.txt", "Content")

        assert "No active brand selected" in result


class TestListFiles:
    """Tests for _impl_list_files function."""

    def test_list_root_directory(self, tmp_path: Path) -> None:
        """Test listing root brand directory."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        (brand_dir / "identity.json").write_text("{}")
        (brand_dir / "assets").mkdir()
        (brand_dir / "assets" / "logo.png").write_bytes(b"png")

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _impl_list_files("")

        assert "identity.json" in result
        assert "assets/" in result
        assert "(1 items)" in result

    def test_list_subdirectory(self, tmp_path: Path) -> None:
        """Test listing a subdirectory."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        (brand_dir / "assets").mkdir(parents=True)
        (brand_dir / "assets" / "logo.png").write_bytes(b"png")
        (brand_dir / "assets" / "banner.jpg").write_bytes(b"jpg")

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _impl_list_files("assets/")

        assert "logo.png" in result
        assert "banner.jpg" in result

    def test_list_empty_directory(self, tmp_path: Path) -> None:
        """Test listing an empty directory."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        (brand_dir / "empty").mkdir(parents=True)

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _impl_list_files("empty/")

        assert "Directory is empty" in result


class TestLoadBrand:
    """Tests for _impl_load_brand function."""

    def test_load_brand_no_active_no_brands(self) -> None:
        """Test _impl_load_brand with no active brand and no brands available."""
        from sip_videogen.advisor.tools import _impl_load_brand

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None), patch(
            "sip_videogen.advisor.tools.storage_load_brand", return_value=None
        ), patch(
            # list_brands is imported inside the function from sip_videogen.brands.storage
            "sip_videogen.brands.storage.list_brands", return_value=[]
        ):
            result = _impl_load_brand(slug=None)

        assert "No brands found" in result or "No active brand" in result

    def test_load_brand_not_found(self) -> None:
        """Test loading non-existent brand."""
        from sip_videogen.advisor.tools import _impl_load_brand

        with patch(
            "sip_videogen.advisor.tools.storage_load_brand", return_value=None
        ), patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="nonexistent"
        ):
            result = _impl_load_brand(slug="nonexistent")

        assert "Error: Brand not found" in result

    def test_load_brand_includes_assets_section(self) -> None:
        """Test that load_brand includes Available Assets section with per-category counts."""
        from sip_videogen.advisor.tools import _impl_load_brand

        # Create mock identity
        mock_identity = MagicMock()
        mock_identity.core.name = "Test Brand"
        mock_identity.core.tagline = "Test tagline"
        mock_identity.core.mission = "Test mission"
        mock_identity.core.values = []
        mock_identity.positioning.market_category = "Test"
        mock_identity.positioning.unique_value_proposition = "Test UVP"
        mock_identity.positioning.positioning_statement = None
        mock_identity.voice.tone_attributes = ["friendly"]
        mock_identity.voice.personality = "Friendly"
        mock_identity.voice.key_messages = []
        mock_identity.visual.primary_colors = []
        mock_identity.visual.style_keywords = []
        mock_identity.visual.overall_aesthetic = None
        mock_identity.audience.primary_summary = "Test audience"
        mock_identity.audience.demographics = None

        # Mock assets returned as list of dicts (the actual return type)
        mock_assets = [
            {"category": "logo", "name": "primary", "path": "/test/logo/primary.png"},
            {"category": "logo", "name": "secondary", "path": "/test/logo/secondary.png"},
            {"category": "mascot", "name": "benny", "path": "/test/mascot/benny.png"},
        ]

        with patch(
            "sip_videogen.advisor.tools.storage_load_brand", return_value=mock_identity
        ), patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.brands.memory.list_brand_assets", return_value=mock_assets
        ), patch(
            "sip_videogen.brands.storage.set_active_brand"
        ):
            result = _impl_load_brand(slug="test-brand")

        # Check that assets section is present with per-category counts
        assert "## Available Assets" in result
        assert "logo" in result.lower()
        assert "mascot" in result.lower()


class TestResolveBrandPath:
    """Tests for _resolve_brand_path helper."""

    def test_resolve_normal_path(self, tmp_path: Path) -> None:
        """Test resolving a normal relative path."""
        from sip_videogen.advisor.tools import _resolve_brand_path

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _resolve_brand_path("assets/logo.png")

        assert result == brand_dir / "assets/logo.png"

    def test_resolve_prevents_directory_escape(self, tmp_path: Path) -> None:
        """Test that path traversal is blocked."""
        from sip_videogen.advisor.tools import _resolve_brand_path

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ):
            result = _resolve_brand_path("../../../etc/passwd")

        assert result is None

    def test_resolve_no_active_brand(self) -> None:
        """Test that None is returned when no active brand."""
        from sip_videogen.advisor.tools import _resolve_brand_path

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _resolve_brand_path("test.txt")

        assert result is None


class TestGenerateImage:
    """Tests for _impl_generate_image function."""

    @pytest.mark.asyncio
    async def test_generate_image_mock(self, tmp_path: Path) -> None:
        """Test _impl_generate_image with mocked Gemini client."""
        from sip_videogen.advisor.tools import _impl_generate_image

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        # Mock the genai client and response
        mock_image = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data = True
        mock_part.as_image.return_value = mock_image

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        mock_settings = MagicMock()
        mock_settings.gemini_api_key = "test-key"

        with patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings), patch(
            "sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"
        ), patch(
            "sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir
        ), patch(
            "sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path
        ), patch(
            "google.genai.Client", return_value=mock_client
        ):
            result = await _impl_generate_image("A test image", aspect_ratio="1:1")

        # Should have called save on the image
        mock_image.save.assert_called_once()
        assert "test-brand" in result or "image_" in result
