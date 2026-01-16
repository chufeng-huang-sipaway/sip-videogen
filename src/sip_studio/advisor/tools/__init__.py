"""Universal tools for Brand Marketing Advisor.
Core tools available to the advisor agent:
1. generate_image - Create images via Gemini 3.0 Pro
2. read_file - Read files from brand directory
3. write_file - Write files to brand directory
4. list_files - List files in brand directory
5. load_brand - Load brand identity and context
6. propose_choices - Present choices to user
7. propose_images - Present images for selection
8. update_memory - Store user preferences
Product and Project exploration tools:
9. list_products - List all products for the active brand
10. list_projects - List all projects/campaigns for the active brand
11. get_product_detail - Get detailed product information
12. get_project_detail - Get detailed project information
Tool functions are defined as pure functions (prefixed with _impl_) for testing,
then wrapped with @function_tool for agent use.
"""

__all__ = [
    # session
    "get_active_aspect_ratio",
    "set_active_aspect_ratio",
    # metadata
    "ImageGenerationMetadata",
    "store_image_metadata",
    "get_image_metadata",
    "load_image_metadata",
    "store_video_metadata",
    "get_video_metadata",
    "load_video_metadata",
    # image_tools
    "generate_image",
    "propose_images",
    "get_recent_generated_images",
    "wait_for_batch_images",
    "_generate_output_filename",
    "_impl_generate_image",
    "_impl_wait_for_batch_images",
    # video_tools
    "generate_video_clip",
    "_impl_generate_video_clip",
    # file_tools
    "read_file",
    "write_file",
    "list_files",
    "_impl_list_files",
    "_impl_read_file",
    "_impl_write_file",
    "_resolve_brand_path",
    # product_tools
    "create_product",
    "add_product_image",
    "update_product",
    "delete_product",
    "set_product_primary_image",
    "analyze_product_packaging",
    "analyze_all_product_packaging",
    "update_product_packaging_text",
    "AttributeInput",
    "PackagingTextElementInput",
    "MAX_PRODUCT_IMAGE_SIZE_BYTES",
    "_impl_add_product_image",
    "_impl_analyze_all_product_packaging",
    "_impl_analyze_product_packaging",
    "_impl_create_product",
    "_impl_delete_product",
    "_impl_set_product_primary_image",
    "_impl_update_product",
    "_impl_update_product_packaging_text",
    "_validate_slug",
    # style_reference_tools
    "list_style_references",
    "get_style_reference_detail",
    "create_style_reference",
    "create_style_references_from_images",
    "update_style_reference",
    "add_style_reference_image",
    "reanalyze_style_reference",
    "delete_style_reference",
    # brand_tools
    "load_brand",
    "fetch_brand_detail",
    "browse_brand_assets",
    "list_products",
    "list_projects",
    "get_product_detail",
    "get_project_detail",
    "_impl_browse_brand_assets",
    "_impl_fetch_brand_detail",
    "_impl_get_product_detail",
    "_impl_get_project_detail",
    "_impl_list_products",
    "_impl_list_projects",
    "_impl_load_brand",
    # memory_tools
    "update_memory",
    "propose_choices",
    "get_pending_memory_update",
    "get_pending_interaction",
    "set_tool_progress_callback",
    "emit_tool_thinking",
    # todo_tools
    "create_todo_list",
    "update_todo_item",
    "add_todo_output",
    "complete_todo_list",
    "check_interrupt",
    "set_tool_context",
    "get_tool_state",
    "clear_tool_context",
    "set_current_batch_id",
    "get_current_batch_id",
    "batch_context",
    "set_async_mode",
    "get_async_mode",
    "_impl_create_todo_list",
    "_impl_update_todo_item",
    "_impl_add_todo_output",
    "_impl_complete_todo_list",
    "_impl_check_interrupt",
    # task_tools (file-based)
    "create_task_file",
    "get_remaining_tasks",
    "update_task",
    "complete_task_file",
    "_impl_create_task_file",
    "_impl_get_remaining_tasks",
    "_impl_update_task",
    "_impl_complete_task_file",
    "_impl_archive_existing_tasks",
    "_get_tasks_path",
    "_parse_tasks_file",
    "_build_tasks_file",
    # utility_tools
    "fetch_url_content",
    "report_thinking",
    "parse_thinking_step_result",
    "_MAX_DETAIL_LEN",
    "_MAX_STEP_LEN",
    "_impl_report_thinking",
    # context_tools
    "fetch_context_cached",
    "get_cached_product_context",
    "get_cached_style_reference_context",
    "set_context_cache",
    "get_context_cache",
    "_impl_fetch_context_cached",
    "_impl_get_cached_product_context",
    "_impl_get_cached_style_reference_context",
    # skill_tools (progressive disclosure)
    "activate_skill",
    "mark_brief_complete",
    "get_workflow_state",
    "reset_workflow_state",
    "check_image_workflow_compliance",
    "mark_skill_activated",
    "mark_composition_brief_produced",
    "_impl_activate_skill",
    # aggregate
    "ADVISOR_TOOLS",
    # Re-exports for test patching compatibility
    "datetime",
    "get_active_brand",
    "get_active_project",
    "get_brand_dir",
    "get_brands_dir",
    "get_settings",
    "load_product",
    "storage_add_product_image",
    "storage_create_product",
    "storage_delete_product",
    "storage_list_products",
    "storage_list_projects",
    "storage_load_brand",
    "storage_save_product",
    "storage_set_primary_product_image",
]
# Re-export from submodules + dependencies for test patching
from datetime import datetime

