"""Tool registry for dynamic tool loading based on activated skills.
Implements Stage 2 of TOOL_REFACTOR_PLAN.md.
Core tools (always available) + skill-specific tools (loaded on demand).
Target: 8-12 tools active per turn instead of 37+.
"""

from __future__ import annotations

import importlib
from typing import Any

from sip_studio.config.logging import get_logger

logger = get_logger(__name__)
# Core tools - always available (7 tools)
# report_thinking is MANDATORY per advisor.md - agent must always show reasoning
# update_memory is needed for preference persistence across sessions
CORE_TOOLS = [
    "load_brand",
    "propose_choices",
    "activate_skill",
    "list_products",
    "check_interrupt",
    "report_thinking",
    "update_memory",
]
# Skill-to-tool mapping (skill name -> list of tool names)
# Skills with empty lists are instruction-only (guidelines, no extra tools)
SKILL_TOOL_MAPPING: dict[str, list[str]] = {
    "image-composer": ["generate_image", "propose_images", "get_recent_generated_images"],
    "image-prompt-engineering": [],  # Instructions only
    "video-prompt-engineering": [],  # Instructions only
    "brand-evolution": [
        "read_file",
        "write_file",
        "list_files",
    ],  # Needs file access to update identity
    "product-management": [
        "manage_product",
        "analyze_packaging",
        "update_packaging_text",
        "get_product_detail",
    ],
    "style-references": ["manage_style_reference", "get_style_reference"],
    "research": [
        "web_search",
        "request_deep_research",
        "get_research_status",
        "search_research_cache",
    ],
    "brand-identity": [
        "fetch_brand_detail",
        "browse_brand_assets",
        "read_file",
        "write_file",
        "list_files",
    ],
    "file-operations": ["read_file", "write_file", "list_files"],
    "project-management": ["list_projects", "get_project_detail"],
    "video-generation": ["generate_video_clip"],
}
# Tool name -> (module_path, attribute_name) for lazy import
TOOL_MODULES: dict[str, tuple[str, str]] = {
    # Core tools
    "load_brand": ("sip_studio.advisor.tools.brand_tools", "load_brand"),
    "propose_choices": ("sip_studio.advisor.tools.memory_tools", "propose_choices"),
    "activate_skill": ("sip_studio.advisor.tools.skill_tools", "activate_skill"),
    "list_products": ("sip_studio.advisor.tools.brand_tools", "list_products"),
    "check_interrupt": ("sip_studio.advisor.tools.todo_tools", "check_interrupt"),
    # Image tools
    "generate_image": ("sip_studio.advisor.tools.image_tools", "generate_image"),
    "propose_images": ("sip_studio.advisor.tools.image_tools", "propose_images"),
    "get_recent_generated_images": (
        "sip_studio.advisor.tools.image_tools",
        "get_recent_generated_images",
    ),
    # Product tools
    "manage_product": ("sip_studio.advisor.tools.product_tools", "manage_product"),
    "analyze_packaging": ("sip_studio.advisor.tools.product_tools", "analyze_packaging"),
    "update_packaging_text": ("sip_studio.advisor.tools.product_tools", "update_packaging_text"),
    "get_product_detail": ("sip_studio.advisor.tools.brand_tools", "get_product_detail"),
    # Style reference tools
    "manage_style_reference": (
        "sip_studio.advisor.tools.style_reference_tools",
        "manage_style_reference",
    ),
    "get_style_reference": (
        "sip_studio.advisor.tools.style_reference_tools",
        "get_style_reference",
    ),
    # Research tools
    "web_search": ("sip_studio.advisor.tools.research_tools", "web_search"),
    "request_deep_research": ("sip_studio.advisor.tools.research_tools", "request_deep_research"),
    "get_research_status": ("sip_studio.advisor.tools.research_tools", "get_research_status"),
    "search_research_cache": ("sip_studio.advisor.tools.research_tools", "search_research_cache"),
    # Brand tools
    "fetch_brand_detail": ("sip_studio.advisor.tools.brand_tools", "fetch_brand_detail"),
    "browse_brand_assets": ("sip_studio.advisor.tools.brand_tools", "browse_brand_assets"),
    # File tools
    "read_file": ("sip_studio.advisor.tools.file_tools", "read_file"),
    "write_file": ("sip_studio.advisor.tools.file_tools", "write_file"),
    "list_files": ("sip_studio.advisor.tools.file_tools", "list_files"),
    # Project tools
    "list_projects": ("sip_studio.advisor.tools.brand_tools", "list_projects"),
    "get_project_detail": ("sip_studio.advisor.tools.brand_tools", "get_project_detail"),
    # Video tools
    "generate_video_clip": ("sip_studio.advisor.tools.video_tools", "generate_video_clip"),
    # Utility tools
    "fetch_url_content": ("sip_studio.advisor.tools.utility_tools", "fetch_url_content"),
    "report_thinking": ("sip_studio.advisor.tools.utility_tools", "report_thinking"),
    "update_memory": ("sip_studio.advisor.tools.memory_tools", "update_memory"),
    # Todo/task tools
    "create_todo_list": ("sip_studio.advisor.tools.todo_tools", "create_todo_list"),
    "update_todo_item": ("sip_studio.advisor.tools.todo_tools", "update_todo_item"),
    "add_todo_output": ("sip_studio.advisor.tools.todo_tools", "add_todo_output"),
    "complete_todo_list": ("sip_studio.advisor.tools.todo_tools", "complete_todo_list"),
    "create_task_file": ("sip_studio.advisor.tools.task_tools", "create_task_file"),
    "get_remaining_tasks": ("sip_studio.advisor.tools.task_tools", "get_remaining_tasks"),
    "update_task": ("sip_studio.advisor.tools.task_tools", "update_task"),
    "complete_task_file": ("sip_studio.advisor.tools.task_tools", "complete_task_file"),
    # Context tools
    "fetch_context_cached": ("sip_studio.advisor.tools.context_tools", "fetch_context_cached"),
    "get_cached_product_context": (
        "sip_studio.advisor.tools.context_tools",
        "get_cached_product_context",
    ),
    "get_cached_style_reference_context": (
        "sip_studio.advisor.tools.context_tools",
        "get_cached_style_reference_context",
    ),
    # Skill tools
    "mark_brief_complete": ("sip_studio.advisor.tools.skill_tools", "mark_brief_complete"),
}
# Cache for resolved tools to avoid repeated imports
_tool_cache: dict[str, Any] = {}


