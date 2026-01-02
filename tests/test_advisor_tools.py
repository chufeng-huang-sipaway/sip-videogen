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

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
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

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
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

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_read_file("image.png")

        assert "Binary file exists" in result
        assert "108 bytes" in result

    def test_read_file_not_found(self, tmp_path: Path) -> None:
        """Test reading non-existent file returns error."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_read_file("nonexistent.txt")

        assert "Error: File not found" in result

    def test_read_file_no_active_brand(self) -> None:
        """Test reading file with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_read_file

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_read_file("test.txt")

        assert "No active brand selected" in result

    def test_read_large_file_chunked(self, tmp_path: Path) -> None:
        """Test reading a large file returns first chunk with metadata."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "large.txt"
        # Create a file with 5000 characters
        content = "A" * 5000
        test_file.write_text(content)

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_read_file("large.txt")

        # Should return first chunk with metadata
        assert "[Chunk 1/3]" in result
        assert "(chars 1-2000 of 5000)" in result
        assert 'read_file("large.txt", chunk=1)' in result

    def test_read_file_second_chunk(self, tmp_path: Path) -> None:
        """Test reading second chunk of a large file."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "large.txt"
        # Create a file with 5000 characters (B's for first 2000, C's for next 2000, D's for rest)
        content = "B" * 2000 + "C" * 2000 + "D" * 1000
        test_file.write_text(content)

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_read_file("large.txt", chunk=1)

        # Should return second chunk
        assert "[Chunk 2/3]" in result
        assert "(chars 2001-4000 of 5000)" in result
        assert "C" * 100 in result  # Should contain C's
        assert 'read_file("large.txt", chunk=2)' in result

    def test_read_file_last_chunk(self, tmp_path: Path) -> None:
        """Test reading last chunk doesn't show next chunk hint."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "large.txt"
        content = "X" * 5000
        test_file.write_text(content)

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_read_file("large.txt", chunk=2)

        # Should be last chunk
        assert "[Chunk 3/3]" in result
        # Should NOT have hint for next chunk
        assert "chunk=3" not in result

    def test_read_file_invalid_chunk(self, tmp_path: Path) -> None:
        """Test reading invalid chunk number returns error."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "large.txt"
        test_file.write_text("X" * 5000)  # 3 chunks at 2000 per chunk

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_read_file("large.txt", chunk=10)

        assert "Error: chunk 10 does not exist" in result
        assert "File has 3 chunks (0-2)" in result

    def test_read_file_negative_chunk(self, tmp_path: Path) -> None:
        """Test reading with negative chunk returns error."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "test.txt"
        test_file.write_text("Some content")

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_read_file("test.txt", chunk=-1)

        assert "Error: chunk must be >= 0" in result

    def test_read_small_file_no_chunking(self, tmp_path: Path) -> None:
        """Test small files are returned without chunking metadata."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "small.txt"
        content = "Small content"
        test_file.write_text(content)

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_read_file("small.txt")

        # Should return content as-is without chunking metadata
        assert result == "Small content"
        assert "[Chunk" not in result

    def test_read_file_custom_chunk_size(self, tmp_path: Path) -> None:
        """Test reading with custom chunk size."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "test.txt"
        test_file.write_text("X" * 1000)  # 1000 characters

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            # With chunk_size=500, should have 2 chunks
            result = _impl_read_file("test.txt", chunk=0, chunk_size=500)

        assert "[Chunk 1/2]" in result
        assert "(chars 1-500 of 1000)" in result

    def test_read_file_chunk_size_validation(self, tmp_path: Path) -> None:
        """Test chunk_size is capped at min/max values."""
        from sip_videogen.advisor.tools import _impl_read_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        test_file = brand_dir / "test.txt"
        test_file.write_text("X" * 500)

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            # With chunk_size too small (< 100), should use 100
            result = _impl_read_file("test.txt", chunk=0, chunk_size=10)

        # File is 500 chars, with chunk_size=100, should have 5 chunks
        assert "[Chunk 1/5]" in result


class TestWriteFile:
    """Tests for _impl_write_file function."""

    def test_write_text_file(self, tmp_path: Path) -> None:
        """Test writing a text file."""
        from sip_videogen.advisor.tools import _impl_write_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_write_file("test.txt", "Hello, World!")

        assert "Successfully wrote" in result
        assert (brand_dir / "test.txt").read_text() == "Hello, World!"

    def test_write_creates_directories(self, tmp_path: Path) -> None:
        """Test that _impl_write_file creates parent directories."""
        from sip_videogen.advisor.tools import _impl_write_file

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
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

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
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

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_list_files("assets/")

        assert "logo.png" in result
        assert "banner.jpg" in result

    def test_list_empty_directory(self, tmp_path: Path) -> None:
        """Test listing an empty directory."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        (brand_dir / "empty").mkdir(parents=True)

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_list_files("empty/")

        assert "Directory is empty" in result

    def test_list_files_pagination_default_limit(self, tmp_path: Path) -> None:
        """Test that pagination shows 20 items by default."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        # Create 30 files
        for i in range(30):
            (brand_dir / f"file_{i:02d}.txt").write_text(f"content {i}")

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_list_files("")

        # Should show pagination info
        assert "showing 1-20 of 30" in result
        # Should include hint for more
        assert "offset=20" in result
        # Should contain first 20 files (file_00 through file_19)
        assert "file_00.txt" in result
        assert "file_19.txt" in result
        # Should NOT contain file_20
        assert "file_20.txt" not in result

    def test_list_files_pagination_with_offset(self, tmp_path: Path) -> None:
        """Test pagination with offset parameter."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        # Create 30 files
        for i in range(30):
            (brand_dir / f"file_{i:02d}.txt").write_text(f"content {i}")

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_list_files("", offset=20)

        # Should show pagination info for items 21-30
        assert "showing 21-30 of 30" in result
        # Should contain last 10 files
        assert "file_20.txt" in result
        assert "file_29.txt" in result
        # Should NOT contain earlier files
        assert "file_00.txt" not in result
        # Should NOT have "see more" hint (we're at the end)
        assert "offset=" not in result or "offset=20" not in result

    def test_list_files_pagination_custom_limit(self, tmp_path: Path) -> None:
        """Test pagination with custom limit parameter."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        # Create 15 files
        for i in range(15):
            (brand_dir / f"file_{i:02d}.txt").write_text(f"content {i}")

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_list_files("", limit=5)

        # Should show 5 items
        assert "showing 1-5 of 15" in result
        assert "offset=5" in result

    def test_list_files_pagination_offset_past_end(self, tmp_path: Path) -> None:
        """Test that offset past end returns error."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        # Create 5 files
        for i in range(5):
            (brand_dir / f"file_{i}.txt").write_text(f"content {i}")

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_list_files("", offset=100)

        assert "Error" in result
        assert "offset 100 is past end" in result
        assert "5 items" in result

    def test_list_files_pagination_invalid_params(self, tmp_path: Path) -> None:
        """Test that invalid params are handled gracefully."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        # Create 25 files
        for i in range(25):
            (brand_dir / f"file_{i:02d}.txt").write_text(f"content {i}")

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            # Negative limit should use default (20)
            result = _impl_list_files("", limit=-5)
            assert "showing 1-20 of 25" in result

            # Limit > 100 should be capped at 100
            result = _impl_list_files("", limit=500)
            assert "file_00.txt" in result  # Should still work

            # Negative offset should be treated as 0
            result = _impl_list_files("", offset=-10)
            assert "file_00.txt" in result

    def test_list_files_no_pagination_for_small_dirs(self, tmp_path: Path) -> None:
        """Test that small directories don't show pagination info."""
        from sip_videogen.advisor.tools import _impl_list_files

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        # Create just 3 files
        for i in range(3):
            (brand_dir / f"file_{i}.txt").write_text(f"content {i}")

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _impl_list_files("")

        # Should NOT show pagination info
        assert "showing" not in result
        assert "offset=" not in result
        # Should just show contents
        assert "Contents of /:" in result


