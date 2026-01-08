"""Tests for sip_studio.advisor.tools.todo_tools module."""

from __future__ import annotations

from sip_studio.advisor.tools.todo_tools import (
    _impl_add_todo_output,
    _impl_check_interrupt,
    _impl_complete_todo_list,
    _impl_create_todo_list,
    _impl_update_todo_item,
    clear_tool_context,
    get_tool_state,
    set_tool_context,
)
from sip_studio.studio.state import BridgeState, TodoItem, TodoList


class MockWindow:
    """Mock pywebview window for testing push methods."""

    def __init__(self):
        self.calls: list[str] = []

    def evaluate_js(self, js: str) -> None:
        self.calls.append(js)


# =========================================================================
# Context Var Tests
# =========================================================================
def test_set_and_get_tool_context():
    state = BridgeState()
    set_tool_context(state)
    assert get_tool_state() is state
    clear_tool_context()
    assert get_tool_state() is None


def test_clear_tool_context():
    state = BridgeState()
    set_tool_context(state)
    clear_tool_context()
    assert get_tool_state() is None


def test_get_tool_state_default_none():
    clear_tool_context()
    assert get_tool_state() is None


# =========================================================================
# _impl_create_todo_list Tests
# =========================================================================
def test_create_todo_list_success():
    state = BridgeState()
    state.window = MockWindow()
    set_tool_context(state)
    try:
        result = _impl_create_todo_list(title="Test Task", items=["Item 1", "Item 2", "Item 3"])
        assert "Created todo list 'Test Task'" in result
        assert "3 tasks" in result
        todo = state.get_todo_list()
        assert todo is not None
        assert todo.title == "Test Task"
        assert len(todo.items) == 3
        assert todo.items[0].description == "Item 1"
        assert todo.items[0].status == "pending"
    finally:
        clear_tool_context()


def test_create_todo_list_no_context():
    clear_tool_context()
    result = _impl_create_todo_list(title="Test", items=["Item"])
    assert "Error: State not initialized" in result


def test_create_todo_list_pushes_event():
    state = BridgeState()
    state.window = MockWindow()
    set_tool_context(state)
    try:
        _impl_create_todo_list(title="Push Test", items=["A", "B"])
        assert any("__onTodoList" in c for c in state.window.calls)
    finally:
        clear_tool_context()


# =========================================================================
# _impl_update_todo_item Tests
# =========================================================================
def test_update_todo_item_success():
    state = BridgeState()
    todo = TodoList(id="t1", title="Test", items=[TodoItem(id="t1-0", description="Task 1")])
    state.set_todo_list(todo)
    set_tool_context(state)
    try:
        result = _impl_update_todo_item(item_id="t1-0", status="in_progress")
        assert "status updated to in_progress" in result
        assert state.get_todo_list().items[0].status == "in_progress"
    finally:
        clear_tool_context()


def test_update_todo_item_with_error():
    state = BridgeState()
    todo = TodoList(id="t1", title="Test", items=[TodoItem(id="t1-0", description="Task")])
    state.set_todo_list(todo)
    set_tool_context(state)
    try:
        result = _impl_update_todo_item(item_id="t1-0", status="error", error="Something failed")
        assert "status updated to error" in result
        item = state.get_todo_list().items[0]
        assert item.status == "error"
        assert item.error == "Something failed"
    finally:
        clear_tool_context()


def test_update_todo_item_invalid_status():
    state = BridgeState()
    todo = TodoList(id="t1", title="Test", items=[TodoItem(id="t1-0", description="Task")])
    state.set_todo_list(todo)
    set_tool_context(state)
    try:
        result = _impl_update_todo_item(item_id="t1-0", status="invalid")
        assert "Error: Invalid status" in result
    finally:
        clear_tool_context()


def test_update_todo_item_no_context():
    clear_tool_context()
    result = _impl_update_todo_item(item_id="x", status="done")
    assert "Error: State not initialized" in result


# =========================================================================
# _impl_add_todo_output Tests
# =========================================================================
def test_add_todo_output_success():
    state = BridgeState()
    todo = TodoList(id="t1", title="Test", items=[TodoItem(id="t1-0", description="Generate")])
    state.set_todo_list(todo)
    set_tool_context(state)
    try:
        result = _impl_add_todo_output(
            item_id="t1-0", output_path="/path/to/img.png", output_type="image"
        )
        assert "Added image output" in result
        item = state.get_todo_list().items[0]
        assert len(item.outputs) == 1
        assert item.outputs[0]["path"] == "/path/to/img.png"
        assert item.outputs[0]["type"] == "image"
        # Status should be preserved
        assert item.status == "pending"
    finally:
        clear_tool_context()


