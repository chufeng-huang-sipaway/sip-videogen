"""Tests for StudioBridge facade."""

from unittest.mock import MagicMock, patch

import pytest

from sip_studio.constants import (
    ASSET_CATEGORIES,
)
from sip_studio.studio.bridge import StudioBridge


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def bridge():
    """Create StudioBridge instance with mocked services."""
    with patch("sip_studio.studio.bridge.load_api_keys_from_config"):
        return StudioBridge()


@pytest.fixture
def mock_brand_service():
    """Mock BrandService."""
    return MagicMock()


@pytest.fixture
def mock_document_service():
    """Mock DocumentService."""
    return MagicMock()


@pytest.fixture
def mock_asset_service():
    """Mock AssetService."""
    return MagicMock()


# =============================================================================
# get_constants tests
# =============================================================================
class TestGetConstants:
    """Tests for get_constants method."""

    def test_returns_all_constants(self, bridge):
        """Should return all constants."""
        result = bridge.get_constants()
        assert result["success"]
        data = result["data"]
        assert "asset_categories" in data
        assert "allowed_image_exts" in data
        assert "allowed_video_exts" in data
        assert "allowed_text_exts" in data
        assert "mime_types" in data

    def test_asset_categories_is_list(self, bridge):
        """Should return asset categories as list."""
        result = bridge.get_constants()
        assert isinstance(result["data"]["asset_categories"], list)
        assert result["data"]["asset_categories"] == list(ASSET_CATEGORIES)

    def test_extensions_are_sorted(self, bridge):
        """Should return sorted extension lists."""
        result = bridge.get_constants()
        exts = result["data"]["allowed_image_exts"]
        assert exts == sorted(exts)


# =============================================================================
# check_api_keys tests
# =============================================================================
class TestCheckApiKeys:
    """Tests for check_api_keys method."""

    def test_returns_key_status(self, bridge):
        """Should return API key status."""
        with patch(
            "sip_studio.studio.bridge.do_check_api_keys",
            return_value={"openai": True, "gemini": False},
        ):
            result = bridge.check_api_keys()
        assert result["success"]
        assert result["data"]["openai"]
        assert not result["data"]["gemini"]


# =============================================================================
# save_api_keys tests
# =============================================================================
class TestSaveApiKeys:
    """Tests for save_api_keys method."""

    def test_saves_keys_successfully(self, bridge):
        """Should save keys and return success."""
        with patch("sip_studio.studio.bridge.do_save_api_keys") as mock_save:
            result = bridge.save_api_keys("openai-key", "gemini-key", "firecrawl-key")
        assert result["success"]
        mock_save.assert_called_once_with("openai-key", "gemini-key", "firecrawl-key")

    def test_returns_error_on_failure(self, bridge):
        """Should return error if save fails."""
        with patch(
            "sip_studio.studio.bridge.do_save_api_keys", side_effect=Exception("Write error")
        ):
            result = bridge.save_api_keys("key1", "key2")
        assert not result["success"]
        assert "Write error" in result["error"]


# =============================================================================
# Brand delegation tests
# =============================================================================
class TestBrandDelegation:
    """Tests for brand method delegation."""

    def test_get_brands_delegates(self, bridge, mock_brand_service):
        """Should delegate get_brands to BrandService."""
        bridge._brand = mock_brand_service
        mock_brand_service.get_brands.return_value = {"success": True, "data": {"brands": []}}
        result = bridge.get_brands()
        mock_brand_service.get_brands.assert_called_once()
        assert result["success"]

    def test_set_brand_delegates(self, bridge, mock_brand_service):
        """Should delegate set_brand to BrandService."""
        bridge._brand = mock_brand_service
        mock_brand_service.set_brand.return_value = {"success": True, "data": {"slug": "test"}}
        bridge.set_brand("test")
        mock_brand_service.set_brand.assert_called_once_with("test")

    def test_get_brand_info_delegates(self, bridge, mock_brand_service):
        """Should delegate get_brand_info with optional slug."""
        bridge._brand = mock_brand_service
        mock_brand_service.get_brand_info.return_value = {"success": True, "data": {}}
        bridge.get_brand_info("custom-slug")
        mock_brand_service.get_brand_info.assert_called_once_with("custom-slug")

    def test_delete_brand_delegates(self, bridge, mock_brand_service):
        """Should delegate delete_brand to BrandService."""
        bridge._brand = mock_brand_service
        mock_brand_service.delete_brand.return_value = {"success": True}
        bridge.delete_brand("test-brand")
        mock_brand_service.delete_brand.assert_called_once_with("test-brand")


