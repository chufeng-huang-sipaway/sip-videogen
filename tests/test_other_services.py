"""Tests for ProductService, ProjectService, and TemplateService."""
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock,patch
from sip_videogen.studio.services.product_service import ProductService
from sip_videogen.studio.services.project_service import ProjectService
from sip_videogen.studio.services.template_service import TemplateService
from sip_videogen.studio.state import BridgeState
from sip_videogen.brands.models import ProductFull,ProductSummary,ProjectFull,ProjectStatus,TemplateFull
#=============================================================================
#Common Fixtures
#=============================================================================
@pytest.fixture
def state():
    """Create fresh BridgeState."""
    s=BridgeState()
    s.get_active_slug=MagicMock(return_value="test-brand")
    return s
@pytest.fixture
def mock_brand_dir(tmp_path)->Path:
    """Create mock brand directory."""
    bd=tmp_path/"test-brand"
    bd.mkdir()
    (bd/"products").mkdir()
    (bd/"templates").mkdir()
    return bd
#=============================================================================
#ProductService Tests
#=============================================================================
class TestProductService:
    """Tests for ProductService."""
    @pytest.fixture
    def service(self,state):
        return ProductService(state)
    def test_get_products_returns_list(self,service):
        """Should return list of products."""
        mock_products=[ProductSummary(slug="prod-1",name="Product 1",description="Desc",primary_image="",created_at=datetime.utcnow(),updated_at=datetime.utcnow())]
        with patch("sip_videogen.studio.services.product_service.list_products",return_value=mock_products):
            result=service.get_products()
        assert result["success"]==True
        assert len(result["data"]["products"])==1
    def test_get_products_error_no_brand(self,service,state):
        """Should error when no brand selected."""
        state.get_active_slug=MagicMock(return_value=None)
        result=service.get_products()
        assert result["success"]==False
        assert "No brand selected"in result["error"]
    def test_get_product_returns_details(self,service):
        """Should return product details."""
        mock_product=ProductFull(slug="prod-1",name="Product",description="Desc",images=[],primary_image="",attributes=[],created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        with patch("sip_videogen.studio.services.product_service.load_product",return_value=mock_product):
            result=service.get_product("prod-1")
        assert result["success"]==True
        assert result["data"]["slug"]=="prod-1"
    def test_get_product_not_found(self,service):
        """Should error when product not found."""
        with patch("sip_videogen.studio.services.product_service.load_product",return_value=None):
            result=service.get_product("missing")
        assert result["success"]==False
        assert "not found"in result["error"]
    def test_create_product_success(self,service):
        """Should create product successfully."""
        with patch("sip_videogen.studio.services.product_service.load_product",return_value=None):
            with patch("sip_videogen.studio.services.product_service.create_product"):
                result=service.create_product("New Product","Description")
        assert result["success"]==True
        assert "slug"in result["data"]
    def test_create_product_empty_name(self,service):
        """Should reject empty product name."""
        result=service.create_product("","Description")
        assert result["success"]==False
        assert "required"in result["error"]
    def test_create_product_already_exists(self,service):
        """Should reject duplicate product slug."""
        mock_product=ProductFull(slug="existing",name="Existing",description="",images=[],primary_image="",attributes=[],created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        with patch("sip_videogen.studio.services.product_service.load_product",return_value=mock_product):
            result=service.create_product("Existing","Description")
        assert result["success"]==False
        assert "already exists"in result["error"]
    def test_delete_product_success(self,service):
        """Should delete product."""
        with patch("sip_videogen.studio.services.product_service.delete_product",return_value=True):
            result=service.delete_product("prod-1")
        assert result["success"]==True
    def test_delete_product_not_found(self,service):
        """Should error when product not found."""
        with patch("sip_videogen.studio.services.product_service.delete_product",return_value=False):
            result=service.delete_product("missing")
        assert result["success"]==False
        assert "not found"in result["error"]
#=============================================================================
#ProjectService Tests
#=============================================================================
class TestProjectService:
    """Tests for ProjectService."""
    @pytest.fixture
    def service(self,state):
        return ProjectService(state)
    def test_get_projects_returns_list(self,service):
        """Should return list of projects."""
        mock_projects=[MagicMock(slug="proj-1",name="Project 1",status=ProjectStatus.ACTIVE,created_at=datetime.utcnow(),updated_at=datetime.utcnow())]
        with patch("sip_videogen.studio.services.project_service.list_projects",return_value=mock_projects):
            with patch("sip_videogen.studio.services.project_service.get_active_project",return_value=None):
                with patch("sip_videogen.studio.services.project_service.count_project_assets",return_value=5):
                    result=service.get_projects()
        assert result["success"]==True
        assert len(result["data"]["projects"])==1
    def test_get_projects_error_no_brand(self,service,state):
        """Should error when no brand selected."""
        state.get_active_slug=MagicMock(return_value=None)
        result=service.get_projects()
        assert result["success"]==False
        assert "No brand selected"in result["error"]
    def test_get_project_returns_details(self,service):
        """Should return project details."""
        mock_project=ProjectFull(slug="proj-1",name="Project",status=ProjectStatus.ACTIVE,instructions="",created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        with patch("sip_videogen.studio.services.project_service.load_project",return_value=mock_project):
            with patch("sip_videogen.studio.services.project_service.list_project_assets",return_value=[]):
                result=service.get_project("proj-1")
        assert result["success"]==True
        assert result["data"]["slug"]=="proj-1"
    def test_get_project_not_found(self,service):
        """Should error when project not found."""
        with patch("sip_videogen.studio.services.project_service.load_project",return_value=None):
            result=service.get_project("missing")
        assert result["success"]==False
        assert "not found"in result["error"]
    def test_create_project_success(self,service):
        """Should create project successfully."""
        with patch("sip_videogen.studio.services.project_service.load_project",return_value=None):
            with patch("sip_videogen.studio.services.project_service.create_project"):
                result=service.create_project("New Project","Instructions here")
        assert result["success"]==True
        assert "slug"in result["data"]
    def test_create_project_empty_name(self,service):
        """Should reject empty project name."""
        result=service.create_project("","Instructions")
        assert result["success"]==False
        assert "required"in result["error"]
    def test_update_project_success(self,service):
        """Should update project."""
        mock_project=ProjectFull(slug="proj-1",name="Old Name",status=ProjectStatus.ACTIVE,instructions="",created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        with patch("sip_videogen.studio.services.project_service.load_project",return_value=mock_project):
            with patch("sip_videogen.studio.services.project_service.save_project"):
                result=service.update_project("proj-1",name="New Name")
        assert result["success"]==True
        assert result["data"]["name"]=="New Name"
    def test_update_project_status(self,service):
        """Should update project status."""
        mock_project=ProjectFull(slug="proj-1",name="Project",status=ProjectStatus.ACTIVE,instructions="",created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        with patch("sip_videogen.studio.services.project_service.load_project",return_value=mock_project):
            with patch("sip_videogen.studio.services.project_service.save_project"):
                result=service.update_project("proj-1",status="archived")
        assert result["success"]==True
        assert result["data"]["status"]=="archived"
    def test_update_project_invalid_status(self,service):
        """Should reject invalid status."""
        mock_project=ProjectFull(slug="proj-1",name="Project",status=ProjectStatus.ACTIVE,instructions="",created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        with patch("sip_videogen.studio.services.project_service.load_project",return_value=mock_project):
            result=service.update_project("proj-1",status="invalid")
        assert result["success"]==False
        assert "Invalid status"in result["error"]
    def test_delete_project_success(self,service):
        """Should delete project."""
        with patch("sip_videogen.studio.services.project_service.get_active_project",return_value=None):
            with patch("sip_videogen.studio.services.project_service.delete_project",return_value=True):
                result=service.delete_project("proj-1")
        assert result["success"]==True
    def test_set_active_project_success(self,service):
        """Should set active project."""
        mock_project=ProjectFull(slug="proj-1",name="Project",status=ProjectStatus.ACTIVE,instructions="",created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        with patch("sip_videogen.studio.services.project_service.load_project",return_value=mock_project):
            with patch("sip_videogen.studio.services.project_service.set_active_project"):
                result=service.set_active_project("proj-1")
        assert result["success"]==True
        assert result["data"]["active_project"]=="proj-1"
    def test_set_active_project_none(self,service):
        """Should clear active project when None."""
        with patch("sip_videogen.studio.services.project_service.set_active_project"):
            result=service.set_active_project(None)
        assert result["success"]==True
        assert result["data"]["active_project"]==None
#=============================================================================
#TemplateService Tests
#=============================================================================
class TestTemplateService:
    """Tests for TemplateService."""
    @pytest.fixture
    def service(self,state):
        return TemplateService(state)
    def test_get_templates_returns_list(self,service):
        """Should return list of templates."""
        mock_templates=[MagicMock(slug="tmpl-1",name="Template 1",description="Desc",primary_image="",default_strict=True,created_at=datetime.utcnow(),updated_at=datetime.utcnow())]
        with patch("sip_videogen.studio.services.template_service.list_templates",return_value=mock_templates):
            result=service.get_templates()
        assert result["success"]==True
        assert len(result["data"]["templates"])==1
    def test_get_templates_error_no_brand(self,service,state):
        """Should error when no brand selected."""
        state.get_active_slug=MagicMock(return_value=None)
        result=service.get_templates()
        assert result["success"]==False
        assert "No brand selected"in result["error"]
    def test_get_template_returns_details(self,service):
        """Should return template details."""
        mock_template=TemplateFull(slug="tmpl-1",name="Template",description="Desc",images=[],primary_image="",default_strict=True,analysis=None,created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        with patch("sip_videogen.studio.services.template_service.load_template",return_value=mock_template):
            result=service.get_template("tmpl-1")
        assert result["success"]==True
        assert result["data"]["slug"]=="tmpl-1"
    def test_get_template_not_found(self,service):
        """Should error when template not found."""
        with patch("sip_videogen.studio.services.template_service.load_template",return_value=None):
            result=service.get_template("missing")
        assert result["success"]==False
        assert "not found"in result["error"]
    def test_create_template_success(self,service):
        """Should create template successfully."""
        with patch("sip_videogen.studio.services.template_service.load_template",return_value=None):
            with patch("sip_videogen.studio.services.template_service.create_template"):
                result=service.create_template("New Template","Description")
        assert result["success"]==True
        assert "slug"in result["data"]
    def test_create_template_empty_name(self,service):
        """Should reject empty template name."""
        result=service.create_template("","Description")
        assert result["success"]==False
        assert "required"in result["error"]
    def test_update_template_success(self,service):
        """Should update template."""
        mock_template=TemplateFull(slug="tmpl-1",name="Old Name",description="Desc",images=[],primary_image="",default_strict=True,analysis=None,created_at=datetime.utcnow(),updated_at=datetime.utcnow())
        with patch("sip_videogen.studio.services.template_service.load_template",return_value=mock_template):
            with patch("sip_videogen.studio.services.template_service.save_template"):
                result=service.update_template("tmpl-1",name="New Name")
        assert result["success"]==True
        assert result["data"]["name"]=="New Name"
    def test_delete_template_success(self,service):
        """Should delete template."""
        with patch("sip_videogen.studio.services.template_service.delete_template",return_value=True):
            result=service.delete_template("tmpl-1")
        assert result["success"]==True
    def test_delete_template_not_found(self,service):
        """Should error when template not found."""
        with patch("sip_videogen.studio.services.template_service.delete_template",return_value=False):
            result=service.delete_template("missing")
        assert result["success"]==False
        assert "not found"in result["error"]
    def test_get_template_images(self,service):
        """Should return template images."""
        with patch("sip_videogen.studio.services.template_service.list_template_images",return_value=["img1.png","img2.png"]):
            result=service.get_template_images("tmpl-1")
        assert result["success"]==True
        assert result["data"]["images"]==["img1.png","img2.png"]
