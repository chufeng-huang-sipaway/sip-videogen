"""Todo list management tools for multi-step task execution.
Uses contextvars for thread-safe per-session state access.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from agents import function_tool

from sip_studio.config.logging import get_logger

if TYPE_CHECKING:
    from sip_studio.studio.state import BridgeState
logger = get_logger(__name__)
# Thread-safe per-session state using contextvars (NOT module globals)
_tool_state: ContextVar["BridgeState|None"] = ContextVar("todo_tool_state", default=None)
# Batch ID for image generation pool (async-safe via contextvars)
_batch_id_var: ContextVar[str | None] = ContextVar("batch_id", default=None)


def set_current_batch_id(batch_id: str | None) -> None:
    """Set batch ID for current context (used by image pool)."""
    _batch_id_var.set(batch_id)


def get_current_batch_id() -> str | None:
    """Get batch ID for current context."""
    return _batch_id_var.get()


@contextmanager
def batch_context(batch_id: str):
    """Context manager for batch ID scope."""
    token = _batch_id_var.set(batch_id)
    try:
        yield
    finally:
        _batch_id_var.reset(token)


def set_tool_context(state: "BridgeState") -> None:
    """Set state context for current async task. Called by ChatService before agent run."""
    _tool_state.set(state)


def get_tool_state() -> "BridgeState|None":
    """Get state for current context."""
    return _tool_state.get()


def clear_tool_context() -> None:
    """Clear tool context. Called after agent run completes."""
    _tool_state.set(None)


# =========================================================================
# Implementation functions (for testing)
# =========================================================================
def _impl_create_todo_list(title: str, items: list[str]) -> str:
    """Implementation of create_todo_list for testing."""
    from sip_studio.studio.state import TodoItem, TodoList

    state = get_tool_state()
    if not state:
        return "Error: State not initialized - context var not set"
    tid = str(uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    todo_items = [TodoItem(id=f"{tid}-{i}", description=desc) for i, desc in enumerate(items)]
    todo = TodoList(id=tid, title=title, items=todo_items, created_at=now)
    state.set_todo_list(todo)
    logger.info(f"Created todo list '{title}' with {len(items)} items")
    return f"Created todo list '{title}' with {len(items)} tasks. ID: {tid}"


def _impl_update_todo_item(item_id: str, status: str, error: str | None = None) -> str:
    """Implementation of update_todo_item for testing."""
    state = get_tool_state()
    if not state:
        return "Error: State not initialized"
    valid = {"pending", "in_progress", "done", "error", "paused"}
    if status not in valid:
        return f"Error: Invalid status '{status}'. Must be one of: {valid}"
    state.update_todo_item(item_id, status, error=error)
    logger.info(f"Updated todo item {item_id} to {status}")
    return f"Todo item {item_id} status updated to {status}"


def _impl_add_todo_output(item_id: str, output_path: str, output_type: str = "image") -> str:
    """Implementation of add_todo_output for testing."""
    state = get_tool_state()
    if not state:
        return "Error: State not initialized"
    todo = state.get_todo_list()
    if not todo:
        return "Error: No active todo list"
    item = next((i for i in todo.items if i.id == item_id), None)
    if not item:
        return f"Error: Todo item {item_id} not found"
    output = {"path": output_path, "type": output_type}
    state.update_todo_item(item_id, item.status, outputs=[output])
    return f"Added {output_type} output to todo item {item_id}"


def _impl_complete_todo_list(summary: str | None = None) -> str:
    """Implementation of complete_todo_list for testing."""
    state = get_tool_state()
    if not state:
        return "Error: State not initialized"
    todo = state.get_todo_list()
    if not todo:
        return "No active todo list"
    with state._lock:
        todo.completed_at = datetime.now(timezone.utc).isoformat()
    done_count = sum(1 for i in todo.items if i.status == "done")
    total = len(todo.items)
    state._push_todo_completed(todo)
    result = f"Todo list complete: {done_count}/{total} tasks finished."
    if summary:
        result += f" {summary}"
    return result


def _impl_check_interrupt() -> str:
    """Implementation of check_interrupt for testing."""
    state = get_tool_state()
    if not state:
        return "none"
    signal = state.get_interrupt()
    return signal if signal else "none"


# =========================================================================
# Agent tools (decorated with @function_tool)
# =========================================================================
@function_tool
def create_todo_list(title: str, items: list[str]) -> str:
    """Create a todo list for tracking multi-step tasks.
    Use this when the user requests a complex task that requires multiple steps,
    such as "generate 10 campaign ideas with images for each".
    Args:
        title: Brief description of the overall task
        items: List of task descriptions (each will become a todo item)
    Returns:
        Confirmation message with todo list ID
    """
    return _impl_create_todo_list(title, items)


@function_tool
def update_todo_item(item_id: str, status: str, error: str | None = None) -> str:
    """Update the status of a todo item.
    Call this before starting work on an item (status='in_progress')
    and after completing it (status='done') or if it fails (status='error').
    Args:
        item_id: The todo item ID to update
        status: New status - 'pending', 'in_progress', 'done', 'error', 'paused'
        error: Error message if status is 'error'
    Returns:
        Confirmation message
    """
    return _impl_update_todo_item(item_id, status, error)


@function_tool
def add_todo_output(item_id: str, output_path: str, output_type: str = "image") -> str:
    """Add a generated output (image/video) to a todo item without changing status.
    Call this after successfully generating content for a todo item.
    The status should be updated separately via update_todo_item.
    Args:
        item_id: The todo item ID
        output_path: Path to the generated file
        output_type: Type of output - 'image' or 'video'
    Returns:
        Confirmation message
    """
    return _impl_add_todo_output(item_id, output_path, output_type)


@function_tool
def complete_todo_list(summary: str | None = None) -> str:
    """Mark the todo list as complete and push completion event.
    Call this when all items are done or when stopping early.
    Args:
        summary: Optional summary of what was accomplished
    Returns:
        Completion message
    """
    return _impl_complete_todo_list(summary)


@function_tool
def check_interrupt() -> str:
    """Check if user has requested an interrupt (pause/stop/new_direction).
    Call this periodically during long-running operations or between todo items.
    Returns:
        "none" if no interrupt, or the interrupt type ("pause", "stop", "new_direction")
    """
    return _impl_check_interrupt()
