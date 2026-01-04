"""Common imports re-exported for patching compatibility.
This module re-exports dependencies that tests need to patch.
All submodules should import from here instead of directly from the source.
"""
from sip_videogen.brands.storage import (
    get_active_brand,
    get_active_project,
    get_brand_dir,
    get_brands_dir,
    load_product,
    load_template,
    load_template_summary,
    list_brands,
    list_project_assets,
    add_product_image as storage_add_product_image,
    create_product as storage_create_product,
    delete_product as storage_delete_product,
    list_products as storage_list_products,
    list_projects as storage_list_projects,
    load_brand as storage_load_brand,
    save_product as storage_save_product,
    set_primary_product_image as storage_set_primary_product_image,
    create_template as storage_create_template,
    save_template as storage_save_template,
    add_template_image as storage_add_template_image,
    list_templates as storage_list_templates,
    delete_template as storage_delete_template,
)
from sip_videogen.config.settings import get_settings
from sip_videogen.config.logging import get_logger