class TestLoadBrand:
    """Tests for _impl_load_brand function."""

    def _create_mock_identity(self) -> MagicMock:
        """Create a mock BrandIdentityFull for testing."""
        mock_identity = MagicMock()
        mock_identity.core.name = "Test Brand"
        mock_identity.core.tagline = "Test tagline"
        mock_identity.core.mission = "Test mission"
        mock_identity.core.values = []
        mock_identity.positioning.market_category = "Test Category"
        mock_identity.positioning.unique_value_proposition = "Test UVP"
        mock_identity.positioning.positioning_statement = None
        mock_identity.voice.tone_attributes = ["friendly", "warm", "professional"]
        mock_identity.voice.personality = "Friendly"
        mock_identity.voice.key_messages = []
        # Create mock colors with hex values
        mock_color = MagicMock()
        mock_color.name = "Brand Blue"
        mock_color.hex = "#0066CC"
        mock_identity.visual.primary_colors = [mock_color]
        mock_identity.visual.style_keywords = ["modern", "clean", "minimal"]
        mock_identity.visual.overall_aesthetic = None
        mock_identity.audience.primary_summary = "Test audience"
        mock_identity.audience.demographics = None
        return mock_identity

    def test_load_brand_no_active_no_brands(self) -> None:
        """Test _impl_load_brand with no active brand and no brands available."""
        from sip_videogen.advisor.tools import _impl_load_brand

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.tools.storage_load_brand", return_value=None),
            patch(
                # list_brands is imported inside the function from sip_videogen.brands.storage
                "sip_videogen.brands.storage.list_brands",
                return_value=[],
            ),
        ):
            result = _impl_load_brand(slug=None)

        assert "No brands found" in result or "No active brand" in result

    def test_load_brand_not_found(self) -> None:
        """Test loading non-existent brand."""
        from sip_videogen.advisor.tools import _impl_load_brand

        with (
            patch("sip_videogen.advisor.tools.storage_load_brand", return_value=None),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="nonexistent"),
        ):
            result = _impl_load_brand(slug="nonexistent")

        assert "Error: Brand not found" in result

    def test_load_brand_summary_mode_default(self) -> None:
        """Test that load_brand returns summary by default."""
        from sip_videogen.advisor.tools import _impl_load_brand

        mock_identity = self._create_mock_identity()
        mock_assets = [
            {"category": "logo", "name": "primary", "path": "/test/logo/primary.png"},
            {"category": "mascot", "name": "benny", "path": "/test/mascot/benny.png"},
        ]

        with (
            patch("sip_videogen.advisor.tools.storage_load_brand", return_value=mock_identity),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.list_brand_assets", return_value=mock_assets),
            patch("sip_videogen.brands.storage.set_active_brand"),
        ):
            result = _impl_load_brand(slug="test-brand")  # Default is summary

        # Summary should include key info
        assert "Test Brand" in result
        assert "Test tagline" in result
        assert "Test Category" in result
        assert "friendly" in result.lower()  # Tone attributes
        assert "Brand Blue" in result  # Primary color
        assert "2 files" in result  # Asset count
        # Summary should include hint for full details
        assert "load_brand(detail_level='full')" in result
        # Summary should NOT include full sections
        assert "## Available Assets" not in result
        assert "## Brand Voice" not in result

    def test_load_brand_full_mode(self) -> None:
        """Test that load_brand with detail_level='full' returns complete context."""
        from sip_videogen.advisor.tools import _impl_load_brand

        mock_identity = self._create_mock_identity()
        mock_assets = [
            {"category": "logo", "name": "primary", "path": "/test/logo/primary.png"},
            {"category": "logo", "name": "secondary", "path": "/test/logo/secondary.png"},
            {"category": "mascot", "name": "benny", "path": "/test/mascot/benny.png"},
        ]

        with (
            patch("sip_videogen.advisor.tools.storage_load_brand", return_value=mock_identity),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.list_brand_assets", return_value=mock_assets),
            patch("sip_videogen.brands.storage.set_active_brand"),
        ):
            result = _impl_load_brand(slug="test-brand", detail_level="full")

        # Full mode should include all sections
        assert "## Available Assets" in result
        assert "logo" in result.lower()
        assert "mascot" in result.lower()
        # Full mode should NOT include hint for full details (already full)
        assert "load_brand(detail_level='full')" not in result

    def test_load_brand_summary_character_count(self) -> None:
        """Test that summary mode returns approximately 500 chars."""
        from sip_videogen.advisor.tools import _impl_load_brand

        mock_identity = self._create_mock_identity()
        mock_assets = [
            {"category": "logo", "name": "primary", "path": "/test/logo/primary.png"},
        ]

        with (
            patch("sip_videogen.advisor.tools.storage_load_brand", return_value=mock_identity),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.list_brand_assets", return_value=mock_assets),
            patch("sip_videogen.brands.storage.set_active_brand"),
        ):
            result = _impl_load_brand(slug="test-brand", detail_level="summary")

        # Summary should be concise
        assert len(result) < 800  # Allow some margin
        assert len(result) > 200  # But not too short