def _resolve_tool(name: str) -> Any:
    """Lazy import tool by name using importlib.
    Handles missing tools gracefully with clear error.
    Args:
        name: Tool name to resolve.
    Returns:
        The tool function/object.
    Raises:
        ValueError: If tool name is unknown.
        RuntimeError: If tool import fails.
    """
    if name in _tool_cache:
        return _tool_cache[name]
    if name not in TOOL_MODULES:
        raise ValueError(f"Unknown tool '{name}'. Add to TOOL_MODULES in registry.py")
    try:
        module_path, attr_name = TOOL_MODULES[name]
        module = importlib.import_module(module_path)
        tool = getattr(module, attr_name)
        _tool_cache[name] = tool
        return tool
    except (ImportError, AttributeError) as e:
        raise RuntimeError(f"Failed to load tool '{name}': {e}") from e


def get_tools_for_skills(activated_skills: list[str], max_skills: int = 3) -> list[Any]:
    """Get tool list based on activated skills.
    Uses order-preserving dedupe for deterministic tool ordering.
    Args:
        activated_skills: List of activated skill names.
        max_skills: Maximum skills to include (default 3).
    Returns:
        List of resolved tool functions.
    """
    tool_names = list(CORE_TOOLS)
    for skill in activated_skills[:max_skills]:
        if skill in SKILL_TOOL_MAPPING:
            tool_names.extend(SKILL_TOOL_MAPPING[skill])
    # Order-preserving dedupe
    seen = set()
    unique_names = []
    for name in tool_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)
    tools = []
    for name in unique_names:
        try:
            tools.append(_resolve_tool(name))
        except (ValueError, RuntimeError) as e:
            logger.error(f"[TOOL_REGISTRY] Failed to load tool '{name}': {e}")
    logger.info(
        f"[TOOL_REGISTRY] Loaded {len(tools)} tools for skills: {activated_skills[:max_skills]}"
    )
    return tools


def get_all_skill_names() -> list[str]:
    """Get list of all available skill names."""
    return list(SKILL_TOOL_MAPPING.keys())


def get_skill_tool_count(skill_name: str) -> int:
    """Get number of tools a skill provides."""
    return len(SKILL_TOOL_MAPPING.get(skill_name, []))