def test_add_todo_output_preserves_status():
    state = BridgeState()
    items = [TodoItem(id="t1-0", description="Gen", status="in_progress")]
    todo = TodoList(id="t1", title="Test", items=items)
    state.set_todo_list(todo)
    set_tool_context(state)
    try:
        _impl_add_todo_output(item_id="t1-0", output_path="/img.png", output_type="image")
        assert state.get_todo_list().items[0].status == "in_progress"
    finally:
        clear_tool_context()


def test_add_todo_output_no_todo_list():
    state = BridgeState()
    set_tool_context(state)
    try:
        result = _impl_add_todo_output(item_id="x", output_path="/x.png")
        assert "Error: No active todo list" in result
    finally:
        clear_tool_context()


def test_add_todo_output_item_not_found():
    state = BridgeState()
    todo = TodoList(id="t1", title="Test", items=[TodoItem(id="t1-0", description="Task")])
    state.set_todo_list(todo)
    set_tool_context(state)
    try:
        result = _impl_add_todo_output(item_id="nonexistent", output_path="/x.png")
        assert "Error: Todo item nonexistent not found" in result
    finally:
        clear_tool_context()


# =========================================================================
# _impl_complete_todo_list Tests
# =========================================================================
def test_complete_todo_list_success():
    state = BridgeState()
    state.window = MockWindow()
    items = [
        TodoItem(id="i1", description="A", status="done"),
        TodoItem(id="i2", description="B", status="done"),
    ]
    todo = TodoList(id="t1", title="Test", items=items)
    state.set_todo_list(todo)
    set_tool_context(state)
    try:
        result = _impl_complete_todo_list(summary="All done!")
        assert "2/2 tasks finished" in result
        assert "All done!" in result
        assert state.get_todo_list().completed_at is not None
    finally:
        clear_tool_context()


def test_complete_todo_list_partial():
    state = BridgeState()
    state.window = MockWindow()
    items = [
        TodoItem(id="i1", description="A", status="done"),
        TodoItem(id="i2", description="B", status="pending"),
    ]
    todo = TodoList(id="t1", title="Test", items=items)
    state.set_todo_list(todo)
    set_tool_context(state)
    try:
        result = _impl_complete_todo_list()
        assert "1/2 tasks finished" in result
    finally:
        clear_tool_context()


def test_complete_todo_list_pushes_event():
    state = BridgeState()
    state.window = MockWindow()
    todo = TodoList(id="t1", title="Test", items=[])
    state.set_todo_list(todo)
    state.window.calls.clear()
    set_tool_context(state)
    try:
        _impl_complete_todo_list()
        assert any("__onTodoCompleted" in c for c in state.window.calls)
    finally:
        clear_tool_context()


def test_complete_todo_list_no_list():
    state = BridgeState()
    set_tool_context(state)
    try:
        result = _impl_complete_todo_list()
        assert "No active todo list" in result
    finally:
        clear_tool_context()


# =========================================================================
# _impl_check_interrupt Tests
# =========================================================================
def test_check_interrupt_none():
    state = BridgeState()
    set_tool_context(state)
    try:
        result = _impl_check_interrupt()
        assert result == "none"
    finally:
        clear_tool_context()


def test_check_interrupt_pause():
    state = BridgeState()
    state.set_interrupt("pause")
    set_tool_context(state)
    try:
        result = _impl_check_interrupt()
        assert result == "pause"
    finally:
        clear_tool_context()


def test_check_interrupt_stop():
    state = BridgeState()
    state.set_interrupt("stop")
    set_tool_context(state)
    try:
        result = _impl_check_interrupt()
        assert result == "stop"
    finally:
        clear_tool_context()


def test_check_interrupt_new_direction():
    state = BridgeState()
    state.set_interrupt("new_direction", "Do something else")
    set_tool_context(state)
    try:
        result = _impl_check_interrupt()
        assert result == "new_direction"
    finally:
        clear_tool_context()


def test_check_interrupt_no_context():
    clear_tool_context()
    result = _impl_check_interrupt()
    assert result == "none"
