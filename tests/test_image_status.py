"""Tests for image status tracking service."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from sip_studio.studio.services.image_status import (
    CURRENT_VERSION,
    STATUS_FILE_NAME,
    ImageStatusService,
)
from sip_studio.studio.state import BridgeState


@pytest.fixture
def temp_brands_dir(tmp_path: Path):
    """Create a temporary brands directory for testing."""
    brands_dir = tmp_path / ".sip-videogen" / "brands"
    brands_dir.mkdir(parents=True)
    # Create test brand directory with assets
    test_brand_dir = brands_dir / "test-brand"
    test_brand_dir.mkdir()
    (test_brand_dir / "assets" / "generated").mkdir(parents=True)
    (test_brand_dir / "assets" / "kept").mkdir(parents=True)
    (test_brand_dir / "assets" / "trash").mkdir(parents=True)
    with patch("sip_studio.brands.storage.base.get_brands_dir", return_value=brands_dir):
        with patch(
            "sip_studio.studio.services.image_status.get_brand_dir",
            lambda slug: brands_dir / slug,
        ):
            yield brands_dir


@pytest.fixture
def service(temp_brands_dir: Path) -> ImageStatusService:
    """Create ImageStatusService with mocked state."""
    state = BridgeState()
    return ImageStatusService(state)


class TestRegisterImage:
    """Tests for registering new images."""

    def test_register_creates_entry_with_unsorted_status(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that register_image creates entry with unsorted status."""
        result = service.register_image("test-brand", "/path/to/image.png")
        assert result["success"] is True
        data = result["data"]
        assert data["status"] == "unsorted"
        assert data["originalPath"] == "/path/to/image.png"
        assert data["currentPath"] == "/path/to/image.png"
        assert data["id"].startswith("img_")
        assert data["keptAt"] is None
        assert data["trashedAt"] is None

    def test_register_stores_prompt_and_source(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that register_image stores optional prompt and source."""
        result = service.register_image(
            "test-brand",
            "/path/to/image.png",
            prompt="A cat",
            source_template_path="/path/to/style_ref.png",
        )
        assert result["success"] is True
        data = result["data"]
        assert data["prompt"] == "A cat"
        assert data["sourceTemplatePath"] == "/path/to/style_ref.png"

    def test_register_generates_unique_ids(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that register_image generates unique IDs."""
        r1 = service.register_image("test-brand", "/path/to/image1.png")
        r2 = service.register_image("test-brand", "/path/to/image2.png")
        assert r1["data"]["id"] != r2["data"]["id"]

    def test_register_persists_to_file(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that register_image persists to image_status.json."""
        service.register_image("test-brand", "/path/to/image.png")
        status_file = temp_brands_dir / "test-brand" / STATUS_FILE_NAME
        assert status_file.exists()
        data = json.loads(status_file.read_text())
        assert data["version"] == CURRENT_VERSION
        assert len(data["images"]) == 1


class TestGetStatus:
    """Tests for getting image status."""

    def test_get_status_returns_entry(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that get_status returns the correct entry."""
        reg = service.register_image("test-brand", "/path/to/image.png")
        image_id = reg["data"]["id"]
        result = service.get_status("test-brand", image_id)
        assert result["success"] is True
        assert result["data"]["id"] == image_id
        assert result["data"]["status"] == "unsorted"

    def test_get_status_not_found(self, service: ImageStatusService, temp_brands_dir: Path) -> None:
        """Test that get_status returns error for nonexistent image."""
        result = service.get_status("test-brand", "img_nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestSetStatus:
    """Tests for setting image status."""

    def test_set_status_to_kept(self, service: ImageStatusService, temp_brands_dir: Path) -> None:
        """Test setting status to kept."""
        reg = service.register_image("test-brand", "/path/to/image.png")
        image_id = reg["data"]["id"]
        result = service.set_status("test-brand", image_id, "kept")
        assert result["success"] is True
        assert result["data"]["status"] == "kept"
        assert result["data"]["keptAt"] is not None
        assert result["data"]["trashedAt"] is None

    def test_set_status_to_trashed(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test setting status to trashed."""
        reg = service.register_image("test-brand", "/path/to/image.png")
        image_id = reg["data"]["id"]
        result = service.set_status("test-brand", image_id, "trashed")
        assert result["success"] is True
        assert result["data"]["status"] == "trashed"
        assert result["data"]["trashedAt"] is not None
        assert result["data"]["keptAt"] is None

    def test_set_status_back_to_unsorted(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test setting status back to unsorted clears timestamps."""
        reg = service.register_image("test-brand", "/path/to/image.png")
        image_id = reg["data"]["id"]
        service.set_status("test-brand", image_id, "kept")
        result = service.set_status("test-brand", image_id, "unsorted")
        assert result["success"] is True
        assert result["data"]["status"] == "unsorted"
        assert result["data"]["keptAt"] is None
        assert result["data"]["trashedAt"] is None

    def test_set_status_timestamps_are_iso(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that timestamps are ISO 8601 strings."""
        reg = service.register_image("test-brand", "/path/to/image.png")
        image_id = reg["data"]["id"]
        result = service.set_status("test-brand", image_id, "kept")
        kept_at = result["data"]["keptAt"]
        # Should be parseable as ISO datetime
        dt = datetime.fromisoformat(kept_at)
        assert dt.tzinfo is not None  # Should have timezone

    def test_set_status_not_found(self, service: ImageStatusService, temp_brands_dir: Path) -> None:
        """Test that set_status returns error for nonexistent image."""
        result = service.set_status("test-brand", "img_nonexistent", "kept")
        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestListByStatus:
    """Tests for listing images by status."""

    def test_list_by_status_filters_correctly(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that list_by_status filters by status."""
        # Create actual test files since list_by_status verifies files exist
        gen_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        img1 = gen_dir / "image1.png"
        img2 = gen_dir / "image2.png"
        img3 = gen_dir / "image3.png"
        img1.write_bytes(b"fake")
        img2.write_bytes(b"fake")
        img3.write_bytes(b"fake")
        r1 = service.register_image("test-brand", str(img1))
        r2 = service.register_image("test-brand", str(img2))
        service.register_image("test-brand", str(img3))
        service.set_status("test-brand", r1["data"]["id"], "kept")
        service.set_status("test-brand", r2["data"]["id"], "trashed")
        # r3 stays unsorted
        unsorted = service.list_by_status("test-brand", "unsorted")
        kept = service.list_by_status("test-brand", "kept")
        trashed = service.list_by_status("test-brand", "trashed")
        assert unsorted["success"] is True
        assert len(unsorted["data"]) == 1
        assert unsorted["data"][0]["originalPath"] == str(img3)
        assert kept["success"] is True
        assert len(kept["data"]) == 1
        assert kept["data"][0]["originalPath"] == str(img1)
        assert trashed["success"] is True
        assert len(trashed["data"]) == 1
        assert trashed["data"][0]["originalPath"] == str(img2)

    def test_list_by_status_empty(self, service: ImageStatusService, temp_brands_dir: Path) -> None:
        """Test list_by_status returns empty list when none match."""
        result = service.list_by_status("test-brand", "kept")
        assert result["success"] is True
        assert result["data"] == []


class TestUpdatePath:
    """Tests for updating image path."""

    def test_update_path_changes_current_path(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that update_path changes currentPath."""
        reg = service.register_image("test-brand", "/path/to/original.png")
        image_id = reg["data"]["id"]
        result = service.update_path("test-brand", image_id, "/path/to/kept/original.png")
        assert result["success"] is True
        assert result["data"]["originalPath"] == "/path/to/original.png"
        assert result["data"]["currentPath"] == "/path/to/kept/original.png"

    def test_update_path_not_found(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that update_path returns error for nonexistent image."""
        result = service.update_path("test-brand", "img_nonexistent", "/new/path.png")
        assert result["success"] is False


class TestDeleteImage:
    """Tests for deleting image entries."""

    def test_delete_image_removes_entry(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that delete_image removes the entry."""
        reg = service.register_image("test-brand", "/path/to/image.png")
        image_id = reg["data"]["id"]
        result = service.delete_image("test-brand", image_id)
        assert result["success"] is True
        # Should no longer exist
        get_result = service.get_status("test-brand", image_id)
        assert get_result["success"] is False

    def test_delete_image_not_found(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that delete_image returns error for nonexistent image."""
        result = service.delete_image("test-brand", "img_nonexistent")
        assert result["success"] is False


class TestAtomicWrite:
    """Tests for atomic file writes."""

    def test_atomic_write_no_temp_file_remains(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that no temp file remains after write."""
        service.register_image("test-brand", "/path/to/image.png")
        brand_dir = temp_brands_dir / "test-brand"
        tmp_file = brand_dir / "image_status.json.tmp"
        assert not tmp_file.exists()
        assert (brand_dir / STATUS_FILE_NAME).exists()

    def test_file_not_corrupted_on_concurrent_reads(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that file is readable immediately after write."""
        # Create actual test files since list_by_status verifies files exist
        gen_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        img1 = gen_dir / "image1.png"
        img2 = gen_dir / "image2.png"
        img1.write_bytes(b"fake")
        img2.write_bytes(b"fake")
        service.register_image("test-brand", str(img1))
        service.register_image("test-brand", str(img2))
        # Multiple reads should all succeed
        for _ in range(10):
            result = service.list_by_status("test-brand", "unsorted")
            assert result["success"] is True
            assert len(result["data"]) == 2


class TestBackfillFromFolders:
    """Tests for backfilling from existing folder structure."""

    def test_backfill_creates_entries_from_generated(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test backfill creates entries for images in generated folder."""
        # Create image files
        gen_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        (gen_dir / "image1.png").write_bytes(b"fake")
        (gen_dir / "image2.jpg").write_bytes(b"fake")
        result = service.backfill_from_folders("test-brand")
        assert result["success"] is True
        assert result["data"]["count"] == 2
        unsorted = service.list_by_status("test-brand", "unsorted")
        assert len(unsorted["data"]) == 2

    def test_backfill_creates_entries_from_kept(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test backfill creates entries for images in kept folder."""
        kept_dir = temp_brands_dir / "test-brand" / "assets" / "kept"
        (kept_dir / "image1.png").write_bytes(b"fake")
        result = service.backfill_from_folders("test-brand")
        assert result["success"] is True
        kept = service.list_by_status("test-brand", "kept")
        assert len(kept["data"]) == 1
        assert kept["data"][0]["keptAt"] is not None

    def test_backfill_creates_entries_from_trash(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test backfill creates entries for images in trash folder."""
        trash_dir = temp_brands_dir / "test-brand" / "assets" / "trash"
        (trash_dir / "image1.png").write_bytes(b"fake")
        service.backfill_from_folders("test-brand")
        trashed = service.list_by_status("test-brand", "trashed")
        assert len(trashed["data"]) == 1
        assert trashed["data"][0]["trashedAt"] is not None

    def test_backfill_skips_existing_entries(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test backfill doesn't duplicate existing entries."""
        gen_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        img_path = gen_dir / "image1.png"
        img_path.write_bytes(b"fake")
        # Register first
        service.register_image("test-brand", str(img_path))
        # Then backfill
        result = service.backfill_from_folders("test-brand")
        assert result["data"]["count"] == 0  # No new entries
        unsorted = service.list_by_status("test-brand", "unsorted")
        assert len(unsorted["data"]) == 1  # Still just one

    def test_backfill_ignores_non_image_files(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test backfill ignores non-image files."""
        gen_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        (gen_dir / "image1.png").write_bytes(b"fake")
        (gen_dir / "readme.txt").write_bytes(b"fake")
        (gen_dir / ".DS_Store").write_bytes(b"fake")
        result = service.backfill_from_folders("test-brand")
        assert result["data"]["count"] == 1  # Only the png

    def test_backfill_marks_migration_images_as_viewed(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """First-time migration marks all existing images as viewed (read)."""
        gen_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        (gen_dir / "image1.png").write_bytes(b"fake")
        result = service.backfill_from_folders("test-brand")
        assert result["data"]["count"] == 1
        unsorted = service.list_by_status("test-brand", "unsorted")
        # Should be marked as viewed (read) since this is first migration
        assert unsorted["data"][0]["viewedAt"] is not None

    def test_backfill_new_images_unread_after_migration(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """After migration, new images should be unread."""
        gen_dir = temp_brands_dir / "test-brand" / "assets" / "generated"
        (gen_dir / "image1.png").write_bytes(b"fake")
        # First migration
        service.backfill_from_folders("test-brand")
        # Add new image
        (gen_dir / "image2.png").write_bytes(b"fake")
        result = service.backfill_from_folders("test-brand")
        # New image should be unread
        assert result["data"]["added"][0]["viewedAt"] is None


class TestCleanupOldTrash:
    """Tests for cleaning up old trashed images."""

    def test_cleanup_deletes_old_trashed_images(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test cleanup deletes images older than threshold."""
        # Create and trash an image
        trash_dir = temp_brands_dir / "test-brand" / "assets" / "trash"
        img_path = trash_dir / "old_image.png"
        img_path.write_bytes(b"fake")
        # Register and trash it
        reg = service.register_image("test-brand", str(img_path))
        image_id = reg["data"]["id"]
        service.set_status("test-brand", image_id, "trashed")
        # Manually backdate the trashedAt
        status_file = temp_brands_dir / "test-brand" / STATUS_FILE_NAME
        data = json.loads(status_file.read_text())
        old_time = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        data["images"][image_id]["trashedAt"] = old_time
        status_file.write_text(json.dumps(data))
        # Run cleanup
        result = service.cleanup_old_trash("test-brand", days=30)
        assert result["success"] is True
        assert result["data"]["count"] == 1
        # Image should be gone from status
        get_result = service.get_status("test-brand", image_id)
        assert get_result["success"] is False
        # File should be deleted
        assert not img_path.exists()

    def test_cleanup_keeps_recent_trashed_images(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test cleanup keeps recently trashed images."""
        trash_dir = temp_brands_dir / "test-brand" / "assets" / "trash"
        img_path = trash_dir / "recent_image.png"
        img_path.write_bytes(b"fake")
        reg = service.register_image("test-brand", str(img_path))
        image_id = reg["data"]["id"]
        service.set_status("test-brand", image_id, "trashed")
        result = service.cleanup_old_trash("test-brand", days=30)
        assert result["data"]["count"] == 0
        # Image should still exist
        get_result = service.get_status("test-brand", image_id)
        assert get_result["success"] is True
        assert img_path.exists()


class TestLoadStatusData:
    """Tests for loading status data."""

    def test_load_creates_empty_structure_if_missing(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that loading creates empty structure if file missing."""
        result = service.list_by_status("test-brand", "unsorted")
        assert result["success"] is True
        assert result["data"] == []

    def test_load_handles_invalid_json(
        self, service: ImageStatusService, temp_brands_dir: Path
    ) -> None:
        """Test that loading handles invalid JSON gracefully."""
        status_file = temp_brands_dir / "test-brand" / STATUS_FILE_NAME
        status_file.write_text("not valid json")
        result = service.list_by_status("test-brand", "unsorted")
        assert result["success"] is True
        assert result["data"] == []