from sip_studio.brands.storage import (
    add_product_image as storage_add_product_image,
)
from sip_studio.brands.storage import (
    create_product as storage_create_product,
)
from sip_studio.brands.storage import (
    delete_product as storage_delete_product,
)
from sip_studio.brands.storage import (
    get_active_brand,
    get_active_project,
    get_brand_dir,
    get_brands_dir,
    load_product,
)
from sip_studio.brands.storage import (
    list_products as storage_list_products,
)
from sip_studio.brands.storage import (
    list_projects as storage_list_projects,
)
from sip_studio.brands.storage import (
    load_brand as storage_load_brand,
)
from sip_studio.brands.storage import (
    save_product as storage_save_product,
)
from sip_studio.brands.storage import (
    set_primary_product_image as storage_set_primary_product_image,
)
from sip_studio.config.settings import get_settings

from .brand_tools import (
    _impl_browse_brand_assets,
    _impl_fetch_brand_detail,
    _impl_get_product_detail,
    _impl_get_project_detail,
    _impl_list_products,
    _impl_list_projects,
    _impl_load_brand,
    browse_brand_assets,
    fetch_brand_detail,
    get_product_detail,
    get_project_detail,
    list_products,
    list_projects,
    load_brand,
)
from .context_tools import (
    _impl_fetch_context_cached,
    _impl_get_cached_product_context,
    _impl_get_cached_style_reference_context,
    fetch_context_cached,
    get_cached_product_context,
    get_cached_style_reference_context,
    get_context_cache,
    set_context_cache,
)

