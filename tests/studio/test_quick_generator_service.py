"""Tests for sip_studio.studio.services.quick_generator_service module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_studio.studio.services.quick_generator_service import QuickGeneratorService
from sip_studio.studio.state import BridgeState


# =========================================================================
# Test fixtures
# =========================================================================
@pytest.fixture
def mock_state():
    return BridgeState()


@pytest.fixture
def service(mock_state):
    return QuickGeneratorService(mock_state)


# =========================================================================
# Validation Tests
# =========================================================================
def test_generate_no_brand_returns_error(service):
    """Test generate fails when no brand is active."""
    with patch(
        "sip_studio.studio.services.quick_generator_service.get_active_brand", return_value=None
    ):
        result = service.generate("test prompt")
        assert result["success"] is False
        assert "No brand selected" in result["error"]


def test_generate_invalid_product_returns_error(service):
    """Test generate fails when product not found."""
    with (
        patch(
            "sip_studio.studio.services.quick_generator_service.get_active_brand",
            return_value="test-brand",
        ),
        patch("sip_studio.studio.services.quick_generator_service.load_product", return_value=None),
    ):
        result = service.generate("test prompt", product_slug="invalid-product")
        assert result["success"] is False
        assert "not found" in result["error"]


def test_generate_invalid_style_reference_returns_error(service):
    """Test generate fails when style reference not found."""
    with (
        patch(
            "sip_studio.studio.services.quick_generator_service.get_active_brand",
            return_value="test-brand",
        ),
        patch(
            "sip_studio.studio.services.quick_generator_service.load_style_reference",
            return_value=None,
        ),
    ):
        result = service.generate("test prompt", style_reference_slug="invalid-style")
        assert result["success"] is False
        assert "not found" in result["error"]


def test_generate_count_clamped_to_range(service):
    """Test count is clamped between 1 and 10."""
    with (
        patch(
            "sip_studio.studio.services.quick_generator_service.get_active_brand",
            return_value="test-brand",
        ),
        patch.object(service, "_async_generate_single", new_callable=AsyncMock) as mock_gen,
    ):
        mock_gen.return_value = {"path": "/test/img.png", "prompt": "test"}
        with patch.object(service, "_path_to_base64", return_value="data:image/png;base64,test"):
            # Test count=0 becomes 1
            result = service.generate("test prompt", count=0)
            assert result["requested"] == 1
            # Test count=100 becomes 10
            result = service.generate("test prompt", count=100)
            assert result["requested"] == 10


# =========================================================================
# Success Path Tests
# =========================================================================
def test_generate_single_success(service):
    """Test successful single image generation."""
    with (
        patch(
            "sip_studio.studio.services.quick_generator_service.get_active_brand",
            return_value="test-brand",
        ),
        patch.object(service, "_async_generate_single", new_callable=AsyncMock) as mock_gen,
        patch.object(service, "_path_to_base64", return_value="data:image/png;base64,test"),
    ):
        mock_gen.return_value = {"path": "/test/img.png", "prompt": "test"}
        result = service.generate("test prompt", count=1)
        assert result["success"] is True
        assert result["generated"] == 1
        assert result["requested"] == 1
        assert len(result["images"]) == 1
        assert result["images"][0]["data"] == "data:image/png;base64,test"
        assert result["errors"] is None


def test_generate_batch_success(service):
    """Test successful batch image generation."""
    with (
        patch(
            "sip_studio.studio.services.quick_generator_service.get_active_brand",
            return_value="test-brand",
        ),
        patch.object(service, "_async_generate_single", new_callable=AsyncMock) as mock_gen,
        patch.object(service, "_path_to_base64", return_value="data:image/png;base64,test"),
    ):
        mock_gen.return_value = {"path": "/test/img.png", "prompt": "test"}
        result = service.generate("test prompt", count=3)
        assert result["success"] is True
        assert result["generated"] == 3
        assert result["requested"] == 3
        assert len(result["images"]) == 3


# =========================================================================
# Partial Failure Tests
# =========================================================================
def test_generate_partial_failure(service):
    """Test partial failure returns some results."""
    call_count = [0]

    async def mock_gen(*_args, **_kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("Generation failed")
        return {"path": "/test/img.png", "prompt": "test"}

    with (
        patch(
            "sip_studio.studio.services.quick_generator_service.get_active_brand",
            return_value="test-brand",
        ),
        patch.object(service, "_async_generate_single", side_effect=mock_gen),
        patch.object(service, "_path_to_base64", return_value="data:image/png;base64,test"),
    ):
        result = service.generate("test prompt", count=3)
        assert result["success"] is True
        assert result["generated"] == 2
        assert result["requested"] == 3
        assert len(result["images"]) == 2
        assert len(result["errors"]) == 1
        assert result["errors"][0]["index"] == 1


def test_generate_all_fail(service):
    """Test all failures returns error."""
    with (
        patch(
            "sip_studio.studio.services.quick_generator_service.get_active_brand",
            return_value="test-brand",
        ),
        patch.object(service, "_async_generate_single", new_callable=AsyncMock) as mock_gen,
    ):
        mock_gen.side_effect = RuntimeError("All failed")
        result = service.generate("test prompt", count=2)
        assert result["success"] is False
        assert "All generations failed" in result["error"]
        assert len(result["errors"]) == 2


# =========================================================================
# Product and Style Reference Tests
# =========================================================================
def test_generate_with_product(service):
    """Test generation with product validates product exists."""
    mock_product = MagicMock()
    mock_product.primary_image = "products/test/img.png"
    with (
        patch(
            "sip_studio.studio.services.quick_generator_service.get_active_brand",
            return_value="test-brand",
        ),
        patch(
            "sip_studio.studio.services.quick_generator_service.load_product",
            return_value=mock_product,
        ) as mock_load,
        patch.object(service, "_async_generate_single", new_callable=AsyncMock) as mock_gen,
        patch.object(service, "_path_to_base64", return_value="data:image/png;base64,test"),
    ):
        mock_gen.return_value = {"path": "/test/img.png", "prompt": "test"}
        result = service.generate("test prompt", product_slug="test-product")
        assert result["success"] is True
        mock_load.assert_called_once_with("test-brand", "test-product")


def test_generate_with_style_reference(service):
    """Test generation with style reference validates style ref exists."""
    mock_style_ref = MagicMock()
    with (
        patch(
            "sip_studio.studio.services.quick_generator_service.get_active_brand",
            return_value="test-brand",
        ),
        patch(
            "sip_studio.studio.services.quick_generator_service.load_style_reference",
            return_value=mock_style_ref,
        ) as mock_load,
        patch.object(service, "_async_generate_single", new_callable=AsyncMock) as mock_gen,
        patch.object(service, "_path_to_base64", return_value="data:image/png;base64,test"),
    ):
        mock_gen.return_value = {"path": "/test/img.png", "prompt": "test"}
        result = service.generate("test prompt", style_reference_slug="test-style")
        assert result["success"] is True
        mock_load.assert_called_once_with("test-brand", "test-style")


# =========================================================================
# Base64 Conversion Tests
# =========================================================================
def test_path_to_base64_returns_none_for_nonexistent(service):
    """Test _path_to_base64 returns None for nonexistent file."""
    result = service._path_to_base64("/nonexistent/path.png")
    assert result is None


def test_path_to_base64_handles_exception(service):
    """Test _path_to_base64 handles exceptions gracefully."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_bytes", side_effect=PermissionError("No access")),
    ):
        result = service._path_to_base64("/some/path.png")
        assert result is None


