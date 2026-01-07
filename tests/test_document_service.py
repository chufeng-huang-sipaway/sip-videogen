"""Tests for DocumentService."""

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sip_studio.studio.services.document_service import DocumentService
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
    """Create DocumentService with state."""
    return DocumentService(state)


@pytest.fixture
def mock_brand_dir(tmp_path) -> Path:
    """Create mock brand directory with docs folder."""
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    docs_dir = brand_dir / "docs"
    docs_dir.mkdir()
    return brand_dir


# =============================================================================
# get_documents tests
# =============================================================================
class TestGetDocuments:
    """Tests for get_documents method."""

    def test_returns_documents_list(self, service):
        """Should return list of documents."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value="test",
        ):
            with patch(
                "sip_studio.studio.services.document_service.storage.list_documents",
                return_value=["doc1.txt", "doc2.md"],
            ):
                result = service.get_documents()
        assert result["success"] == True
        assert result["data"]["documents"] == ["doc1.txt", "doc2.md"]

    def test_uses_provided_slug(self, service):
        """Should use provided slug instead of active brand."""
        with patch(
            "sip_studio.studio.services.document_service.storage.list_documents", return_value=[]
        ) as mock_list:
            service.get_documents("custom-brand")
        mock_list.assert_called_once_with("custom-brand")

    def test_error_when_no_brand(self, service):
        """Should return error when no brand selected."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value=None,
        ):
            result = service.get_documents()
        assert result["success"] == False
        assert "No brand selected" in result["error"]

    def test_handles_exception(self, service):
        """Should return error on exception."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            side_effect=Exception("Storage error"),
        ):
            result = service.get_documents()
        assert result["success"] == False
        assert "Storage error" in result["error"]


# =============================================================================
# read_document tests
# =============================================================================
class TestReadDocument:
    """Tests for read_document method."""

    def test_reads_document_content(self, service, state, mock_brand_dir):
        """Should read and return document content."""
        doc_path = mock_brand_dir / "docs" / "test.txt"
        doc_path.write_text("Hello World")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        # relative path is within docs/, not including docs/ prefix
        result = service.read_document("test.txt")
        assert result["success"] == True
        assert result["data"]["content"] == "Hello World"

    def test_error_when_no_brand(self, service, state):
        """Should return error when no brand dir."""
        state.get_brand_dir = MagicMock(return_value=(None, "No brand selected"))
        result = service.read_document("docs/test.txt")
        assert result["success"] == False
        assert "No brand selected" in result["error"]

    def test_error_for_missing_file(self, service, state, mock_brand_dir):
        """Should return error when file doesn't exist."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.read_document("missing.txt")
        assert result["success"] == False
        assert "not found" in result["error"]

    def test_error_for_unsupported_type(self, service, state, mock_brand_dir):
        """Should reject unsupported file types."""
        bad_file = mock_brand_dir / "docs" / "test.exe"
        bad_file.write_text("binary")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.read_document("test.exe")
        assert result["success"] == False
        assert "Unsupported" in result["error"]

    def test_error_for_large_file(self, service, state, mock_brand_dir):
        """Should reject files over 512KB."""
        large_file = mock_brand_dir / "docs" / "large.txt"
        large_file.write_text("x" * (513 * 1024))
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.read_document("large.txt")
        assert result["success"] == False
        assert "too large" in result["error"]

    def test_rejects_path_traversal(self, service, state, mock_brand_dir):
        """Should reject path traversal attempts."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.read_document("../../../etc/passwd")
        assert result["success"] == False


# =============================================================================
# upload_document tests
# =============================================================================
class TestUploadDocument:
    """Tests for upload_document method."""

    def test_uploads_document(self, service):
        """Should upload document successfully."""
        content = base64.b64encode(b"test content").decode()
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value="test",
        ):
            with patch(
                "sip_studio.studio.services.document_service.storage.get_docs_dir"
            ) as mock_docs:
                mock_docs.return_value = MagicMock(
                    exists=MagicMock(return_value=False),
                    __truediv__=lambda s, f: MagicMock(exists=MagicMock(return_value=False)),
                )
                with patch(
                    "sip_studio.studio.services.document_service.storage.save_document",
                    return_value=("docs/test.txt", None),
                ):
                    result = service.upload_document("test.txt", content)
        assert result["success"] == True
        assert result["data"]["path"] == "docs/test.txt"

    def test_error_when_no_brand(self, service):
        """Should return error when no brand selected."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value=None,
        ):
            result = service.upload_document("test.txt", "base64data")
        assert result["success"] == False
        assert "No brand selected" in result["error"]

    def test_rejects_path_in_filename(self, service):
        """Should reject filenames with path separators."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value="test",
        ):
            result = service.upload_document("../test.txt", "data")
        assert result["success"] == False
        assert "Invalid filename" in result["error"]

    def test_rejects_unsupported_extension(self, service):
        """Should reject unsupported file types."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value="test",
        ):
            result = service.upload_document("test.exe", "data")
        assert result["success"] == False
        assert "Unsupported" in result["error"]


