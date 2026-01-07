"""Tests for ProductService, ProjectService, and StyleReferenceService."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sip_studio.brands.models import (
    ProductFull,
    ProductSummary,
    ProjectFull,
    ProjectStatus,
    StyleReferenceFull,
)
from sip_studio.studio.services.product_service import ProductService
from sip_studio.studio.services.project_service import ProjectService
from sip_studio.studio.services.style_reference_service import StyleReferenceService
from sip_studio.studio.state import BridgeState


# =============================================================================
# Common Fixtures
# =============================================================================
@pytest.fixture
def state():
    """Create fresh BridgeState."""
    s = BridgeState()
    s.get_active_slug = MagicMock(return_value="test-brand")
    return s


@pytest.fixture
def mock_brand_dir(tmp_path) -> Path:
    """Create mock brand directory."""
    bd = tmp_path / "test-brand"
    bd.mkdir()
    (bd / "products").mkdir()
    (bd / "templates").mkdir()
    return bd


# =============================================================================
# ProductService Tests
# =============================================================================
class TestProductService:
    """Tests for ProductService."""

    @pytest.fixture
    def service(self, state):
        return ProductService(state)

    def test_get_products_returns_list(self, service):
        """Should return list of products."""
        mock_products = [
            ProductSummary(
                slug="prod-1",
                name="Product 1",
                description="Desc",
                primary_image="",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]
        with patch(
            "sip_studio.studio.services.product_service.list_products", return_value=mock_products
        ):
            result = service.get_products()
        assert result["success"]
        assert len(result["data"]["products"]) == 1

    def test_get_products_error_no_brand(self, service, state):
        """Should error when no brand selected."""
        state.get_active_slug = MagicMock(return_value=None)
        result = service.get_products()
        assert not result["success"]
        assert "No brand selected" in result["error"]

    def test_get_product_returns_details(self, service):
        """Should return product details."""
        mock_product = ProductFull(
            slug="prod-1",
            name="Product",
            description="Desc",
            images=[],
            primary_image="",
            attributes=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with patch(
            "sip_studio.studio.services.product_service.load_product", return_value=mock_product
        ):
            result = service.get_product("prod-1")
        assert result["success"]
        assert result["data"]["slug"] == "prod-1"

    def test_get_product_not_found(self, service):
        """Should error when product not found."""
        with patch("sip_studio.studio.services.product_service.load_product", return_value=None):
            result = service.get_product("missing")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_create_product_success(self, service):
        """Should create product successfully."""
        with patch("sip_studio.studio.services.product_service.load_product", return_value=None):
            with patch("sip_studio.studio.services.product_service.create_product"):
                result = service.create_product("New Product", "Description")
        assert result["success"]
        assert "slug" in result["data"]

    def test_create_product_empty_name(self, service):
        """Should reject empty product name."""
        result = service.create_product("", "Description")
        assert not result["success"]
        assert "required" in result["error"]

    def test_create_product_already_exists(self, service):
        """Should reject duplicate product slug."""
        mock_product = ProductFull(
            slug="existing",
            name="Existing",
            description="",
            images=[],
            primary_image="",
            attributes=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with patch(
            "sip_studio.studio.services.product_service.load_product", return_value=mock_product
        ):
            result = service.create_product("Existing", "Description")
        assert not result["success"]
        assert "already exists" in result["error"]

    def test_delete_product_success(self, service):
        """Should delete product."""
        with patch("sip_studio.studio.services.product_service.delete_product", return_value=True):
            result = service.delete_product("prod-1")
        assert result["success"]

    def test_delete_product_not_found(self, service):
        """Should error when product not found."""
        with patch("sip_studio.studio.services.product_service.delete_product", return_value=False):
            result = service.delete_product("missing")
        assert not result["success"]
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_analyze_all_packaging_text_success(self, service):
        """Should analyze all products packaging text."""
        with patch(
            "sip_studio.advisor.tools._impl_analyze_all_product_packaging",
            return_value="Analyzed 3 products, 0 skipped, 0 failed",
        ) as mock_impl:
            result = await service.analyze_all_packaging_text()
        assert result["success"]
        assert "Analyzed 3 products" in result["data"]["result"]
        mock_impl.assert_called_once_with(
            skip_existing=True, skip_human_edited=True, max_products=50
        )

    @pytest.mark.asyncio
    async def test_analyze_all_packaging_text_no_brand(self, service, state):
        """Should error when no brand selected."""
        state.get_active_slug = MagicMock(return_value=None)
        result = await service.analyze_all_packaging_text()
        assert not result["success"]
        assert "No brand selected" in result["error"]

    @pytest.mark.asyncio
    async def test_analyze_all_packaging_text_skip_existing_false(self, service):
        """Should pass skip_existing parameter."""
        with patch(
            "sip_studio.advisor.tools._impl_analyze_all_product_packaging",
            return_value="Analyzed 5 products",
        ) as mock_impl:
            result = await service.analyze_all_packaging_text(skip_existing=False)
        assert result["success"]
        mock_impl.assert_called_once_with(
            skip_existing=False, skip_human_edited=True, max_products=50
        )


# =============================================================================
# ProjectService Tests
# =============================================================================
class TestProjectService:
    """Tests for ProjectService."""

    @pytest.fixture
    def service(self, state):
        return ProjectService(state)

    def test_get_projects_returns_list(self, service):
        """Should return list of projects."""
        mock_projects = [
            MagicMock(
                slug="proj-1",
                name="Project 1",
                status=ProjectStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]
        with patch(
            "sip_studio.studio.services.project_service.list_projects", return_value=mock_projects
        ):
            with patch(
                "sip_studio.studio.services.project_service.get_active_project", return_value=None
            ):
                with patch(
                    "sip_studio.studio.services.project_service.count_project_assets",
                    return_value=5,
                ):
                    result = service.get_projects()
        assert result["success"]
        assert len(result["data"]["projects"]) == 1

    def test_get_projects_error_no_brand(self, service, state):
        """Should error when no brand selected."""
        state.get_active_slug = MagicMock(return_value=None)
        result = service.get_projects()
        assert not result["success"]
        assert "No brand selected" in result["error"]

    def test_get_project_returns_details(self, service):
        """Should return project details."""
        mock_project = ProjectFull(
            slug="proj-1",
            name="Project",
            status=ProjectStatus.ACTIVE,
            instructions="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with patch(
            "sip_studio.studio.services.project_service.load_project", return_value=mock_project
        ):
            with patch(
                "sip_studio.studio.services.project_service.list_project_assets", return_value=[]
            ):
                result = service.get_project("proj-1")
        assert result["success"]
        assert result["data"]["slug"] == "proj-1"

    def test_get_project_not_found(self, service):
        """Should error when project not found."""
        with patch("sip_studio.studio.services.project_service.load_project", return_value=None):
            result = service.get_project("missing")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_create_project_success(self, service):
        """Should create project successfully."""
        with patch("sip_studio.studio.services.project_service.load_project", return_value=None):
            with patch("sip_studio.studio.services.project_service.create_project"):
                result = service.create_project("New Project", "Instructions here")
        assert result["success"]
        assert "slug" in result["data"]

    def test_create_project_empty_name(self, service):
        """Should reject empty project name."""
        result = service.create_project("", "Instructions")
        assert not result["success"]
        assert "required" in result["error"]

    def test_update_project_success(self, service):
        """Should update project."""
        mock_project = ProjectFull(
            slug="proj-1",
            name="Old Name",
            status=ProjectStatus.ACTIVE,
            instructions="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with patch(
            "sip_studio.studio.services.project_service.load_project", return_value=mock_project
        ):
            with patch("sip_studio.studio.services.project_service.save_project"):
                result = service.update_project("proj-1", name="New Name")
        assert result["success"]
        assert result["data"]["name"] == "New Name"

    def test_update_project_status(self, service):
        """Should update project status."""
        mock_project = ProjectFull(
            slug="proj-1",
            name="Project",
            status=ProjectStatus.ACTIVE,
            instructions="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with patch(
            "sip_studio.studio.services.project_service.load_project", return_value=mock_project
        ):
            with patch("sip_studio.studio.services.project_service.save_project"):
                result = service.update_project("proj-1", status="archived")
        assert result["success"]
        assert result["data"]["status"] == "archived"

    def test_update_project_invalid_status(self, service):
        """Should reject invalid status."""
        mock_project = ProjectFull(
            slug="proj-1",
            name="Project",
            status=ProjectStatus.ACTIVE,
            instructions="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with patch(
            "sip_studio.studio.services.project_service.load_project", return_value=mock_project
        ):
            result = service.update_project("proj-1", status="invalid")
        assert not result["success"]
        assert "Invalid status" in result["error"]

    def test_delete_project_success(self, service):
        """Should delete project."""
        with patch(
            "sip_studio.studio.services.project_service.get_active_project", return_value=None
        ):
            with patch(
                "sip_studio.studio.services.project_service.delete_project", return_value=True
            ):
                result = service.delete_project("proj-1")
        assert result["success"]

    def test_set_active_project_success(self, service):
        """Should set active project."""
        mock_project = ProjectFull(
            slug="proj-1",
            name="Project",
            status=ProjectStatus.ACTIVE,
            instructions="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with patch(
            "sip_studio.studio.services.project_service.load_project", return_value=mock_project
        ):
            with patch("sip_studio.studio.services.project_service.set_active_project"):
                result = service.set_active_project("proj-1")
        assert result["success"]
        assert result["data"]["active_project"] == "proj-1"

    def test_set_active_project_none(self, service):
        """Should clear active project when None."""
        with patch("sip_studio.studio.services.project_service.set_active_project"):
            result = service.set_active_project(None)
        assert result["success"]
        assert result["data"]["active_project"] is None


# =============================================================================
# StyleReferenceService Tests
# =============================================================================
class TestStyleReferenceService:
    """Tests for StyleReferenceService."""

    @pytest.fixture
    def service(self, state):
        return StyleReferenceService(state)

    def test_get_style_references_returns_list(self, service):
        """Should return list of style references."""
        mock_refs = [
            MagicMock(
                slug="sr-1",
                name="Style Ref 1",
                description="Desc",
                primary_image="",
                default_strict=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]
        with patch(
            "sip_studio.studio.services.style_reference_service.list_style_references",
            return_value=mock_refs,
        ):
            result = service.get_style_references()
        assert result["success"]
        assert len(result["data"]["style_references"]) == 1

    def test_get_style_references_error_no_brand(self, service, state):
        """Should error when no brand selected."""
        state.get_active_slug = MagicMock(return_value=None)
        result = service.get_style_references()
        assert not result["success"]
        assert "No brand selected" in result["error"]

    def test_get_style_reference_returns_details(self, service):
        """Should return style reference details."""
        mock_ref = StyleReferenceFull(
            slug="sr-1",
            name="Style Ref",
            description="Desc",
            images=[],
            primary_image="",
            default_strict=True,
            analysis=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with patch(
            "sip_studio.studio.services.style_reference_service.load_style_reference",
            return_value=mock_ref,
        ):
            result = service.get_style_reference("sr-1")
        assert result["success"]
        assert result["data"]["slug"] == "sr-1"

    def test_get_style_reference_not_found(self, service):
        """Should error when style reference not found."""
        with patch(
            "sip_studio.studio.services.style_reference_service.load_style_reference",
            return_value=None,
        ):
            result = service.get_style_reference("missing")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_create_style_reference_success(self, service):
        """Should create style reference successfully."""
        with patch(
            "sip_studio.studio.services.style_reference_service.load_style_reference",
            return_value=None,
        ):
            with patch("sip_studio.studio.services.style_reference_service.create_style_reference"):
                result = service.create_style_reference("New Style Ref", "Description")
        assert result["success"]
        assert "slug" in result["data"]

    def test_create_style_reference_empty_name(self, service):
        """Should reject empty style reference name."""
        result = service.create_style_reference("", "Description")
        assert not result["success"]
        assert "required" in result["error"]

    def test_update_style_reference_success(self, service):
        """Should update style reference."""
        mock_ref = StyleReferenceFull(
            slug="sr-1",
            name="Old Name",
            description="Desc",
            images=[],
            primary_image="",
            default_strict=True,
            analysis=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with patch(
            "sip_studio.studio.services.style_reference_service.load_style_reference",
            return_value=mock_ref,
        ):
            with patch("sip_studio.studio.services.style_reference_service.save_style_reference"):
                result = service.update_style_reference("sr-1", name="New Name")
        assert result["success"]
        assert result["data"]["name"] == "New Name"

    def test_delete_style_reference_success(self, service):
        """Should delete style reference."""
        with patch(
            "sip_studio.studio.services.style_reference_service.delete_style_reference",
            return_value=True,
        ):
            result = service.delete_style_reference("sr-1")
        assert result["success"]

    def test_delete_style_reference_not_found(self, service):
        """Should error when style reference not found."""
        with patch(
            "sip_studio.studio.services.style_reference_service.delete_style_reference",
            return_value=False,
        ):
            result = service.delete_style_reference("missing")
        assert not result["success"]
        assert "not found" in result["error"]

    def test_get_style_reference_images(self, service):
        """Should return style reference images."""
        with patch(
            "sip_studio.studio.services.style_reference_service.list_style_reference_images",
            return_value=["img1.png", "img2.png"],
        ):
            result = service.get_style_reference_images("sr-1")
        assert result["success"]
        assert result["data"]["images"] == ["img1.png", "img2.png"]