# Export _impl_ functions for testing
from .file_tools import (
    _impl_list_files,
    _impl_read_file,
    _impl_write_file,
    _resolve_brand_path,
    list_files,
    read_file,
    write_file,
)
from .image_tools import (
    _generate_output_filename,
    _impl_generate_image,
    _impl_wait_for_batch_images,
    generate_image,
    get_recent_generated_images,
    propose_images,
    wait_for_batch_images,
)
from .memory_tools import (
    emit_tool_thinking,
    get_pending_interaction,
    get_pending_memory_update,
    propose_choices,
    set_tool_progress_callback,
    update_memory,
)
from .metadata import (
    ImageGenerationMetadata,
    get_image_metadata,
    get_video_metadata,
    load_image_metadata,
    load_video_metadata,
    store_image_metadata,
    store_video_metadata,
)
from .product_tools import (
    MAX_PRODUCT_IMAGE_SIZE_BYTES,
    AttributeInput,
    PackagingTextElementInput,
    _impl_add_product_image,
    _impl_analyze_all_product_packaging,
    _impl_analyze_product_packaging,
    _impl_create_product,
    _impl_delete_product,
    _impl_set_product_primary_image,
    _impl_update_product,
    _impl_update_product_packaging_text,
    _validate_slug,
    add_product_image,
    analyze_all_product_packaging,
    analyze_product_packaging,
    create_product,
    delete_product,
    set_product_primary_image,
    update_product,
    update_product_packaging_text,
)
from .session import get_active_aspect_ratio, set_active_aspect_ratio
from .skill_tools import (
    _impl_activate_skill,
    activate_skill,
    check_image_workflow_compliance,
    get_workflow_state,
    mark_brief_complete,
    mark_composition_brief_produced,
    mark_skill_activated,
    reset_workflow_state,
)
from .style_reference_tools import (
    add_style_reference_image,
    create_style_reference,
    create_style_references_from_images,
    delete_style_reference,
    get_style_reference_detail,
    list_style_references,
    reanalyze_style_reference,
    update_style_reference,
)
from .task_tools import (
    _build_tasks_file,
    _get_tasks_path,
    _impl_archive_existing_tasks,
    _impl_complete_task_file,
    _impl_create_task_file,
    _impl_get_remaining_tasks,
    _impl_update_task,
    _parse_tasks_file,
    complete_task_file,
    create_task_file,
    get_remaining_tasks,
    update_task,
)
from .todo_tools import (
    _impl_add_todo_output,
    _impl_check_interrupt,
    _impl_complete_todo_list,
    _impl_create_todo_list,
    _impl_update_todo_item,
    add_todo_output,
    batch_context,
    check_interrupt,
    clear_tool_context,
    complete_todo_list,
    create_todo_list,
    get_async_mode,
    get_current_batch_id,
    get_tool_state,
    set_async_mode,
    set_current_batch_id,
    set_tool_context,
    update_todo_item,
)
from .utility_tools import (
    _MAX_DETAIL_LEN,
    _MAX_STEP_LEN,
    _impl_report_thinking,
    fetch_url_content,
    parse_thinking_step_result,
    report_thinking,
)
from .video_tools import _impl_generate_video_clip, generate_video_clip

# List of all tools for the advisor agent
ADVISOR_TOOLS = [
    generate_image,
    generate_video_clip,
    get_recent_generated_images,
    read_file,
    write_file,
    list_files,
    load_brand,
    propose_choices,
    propose_images,
    update_memory,
    list_products,
    list_projects,
    get_product_detail,
    get_project_detail,
    create_product,
    update_product,
    delete_product,
    add_product_image,
    set_product_primary_image,
    list_style_references,
    get_style_reference_detail,
    create_style_reference,
    create_style_references_from_images,
    update_style_reference,
    add_style_reference_image,
    reanalyze_style_reference,
    delete_style_reference,
    analyze_product_packaging,
    analyze_all_product_packaging,
    update_product_packaging_text,
    fetch_brand_detail,
    browse_brand_assets,
    fetch_url_content,
    report_thinking,
    # todo tools
    create_todo_list,
    update_todo_item,
    add_todo_output,
    complete_todo_list,
    check_interrupt,
    # task tools (file-based persistence)
    create_task_file,
    get_remaining_tasks,
    update_task,
    complete_task_file,
    # context tools (lean context pattern)
    fetch_context_cached,
    get_cached_product_context,
    get_cached_style_reference_context,
    # skill tools (progressive disclosure)
    activate_skill,
    mark_brief_complete,
]