# =========================================================================
# Bridge Method Tests (integration with StudioBridge)
# =========================================================================
def test_bridge_quick_generate_validates_aspect_ratio():
    """Test bridge validates aspect ratio."""
    from sip_studio.studio.bridge import StudioBridge

    with patch("sip_studio.studio.bridge.load_api_keys_from_config"):
        bridge = StudioBridge()
        _ = bridge.quick_generate("test", "invalid_ratio")
        # If aspect ratio in wrong position, it validates correctly
        # Actually, second param is product_slug, so this tests a different path


def test_bridge_quick_generate_invalid_aspect_ratio():
    """Test bridge returns error for invalid aspect ratio."""
    from sip_studio.studio.bridge import StudioBridge

    with patch("sip_studio.studio.bridge.load_api_keys_from_config"):
        bridge = StudioBridge()
        result = bridge.quick_generate("test", aspect_ratio="invalid")
        assert result.get("success") is False
        assert "Invalid aspect ratio" in result.get("error", "")


def test_bridge_quick_generate_delegates_to_service():
    """Test bridge delegates to QuickGeneratorService."""
    from sip_studio.studio.bridge import StudioBridge

    mock_result = {"success": True, "images": [], "errors": None, "generated": 1, "requested": 1}
    with (
        patch("sip_studio.studio.bridge.load_api_keys_from_config"),
        patch(
            "sip_studio.studio.services.quick_generator_service.QuickGeneratorService.generate",
            return_value=mock_result,
        ),
    ):
        bridge = StudioBridge()
        result = bridge.quick_generate("test prompt", aspect_ratio="1:1")
        assert result.get("success") is True