# =============================================================================
# delete_document tests
# =============================================================================
class TestDeleteDocument:
    """Tests for delete_document method."""

    def test_deletes_document(self, service):
        """Should delete document successfully."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value="test",
        ):
            with patch(
                "sip_studio.studio.services.document_service.storage.delete_document",
                return_value=(True, None),
            ):
                result = service.delete_document("docs/test.txt")
        assert result["success"] == True

    def test_error_when_no_brand(self, service):
        """Should return error when no brand selected."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value=None,
        ):
            result = service.delete_document("docs/test.txt")
        assert result["success"] == False
        assert "No brand selected" in result["error"]

    def test_returns_storage_error(self, service):
        """Should return storage error message."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value="test",
        ):
            with patch(
                "sip_studio.studio.services.document_service.storage.delete_document",
                return_value=(False, "File not found"),
            ):
                result = service.delete_document("docs/missing.txt")
        assert result["success"] == False
        assert "File not found" in result["error"]


# =============================================================================
# rename_document tests
# =============================================================================
class TestRenameDocument:
    """Tests for rename_document method."""

    def test_renames_document(self, service):
        """Should rename document successfully."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value="test",
        ):
            with patch(
                "sip_studio.studio.services.document_service.storage.rename_document",
                return_value=("docs/new.txt", None),
            ):
                result = service.rename_document("docs/old.txt", "new.txt")
        assert result["success"] == True
        assert result["data"]["newPath"] == "docs/new.txt"

    def test_error_when_no_brand(self, service):
        """Should return error when no brand selected."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value=None,
        ):
            result = service.rename_document("docs/old.txt", "new.txt")
        assert result["success"] == False
        assert "No brand selected" in result["error"]

    def test_rejects_unsupported_new_extension(self, service):
        """Should reject rename to unsupported extension."""
        with patch(
            "sip_studio.studio.services.document_service.storage.get_active_brand",
            return_value="test",
        ):
            result = service.rename_document("docs/old.txt", "new.exe")
        assert result["success"] == False
        assert "Unsupported" in result["error"]


# =============================================================================
# open_document_in_finder tests
# =============================================================================
class TestOpenDocumentInFinder:
    """Tests for open_document_in_finder method."""

    def test_opens_document(self, service, state, mock_brand_dir):
        """Should reveal document in finder."""
        doc_path = mock_brand_dir / "docs" / "test.txt"
        doc_path.write_text("content")
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        with patch(
            "sip_studio.studio.services.document_service.reveal_in_file_manager"
        ) as mock_reveal:
            result = service.open_document_in_finder("test.txt")
        assert result["success"] == True
        mock_reveal.assert_called_once()

    def test_error_when_no_brand(self, service, state):
        """Should return error when no brand dir."""
        state.get_brand_dir = MagicMock(return_value=(None, "No brand selected"))
        result = service.open_document_in_finder("test.txt")
        assert result["success"] == False

    def test_error_for_missing_file(self, service, state, mock_brand_dir):
        """Should return error when file doesn't exist."""
        state.get_brand_dir = MagicMock(return_value=(mock_brand_dir, None))
        result = service.open_document_in_finder("missing.txt")
        assert result["success"] == False
        assert "not found" in result["error"]
