"""Tests for studio decorators."""

import pytest

from sip_videogen.studio.utils.decorators import require_brand


# =============================================================================
# Test fixtures
# =============================================================================
class MockState:
    """Mock BridgeState for testing."""

    def __init__(self, slug: str | None = None):
        self._slug = slug

    def get_active_slug(self) -> str | None:
        return self._slug


class MockService:
    """Mock service class for decorator testing."""

    def __init__(self, state: MockState):
        self._state = state

    @require_brand()
    def sync_method(self, brand_slug: str | None = None) -> dict:
        return {"success": True, "slug": brand_slug}

    @require_brand(param_name="slug")
    def sync_method_custom_param(self, slug: str | None = None) -> dict:
        return {"success": True, "slug": slug}

    @require_brand()
    async def async_method(self, brand_slug: str | None = None) -> dict:
        return {"success": True, "slug": brand_slug}


# =============================================================================
# Sync method tests
# =============================================================================
class TestSyncMethod:
    """Tests for require_brand on sync methods."""

    def test_uses_active_slug_when_none_passed(self):
        """Should use active slug when brand_slug is None."""
        state = MockState(slug="active-brand")
        service = MockService(state)
        result = service.sync_method()
        assert result["success"] == True
        assert result["slug"] == "active-brand"

    def test_uses_explicit_slug_when_passed(self):
        """Should use explicit slug when provided."""
        state = MockState(slug="active-brand")
        service = MockService(state)
        result = service.sync_method(brand_slug="explicit-brand")
        assert result["success"] == True
        assert result["slug"] == "explicit-brand"

    def test_returns_error_when_no_brand_available(self):
        """Should return error when no brand selected."""
        state = MockState(slug=None)
        service = MockService(state)
        result = service.sync_method()
        assert result["success"] == False
        assert "No brand selected" in result["error"]

    def test_explicit_none_uses_active(self):
        """Should use active brand when None is explicitly passed."""
        state = MockState(slug="active-brand")
        service = MockService(state)
        result = service.sync_method(brand_slug=None)
        assert result["success"] == True
        assert result["slug"] == "active-brand"

    def test_custom_param_name(self):
        """Should work with custom param name."""
        state = MockState(slug="active-brand")
        service = MockService(state)
        result = service.sync_method_custom_param()
        assert result["success"] == True
        assert result["slug"] == "active-brand"


# =============================================================================
# Async method tests
# =============================================================================
class TestAsyncMethod:
    """Tests for require_brand on async methods."""

    @pytest.mark.asyncio
    async def test_uses_active_slug_when_none_passed(self):
        """Should use active slug when brand_slug is None."""
        state = MockState(slug="active-brand")
        service = MockService(state)
        result = await service.async_method()
        assert result["success"] == True
        assert result["slug"] == "active-brand"

    @pytest.mark.asyncio
    async def test_uses_explicit_slug_when_passed(self):
        """Should use explicit slug when provided."""
        state = MockState(slug="active-brand")
        service = MockService(state)
        result = await service.async_method(brand_slug="explicit-brand")
        assert result["success"] == True
        assert result["slug"] == "explicit-brand"

    @pytest.mark.asyncio
    async def test_returns_error_when_no_brand_available(self):
        """Should return error when no brand selected."""
        state = MockState(slug=None)
        service = MockService(state)
        result = await service.async_method()
        assert result["success"] == False
        assert "No brand selected" in result["error"]


# =============================================================================
# Decorator validation tests
# =============================================================================
class TestDecoratorValidation:
    """Tests for decorator parameter validation."""

    def test_raises_type_error_for_missing_param(self):
        """Should raise TypeError when param_name doesn't exist."""
        with pytest.raises(TypeError, match="has no 'brand_slug' parameter"):

            class BadService:
                @require_brand()
                def method_without_param(self):
                    pass

    def test_raises_type_error_for_wrong_param_name(self):
        """Should raise TypeError when custom param_name doesn't exist."""
        with pytest.raises(TypeError, match="has no 'wrong_name' parameter"):

            class BadService:
                @require_brand(param_name="wrong_name")
                def method_with_different_param(self, slug: str | None = None):
                    pass

    def test_allows_kwargs_method(self):
        """Should allow methods with **kwargs."""

        class ServiceWithKwargs:
            def __init__(self):
                self._state = MockState(slug="test")

            @require_brand()
            def method_with_kwargs(self, **kwargs) -> dict:
                return {"success": True, "slug": kwargs.get("brand_slug")}

        service = ServiceWithKwargs()
        result = service.method_with_kwargs()
        assert result["success"] == True
        assert result["slug"] == "test"
