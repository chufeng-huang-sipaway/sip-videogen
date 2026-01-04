"""Brand storage and persistence functions.
Handles reading/writing brand data to ~/.sip-videogen/brands/
"""
__all__=[
    #base
    "get_brands_dir","get_brand_dir","get_index_path","slugify","validate_slug","safe_resolve_path",
    #index
    "load_index","save_index",
    #brand
    "create_brand","load_brand","load_brand_summary","save_brand","delete_brand",
    "list_brands","update_brand_summary_stats","backup_brand_identity",
    "list_brand_backups","restore_brand_backup","get_active_brand","set_active_brand",
    #product
    "get_products_dir","get_product_dir","load_product_index","save_product_index",
    "create_product","load_product","load_product_summary","save_product",
    "delete_product","list_products","list_product_images","add_product_image",
    "delete_product_image","set_primary_product_image",
    #project
    "get_projects_dir","get_project_dir","load_project_index","save_project_index",
    "count_project_assets","list_project_assets","create_project","load_project",
    "load_project_summary","save_project","delete_project","list_projects",
    "get_active_project","set_active_project",
    #template
    "get_templates_dir","get_template_dir","load_template_index","save_template_index",
    "create_template","load_template","load_template_summary","save_template",
    "delete_template","list_templates","list_template_images","add_template_image",
    "delete_template_image","set_primary_template_image","sync_template_index",
    #document
    "get_docs_dir","list_documents","save_document","delete_document","rename_document",
    "load_image_status_raw","save_image_status","get_assets_dir","list_assets","save_asset",
]
#Re-export from submodules
from .base import get_brands_dir,get_brand_dir,get_index_path,slugify,validate_slug,safe_resolve_path
from .index import load_index,save_index
from .brand_storage import(create_brand,load_brand,load_brand_summary,save_brand,delete_brand,list_brands,update_brand_summary_stats,backup_brand_identity,list_brand_backups,restore_brand_backup,get_active_brand,set_active_brand)
from .product_storage import(get_products_dir,get_product_dir,load_product_index,save_product_index,create_product,load_product,load_product_summary,save_product,delete_product,list_products,list_product_images,add_product_image,delete_product_image,set_primary_product_image)
from .project_storage import(get_projects_dir,get_project_dir,load_project_index,save_project_index,count_project_assets,list_project_assets,create_project,load_project,load_project_summary,save_project,delete_project,list_projects,get_active_project,set_active_project)
from .template_storage import(get_templates_dir,get_template_dir,load_template_index,save_template_index,create_template,load_template,load_template_summary,save_template,delete_template,list_templates,list_template_images,add_template_image,delete_template_image,set_primary_template_image,sync_template_index)
from .document_storage import(get_docs_dir,list_documents,save_document,delete_document,rename_document,load_image_status_raw,save_image_status,get_assets_dir,list_assets,save_asset)