# =============================================================================
# Document delegation tests
# =============================================================================
class TestDocumentDelegation:
    """Tests for document method delegation."""

    def test_get_documents_delegates(self, bridge, mock_document_service):
        """Should delegate get_documents to DocumentService."""
        bridge._document = mock_document_service
        mock_document_service.get_documents.return_value = {
            "success": True,
            "data": {"documents": []},
        }
        bridge.get_documents("brand-slug")
        mock_document_service.get_documents.assert_called_once_with("brand-slug")

    def test_upload_document_delegates(self, bridge, mock_document_service):
        """Should delegate upload_document to DocumentService."""
        bridge._document = mock_document_service
        mock_document_service.upload_document.return_value = {"success": True}
        bridge.upload_document("test.pdf", "base64data")
        mock_document_service.upload_document.assert_called_once_with("test.pdf", "base64data")

    def test_delete_document_delegates(self, bridge, mock_document_service):
        """Should delegate delete_document to DocumentService."""
        bridge._document = mock_document_service
        mock_document_service.delete_document.return_value = {"success": True}
        bridge.delete_document("docs/test.pdf")
        mock_document_service.delete_document.assert_called_once_with("docs/test.pdf")


# =============================================================================
# Asset delegation tests
# =============================================================================
class TestAssetDelegation:
    """Tests for asset method delegation."""

    def test_get_assets_delegates(self, bridge, mock_asset_service):
        """Should delegate get_assets to AssetService."""
        bridge._asset = mock_asset_service
        mock_asset_service.get_assets.return_value = {"success": True, "data": {"assets": {}}}
        bridge.get_assets()
        mock_asset_service.get_assets.assert_called_once_with(None)

    def test_upload_asset_delegates(self, bridge, mock_asset_service):
        """Should delegate upload_asset with category."""
        bridge._asset = mock_asset_service
        mock_asset_service.upload_asset.return_value = {"success": True}
        bridge.upload_asset("image.png", "base64data", "logo")
        mock_asset_service.upload_asset.assert_called_once_with("image.png", "base64data", "logo")

    def test_delete_asset_delegates(self, bridge, mock_asset_service):
        """Should delegate delete_asset to AssetService."""
        bridge._asset = mock_asset_service
        mock_asset_service.delete_asset.return_value = {"success": True}
        bridge.delete_asset("generated/image.png")
        mock_asset_service.delete_asset.assert_called_once_with("generated/image.png")


# =============================================================================
# Image status tests
# =============================================================================
class TestImageStatus:
    """Tests for image status methods."""

    def test_get_unsorted_images_requires_brand(self, bridge):
        """Should return error when no brand selected."""
        bridge._state.get_active_slug = MagicMock(return_value=None)
        result = bridge.get_unsorted_images()
        assert not result["success"]
        assert "No brand selected" in result["error"]

    def test_get_unsorted_images_uses_active_brand(self, bridge):
        """Should use active brand when not specified."""
        bridge._state.get_active_slug = MagicMock(return_value="test-brand")
        bridge._image_status = MagicMock()
        bridge._image_status.list_by_status.return_value = {"success": True, "data": []}
        bridge.get_unsorted_images()
        bridge._image_status.list_by_status.assert_called_once_with("test-brand", "unsorted")

    def test_register_generated_images_success(self, bridge):
        """Should register multiple images."""
        bridge._state.get_active_slug = MagicMock(return_value="test")
        bridge._image_status = MagicMock()
        bridge._image_status.register_image.return_value = {"success": True, "data": {"id": "img1"}}
        result = bridge.register_generated_images([{"path": "a.png"}, {"path": "b.png"}])
        assert result["success"]
        assert len(result["data"]) == 2

    def test_cancel_generation_always_succeeds(self, bridge):
        """Should always return success for cancel."""
        result = bridge.cancel_generation()
        assert result["success"]
        assert result["data"]["cancelled"]