class TestResolveBrandPath:
    """Tests for _resolve_brand_path helper."""

    def test_resolve_normal_path(self, tmp_path: Path) -> None:
        """Test resolving a normal relative path."""
        from sip_videogen.advisor.tools import _resolve_brand_path

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
        ):
            result = _resolve_brand_path("assets/logo.png")

        assert result == brand_dir / "assets/logo.png"

    def test_resolve_prevents_directory_escape(self, tmp_path: Path) -> None:
        """Test that path traversal is blocked."""
        from sip_videogen.advisor.tools import _resolve_brand_path

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
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

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
            patch("google.genai.Client", return_value=mock_client),
        ):
            result = await _impl_generate_image("A test image", aspect_ratio="1:1")

        # Should have called save on the image
        mock_image.save.assert_called_once()
        assert "test-brand" in result or "image_" in result

    @pytest.mark.asyncio
    async def test_generate_image_with_product_slug(self, tmp_path: Path) -> None:
        """Test _impl_generate_image with product_slug auto-loads product's primary image."""
        from sip_videogen.advisor.tools import _impl_generate_image
        from sip_videogen.brands.models import ProductFull

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()
        # Create product image directory and file
        product_images_dir = brand_dir / "products" / "night-cream" / "images"
        product_images_dir.mkdir(parents=True)
        primary_image_path = product_images_dir / "main.png"
        primary_image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # Fake PNG
        secondary_image_path = product_images_dir / "texture.png"
        secondary_image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # Fake PNG

        # Create mock product
        mock_product = ProductFull(
            slug="night-cream",
            name="Night Cream",
            description="A luxurious night cream",
            images=[
                "products/night-cream/images/main.png",
                "products/night-cream/images/texture.png",
            ],
            primary_image="products/night-cream/images/main.png",
            attributes=[],
        )

        mock_settings = MagicMock()
        mock_settings.gemini_api_key = "test-key"
        mock_settings.sip_product_ref_images_per_product = 2

        # Mock generate_with_validation since validate_identity=True is auto-enabled
        expected_output = str(brand_dir / "assets" / "generated" / "image.png")

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch(
                "sip_videogen.advisor.validation.generate_with_validation",
                return_value=expected_output,
            ) as mock_validation,
            patch("google.genai.Client"),
        ):
            result = await _impl_generate_image(
                "A lifestyle shot featuring the night cream",
                aspect_ratio="1:1",
                product_slug="night-cream",
            )

        # Should have called generate_with_validation (validate_identity auto-enabled)
        mock_validation.assert_called_once()
        call_kwargs = mock_validation.call_args.kwargs
        # Verify reference_image_bytes was passed (loaded from product)
        assert call_kwargs["reference_image_bytes"] is not None
        assert len(call_kwargs["reference_image_bytes"]) > 0
        assert len(call_kwargs["reference_images_bytes"]) == 2
        assert result == expected_output

    @pytest.mark.asyncio
    async def test_generate_image_with_product_slug_not_found(self, tmp_path: Path) -> None:
        """Test _impl_generate_image with non-existent product returns error."""
        from sip_videogen.advisor.tools import _impl_generate_image

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        mock_settings = MagicMock()
        mock_settings.gemini_api_key = "test-key"

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
            patch("sip_videogen.advisor.tools.load_product", return_value=None),
        ):
            result = await _impl_generate_image(
                "A lifestyle shot",
                aspect_ratio="1:1",
                product_slug="nonexistent-product",
            )

        assert "Error: Product not found" in result
        assert "nonexistent-product" in result

    @pytest.mark.asyncio
    async def test_generate_image_with_product_slug_no_primary_image(self, tmp_path: Path) -> None:
        """Test _impl_generate_image with product having no primary image."""
        from sip_videogen.advisor.tools import _impl_generate_image
        from sip_videogen.brands.models import ProductFull

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        # Create mock product with no primary image
        mock_product = ProductFull(
            slug="night-cream",
            name="Night Cream",
            description="A luxurious night cream",
            images=[],
            primary_image="",  # No primary image
            attributes=[],
        )

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

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch("google.genai.Client", return_value=mock_client),
        ):
            await _impl_generate_image(
                "A lifestyle shot",
                aspect_ratio="1:1",
                product_slug="night-cream",
            )

        # Should proceed without reference (content is just the prompt string)
        call_args = mock_client.models.generate_content.call_args
        contents = call_args[1]["contents"]
        # Without reference image, contents should be just the prompt string
        assert contents == "A lifestyle shot"

    @pytest.mark.asyncio
    async def test_generate_image_with_product_slug_no_active_brand(self, tmp_path: Path) -> None:
        """Test _impl_generate_image with product_slug but no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_generate_image

        mock_settings = MagicMock()
        mock_settings.gemini_api_key = "test-key"

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
        ):
            result = await _impl_generate_image(
                "A lifestyle shot",
                aspect_ratio="1:1",
                product_slug="night-cream",
            )

        assert "Error: No active brand" in result

    @pytest.mark.asyncio
    async def test_generate_image_with_product_slug_reference_image_takes_precedence(
        self, tmp_path: Path
    ) -> None:
        """Test that explicit reference_image takes precedence over product_slug."""
        from sip_videogen.advisor.tools import _impl_generate_image

        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir()

        # Create explicit reference image
        explicit_ref_dir = brand_dir / "assets" / "references"
        explicit_ref_dir.mkdir(parents=True)
        explicit_ref_path = explicit_ref_dir / "custom.png"
        explicit_ref_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

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

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
            patch("sip_videogen.advisor.tools.load_product") as mock_load_product,
            patch("google.genai.Client", return_value=mock_client),
        ):
            await _impl_generate_image(
                "A lifestyle shot",
                aspect_ratio="1:1",
                reference_image="assets/references/custom.png",
                product_slug="night-cream",  # Should be ignored
            )

        # load_product should NOT be called because explicit reference_image is provided
        mock_load_product.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_image_with_active_project_tags_filename(self, tmp_path: Path) -> None:
        """Test _impl_generate_image tags filename with active project prefix."""
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

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
            patch(
                "sip_videogen.advisor.tools.get_active_project",
                return_value="christmas-campaign",
            ),
            patch("google.genai.Client", return_value=mock_client),
        ):
            await _impl_generate_image("A festive image", aspect_ratio="1:1")

        # Should save image with project prefix in filename
        mock_image.save.assert_called_once()
        saved_path = mock_image.save.call_args[0][0]
        assert "christmas-campaign__" in saved_path
        assert saved_path.endswith(".png")

    @pytest.mark.asyncio
    async def test_generate_image_without_active_project_no_prefix(self, tmp_path: Path) -> None:
        """Test _impl_generate_image without active project does not add prefix."""
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

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
            patch("sip_videogen.advisor.tools.get_active_project", return_value=None),
            patch("google.genai.Client", return_value=mock_client),
        ):
            await _impl_generate_image("A regular image", aspect_ratio="1:1")

        # Should save image WITHOUT project prefix
        mock_image.save.assert_called_once()
        saved_path = mock_image.save.call_args[0][0]
        # Filename should NOT contain __ (project separator)
        filename = Path(saved_path).name
        assert "__" not in filename or filename.count("__") == 0

    @pytest.mark.asyncio
    async def test_generate_image_explicit_filename_overridden_when_project_active(
        self, tmp_path: Path
    ) -> None:
        """Test _impl_generate_image with explicit filename is overridden when project is active.

        When a project is active, we always use our project-tagged filename format
        to ensure proper project association, even if the agent provides a filename.
        """
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

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir", return_value=brand_dir),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
            patch(
                "sip_videogen.advisor.tools.get_active_project",
                return_value="christmas-campaign",
            ) as mock_get_project,
            patch("google.genai.Client", return_value=mock_client),
        ):
            await _impl_generate_image(
                "A custom named image",
                aspect_ratio="1:1",
                filename="my_custom_image",  # Explicit filename - will be overridden
            )

        # get_active_project IS called to check if we need project tagging
        mock_get_project.assert_called_once_with("test-brand")
        # Should use project-tagged filename (explicit filename is overridden)
        mock_image.save.assert_called_once()
        saved_path = mock_image.save.call_args[0][0]
        # Filename should contain project prefix with double underscore
        filename = Path(saved_path).name
        assert filename.startswith("christmas-campaign__")
        assert filename.endswith(".png")

    @pytest.mark.asyncio
    async def test_generate_image_no_brand_no_project_check(self, tmp_path: Path) -> None:
        """Test _impl_generate_image without active brand skips project check."""
        from sip_videogen.advisor.tools import _impl_generate_image

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

        with (
            patch("sip_videogen.advisor.tools.get_settings", return_value=mock_settings),
            patch("sip_videogen.advisor.tools.get_active_brand", return_value=None),
            patch("sip_videogen.advisor.tools.get_brands_dir", return_value=tmp_path),
            patch(
                "sip_videogen.advisor.tools.get_active_project"
            ) as mock_get_project,
            patch("google.genai.Client", return_value=mock_client),
        ):
            await _impl_generate_image("An image without brand", aspect_ratio="1:1")

        # get_active_project should NOT be called when no brand is active
        mock_get_project.assert_not_called()


class TestGenerateOutputFilename:
    """Tests for _generate_output_filename helper function."""

    def test_generate_output_filename_with_project(self) -> None:
        """Test filename generation with project prefix."""
        from sip_videogen.advisor.tools import _generate_output_filename

        filename = _generate_output_filename("christmas-campaign")

        # Should have project prefix followed by __
        assert filename.startswith("christmas-campaign__")
        # Should have timestamp format (YYYYMMDD_HHMMSS)
        parts = filename.split("__")[1]
        assert "_" in parts
        # Should have 8-char hash suffix
        hash_part = parts.split("_")[-1]
        assert len(hash_part) == 8
        assert hash_part.isalnum()

    def test_generate_output_filename_without_project(self) -> None:
        """Test filename generation without project prefix."""
        from sip_videogen.advisor.tools import _generate_output_filename

        filename = _generate_output_filename(None)

        # Should NOT have __ separator (no project prefix)
        # The format is: {timestamp}_{hash}
        parts = filename.split("_")
        # Should have timestamp parts + hash (at least 3 parts: YYYYMMDD, HHMMSS, hash)
        assert len(parts) >= 3
        # Last part should be 8-char hash
        assert len(parts[-1]) == 8
        assert parts[-1].isalnum()
        # Should NOT have double underscore
        assert "__" not in filename

    def test_generate_output_filename_unique(self) -> None:
        """Test that filenames are unique (different hash each call)."""
        from sip_videogen.advisor.tools import _generate_output_filename

        filename1 = _generate_output_filename("my-project")
        filename2 = _generate_output_filename("my-project")

        # Should be different due to unique hash (unless called in same instant)
        # Extract hash parts
        hash1 = filename1.split("_")[-1]
        hash2 = filename2.split("_")[-1]
        assert hash1 != hash2


class TestListProducts:
    """Tests for _impl_list_products function."""

    def test_list_products_no_active_brand(self) -> None:
        """Test list_products with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_list_products

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_list_products()

        assert "Error: No active brand selected" in result

    def test_list_products_empty(self) -> None:
        """Test list_products with no products returns helpful message."""
        from sip_videogen.advisor.tools import _impl_list_products

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_list_products", return_value=[]),
        ):
            result = _impl_list_products()

        assert "No products found" in result
        assert "test-brand" in result

    def test_list_products_with_products(self) -> None:
        """Test list_products returns formatted product list."""
        from datetime import datetime

        from sip_videogen.advisor.tools import _impl_list_products
        from sip_videogen.brands.models import ProductSummary

        mock_products = [
            ProductSummary(
                slug="night-cream",
                name="Night Cream",
                description="A luxurious night cream for deep hydration.",
                primary_image="products/night-cream/images/main.png",
                attribute_count=5,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            ProductSummary(
                slug="day-serum",
                name="Day Serum",
                description="Lightweight serum for daytime protection.",
                primary_image="",
                attribute_count=0,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        ]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_list_products", return_value=mock_products),
        ):
            result = _impl_list_products()

        assert "Products for brand 'test-brand'" in result
        assert "**Night Cream**" in result
        assert "`night-cream`" in result
        assert "5 attributes" in result
        assert "primary image:" in result
        assert "**Day Serum**" in result
        assert "get_product_detail" in result

    def test_list_products_truncates_long_description(self) -> None:
        """Test list_products truncates long descriptions."""
        from datetime import datetime

        from sip_videogen.advisor.tools import _impl_list_products
        from sip_videogen.brands.models import ProductSummary

        mock_products = [
            ProductSummary(
                slug="verbose-product",
                name="Verbose Product",
                description="A" * 200,  # Very long description
                primary_image="",
                attribute_count=0,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        ]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_list_products", return_value=mock_products),
        ):
            result = _impl_list_products()

        # Should truncate and add ellipsis
        assert "..." in result
        assert "A" * 200 not in result


class TestListProjects:
    """Tests for _impl_list_projects function."""

    def test_list_projects_no_active_brand(self) -> None:
        """Test list_projects with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_list_projects

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_list_projects()

        assert "Error: No active brand selected" in result

    def test_list_projects_empty(self) -> None:
        """Test list_projects with no projects returns helpful message."""
        from sip_videogen.advisor.tools import _impl_list_projects

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_list_projects", return_value=[]),
        ):
            result = _impl_list_projects()

        assert "No projects found" in result
        assert "test-brand" in result

    def test_list_projects_with_projects(self) -> None:
        """Test list_projects returns formatted project list."""
        from datetime import datetime

        from sip_videogen.advisor.tools import _impl_list_projects
        from sip_videogen.brands.models import ProjectStatus, ProjectSummary

        mock_projects = [
            ProjectSummary(
                slug="christmas-campaign",
                name="Christmas Campaign",
                status=ProjectStatus.ACTIVE,
                asset_count=12,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            ProjectSummary(
                slug="summer-sale",
                name="Summer Sale",
                status=ProjectStatus.ARCHIVED,
                asset_count=8,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        ]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_list_projects", return_value=mock_projects),
            patch(
                "sip_videogen.brands.storage.get_active_project",
                return_value="christmas-campaign",
            ),
        ):
            result = _impl_list_projects()

        assert "Projects for brand 'test-brand'" in result
        assert "**Christmas Campaign**" in result
        assert "`christmas-campaign`" in result
        assert "[active]" in result
        assert "12 assets" in result
        assert "**Summer Sale**" in result
        assert "[archived]" in result
        assert "get_project_detail" in result

    def test_list_projects_shows_active_marker(self) -> None:
        """Test list_projects shows active marker for active project."""
        from datetime import datetime

        from sip_videogen.advisor.tools import _impl_list_projects
        from sip_videogen.brands.models import ProjectStatus, ProjectSummary

        mock_projects = [
            ProjectSummary(
                slug="christmas-campaign",
                name="Christmas Campaign",
                status=ProjectStatus.ACTIVE,
                asset_count=12,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        ]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_list_projects", return_value=mock_projects),
            patch(
                "sip_videogen.brands.storage.get_active_project",
                return_value="christmas-campaign",
            ),
        ):
            result = _impl_list_projects()

        assert "ACTIVE" in result


class TestGetProductDetail:
    """Tests for _impl_get_product_detail function."""

    def test_get_product_detail_no_active_brand(self) -> None:
        """Test get_product_detail with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_get_product_detail

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_get_product_detail("night-cream")

        assert "Error: No active brand selected" in result

    def test_get_product_detail_not_found(self) -> None:
        """Test get_product_detail with non-existent product returns error."""
        from sip_videogen.advisor.tools import _impl_get_product_detail

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.get_product_full", return_value=None),
        ):
            result = _impl_get_product_detail("nonexistent")

        assert "Error: Product 'nonexistent' not found" in result
        assert "test-brand" in result

    def test_get_product_detail_returns_formatted_output(self) -> None:
        """Test get_product_detail returns properly formatted markdown."""
        from datetime import datetime

        from sip_videogen.advisor.tools import _impl_get_product_detail
        from sip_videogen.brands.models import ProductAttribute, ProductFull

        mock_product = ProductFull(
            slug="night-cream",
            name="Night Cream",
            description="A luxurious night cream for deep hydration and skin repair.",
            images=[
                "products/night-cream/images/main.png",
                "products/night-cream/images/side.png",
            ],
            primary_image="products/night-cream/images/main.png",
            attributes=[
                ProductAttribute(key="size", value="50ml", category="measurements"),
                ProductAttribute(key="texture", value="rich cream", category="texture"),
            ],
            created_at=datetime(2024, 1, 15, 10, 30),
            updated_at=datetime(2024, 3, 20, 14, 45),
        )

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.get_product_full", return_value=mock_product),
        ):
            result = _impl_get_product_detail("night-cream")

        # Check header
        assert "# Product: Night Cream" in result
        assert "`night-cream`" in result

        # Check description section
        assert "## Description" in result
        assert "luxurious night cream" in result

        # Check attributes section
        assert "## Attributes" in result
        assert "**size** (measurements): 50ml" in result
        assert "**texture** (texture): rich cream" in result

        # Check images section
        assert "## Images" in result
        assert "products/night-cream/images/main.png" in result
        assert "PRIMARY" in result

        # Check metadata
        assert "## Metadata" in result
        assert "Created:" in result
        assert "Updated:" in result


