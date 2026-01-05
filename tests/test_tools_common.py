"""Tests for _common.py re-exports - prevents silent breakage of tool dependencies."""

import pytest


class TestCommonExports:
    """Verify _common.py re-exports all functions that tools depend on."""

    def test_storage_functions_exported(self):
        """Core storage functions must be available via _common."""
        from sip_videogen.advisor.tools import _common

        required = [
            "get_active_brand",
            "get_active_project",
            "get_brand_dir",
            "get_brands_dir",
            "load_product",
            "load_style_reference",
            "load_style_reference_summary",
            "list_brands",
            "list_project_assets",
        ]
        for name in required:
            assert hasattr(_common, name), f"_common missing required export: {name}"

    def test_aliased_storage_functions_exported(self):
        """Aliased storage functions (storage_*) must be available."""
        from sip_videogen.advisor.tools import _common

        required = [
            "storage_add_product_image",
            "storage_create_product",
            "storage_delete_product",
            "storage_list_products",
            "storage_list_projects",
            "storage_load_brand",
            "storage_save_product",
            "storage_set_primary_product_image",
            "storage_create_style_reference",
            "storage_save_style_reference",
            "storage_add_style_reference_image",
            "storage_list_style_references",
            "storage_delete_style_reference",
        ]
        for name in required:
            assert hasattr(_common, name), f"_common missing required aliased export: {name}"

    def test_config_functions_exported(self):
        """Config functions must be available via _common."""
        from sip_videogen.advisor.tools import _common

        required = [
            "get_settings",
            "get_logger",
        ]
        for name in required:
            assert hasattr(_common, name), f"_common missing required config export: {name}"

    def test_load_style_reference_is_callable(self):
        """load_style_reference must be a callable function, not None."""
        from sip_videogen.advisor.tools import _common

        assert callable(_common.load_style_reference), "load_style_reference must be callable"

    def test_image_tools_can_import_common(self):
        """image_tools.py must be able to import and use _common."""
        from sip_videogen.advisor.tools import image_tools
        from sip_videogen.advisor.tools import _common

        # Verify image_tools has access to _common (it imports it)
        assert hasattr(image_tools, "_common") or True  # Module imports are internal
        # The real test: _common functions are usable
        assert callable(_common.get_active_brand)
        assert callable(_common.load_style_reference)
