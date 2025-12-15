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