class TestGetProjectDetail:
    """Tests for _impl_get_project_detail function."""

    def test_get_project_detail_no_active_brand(self) -> None:
        """Test get_project_detail with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_get_project_detail

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_get_project_detail("christmas-campaign")

        assert "Error: No active brand selected" in result

    def test_get_project_detail_not_found(self) -> None:
        """Test get_project_detail with non-existent project returns error."""
        from sip_videogen.advisor.tools import _impl_get_project_detail

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.get_project_full", return_value=None),
        ):
            result = _impl_get_project_detail("nonexistent")

        assert "Error: Project 'nonexistent' not found" in result
        assert "test-brand" in result

    def test_get_project_detail_returns_formatted_output(self) -> None:
        """Test get_project_detail returns properly formatted markdown."""
        from datetime import datetime

        from sip_videogen.advisor.tools import _impl_get_project_detail
        from sip_videogen.brands.models import ProjectFull, ProjectStatus

        mock_project = ProjectFull(
            slug="christmas-campaign",
            name="Christmas Campaign",
            status=ProjectStatus.ACTIVE,
            instructions="## Holiday Guidelines\n- Use festive colors\n- Include holiday imagery",
            created_at=datetime(2024, 11, 1, 9, 0),
            updated_at=datetime(2024, 11, 15, 16, 30),
        )

        mock_assets = [
            "generated/christmas-campaign__20241115_120000_abc123.png",
            "generated/christmas-campaign__20241115_130000_def456.png",
        ]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.get_project_full", return_value=mock_project),
            patch(
                "sip_videogen.brands.storage.get_active_project",
                return_value="christmas-campaign",
            ),
            patch(
                "sip_videogen.brands.storage.list_project_assets",
                return_value=mock_assets,
            ),
        ):
            result = _impl_get_project_detail("christmas-campaign")

        # Check header
        assert "# Project: Christmas Campaign" in result
        assert "`christmas-campaign`" in result

        # Check status with active marker
        assert "**Status**: active" in result
        assert "ACTIVE" in result

        # Check instructions section
        assert "## Instructions" in result
        assert "Holiday Guidelines" in result
        assert "festive colors" in result

        # Check assets section
        assert "## Generated Assets" in result
        assert "2 generated assets" in result

        # Check metadata
        assert "## Metadata" in result
        assert "Created:" in result
        assert "Updated:" in result

    def test_get_project_detail_no_instructions(self) -> None:
        """Test get_project_detail with empty instructions shows placeholder."""
        from datetime import datetime

        from sip_videogen.advisor.tools import _impl_get_project_detail
        from sip_videogen.brands.models import ProjectFull, ProjectStatus

        mock_project = ProjectFull(
            slug="quick-project",
            name="Quick Project",
            status=ProjectStatus.ACTIVE,
            instructions="",  # Empty instructions
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.get_project_full", return_value=mock_project),
            patch("sip_videogen.brands.storage.get_active_project", return_value=None),
            patch("sip_videogen.brands.storage.list_project_assets", return_value=[]),
        ):
            result = _impl_get_project_detail("quick-project")

        assert "*No instructions set.*" in result

    def test_get_project_detail_inactive_project(self) -> None:
        """Test get_project_detail for inactive project has no active marker."""
        from datetime import datetime

        from sip_videogen.advisor.tools import _impl_get_project_detail
        from sip_videogen.brands.models import ProjectFull, ProjectStatus

        mock_project = ProjectFull(
            slug="summer-sale",
            name="Summer Sale",
            status=ProjectStatus.ARCHIVED,
            instructions="Summer promotion guidelines.",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.get_project_full", return_value=mock_project),
            # Different active project
            patch(
                "sip_videogen.brands.storage.get_active_project",
                return_value="christmas-campaign",
            ),
            patch("sip_videogen.brands.storage.list_project_assets", return_value=[]),
        ):
            result = _impl_get_project_detail("summer-sale")

        # Should show archived status without ACTIVE marker
        assert "archived" in result
        # The line with status should NOT have ACTIVE marker
        status_line = [line for line in result.split("\n") if "**Status**" in line][0]
        assert "ACTIVE" not in status_line

    def test_get_project_detail_truncates_many_assets(self) -> None:
        """Test get_project_detail only shows first 10 assets."""
        from datetime import datetime

        from sip_videogen.advisor.tools import _impl_get_project_detail
        from sip_videogen.brands.models import ProjectFull, ProjectStatus

        mock_project = ProjectFull(
            slug="prolific-project",
            name="Prolific Project",
            status=ProjectStatus.ACTIVE,
            instructions="Instructions.",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )

        # Create 15 mock assets
        mock_assets = [f"generated/prolific-project__{i:04d}.png" for i in range(15)]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.brands.memory.get_project_full", return_value=mock_project),
            patch("sip_videogen.brands.storage.get_active_project", return_value=None),
            patch(
                "sip_videogen.brands.storage.list_project_assets",
                return_value=mock_assets,
            ),
        ):
            result = _impl_get_project_detail("prolific-project")

        # Should show 15 assets
        assert "15 generated assets" in result
        # Should indicate more assets
        assert "...and 5 more" in result


class TestCreateProduct:
    """Tests for _impl_create_product function."""

    def test_create_product_success(self) -> None:
        """Test creating a product successfully."""
        from sip_videogen.advisor.tools import _impl_create_product

        mock_product = MagicMock()
        mock_product.name = "Test Product"

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_create_product"),
            patch("sip_videogen.advisor.tools.load_product", return_value=None),
        ):
            result = _impl_create_product(
                name="Test Product",
                description="A test product",
                attributes=[
                    {"key": "size", "value": "50ml", "category": "measurements"},
                    {"key": "color", "value": "blue", "category": "appearance"},
                ],
            )

        assert "Created product **Test Product**" in result
        assert "`test-product`" in result

    def test_create_product_no_active_brand(self) -> None:
        """Test create_product with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_create_product

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_create_product(name="Test Product")

        assert "Error: No active brand selected" in result

    def test_create_product_slug_already_exists(self) -> None:
        """Test create_product with existing slug returns error."""
        from sip_videogen.advisor.tools import _impl_create_product

        mock_product = MagicMock()

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
        ):
            result = _impl_create_product(name="Test Product")

        assert "Error: Product 'test-product' already exists" in result

    def test_create_product_invalid_name_generates_bad_slug(self) -> None:
        """Test create_product with name that generates invalid slug."""
        from sip_videogen.advisor.tools import _impl_create_product

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product", return_value=None),
        ):
            result = _impl_create_product(name="")

        assert "Error: Cannot generate valid slug" in result

    def test_create_product_with_empty_attributes(self) -> None:
        """Test create_product with empty attributes list."""
        from sip_videogen.advisor.tools import _impl_create_product

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_create_product"),
            patch("sip_videogen.advisor.tools.load_product", return_value=None),
        ):
            result = _impl_create_product(
                name="Test Product",
                description="A test product",
                attributes=[],
            )

        assert "Created product **Test Product**" in result

    def test_create_product_with_attributes_default_category(self) -> None:
        """Test create_product assigns default category to attributes without category."""
        from sip_videogen.advisor.tools import _impl_create_product

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_create_product") as mock_create,
            patch("sip_videogen.advisor.tools.load_product", return_value=None),
        ):
            result = _impl_create_product(
                name="Test Product",
                attributes=[
                    {"key": "size", "value": "50ml"},  # No category specified
                    {"key": "color", "value": "blue", "category": "appearance"},
                ],
            )

        assert "Created product **Test Product**" in result
        # Verify that storage_create_product was called with ProductFull having attributes
        _, created_product = mock_create.call_args[0]
        assert len(created_product.attributes) == 2
        # Check that default category was assigned
        size_attr = next(attr for attr in created_product.attributes if attr.key == "size")
        assert size_attr.category == "general"
        # Check that explicit category was preserved
        color_attr = next(attr for attr in created_product.attributes if attr.key == "color")
        assert color_attr.category == "appearance"


