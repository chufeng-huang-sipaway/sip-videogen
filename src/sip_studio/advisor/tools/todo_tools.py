"""To-do list tools for agent execution tracking.
Tools for creating and managing to-do lists during agent runs,
enabling multi-step task tracking with frontend synchronization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agents import function_tool

from sip_studio.advisor.context import RunContext, get_active_context
from sip_studio.config.logging import get_logger
from sip_studio.studio.job_state import (
    InterruptedError,
    JobState,
    TodoItemStatus,
    TodoList,
    is_valid_transition,
)

if TYPE_CHECKING:
    pass
logger = get_logger(__name__)


def _get_ctx_and_state() -> tuple[RunContext | None, JobState | None, str | None]:
    """Get active context and job state. Returns (ctx, job_state, error)."""
    ctx = get_active_context()
    if not ctx:
        return None, None, "No active run context"
    if not ctx.job_state:
        return ctx, None, "No job state available"
    return ctx, ctx.job_state, None


def _check_interrupt(ctx: RunContext) -> None:
    """Check for interrupt and raise if found."""
    action = ctx.check_interrupt()
    if action:
        raise InterruptedError(action, ctx.get_interrupt_message())  # type: ignore[arg-type]


@function_tool
def create_todo_list(title: str, items: list[str]) -> str:
    """Create a new to-do list for tracking multi-step tasks.
    Use this tool when you need to execute multiple steps and want to show
    progress to the user. The to-do list will be displayed in the UI.
    Args:
            title: Title for the to-do list (e.g., "Generate Product Images")
            items: List of task descriptions to execute in order
    Returns:
            Confirmation with the list ID, or error message.
    """
    ctx, job_state, err = _get_ctx_and_state()
    if err or ctx is None or job_state is None:
        return f"Error: {err}"
    _check_interrupt(ctx)
    if not items:
        return "Error: Please provide at least one item"
    todo_list = TodoList.create(ctx.run_id, title)
    for desc in items:
        todo_list.add_item(desc)
    job_state.todo_list = todo_list
    if ctx.push_event:
        ctx.push_event("__onTodoListCreated", todo_list.model_dump(by_alias=True))
    logger.info("Created todo list '%s' with %d items for run %s", title, len(items), ctx.run_id)
    return f"Created to-do list '{title}' with {len(items)} items. List ID: {todo_list.id}"


@function_tool
def start_todo_item(item_id: str) -> str:
    """Mark a to-do item as in-progress.
    Call this before starting work on an item to show progress in the UI.
    Args:
            item_id: ID of the item to start
    Returns:
            Confirmation or error message.
    """
    ctx, job_state, err = _get_ctx_and_state()
    if err or ctx is None or job_state is None:
        return f"Error: {err}"
    _check_interrupt(ctx)
    if not job_state.todo_list:
        return "Error: No to-do list exists"
    item = job_state.todo_list.get_item(item_id)
    if not item:
        return f"Error: Item {item_id} not found"
    if not is_valid_transition(item.status.value, "in_progress"):
        return f"Error: Cannot start item with status '{item.status.value}'"
    item.status = TodoItemStatus.IN_PROGRESS
    from datetime import datetime

    item.updated_at = datetime.utcnow().isoformat() + "Z"
    job_state.todo_list.updated_at = item.updated_at
    if ctx.push_event:
        ctx.push_event(
            "__onTodoItemUpdated", {"runId": ctx.run_id, "itemId": item_id, "status": "in_progress"}
        )
    return f"Started item: {item.description}"


@function_tool
def complete_todo_item(item_id: str, outputs: list[str] | None = None) -> str:
    """Mark a to-do item as completed.
    Call this after successfully completing an item's work.
    Args:
            item_id: ID of the item to complete
            outputs: Optional list of output paths (e.g., generated image paths)
    Returns:
            Confirmation or error message.
    """
    ctx, job_state, err = _get_ctx_and_state()
    if err or ctx is None or job_state is None:
        return f"Error: {err}"
    _check_interrupt(ctx)
    if not job_state.todo_list:
        return "Error: No to-do list exists"
    item = job_state.todo_list.get_item(item_id)
    if not item:
        return f"Error: Item {item_id} not found"
    if not is_valid_transition(item.status.value, "done"):
        return f"Error: Cannot complete item with status '{item.status.value}'"
    item.status = TodoItemStatus.DONE
    if outputs:
        item.outputs = outputs
    from datetime import datetime

    item.updated_at = datetime.utcnow().isoformat() + "Z"
    job_state.todo_list.updated_at = item.updated_at
    if ctx.push_event:
        ctx.push_event(
            "__onTodoItemUpdated",
            {"runId": ctx.run_id, "itemId": item_id, "status": "done", "outputs": outputs},
        )
    return f"Completed item: {item.description}"


@function_tool
def fail_todo_item(item_id: str, error: str) -> str:
    """Mark a to-do item as failed with an error message.
    Call this when an item's work fails and cannot be completed.
    Args:
            item_id: ID of the item that failed
            error: Error message describing what went wrong
    Returns:
            Confirmation or error message.
    """
    ctx, job_state, err = _get_ctx_and_state()
    if err or ctx is None or job_state is None:
        return f"Error: {err}"
    if not job_state.todo_list:
        return "Error: No to-do list exists"
    item = job_state.todo_list.get_item(item_id)
    if not item:
        return f"Error: Item {item_id} not found"
    if not is_valid_transition(item.status.value, "error"):
        return f"Error: Cannot fail item with status '{item.status.value}'"
    item.status = TodoItemStatus.ERROR
    item.error = error
    from datetime import datetime

    item.updated_at = datetime.utcnow().isoformat() + "Z"
    job_state.todo_list.updated_at = item.updated_at
    if ctx.push_event:
        ctx.push_event(
            "__onTodoItemUpdated",
            {"runId": ctx.run_id, "itemId": item_id, "status": "error", "error": error},
        )
    logger.warning("Todo item %s failed: %s", item_id, error)
    return f"Marked item as failed: {item.description}"


@function_tool
def get_next_todo_item() -> str:
    """Get the next pending item to work on.
    Use this to find what to do next in the to-do list.
    Returns:
            Item ID and description, or message if no pending items.
    """
    ctx, job_state, err = _get_ctx_and_state()
    if err or ctx is None or job_state is None:
        return f"Error: {err}"
    _check_interrupt(ctx)
    if not job_state.todo_list:
        return "No to-do list exists"
    item = job_state.todo_list.get_next_pending()
    if not item:
        progress = job_state.todo_list.progress
        return f"All items complete ({progress['done']}/{progress['total']})"
    return f"Next item: {item.id} - {item.description}"


@function_tool
def get_todo_progress() -> str:
    """Get current progress of the to-do list.
    Returns:
            Progress summary with completed/total counts.
    """
    ctx, job_state, err = _get_ctx_and_state()
    if err or ctx is None or job_state is None:
        return f"Error: {err}"
    if not job_state.todo_list:
        return "No to-do list exists"
    progress = job_state.todo_list.progress
    items_summary = []
    for item in job_state.todo_list.items:
        status_icon = {
            "pending": "⏳",
            "in_progress": "🔄",
            "done": "✅",
            "error": "❌",
            "paused": "⏸️",
            "cancelled": "🚫",
            "skipped": "⏭️",
        }.get(item.status.value, "?")
        items_summary.append(f"{status_icon} {item.description}")
    return f"Progress: {progress['done']}/{progress['total']} complete\n" + "\n".join(items_summary)


# Exports for __init__.py
__all__ = [
    "create_todo_list",
    "start_todo_item",
    "complete_todo_item",
    "fail_todo_item",
    "get_next_todo_item",
    "get_todo_progress",
]
