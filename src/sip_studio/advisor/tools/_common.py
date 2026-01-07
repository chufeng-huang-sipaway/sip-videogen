"""Common imports re-exported for patching compatibility.
This module re-exports dependencies that tests need to patch.
All submodules should import from here instead of directly from the source.
"""

from sip_studio.brands.storage import add_product_image as storage_add_product_image
from sip_studio.brands.storage import (
    add_style_reference_image as storage_add_style_reference_image,
)
from sip_studio.brands.storage import create_product as storage_create_product
from sip_studio.brands.storage import create_style_reference as storage_create_style_reference
from sip_studio.brands.storage import delete_product as storage_delete_product
from sip_studio.brands.storage import delete_style_reference as storage_delete_style_reference
from sip_studio.brands.storage import (
    get_active_brand,
    get_active_project,
    get_brand_dir,
    get_brands_dir,
    list_brands,
    list_project_assets,
    load_product,
    load_style_reference,
    load_style_reference_summary,
)
from sip_studio.brands.storage import list_products as storage_list_products
from sip_studio.brands.storage import list_projects as storage_list_projects
from sip_studio.brands.storage import list_style_references as storage_list_style_references
from sip_studio.brands.storage import load_brand as storage_load_brand
from sip_studio.brands.storage import save_product as storage_save_product
from sip_studio.brands.storage import save_style_reference as storage_save_style_reference
from sip_studio.brands.storage import (
    set_primary_product_image as storage_set_primary_product_image,
)
from sip_studio.config.logging import get_logger
from sip_studio.config.settings import get_settings

__all__ = [
    "get_active_brand",
    "get_active_project",
    "get_brand_dir",
    "get_brands_dir",
    "load_product",
    "load_style_reference",
    "load_style_reference_summary",
    "list_brands",
    "list_project_assets",
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
    "get_settings",
    "get_logger",
]