class TestUpdateProduct:
    """Tests for _impl_update_product function."""

    def test_update_product_success(self) -> None:
        """Test updating a product successfully."""
        from sip_videogen.advisor.tools import _impl_update_product

        mock_product = MagicMock()
        mock_product.name = "Original Product"
        mock_product.description = "Original description"
        mock_product.attributes = []

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_save_product"),
        ):
            result = _impl_update_product(
                product_slug="test-product",
                name="Updated Product",
                description="Updated description",
                attributes=[
                    {"key": "size", "value": "100ml", "category": "measurements"},
                ],
            )

        assert "Updated product **Updated Product**" in result
        assert "`test-product`" in result

    def test_update_product_no_active_brand(self) -> None:
        """Test update_product with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_update_product

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_update_product(product_slug="test-product")

        assert "Error: No active brand selected" in result

    def test_update_product_not_found(self) -> None:
        """Test update_product with non-existent product returns error."""
        from sip_videogen.advisor.tools import _impl_update_product

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product", return_value=None),
        ):
            result = _impl_update_product(product_slug="nonexistent")

        assert "Error: Product 'nonexistent' not found" in result

    def test_update_product_merge_attributes(self) -> None:
        """Test update_product merges attributes by default."""
        from sip_videogen.advisor.tools import _impl_update_product
        from sip_videogen.brands.models import ProductAttribute

        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.description = "Original description"
        mock_product.attributes = [
            ProductAttribute(key="size", value="50ml", category="measurements"),
            ProductAttribute(key="color", value="red", category="appearance"),
        ]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_save_product"),
        ):
            result = _impl_update_product(
                product_slug="test-product",
                description="Updated description",
                attributes=[
                    {"key": "size", "value": "100ml", "category": "measurements"},
                    {"key": "material", "value": "cotton", "category": "materials"},
                ],
                replace_attributes=False,
            )

        assert "Updated product **Test Product**" in result
        # Verify attributes were merged
        assert len(mock_product.attributes) == 3
        # Check that existing attribute was updated
        size_attr = next(attr for attr in mock_product.attributes if attr.key == "size")
        assert size_attr.value == "100ml"
        # Check that new attribute was added
        material_attr = next(attr for attr in mock_product.attributes if attr.key == "material")
        assert material_attr.value == "cotton"

    def test_update_product_replace_attributes(self) -> None:
        """Test update_product replaces all attributes when replace_attributes=True."""
        from sip_videogen.advisor.tools import _impl_update_product
        from sip_videogen.brands.models import ProductAttribute

        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.attributes = [
            ProductAttribute(key="size", value="50ml", category="measurements"),
            ProductAttribute(key="color", value="red", category="appearance"),
        ]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_save_product"),
        ):
            result = _impl_update_product(
                product_slug="test-product",
                attributes=[
                    {"key": "material", "value": "cotton", "category": "materials"},
                ],
                replace_attributes=True,
            )

        assert "Updated product **Test Product**" in result
        # Verify all attributes were replaced
        assert len(mock_product.attributes) == 1
        material_attr = mock_product.attributes[0]
        assert material_attr.key == "material"
        assert material_attr.value == "cotton"

    def test_update_product_case_insensitive_merge(self) -> None:
        """Test update_product merges attributes case-insensitively."""
        from sip_videogen.advisor.tools import _impl_update_product
        from sip_videogen.brands.models import ProductAttribute

        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.attributes = [
            ProductAttribute(key="SIZE", value="50ml", category="MEASUREMENTS"),
        ]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_save_product"),
        ):
            result = _impl_update_product(
                product_slug="test-product",
                attributes=[
                    {"key": "size", "value": "100ml", "category": "measurements"},
                ],
                replace_attributes=False,
            )

        assert "Updated product **Test Product**" in result
        # Verify the existing attribute was updated (not duplicated)
        assert len(mock_product.attributes) == 1
        size_attr = mock_product.attributes[0]
        assert size_attr.value == "100ml"

    def test_update_product_invalid_slug(self) -> None:
        """Test update_product with invalid slug returns error."""
        from sip_videogen.advisor.tools import _impl_update_product

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
        ):
            result = _impl_update_product(product_slug="../etc/passwd")

        assert "Error: Invalid slug" in result


class TestAddProductImage:
    """Tests for _impl_add_product_image function."""
    @pytest.mark.asyncio
    async def test_add_product_image_success(self,tmp_path:Path)->None:
        """Test adding a product image successfully."""
        import io
        from PIL import Image
        from sip_videogen.advisor.tools import _impl_add_product_image
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        image_file=uploads_dir/"photo.jpg"
        buf=io.BytesIO()
        Image.new("RGB",(1,1),color=(255,0,0)).save(buf,format="JPEG")
        image_file.write_bytes(buf.getvalue())
        mock_product=MagicMock()
        mock_product.name="Test Product"
        mock_product.images=[]
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
            patch("sip_videogen.advisor.tools.load_product",return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_add_product_image",return_value="products/test-product/images/photo.jpg"),
        ):
            mock_resolve.return_value=image_file
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg")
        assert "Added image `photo.jpg` to product **Test Product**" in result
        assert "`test-product`" in result
    @pytest.mark.asyncio
    async def test_add_product_image_no_active_brand(self)->None:
        """Test add_product_image with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_add_product_image
        with patch("sip_videogen.advisor.tools.get_active_brand",return_value=None):
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg")

        assert "Error: No active brand selected" in result
    @pytest.mark.asyncio
    async def test_add_product_image_invalid_slug(self)->None:
        """Test add_product_image with invalid product_slug returns error."""
        from sip_videogen.advisor.tools import _impl_add_product_image
        with patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"):
            result=await _impl_add_product_image(product_slug="../etc/passwd",image_path="uploads/photo.jpg")
        assert "Error: Invalid slug" in result
    @pytest.mark.asyncio
    async def test_add_product_image_not_in_uploads(self)->None:
        """Test add_product_image with path not in uploads/ returns error."""
        from sip_videogen.advisor.tools import _impl_add_product_image
        with patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"):
            result=await _impl_add_product_image(product_slug="test-product",image_path="assets/logo.png")
        assert "Error: image_path must be within the uploads/ folder" in result
    @pytest.mark.asyncio
    async def test_add_product_image_not_found(self,tmp_path:Path)->None:
        """Test add_product_image with non-existent file returns error."""
        from sip_videogen.advisor.tools import _impl_add_product_image
        missing_file=tmp_path/"uploads"/"photo.jpg"
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
        ):
            mock_resolve.return_value=missing_file
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg")
        assert "Error: File not found" in result
    @pytest.mark.asyncio
    async def test_add_product_image_too_large(self,tmp_path:Path)->None:
        """Test add_product_image with file too large returns error."""
        from sip_videogen.advisor.tools import _impl_add_product_image
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        image_file=uploads_dir/"photo.jpg"
        image_file.write_bytes(b"x"*(2*1024*1024))
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
            patch("sip_videogen.advisor.tools.MAX_PRODUCT_IMAGE_SIZE_BYTES",1*1024*1024),
        ):
            mock_resolve.return_value=image_file
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg")
        assert "Error: Image too large" in result
    @pytest.mark.asyncio
    async def test_add_product_image_invalid_format(self,tmp_path:Path)->None:
        """Test add_product_image with invalid file format returns error."""
        from sip_videogen.advisor.tools import _impl_add_product_image
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        invalid_file=uploads_dir/"photo.txt"
        invalid_file.write_bytes(b"not an image")
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
        ):
            mock_resolve.return_value=invalid_file
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.txt")
        assert "Error: Invalid file extension" in result
    @pytest.mark.asyncio
    async def test_add_product_image_set_as_primary(self,tmp_path:Path)->None:
        """Test add_product_image with set_as_primary=True triggers auto-analysis."""
        import io
        from PIL import Image
        from sip_videogen.advisor.tools import _impl_add_product_image
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        image_file=uploads_dir/"photo.jpg"
        buf=io.BytesIO()
        Image.new("RGB",(1,1),color=(255,0,0)).save(buf,format="JPEG")
        image_file.write_bytes(buf.getvalue())
        mock_product=MagicMock()
        mock_product.name="Test Product"
        mock_product.images=[]
        mock_product.packaging_text=None
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
            patch("sip_videogen.advisor.tools.load_product",return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_add_product_image",return_value="products/test-product/images/photo.jpg"),
            patch("sip_videogen.advisor.tools.storage_set_primary_product_image",return_value=True),
            patch("sip_videogen.advisor.tools.get_brand_dir",return_value=tmp_path),
            patch("sip_videogen.advisor.tools.storage_save_product"),
        ):
            mock_resolve.return_value=image_file
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg",set_as_primary=True)
        assert "set as primary image" in result
    @pytest.mark.asyncio
    async def test_add_product_image_filename_collision(self,tmp_path:Path)->None:
        """Test add_product_image handles filename collision with timestamp."""
        import io
        from datetime import datetime
        from PIL import Image
        from sip_videogen.advisor.tools import _impl_add_product_image
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        image_file=uploads_dir/"photo.jpg"
        buf=io.BytesIO()
        Image.new("RGB",(1,1),color=(255,0,0)).save(buf,format="JPEG")
        image_file.write_bytes(buf.getvalue())
        mock_product=MagicMock()
        mock_product.name="Test Product"
        mock_product.images=["products/test-product/images/photo.jpg"]
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
            patch("sip_videogen.advisor.tools.load_product",return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_add_product_image",return_value="products/test-product/images/photo_20241215_120000.jpg"),
        ):
            mock_resolve.return_value=image_file
            with patch("sip_videogen.advisor.tools.datetime") as mock_datetime:
                mock_now=datetime(2024,12,15,12,0,0)
                mock_datetime.now.return_value=mock_now
                result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg")
        assert "photo_20241215_120000.jpg" in result
    @pytest.mark.asyncio
    async def test_add_product_image_rejects_non_reference_when_analyzed(self,tmp_path:Path)->None:
        """Test add_product_image refuses screenshots/documents when analysis cache exists."""
        import io
        import json
        from PIL import Image
        from sip_videogen.advisor.tools import _impl_add_product_image
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        image_file=uploads_dir/"screenshot.jpg"
        buf=io.BytesIO()
        Image.new("RGB",(1,1),color=(255,255,255)).save(buf,format="JPEG")
        image_file.write_bytes(buf.getvalue())
        (uploads_dir/"screenshot.jpg.analysis.json").write_text(json.dumps({"image_type":"screenshot","is_suitable_reference":False}))
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path",return_value=image_file),
        ):
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/screenshot.jpg")
        assert "not suitable as a product reference image" in result
        assert "allow_non_reference=True" in result
    @pytest.mark.asyncio
    async def test_add_product_image_allows_non_reference_with_override(self,tmp_path:Path)->None:
        """Test add_product_image can be forced to store a non-reference image."""
        import io
        import json
        from PIL import Image
        from sip_videogen.advisor.tools import _impl_add_product_image
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        image_file=uploads_dir/"screenshot.jpg"
        buf=io.BytesIO()
        Image.new("RGB",(1,1),color=(255,255,255)).save(buf,format="JPEG")
        image_file.write_bytes(buf.getvalue())
        (uploads_dir/"screenshot.jpg.analysis.json").write_text(json.dumps({"image_type":"screenshot","is_suitable_reference":False}))
        mock_product=MagicMock()
        mock_product.name="Test Product"
        mock_product.images=[]
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path",return_value=image_file),
            patch("sip_videogen.advisor.tools.load_product",return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_add_product_image",return_value="products/test-product/images/screenshot.jpg"),
        ):
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/screenshot.jpg",allow_non_reference=True)
        assert "Added image `screenshot.jpg` to product **Test Product**" in result
    @pytest.mark.asyncio
    async def test_add_product_image_auto_analysis_triggers(self,tmp_path:Path)->None:
        """Test auto-analysis triggers on primary image add when packaging_text is None."""
        import io
        from unittest.mock import AsyncMock
        from PIL import Image
        from sip_videogen.advisor.tools import _impl_add_product_image
        from sip_videogen.brands.models import PackagingTextDescription,PackagingTextElement
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        products_dir=tmp_path/"products"/"test-product"/"images"
        products_dir.mkdir(parents=True)
        image_file=uploads_dir/"photo.jpg"
        buf=io.BytesIO()
        Image.new("RGB",(100,100),color=(255,0,0)).save(buf,format="JPEG")
        image_file.write_bytes(buf.getvalue())
        #Copy to products dir for full_path resolution
        (products_dir/"photo.jpg").write_bytes(buf.getvalue())
        mock_product=MagicMock()
        mock_product.name="Test Product"
        mock_product.images=[]
        mock_product.packaging_text=None
        mock_analysis=PackagingTextDescription(summary="Test summary",elements=[PackagingTextElement(text="BRAND",role="brand_name")],source_image="",generated_at=None)
        mock_analyze=AsyncMock(return_value=mock_analysis)
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
            patch("sip_videogen.advisor.tools.load_product",return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_add_product_image",return_value="products/test-product/images/photo.jpg"),
            patch("sip_videogen.advisor.tools.storage_set_primary_product_image",return_value=True),
            patch("sip_videogen.advisor.tools.get_brand_dir",return_value=tmp_path),
            patch("sip_videogen.advisor.tools.storage_save_product") as mock_save,
            patch("sip_videogen.advisor.image_analyzer.analyze_packaging_text",mock_analyze),
        ):
            mock_resolve.return_value=image_file
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg",set_as_primary=True)
        assert "Auto-extracted 1 text elements from packaging" in result
        mock_analyze.assert_called_once()
        mock_save.assert_called()
    @pytest.mark.asyncio
    async def test_add_product_image_auto_analysis_skips_human_edited(self,tmp_path:Path)->None:
        """Test auto-analysis skips if packaging_text is human-edited."""
        import io
        from unittest.mock import AsyncMock
        from PIL import Image
        from sip_videogen.advisor.tools import _impl_add_product_image
        from sip_videogen.brands.models import PackagingTextDescription
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        image_file=uploads_dir/"photo.jpg"
        buf=io.BytesIO()
        Image.new("RGB",(1,1),color=(255,0,0)).save(buf,format="JPEG")
        image_file.write_bytes(buf.getvalue())
        mock_product=MagicMock()
        mock_product.name="Test Product"
        mock_product.images=[]
        #Existing human-edited packaging_text with different source_image
        mock_product.packaging_text=PackagingTextDescription(summary="Human edited",elements=[],source_image="old-image.jpg",is_human_edited=True)
        mock_analyze=AsyncMock()
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
            patch("sip_videogen.advisor.tools.load_product",return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_add_product_image",return_value="products/test-product/images/photo.jpg"),
            patch("sip_videogen.advisor.tools.storage_set_primary_product_image",return_value=True),
            patch("sip_videogen.advisor.tools.get_brand_dir",return_value=tmp_path),
            patch("sip_videogen.advisor.image_analyzer.analyze_packaging_text",mock_analyze),
        ):
            mock_resolve.return_value=image_file
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg",set_as_primary=True)
        assert "set as primary image" in result
        assert "Auto-extracted" not in result
        mock_analyze.assert_not_called()
    @pytest.mark.asyncio
    async def test_add_product_image_auto_analysis_skips_same_source(self,tmp_path:Path)->None:
        """Test auto-analysis skips if source_image matches new primary."""
        import io
        from unittest.mock import AsyncMock
        from PIL import Image
        from sip_videogen.advisor.tools import _impl_add_product_image
        from sip_videogen.brands.models import PackagingTextDescription
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        image_file=uploads_dir/"photo.jpg"
        buf=io.BytesIO()
        Image.new("RGB",(1,1),color=(255,0,0)).save(buf,format="JPEG")
        image_file.write_bytes(buf.getvalue())
        mock_product=MagicMock()
        mock_product.name="Test Product"
        mock_product.images=[]
        #Existing packaging_text with same source_image as new primary
        mock_product.packaging_text=PackagingTextDescription(summary="Already analyzed",elements=[],source_image="products/test-product/images/photo.jpg",is_human_edited=False)
        mock_analyze=AsyncMock()
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
            patch("sip_videogen.advisor.tools.load_product",return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_add_product_image",return_value="products/test-product/images/photo.jpg"),
            patch("sip_videogen.advisor.tools.storage_set_primary_product_image",return_value=True),
            patch("sip_videogen.advisor.tools.get_brand_dir",return_value=tmp_path),
            patch("sip_videogen.advisor.image_analyzer.analyze_packaging_text",mock_analyze),
        ):
            mock_resolve.return_value=image_file
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg",set_as_primary=True)
        assert "set as primary image" in result
        assert "Auto-extracted" not in result
        mock_analyze.assert_not_called()
    @pytest.mark.asyncio
    async def test_add_product_image_auto_analysis_failure_doesnt_break(self,tmp_path:Path)->None:
        """Test auto-analysis failure doesn't break image add."""
        import io
        from unittest.mock import AsyncMock
        from PIL import Image
        from sip_videogen.advisor.tools import _impl_add_product_image
        uploads_dir=tmp_path/"uploads"
        uploads_dir.mkdir()
        image_file=uploads_dir/"photo.jpg"
        buf=io.BytesIO()
        Image.new("RGB",(1,1),color=(255,0,0)).save(buf,format="JPEG")
        image_file.write_bytes(buf.getvalue())
        mock_product=MagicMock()
        mock_product.name="Test Product"
        mock_product.images=[]
        mock_product.packaging_text=None
        mock_analyze=AsyncMock(side_effect=Exception("API error"))
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools._resolve_brand_path") as mock_resolve,
            patch("sip_videogen.advisor.tools.load_product",return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_add_product_image",return_value="products/test-product/images/photo.jpg"),
            patch("sip_videogen.advisor.tools.storage_set_primary_product_image",return_value=True),
            patch("sip_videogen.advisor.tools.get_brand_dir",return_value=tmp_path),
            patch("sip_videogen.advisor.image_analyzer.analyze_packaging_text",mock_analyze),
        ):
            mock_resolve.return_value=image_file
            result=await _impl_add_product_image(product_slug="test-product",image_path="uploads/photo.jpg",set_as_primary=True)
        #Should still succeed even though analysis failed
        assert "set as primary image" in result
        assert "Auto-extracted" not in result


