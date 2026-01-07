"""Tests for BrandService."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sip_studio.brands.models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIdentityFull,
    BrandIndexEntry,
    ColorDefinition,
    CompetitivePositioning,
    VisualIdentity,
    VoiceGuidelines,
)
from sip_studio.studio.services.brand_service import BrandService
from sip_studio.studio.state import BridgeState


def set_state_slug(state: BridgeState, slug: str | None) -> None:
    """Set state slug directly without storage validation (for tests only)."""
    state._cached_slug = slug
    state._cache_valid = True


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def state():
    """Create a fresh BridgeState."""
    return BridgeState()


@pytest.fixture
def service(state):
    """Create BrandService with state."""
    return BrandService(state)


@pytest.fixture
def sample_identity() -> BrandIdentityFull:
    """Create a sample brand identity for testing."""
    return BrandIdentityFull(
        slug="test-brand",
        core=BrandCoreIdentity(
            name="Test Brand", tagline="Test tagline", mission="Test mission", values=["Quality"]
        ),
        visual=VisualIdentity(
            primary_colors=[ColorDefinition(hex="#000000", name="Black", usage="Primary")],
            typography_style="Modern",
            image_style="Clean",
        ),
        voice=VoiceGuidelines(
            personality="Friendly and professional", tone_attributes=["Professional", "Warm"]
        ),
        audience=AudienceProfile(primary_summary="Adults", pain_points=["Time"]),
        positioning=CompetitivePositioning(
            market_category="Tech", unique_value_proposition="Best", primary_competitors=[]
        ),
        constraints=[],
        avoid=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def brands_dir(tmp_path, monkeypatch) -> Path:
    """Setup isolated brands directory."""
    bd = tmp_path / "brands"
    bd.mkdir()
    (bd / "index.json").write_text('{"brands":[],"active_brand":null}')
    # Patch the get_brands_dir function to return our temp dir
    monkeypatch.setattr("sip_studio.brands.storage.base.get_brands_dir", lambda: bd)
    monkeypatch.setattr("sip_studio.studio.services.brand_service.get_brand_dir", lambda s: bd / s)
    return bd


# =============================================================================
# get_brands tests
# =============================================================================
class TestGetBrands:
    """Tests for get_brands method."""

    def test_returns_empty_list_when_no_brands(self, service, brands_dir):
        """Should return empty list when no brands exist."""
        with patch("sip_studio.studio.services.brand_service.list_brands", return_value=[]):
            result = service.get_brands()
        assert result["success"]
        assert result["data"]["brands"] == []
        assert result["data"]["active"] is None

    def test_returns_brands_list(self, service, state, brands_dir):
        """Should return list of brands."""
        entries = [
            BrandIndexEntry(
                slug="brand-a",
                name="Brand A",
                category="Tech",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            BrandIndexEntry(
                slug="brand-b",
                name="Brand B",
                category="Food",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        set_state_slug(state, "brand-a")
        with patch("sip_studio.studio.services.brand_service.list_brands", return_value=entries):
            result = service.get_brands()
        assert result["success"]
        assert len(result["data"]["brands"]) == 2
        assert result["data"]["brands"][0]["slug"] == "brand-a"
        assert result["data"]["active"] == "brand-a"

    def test_handles_exception(self, service):
        """Should return error on exception."""
        with patch(
            "sip_studio.studio.services.brand_service.list_brands",
            side_effect=Exception("DB error"),
        ):
            result = service.get_brands()
        assert not result["success"]
        assert "DB error" in result["error"]


# =============================================================================
# set_brand tests
# =============================================================================
class TestSetBrand:
    """Tests for set_brand method."""

    def test_sets_active_brand(self, service, state):
        """Should set active brand and initialize advisor."""
        entries = [
            BrandIndexEntry(
                slug="my-brand",
                name="My Brand",
                category="Tech",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]
        with patch("sip_studio.studio.services.brand_service.list_brands", return_value=entries):
            with patch("sip_studio.brands.storage.set_active_brand"):
                with patch("sip_studio.advisor.agent.BrandAdvisor"):
                    result = service.set_brand("my-brand")
        assert result["success"]
        assert result["data"]["slug"] == "my-brand"
        assert state.get_active_slug() == "my-brand"

    def test_returns_error_for_nonexistent_brand(self, service):
        """Should return error if brand not found."""
        with patch("sip_studio.studio.services.brand_service.list_brands", return_value=[]):
            result = service.set_brand("nonexistent")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_preserves_existing_advisor(self, service, state):
        """Should call set_brand on existing advisor."""
        mock_advisor = MagicMock()
        state.advisor = mock_advisor
        entries = [
            BrandIndexEntry(
                slug="new-brand",
                name="New",
                category="Tech",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]
        with patch("sip_studio.studio.services.brand_service.list_brands", return_value=entries):
            with patch("sip_studio.brands.storage.set_active_brand"):
                service.set_brand("new-brand")
        mock_advisor.set_brand.assert_called_once_with("new-brand", preserve_history=False)


# =============================================================================
# get_brand_info tests
# =============================================================================
class TestGetBrandInfo:
    """Tests for get_brand_info method."""

    def test_returns_brand_info(self, service, state):
        """Should return brand summary info."""
        mock_summary = MagicMock()
        mock_summary.name = "Test Brand"
        mock_summary.tagline = "Great stuff"
        mock_summary.category = "Tech"
        set_state_slug(state, "test")
        with patch(
            "sip_studio.studio.services.brand_service.load_brand_summary",
            return_value=mock_summary,
        ):
            result = service.get_brand_info()
        assert result["success"]
        assert result["data"]["name"] == "Test Brand"
        assert result["data"]["slug"] == "test"

    def test_uses_provided_slug(self, service):
        """Should use provided slug instead of active."""
        mock_summary = MagicMock()
        mock_summary.name = "Other"
        mock_summary.tagline = "Tag"
        mock_summary.category = "Food"
        with patch(
            "sip_studio.studio.services.brand_service.load_brand_summary",
            return_value=mock_summary,
        ):
            result = service.get_brand_info("other-brand")
        assert result["data"]["slug"] == "other-brand"

    def test_error_when_no_brand_selected(self, service, state):
        """Should return error when no brand selected."""
        set_state_slug(state, None)  # Explicitly set no active brand
        result = service.get_brand_info()
        assert not result["success"]
        assert "No brand selected" in result["error"]

    def test_error_when_brand_not_found(self, service, state):
        """Should return error when brand not found."""
        set_state_slug(state, "missing")
        with patch(
            "sip_studio.studio.services.brand_service.load_brand_summary", return_value=None
        ):
            result = service.get_brand_info()
        assert not result["success"]
        assert "not found" in result["error"]


# =============================================================================
# get_brand_identity tests
# =============================================================================
class TestGetBrandIdentity:
    """Tests for get_brand_identity method."""

    def test_returns_full_identity(self, service, state, sample_identity):
        """Should return full brand identity."""
        set_state_slug(state, "test-brand")
        with patch(
            "sip_studio.studio.services.brand_service.load_brand",
            return_value=sample_identity,
        ):
            result = service.get_brand_identity()
        assert result["success"]
        assert result["data"]["slug"] == "test-brand"
        assert result["data"]["core"]["name"] == "Test Brand"

    def test_error_when_no_brand_selected(self, service, state):
        """Should return error when no brand selected."""
        set_state_slug(state, None)  # Explicitly set no active brand
        result = service.get_brand_identity()
        assert not result["success"]
        assert "No brand selected" in result["error"]


# =============================================================================
# update_brand_identity_section tests
# =============================================================================
class TestUpdateBrandIdentitySection:
    """Tests for update_brand_identity_section method."""

    def test_updates_core_section(self, service, sample_identity, state):
        """Should update core section."""
        set_state_slug(state, "test")
        with patch(
            "sip_studio.studio.services.brand_service.load_brand",
            return_value=sample_identity,
        ):
            with patch("sip_studio.studio.services.brand_service.save_brand") as mock_save:
                result = service.update_brand_identity_section(
                    "core",
                    {
                        "name": "New Name",
                        "tagline": "New tag",
                        "mission": "New mission",
                        "values": ["New value"],
                    },
                )
        assert result["success"]
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved.core.name == "New Name"

    def test_updates_visual_section(self, service, state, sample_identity):
        """Should update visual section."""
        set_state_slug(state, "test")
        with patch(
            "sip_studio.studio.services.brand_service.load_brand",
            return_value=sample_identity,
        ):
            with patch("sip_studio.studio.services.brand_service.save_brand"):
                result = service.update_brand_identity_section(
                    "visual",
                    {
                        "primary_colors": [{"hex": "#FF0000", "name": "Red", "usage": "Primary"}],
                        "typography_style": "Bold",
                        "image_style": "Vibrant",
                    },
                )
        assert result["success"]

    def test_updates_constraints_avoid(self, service, state, sample_identity):
        """Should update constraints and avoid lists."""
        set_state_slug(state, "test")
        with patch(
            "sip_studio.studio.services.brand_service.load_brand",
            return_value=sample_identity,
        ):
            with patch("sip_studio.studio.services.brand_service.save_brand") as mock_save:
                result = service.update_brand_identity_section(
                    "constraints_avoid",
                    {"constraints": ["Must be blue"], "avoid": ["Red colors"]},
                )
        assert result["success"]
        saved = mock_save.call_args[0][0]
        assert saved.constraints == ["Must be blue"]
        assert saved.avoid == ["Red colors"]

    def test_error_for_invalid_section(self, service, state, sample_identity):
        """Should return error for invalid section name."""
        set_state_slug(state, "test")
        with patch(
            "sip_studio.studio.services.brand_service.load_brand",
            return_value=sample_identity,
        ):
            result = service.update_brand_identity_section("invalid_section", {})
        assert not result["success"]
        assert "Invalid section" in result["error"]

    def test_refreshes_advisor_after_update(self, service, sample_identity, state):
        """Should refresh advisor after identity update."""
        mock_advisor = MagicMock()
        state.advisor = mock_advisor
        set_state_slug(state, "test")
        with patch(
            "sip_studio.studio.services.brand_service.load_brand",
            return_value=sample_identity,
        ):
            with patch("sip_studio.studio.services.brand_service.save_brand"):
                service.update_brand_identity_section(
                    "core", {"name": "Updated", "tagline": "t", "mission": "m", "values": []}
                )
        mock_advisor.set_brand.assert_called_once_with("test", preserve_history=True)


# =============================================================================
# delete_brand tests
# =============================================================================
class TestDeleteBrand:
    """Tests for delete_brand method."""

    def test_deletes_brand(self, service):
        """Should delete brand successfully."""
        entries = [
            BrandIndexEntry(
                slug="to-delete",
                name="Delete Me",
                category="Tech",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]
        with patch("sip_studio.studio.services.brand_service.list_brands", return_value=entries):
            with patch(
                "sip_studio.studio.services.brand_service.storage_delete_brand",
                return_value=True,
            ):
                result = service.delete_brand("to-delete")
        assert result["success"]

    def test_error_for_nonexistent_brand(self, service):
        """Should return error if brand not found."""
        with patch("sip_studio.studio.services.brand_service.list_brands", return_value=[]):
            result = service.delete_brand("nonexistent")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_clears_advisor_when_deleting_active(self, service, state):
        """Should clear advisor when deleting active brand."""
        state.advisor = MagicMock()
        set_state_slug(state, "active-brand")
        entries = [
            BrandIndexEntry(
                slug="active-brand",
                name="Active",
                category="Tech",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]
        with patch("sip_studio.studio.services.brand_service.list_brands", return_value=entries):
            with patch(
                "sip_studio.studio.services.brand_service.storage_delete_brand",
                return_value=True,
            ):
                result = service.delete_brand("active-brand")
        assert result["success"]
        assert state.advisor is None


# =============================================================================
# list_identity_backups tests
# =============================================================================
class TestListIdentityBackups:
    """Tests for list_identity_backups method."""

    def test_returns_backup_list(self, service, state):
        """Should return list of backups."""
        backups = ["2024-01-01T12-00-00.json", "2024-01-02T12-00-00.json"]
        set_state_slug(state, "test")
        with patch(
            "sip_studio.studio.services.brand_service.list_brand_backups",
            return_value=backups,
        ):
            result = service.list_identity_backups()
        assert result["success"]
        assert result["data"]["backups"] == backups

    def test_error_when_no_brand_selected(self, service, state):
        """Should return error when no brand selected."""
        set_state_slug(state, None)  # Explicitly set no active brand
        result = service.list_identity_backups()
        assert not result["success"]


# =============================================================================
# restore_identity_backup tests
# =============================================================================
class TestRestoreIdentityBackup:
    """Tests for restore_identity_backup method."""

    def test_restores_backup(self, service, sample_identity, state):
        """Should restore backup successfully."""
        set_state_slug(state, "test")
        with patch(
            "sip_studio.studio.services.brand_service.restore_brand_backup",
            return_value=sample_identity,
        ):
            with patch("sip_studio.studio.services.brand_service.save_brand"):
                result = service.restore_identity_backup("2024-01-01.json")
        assert result["success"]
        # slug is set to active brand, not the restored identity's original slug
        assert result["data"]["slug"] == "test"

    def test_rejects_path_traversal(self, service, state):
        """Should reject filenames with path separators."""
        set_state_slug(state, "test")
        result = service.restore_identity_backup("../etc/passwd")
        assert not result["success"]
        assert "path separators" in result["error"]

    def test_rejects_non_json_files(self, service, state):
        """Should reject non-JSON filenames."""
        set_state_slug(state, "test")
        result = service.restore_identity_backup("backup.txt")
        assert not result["success"]
        assert ".json" in result["error"]


# =============================================================================
# _build_concept helper tests
# =============================================================================
class TestBuildConcept:
    """Tests for _build_concept helper method."""

    def test_builds_from_description_only(self, service):
        """Should build concept from description only."""
        concept, err = service._build_concept("My brand description", [])
        assert err is None
        assert "My brand description" in concept

    def test_builds_from_documents_only(self, service):
        """Should build concept from documents only."""
        import base64

        doc_content = base64.b64encode(b"Document content here").decode()
        docs = [{"filename": "doc.txt", "data": doc_content}]
        concept, err = service._build_concept("", docs)
        assert err is None
        assert "Document content" in concept

    def test_combines_description_and_documents(self, service):
        """Should combine description and documents."""
        import base64

        doc_content = base64.b64encode(b"Doc text").decode()
        docs = [{"filename": "readme.md", "data": doc_content}]
        concept, err = service._build_concept("Brand desc", docs)
        assert err is None
        assert "Brand desc" in concept
        assert "Doc text" in concept

    def test_error_when_empty(self, service):
        """Should return error when no content provided."""
        concept, err = service._build_concept("", [])
        assert concept is None
        assert "provide" in err.lower()

    def test_truncates_long_content(self, service):
        """Should truncate content exceeding max length."""
        import base64

        long_content = base64.b64encode(b"x" * 100000).decode()
        docs = [{"filename": "big.txt", "data": long_content}]
        concept, err = service._build_concept("", docs)
        assert err is None
        assert len(concept) <= 5000
        assert "truncated" in concept.lower()