# =============================================================================
# set_window tests
# =============================================================================
class TestSetWindow:
    """Tests for set_window method."""

    def test_sets_window_on_state(self, bridge):
        """Should set window on bridge state."""
        mock_window = MagicMock()
        bridge.set_window(mock_window)
        assert bridge._state.window == mock_window


# =============================================================================
# Project delegation tests
# =============================================================================
class TestProjectDelegation:
    """Tests for project method delegation."""

    def test_get_projects_delegates(self, bridge):
        """Should delegate get_projects to ProjectService."""
        bridge._project = MagicMock()
        bridge._project.get_projects.return_value = {"success": True, "data": {"projects": []}}
        bridge.get_projects("brand")
        bridge._project.get_projects.assert_called_once_with("brand")

    def test_create_project_delegates(self, bridge):
        """Should delegate create_project with params."""
        bridge._project = MagicMock()
        bridge._project.create_project.return_value = {"success": True}
        bridge.create_project("My Project", "instructions here")
        bridge._project.create_project.assert_called_once_with("My Project", "instructions here")


# =============================================================================
# Style reference delegation tests
# =============================================================================
class TestStyleReferenceDelegation:
    """Tests for style reference method delegation."""

    def test_get_style_references_delegates(self, bridge):
        """Should delegate get_style_references to StyleReferenceService."""
        bridge._style_reference = MagicMock()
        bridge._style_reference.get_style_references.return_value = {
            "success": True,
            "data": {"style_references": []},
        }
        bridge.get_style_references()
        bridge._style_reference.get_style_references.assert_called_once_with(None)

    def test_create_style_reference_delegates(self, bridge):
        """Should delegate create_style_reference with all params."""
        bridge._style_reference = MagicMock()
        bridge._style_reference.create_style_reference.return_value = {"success": True}
        bridge.create_style_reference("Name", "Desc", [{"filename": "a.png"}], False)
        bridge._style_reference.create_style_reference.assert_called_once_with(
            "Name", "Desc", [{"filename": "a.png"}], False
        )


# =============================================================================
# Chat delegation tests
# =============================================================================
class TestChatDelegation:
    """Tests for chat method delegation."""

    def test_chat_delegates_all_params(self, bridge):
        """Should delegate chat with all parameters (uses chat_sync per Fix #3)."""
        bridge._chat = MagicMock()
        bridge._chat.chat_sync.return_value = {"success": True, "data": {"response": "Hello"}}
        bridge.chat(
            "hi",
            [{"file": "a.png"}],
            "project-1",
            ["prod-1"],
            [{"slug": "tmpl-1"}],
            "16:9",
            "image",
        )
        bridge._chat.chat_sync.assert_called_once_with(
            "hi",
            [{"file": "a.png"}],
            "project-1",
            ["prod-1"],
            [{"slug": "tmpl-1"}],
            "16:9",
            "image",
        )

    def test_clear_chat_delegates(self, bridge):
        """Should delegate clear_chat."""
        bridge._chat = MagicMock()
        bridge._chat.clear_chat.return_value = {"success": True}
        bridge.clear_chat()
        bridge._chat.clear_chat.assert_called_once()


# =============================================================================
# Update delegation tests
# =============================================================================
class TestUpdateDelegation:
    """Tests for update method delegation."""

    def test_get_app_version_delegates(self, bridge):
        """Should delegate get_app_version."""
        bridge._update = MagicMock()
        bridge._update.get_app_version.return_value = {
            "success": True,
            "data": {"version": "1.0.0"},
        }
        bridge.get_app_version()
        bridge._update.get_app_version.assert_called_once()

    def test_check_for_updates_delegates(self, bridge):
        """Should delegate check_for_updates."""
        bridge._update = MagicMock()
        bridge._update.check_for_updates.return_value = {
            "success": True,
            "data": {"has_update": False},
        }
        bridge.check_for_updates()
        bridge._update.check_for_updates.assert_called_once()