class TestDeleteProduct:
    """Tests for _impl_delete_product function."""

    def test_delete_product_no_confirm(self) -> None:
        """Test delete_product without confirm shows warning."""
        from sip_videogen.advisor.tools import _impl_delete_product

        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.images = ["image1.jpg", "image2.jpg"]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value=None),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
        ):
            result = _impl_delete_product(product_slug="test-product", confirm=False)

        assert "This will permanently delete **Test Product**" in result
        assert "all 2 images" in result
        assert "confirm=True" in result

    def test_delete_product_with_confirm(self) -> None:
        """Test delete_product with confirm=True deletes successfully."""
        from sip_videogen.advisor.tools import _impl_delete_product

        mock_product = MagicMock()
        mock_product.name = "Test Product"

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value=None),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch("sip_videogen.advisor.tools.storage_delete_product"),
        ):
            result = _impl_delete_product(product_slug="test-product", confirm=True)

        assert "Deleted product **Test Product**" in result
        assert "`test-product`" in result

    def test_delete_product_no_active_brand(self) -> None:
        """Test delete_product with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_delete_product

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_delete_product(product_slug="test-product")

        assert "Error: No active brand selected" in result

    def test_delete_product_invalid_slug(self) -> None:
        """Test delete_product with invalid slug returns error."""
        from sip_videogen.advisor.tools import _impl_delete_product

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value="Invalid slug"),
        ):
            result = _impl_delete_product(product_slug="invalid/slug")

        assert "Error: Invalid slug" in result

    def test_delete_product_not_found(self) -> None:
        """Test delete_product with non-existent product returns error."""
        from sip_videogen.advisor.tools import _impl_delete_product

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value=None),
            patch("sip_videogen.advisor.tools.load_product", return_value=None),
        ):
            result = _impl_delete_product(product_slug="nonexistent")

        assert "Error: Product 'nonexistent' not found" in result

    def test_delete_product_without_confirm_shows_image_count(self) -> None:
        """Test delete_product without confirm shows exact image count."""
        from sip_videogen.advisor.tools import _impl_delete_product

        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.images = []  # No images

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value=None),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
        ):
            result = _impl_delete_product(product_slug="test-product", confirm=False)

        assert "all 0 images" in result

    def test_delete_product_error_handling(self) -> None:
        """Test delete_product handles deletion errors gracefully."""
        from sip_videogen.advisor.tools import _impl_delete_product

        mock_product = MagicMock()
        mock_product.name = "Test Product"

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value=None),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch(
                "sip_videogen.advisor.tools.storage_delete_product",
                side_effect=Exception("Delete failed"),
            ),
        ):
            result = _impl_delete_product(product_slug="test-product", confirm=True)

        assert "Error deleting product" in result


class TestSetProductPrimaryImage:
    """Tests for _impl_set_product_primary_image function."""

    def test_set_product_primary_image_success(self) -> None:
        """Test setting product primary image successfully."""
        from sip_videogen.advisor.tools import _impl_set_product_primary_image

        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.images = ["image1.jpg", "image2.jpg"]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value=None),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch(
                "sip_videogen.advisor.tools.storage_set_primary_product_image",
                return_value=True,
            ),
        ):
            result = _impl_set_product_primary_image(
                product_slug="test-product",
                image_path="image1.jpg",
            )

        assert "Set `image1.jpg` as primary image" in result
        assert "**Test Product**" in result
        assert "`test-product`" in result

    def test_set_product_primary_image_no_active_brand(self) -> None:
        """Test set_product_primary_image with no active brand returns error."""
        from sip_videogen.advisor.tools import _impl_set_product_primary_image

        with patch("sip_videogen.advisor.tools.get_active_brand", return_value=None):
            result = _impl_set_product_primary_image(
                product_slug="test-product",
                image_path="image1.jpg",
            )

        assert "Error: No active brand selected" in result

    def test_set_product_primary_image_invalid_slug(self) -> None:
        """Test set_product_primary_image with invalid slug returns error."""
        from sip_videogen.advisor.tools import _impl_set_product_primary_image

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value="Invalid slug"),
        ):
            result = _impl_set_product_primary_image(
                product_slug="invalid/slug",
                image_path="image1.jpg",
            )

        assert "Error: Invalid slug" in result

    def test_set_product_primary_image_not_found(self) -> None:
        """Test set_product_primary_image with non-existent product returns error."""
        from sip_videogen.advisor.tools import _impl_set_product_primary_image

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value=None),
            patch("sip_videogen.advisor.tools.load_product", return_value=None),
        ):
            result = _impl_set_product_primary_image(
                product_slug="nonexistent",
                image_path="image1.jpg",
            )

        assert "Error: Product 'nonexistent' not found" in result

    def test_set_product_primary_image_invalid_image(self) -> None:
        """Test set_product_primary_image with image not in product returns error."""
        from sip_videogen.advisor.tools import _impl_set_product_primary_image

        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.images = ["image1.jpg", "image2.jpg"]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value=None),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
        ):
            result = _impl_set_product_primary_image(
                product_slug="test-product",
                image_path="image3.jpg",  # Not in product.images
            )

        assert "Error: Image 'image3.jpg' not found in product" in result
        assert "Available images:" in result
        assert "image1.jpg" in result
        assert "image2.jpg" in result

    def test_set_product_primary_image_failure(self) -> None:
        """Test set_product_primary_image handles failure gracefully."""
        from sip_videogen.advisor.tools import _impl_set_product_primary_image

        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.images = ["image1.jpg", "image2.jpg"]

        with (
            patch("sip_videogen.advisor.tools.get_active_brand", return_value="test-brand"),
            patch("sip_videogen.advisor.tools._validate_slug", return_value=None),
            patch("sip_videogen.advisor.tools.load_product", return_value=mock_product),
            patch(
                "sip_videogen.advisor.tools.storage_set_primary_product_image",
                return_value=False,
            ),
        ):
            result = _impl_set_product_primary_image(
                product_slug="test-product",
                image_path="image1.jpg",
            )

        assert "Error: Failed to set `image1.jpg` as primary image" in result
        assert "**Test Product**" in result
        assert "`test-product`" in result


class TestReportThinking:
    """Tests for report_thinking tool."""
    def test_impl_report_thinking_returns_valid_json(self)->None:
        """Test _impl_report_thinking returns valid JSON."""
        import json
        from sip_videogen.advisor.tools import _impl_report_thinking
        result=_impl_report_thinking("Test step","Test detail")
        data=json.loads(result)
        assert data["_thinking_step"]==True
        assert data["step"]=="Test step"
        assert data["detail"]=="Test detail"
        assert "id" in data
        assert "timestamp" in data
        assert isinstance(data["timestamp"],int)
    def test_parse_thinking_step_result_extracts_data(self)->None:
        """Test parse_thinking_step_result extracts data correctly."""
        import json
        from sip_videogen.advisor.tools import parse_thinking_step_result
        result=json.dumps({"_thinking_step":True,"id":"test-uuid","step":"My step","detail":"My detail","timestamp":1234567890})
        data=parse_thinking_step_result(result)
        assert data is not None
        assert data["id"]=="test-uuid"
        assert data["step"]=="My step"
        assert data["detail"]=="My detail"
        assert data["timestamp"]==1234567890
    def test_parse_thinking_step_result_returns_none_for_invalid(self)->None:
        """Test parse_thinking_step_result returns None for invalid JSON."""
        from sip_videogen.advisor.tools import parse_thinking_step_result
        assert parse_thinking_step_result("not json")==None
        assert parse_thinking_step_result('{"other":"data"}')==None
        assert parse_thinking_step_result("")==None
    def test_clamping_long_step_and_detail(self)->None:
        """Test that long step and detail are clamped."""
        import json
        from sip_videogen.advisor.tools import _impl_report_thinking,_MAX_STEP_LEN,_MAX_DETAIL_LEN
        long_step="A"*100
        long_detail="B"*1000
        result=_impl_report_thinking(long_step,long_detail)
        data=json.loads(result)
        assert len(data["step"])==_MAX_STEP_LEN
        assert len(data["detail"])==_MAX_DETAIL_LEN
    def test_empty_step_defaults_to_thinking(self)->None:
        """Test empty step defaults to 'Thinking'."""
        import json
        from sip_videogen.advisor.tools import _impl_report_thinking
        result=_impl_report_thinking("","")
        data=json.loads(result)
        assert data["step"]=="Thinking"
        assert data["detail"]==""


class TestTextUtils:
    """Tests for text_utils module."""
    def test_escape_text_for_prompt_basic(self)->None:
        """Test basic text passes through unchanged."""
        from sip_videogen.brands.text_utils import escape_text_for_prompt
        assert escape_text_for_prompt("SUMMIT COFFEE")=="SUMMIT COFFEE"
    def test_escape_text_for_prompt_quotes(self)->None:
        """Test quotes are escaped."""
        from sip_videogen.brands.text_utils import escape_text_for_prompt
        assert escape_text_for_prompt('Say "Hello"')=='Say \\"Hello\\"'
    def test_escape_text_for_prompt_newlines(self)->None:
        """Test newlines are escaped."""
        from sip_videogen.brands.text_utils import escape_text_for_prompt
        assert escape_text_for_prompt("Line1\nLine2")=="Line1\\nLine2"
    def test_escape_text_for_prompt_unicode(self)->None:
        """Test unicode characters are escaped for JSON safety."""
        from sip_videogen.brands.text_utils import escape_text_for_prompt
        #json.dumps escapes non-ASCII by default
        result=escape_text_for_prompt("Café Müller")
        assert "Caf" in result and ("\\u00e9" in result or "é" in result)
    def test_escape_text_for_prompt_backslash(self)->None:
        """Test backslashes are escaped."""
        from sip_videogen.brands.text_utils import escape_text_for_prompt
        assert escape_text_for_prompt("path\\to\\file")=="path\\\\to\\\\file"


class TestAnalyzePackagingText:
    """Tests for analyze_packaging_text function."""
    @pytest.mark.asyncio
    async def test_analyze_packaging_text_success(self,tmp_path:Path)->None:
        """Test successful packaging text analysis."""
        from datetime import datetime
        from sip_videogen.advisor.image_analyzer import analyze_packaging_text
        from sip_videogen.brands.models import PackagingTextDescription
        #Create a minimal test image
        from PIL import Image
        img=Image.new("RGB",(100,100),"white")
        img_path=tmp_path/"test.png"
        img.save(img_path)
        mock_response_json='{"summary":"Bold brand name","elements":[{"text":"SUMMIT","role":"brand_name","typography":"sans-serif","size":"large","position":"front-center"}],"layout_notes":"Centered layout"}'
        mock_response=MagicMock()
        mock_response.text=mock_response_json
        mock_client=MagicMock()
        mock_client.models.generate_content.return_value=mock_response
        with patch("sip_videogen.advisor.image_analyzer.genai.Client",return_value=mock_client):
            result=await analyze_packaging_text(img_path)
        assert result is not None
        assert isinstance(result,PackagingTextDescription)
        assert result.summary=="Bold brand name"
        assert len(result.elements)==1
        assert result.elements[0].text=="SUMMIT"
        assert result.elements[0].role=="brand_name"
        assert result.layout_notes=="Centered layout"
        assert result.generated_at is not None
    @pytest.mark.asyncio
    async def test_analyze_packaging_text_with_code_fence(self,tmp_path:Path)->None:
        """Test handling of markdown code fence in response."""
        from sip_videogen.advisor.image_analyzer import analyze_packaging_text
        from PIL import Image
        img=Image.new("RGB",(100,100),"white")
        img_path=tmp_path/"test.png"
        img.save(img_path)
        mock_response_json='```json\n{"summary":"Test","elements":[],"layout_notes":""}\n```'
        mock_response=MagicMock()
        mock_response.text=mock_response_json
        mock_client=MagicMock()
        mock_client.models.generate_content.return_value=mock_response
        with patch("sip_videogen.advisor.image_analyzer.genai.Client",return_value=mock_client):
            result=await analyze_packaging_text(img_path)
        assert result is not None
        assert result.summary=="Test"
        assert result.elements==[]
    @pytest.mark.asyncio
    async def test_analyze_packaging_text_invalid_json(self,tmp_path:Path)->None:
        """Test handling of invalid JSON response."""
        from sip_videogen.advisor.image_analyzer import analyze_packaging_text
        from PIL import Image
        img=Image.new("RGB",(100,100),"white")
        img_path=tmp_path/"test.png"
        img.save(img_path)
        mock_response=MagicMock()
        mock_response.text="not valid json"
        mock_client=MagicMock()
        mock_client.models.generate_content.return_value=mock_response
        with patch("sip_videogen.advisor.image_analyzer.genai.Client",return_value=mock_client):
            result=await analyze_packaging_text(img_path)
        assert result is None
    @pytest.mark.asyncio
    async def test_analyze_packaging_text_api_error(self,tmp_path:Path)->None:
        """Test handling of API error."""
        from sip_videogen.advisor.image_analyzer import analyze_packaging_text
        from PIL import Image
        img=Image.new("RGB",(100,100),"white")
        img_path=tmp_path/"test.png"
        img.save(img_path)
        mock_client=MagicMock()
        mock_client.models.generate_content.side_effect=Exception("API Error")
        with patch("sip_videogen.advisor.image_analyzer.genai.Client",return_value=mock_client):
            result=await analyze_packaging_text(img_path)
        assert result is None


class TestPackagingTextTools:
    """Tests for packaging text analysis tools."""
    @pytest.fixture
    def brand_setup(self,tmp_path:Path):
        """Set up a mock brand with a product."""
        from datetime import datetime
        from sip_videogen.brands.models import ProductFull,PackagingTextDescription,PackagingTextElement
        brand_dir=tmp_path/"test-brand"
        products_dir=brand_dir/"products"/"night-cream"/"images"
        products_dir.mkdir(parents=True)
        #Create a test image
        from PIL import Image
        img=Image.new("RGB",(100,100),"white")
        img_path=products_dir/"main.png"
        img.save(img_path)
        #Create product without packaging_text
        product=ProductFull(slug="night-cream",name="Night Cream",description="A restorative cream",
            images=["products/night-cream/images/main.png"],primary_image="products/night-cream/images/main.png")
        return {"brand_dir":brand_dir,"product":product,"img_path":img_path}
    @pytest.mark.asyncio
    async def test_analyze_product_packaging_success(self,brand_setup,tmp_path:Path)->None:
        """Test successful single product packaging analysis."""
        from sip_videogen.advisor.tools import _impl_analyze_product_packaging
        bd=brand_setup
        mock_response_json='{"summary":"Bold brand","elements":[{"text":"LUMINA","role":"brand_name"}],"layout_notes":"Centered"}'
        mock_response=MagicMock()
        mock_response.text=mock_response_json
        mock_client=MagicMock()
        mock_client.models.generate_content.return_value=mock_response
        saved_products={}
        def mock_save_product(brand_slug,product):
            saved_products[brand_slug]=product
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir",return_value=bd["brand_dir"]),
            patch("sip_videogen.advisor.tools.load_product",return_value=bd["product"]),
            patch("sip_videogen.advisor.tools.storage_save_product",side_effect=mock_save_product),
            patch("sip_videogen.advisor.image_analyzer.genai.Client",return_value=mock_client),
        ):
            result=await _impl_analyze_product_packaging("night-cream")
        assert "Night Cream" in result
        assert "1 text elements" in result
        assert '"LUMINA"' in result
        assert "test-brand" in saved_products
        assert saved_products["test-brand"].packaging_text is not None
    @pytest.mark.asyncio
    async def test_analyze_product_packaging_skip_existing(self,brand_setup)->None:
        """Test skipping analysis when packaging_text already exists."""
        from sip_videogen.advisor.tools import _impl_analyze_product_packaging
        from sip_videogen.brands.models import PackagingTextDescription,PackagingTextElement
        bd=brand_setup
        bd["product"].packaging_text=PackagingTextDescription(
            elements=[PackagingTextElement(text="EXISTING")])
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product",return_value=bd["product"]),
        ):
            result=await _impl_analyze_product_packaging("night-cream")
        assert "already has packaging text" in result
        assert "force=True" in result
    @pytest.mark.asyncio
    async def test_analyze_product_packaging_force_reanalyze(self,brand_setup)->None:
        """Test force re-analysis when packaging_text exists."""
        from sip_videogen.advisor.tools import _impl_analyze_product_packaging
        from sip_videogen.brands.models import PackagingTextDescription,PackagingTextElement
        bd=brand_setup
        bd["product"].packaging_text=PackagingTextDescription(
            elements=[PackagingTextElement(text="OLD")])
        mock_response_json='{"summary":"New","elements":[{"text":"NEW"}],"layout_notes":""}'
        mock_response=MagicMock()
        mock_response.text=mock_response_json
        mock_client=MagicMock()
        mock_client.models.generate_content.return_value=mock_response
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.get_brand_dir",return_value=bd["brand_dir"]),
            patch("sip_videogen.advisor.tools.load_product",return_value=bd["product"]),
            patch("sip_videogen.advisor.tools.storage_save_product"),
            patch("sip_videogen.advisor.image_analyzer.genai.Client",return_value=mock_client),
        ):
            result=await _impl_analyze_product_packaging("night-cream",force=True)
        assert "Night Cream" in result
        assert '"NEW"' in result
    @pytest.mark.asyncio
    async def test_analyze_product_packaging_no_primary_image(self,brand_setup)->None:
        """Test error when product has no primary image."""
        from sip_videogen.advisor.tools import _impl_analyze_product_packaging
        bd=brand_setup
        bd["product"].primary_image=""
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product",return_value=bd["product"]),
        ):
            result=await _impl_analyze_product_packaging("night-cream")
        assert "Error" in result
        assert "no primary image" in result
    @pytest.mark.asyncio
    async def test_analyze_product_packaging_no_active_brand(self)->None:
        """Test error when no active brand."""
        from sip_videogen.advisor.tools import _impl_analyze_product_packaging
        with patch("sip_videogen.advisor.tools.get_active_brand",return_value=None):
            result=await _impl_analyze_product_packaging("night-cream")
        assert "Error" in result
        assert "No active brand" in result
    def test_update_product_packaging_text_success(self,brand_setup)->None:
        """Test updating packaging text with human corrections."""
        from sip_videogen.advisor.tools import _impl_update_product_packaging_text
        bd=brand_setup
        saved_products={}
        def mock_save(brand_slug,product):
            saved_products[brand_slug]=product
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product",return_value=bd["product"]),
            patch("sip_videogen.advisor.tools.storage_save_product",side_effect=mock_save),
        ):
            result=_impl_update_product_packaging_text(
                "night-cream",
                summary="Manual summary",
                elements=[{"text":"BRAND","role":"brand_name"}])
        assert "Updated packaging text" in result
        assert "Night Cream" in result
        saved=saved_products["test-brand"]
        assert saved.packaging_text is not None
        assert saved.packaging_text.is_human_edited is True
        assert saved.packaging_text.edited_at is not None
        assert saved.packaging_text.summary=="Manual summary"
        assert len(saved.packaging_text.elements)==1
    def test_update_product_packaging_text_preserves_existing(self,brand_setup)->None:
        """Test that passing None preserves existing values."""
        from sip_videogen.advisor.tools import _impl_update_product_packaging_text
        from sip_videogen.brands.models import PackagingTextDescription,PackagingTextElement
        bd=brand_setup
        bd["product"].packaging_text=PackagingTextDescription(
            summary="Original",elements=[PackagingTextElement(text="OLD")],layout_notes="Notes")
        saved_products={}
        def mock_save(brand_slug,product):
            saved_products[brand_slug]=product
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product",return_value=bd["product"]),
            patch("sip_videogen.advisor.tools.storage_save_product",side_effect=mock_save),
        ):
            #Only update layout_notes
            result=_impl_update_product_packaging_text("night-cream",layout_notes="New notes")
        saved=saved_products["test-brand"]
        assert saved.packaging_text.summary=="Original"
        assert saved.packaging_text.elements[0].text=="OLD"
        assert saved.packaging_text.layout_notes=="New notes"
        assert saved.packaging_text.is_human_edited is True
    def test_update_product_packaging_text_no_product(self)->None:
        """Test error when product not found."""
        from sip_videogen.advisor.tools import _impl_update_product_packaging_text
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.load_product",return_value=None),
        ):
            result=_impl_update_product_packaging_text("missing",summary="test")
        assert "Error" in result
        assert "not found" in result
    @pytest.mark.asyncio
    async def test_analyze_all_product_packaging_success(self,brand_setup)->None:
        """Test bulk packaging text analysis."""
        from sip_videogen.advisor.tools import _impl_analyze_all_product_packaging
        from sip_videogen.brands.models import ProductSummary,ProductFull
        bd=brand_setup
        #Create product summaries
        summaries=[ProductSummary(slug="night-cream",name="Night Cream",description="test")]
        mock_response_json='{"summary":"Test","elements":[{"text":"T"}],"layout_notes":""}'
        mock_response=MagicMock()
        mock_response.text=mock_response_json
        mock_client=MagicMock()
        mock_client.models.generate_content.return_value=mock_response
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_list_products",return_value=summaries),
            patch("sip_videogen.advisor.tools.load_product",return_value=bd["product"]),
            patch("sip_videogen.advisor.tools.get_brand_dir",return_value=bd["brand_dir"]),
            patch("sip_videogen.advisor.tools.storage_save_product"),
            patch("sip_videogen.advisor.image_analyzer.genai.Client",return_value=mock_client),
            patch("asyncio.sleep",return_value=None),
        ):
            result=await _impl_analyze_all_product_packaging()
        assert "1/1 analyzed" in result
        assert "0 skipped" in result
        assert "0 failed" in result
    @pytest.mark.asyncio
    async def test_analyze_all_product_packaging_skip_existing(self,brand_setup)->None:
        """Test bulk analysis skips products with existing packaging_text."""
        from sip_videogen.advisor.tools import _impl_analyze_all_product_packaging
        from sip_videogen.brands.models import ProductSummary,PackagingTextDescription
        bd=brand_setup
        bd["product"].packaging_text=PackagingTextDescription(elements=[])
        summaries=[ProductSummary(slug="night-cream",name="Night Cream",description="test")]
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_list_products",return_value=summaries),
            patch("sip_videogen.advisor.tools.load_product",return_value=bd["product"]),
        ):
            result=await _impl_analyze_all_product_packaging(skip_existing=True)
        assert "0/1 analyzed" in result
        assert "1 skipped" in result
    @pytest.mark.asyncio
    async def test_analyze_all_product_packaging_skip_human_edited(self,brand_setup)->None:
        """Test bulk analysis skips products with human-edited packaging_text."""
        from sip_videogen.advisor.tools import _impl_analyze_all_product_packaging
        from sip_videogen.brands.models import ProductSummary,PackagingTextDescription
        bd=brand_setup
        bd["product"].packaging_text=PackagingTextDescription(elements=[],is_human_edited=True)
        summaries=[ProductSummary(slug="night-cream",name="Night Cream",description="test")]
        with (
            patch("sip_videogen.advisor.tools.get_active_brand",return_value="test-brand"),
            patch("sip_videogen.advisor.tools.storage_list_products",return_value=summaries),
            patch("sip_videogen.advisor.tools.load_product",return_value=bd["product"]),
        ):
            result=await _impl_analyze_all_product_packaging(skip_existing=False,skip_human_edited=True)
        assert "0/1 analyzed" in result
        assert "1 skipped" in result
