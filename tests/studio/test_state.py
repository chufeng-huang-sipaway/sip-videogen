"""Tests for sip_studio.studio.state module."""

from __future__ import annotations

import threading
import time

from sip_studio.studio.state import ApprovalRequest, BridgeState, TodoItem, TodoList


class MockWindow:
    """Mock pywebview window for testing push methods."""

    def __init__(self):
        self.calls: list[str] = []

    def evaluate_js(self, js: str) -> None:
        self.calls.append(js)


# =========================================================================
# TodoItem and TodoList Model Tests
# =========================================================================
def test_todo_item_to_dict_basic():
    item = TodoItem(id="t1", description="Test task")
    d = item.to_dict()
    assert d["id"] == "t1"
    assert d["description"] == "Test task"
    assert d["status"] == "pending"
    assert "outputs" not in d
    assert "error" not in d


def test_todo_item_to_dict_with_outputs_and_error():
    item = TodoItem(
        id="t2",
        description="Task",
        status="error",
        outputs=[{"path": "/img.png", "type": "image"}],
        error="Failed",
    )
    d = item.to_dict()
    assert d["outputs"] == [{"path": "/img.png", "type": "image"}]
    assert d["error"] == "Failed"


def test_todo_list_to_dict_basic():
    items = [TodoItem(id="i1", description="First"), TodoItem(id="i2", description="Second")]
    todo = TodoList(id="list1", title="Test List", items=items, created_at="2024-01-01T00:00:00Z")
    d = todo.to_dict()
    assert d["id"] == "list1"
    assert d["title"] == "Test List"
    assert d["createdAt"] == "2024-01-01T00:00:00Z"
    assert len(d["items"]) == 2
    assert "completedAt" not in d
    assert "interruptedAt" not in d


def test_todo_list_to_dict_completed():
    todo = TodoList(
        id="l1",
        title="Done",
        items=[],
        created_at="2024-01-01T00:00:00Z",
        completed_at="2024-01-01T01:00:00Z",
    )
    d = todo.to_dict()
    assert d["completedAt"] == "2024-01-01T01:00:00Z"


def test_todo_list_to_dict_interrupted():
    todo = TodoList(
        id="l2",
        title="Stopped",
        items=[],
        created_at="2024-01-01T00:00:00Z",
        interrupted_at="2024-01-01T00:30:00Z",
        interrupt_reason="stop",
    )
    d = todo.to_dict()
    assert d["interruptedAt"] == "2024-01-01T00:30:00Z"
    assert d["interruptReason"] == "stop"


# =========================================================================
# BridgeState TodoList Management Tests
# =========================================================================
def test_set_and_get_todo_list():
    state = BridgeState()
    todo = TodoList(id="t1", title="Test", items=[TodoItem(id="i1", description="Task")])
    state.set_todo_list(todo)
    assert state.get_todo_list() is todo


def test_clear_todo_list():
    state = BridgeState()
    state.set_todo_list(TodoList(id="t1", title="Test"))
    assert state.get_todo_list() is not None
    state.clear_todo_list()
    assert state.get_todo_list() is None


def test_clear_todo_list_pushes_event():
    state = BridgeState()
    state.window = MockWindow()
    state.set_todo_list(TodoList(id="t1", title="Test"))
    state.window.calls.clear()
    state.clear_todo_list()
    assert any("__onTodoCleared" in c for c in state.window.calls)


def test_update_todo_item():
    state = BridgeState()
    items = [TodoItem(id="i1", description="Task1"), TodoItem(id="i2", description="Task2")]
    state.set_todo_list(TodoList(id="t1", title="Test", items=items))
    state.update_todo_item("i1", "in_progress")
    todo = state.get_todo_list()
    assert todo.items[0].status == "in_progress"
    assert todo.items[1].status == "pending"


def test_update_todo_item_with_outputs():
    state = BridgeState()
    items = [TodoItem(id="i1", description="Generate image")]
    state.set_todo_list(TodoList(id="t1", title="Test", items=items))
    state.update_todo_item("i1", "done", outputs=[{"path": "/img.png", "type": "image"}])
    todo = state.get_todo_list()
    assert todo.items[0].status == "done"
    assert len(todo.items[0].outputs) == 1


def test_update_todo_item_with_error():
    state = BridgeState()
    items = [TodoItem(id="i1", description="Task")]
    state.set_todo_list(TodoList(id="t1", title="Test", items=items))
    state.update_todo_item("i1", "error", error="Something failed")
    todo = state.get_todo_list()
    assert todo.items[0].status == "error"
    assert todo.items[0].error == "Something failed"


# =========================================================================
# Push Method Tests
# =========================================================================
def test_push_todo_list():
    state = BridgeState()
    state.window = MockWindow()
    todo = TodoList(id="t1", title="Test", items=[])
    state.set_todo_list(todo)
    assert any("__onTodoList" in c for c in state.window.calls)


def test_push_todo_update():
    state = BridgeState()
    state.window = MockWindow()
    state.set_todo_list(
        TodoList(id="t1", title="Test", items=[TodoItem(id="i1", description="Task")])
    )
    state.window.calls.clear()
    state.update_todo_item("i1", "done")
    assert any("__onTodoUpdate" in c for c in state.window.calls)


def test_push_todo_completed():
    state = BridgeState()
    state.window = MockWindow()
    todo = TodoList(id="t1", title="Test", items=[], completed_at="2024-01-01T00:00:00Z")
    state._push_todo_completed(todo)
    assert any("__onTodoCompleted" in c for c in state.window.calls)
    assert any('"completedAt"' in c for c in state.window.calls)


# =========================================================================
# Autonomy and Approval Tests
# =========================================================================
def test_autonomy_mode():
    state = BridgeState()
    assert not state.is_autonomy_mode()
    state.set_autonomy_mode(True)
    assert state.is_autonomy_mode()
    state.set_autonomy_mode(False)
    assert not state.is_autonomy_mode()


def test_approval_request_to_dict():
    req = ApprovalRequest(
        id="a1", action_type="generate_image", description="Test prompt", prompt="Generate a cat"
    )
    d = req.to_dict()
    assert d["id"] == "a1"
    assert d["actionType"] == "generate_image"
    assert d["description"] == "Test prompt"
    assert d["prompt"] == "Generate a cat"


def test_wait_for_approval_approve():
    state = BridgeState()
    state.APPROVAL_TIMEOUT_SEC = 1.0
    req = ApprovalRequest(id="a1", action_type="generate_image", description="Test")

    def responder():
        time.sleep(0.1)
        state.respond_approval("approve")

    t = threading.Thread(target=responder)
    t.start()
    result = state.wait_for_approval(req)
    t.join()
    assert result["action"] == "approve"
    assert state.get_pending_approval() is None


def test_wait_for_approval_modify():
    state = BridgeState()
    state.APPROVAL_TIMEOUT_SEC = 1.0
    req = ApprovalRequest(id="a1", action_type="generate_image", description="Test")

    def responder():
        time.sleep(0.1)
        state.respond_approval("modify", "New prompt")

    t = threading.Thread(target=responder)
    t.start()
    result = state.wait_for_approval(req)
    t.join()
    assert result["action"] == "modify"
    assert result["modified_prompt"] == "New prompt"


def test_wait_for_approval_timeout():
    state = BridgeState()
    state.APPROVAL_TIMEOUT_SEC = 0.1
    req = ApprovalRequest(id="a1", action_type="generate_image", description="Test")
    result = state.wait_for_approval(req)
    assert result["action"] == "timeout"


def test_wait_for_approval_approve_all_enables_autonomy():
    state = BridgeState()
    state.APPROVAL_TIMEOUT_SEC = 1.0
    req = ApprovalRequest(id="a1", action_type="generate_image", description="Test")
    assert not state.is_autonomy_mode()

    def responder():
        time.sleep(0.1)
        state.respond_approval("approve_all")

    t = threading.Thread(target=responder)
    t.start()
    result = state.wait_for_approval(req)
    t.join()
    assert result["action"] == "approve_all"
    assert state.is_autonomy_mode()


def test_push_approval_request():
    state = BridgeState()
    state.window = MockWindow()
    req = ApprovalRequest(id="a1", action_type="generate_image", description="Test")
    state._push_approval_request(req)
    assert any("__onApprovalRequest" in c for c in state.window.calls)


def test_push_approval_cleared():
    state = BridgeState()
    state.window = MockWindow()
    state._push_approval_cleared()
    assert any("__onApprovalCleared" in c for c in state.window.calls)


# =========================================================================
# Interruption Tests
# =========================================================================
def test_interrupt_set_and_get():
    state = BridgeState()
    assert state.get_interrupt() is None
    assert not state.is_interrupted()
    state.set_interrupt("pause")
    assert state.get_interrupt() == "pause"
    assert state.is_interrupted()


def test_interrupt_new_direction():
    state = BridgeState()
    state.set_interrupt("new_direction", "Do something else")
    assert state.get_interrupt() == "new_direction"
    assert state.get_new_direction_message() == "Do something else"


def test_clear_interrupt():
    state = BridgeState()
    state.set_interrupt("stop")
    assert state.is_interrupted()
    state.clear_interrupt()
    assert not state.is_interrupted()
    assert state.get_interrupt() is None


# =========================================================================
# Interruption Push and Control Tests (Stage 4)
# =========================================================================
def test_push_interrupt_status():
    state = BridgeState()
    state.window = MockWindow()
    state._push_interrupt_status("pause")
    assert any("__onInterruptStatus" in c for c in state.window.calls)
    assert any('"signal": "pause"' in c for c in state.window.calls)


def test_push_interrupt_status_none():
    state = BridgeState()
    state.window = MockWindow()
    state._push_interrupt_status(None)
    assert any("__onInterruptStatus" in c for c in state.window.calls)
    assert any('"signal": null' in c for c in state.window.calls)


def test_set_interrupt_with_push():
    state = BridgeState()
    state.window = MockWindow()
    state.set_interrupt_with_push("pause")
    assert state.get_interrupt() == "pause"
    assert any("__onInterruptStatus" in c for c in state.window.calls)


def test_set_interrupt_with_push_stop_skips_pending_approval():
    state = BridgeState()
    state.window = MockWindow()
    state.APPROVAL_TIMEOUT_SEC = 0.1
    # Set up a pending approval
    req = ApprovalRequest(id="a1", action_type="generate_image", description="Test")
    state.set_pending_approval(req)
    assert state.get_pending_approval() is not None
    # Stop should auto-skip the pending approval by setting event
    state.set_interrupt_with_push("stop")
    # The approval_event should be set
    assert state._approval_event.is_set()


def test_set_interrupt_with_push_new_direction_marks_todo_interrupted():
    state = BridgeState()
    state.window = MockWindow()
    # Set up an active todo list
    todo = TodoList(id="t1", title="Test Todo", items=[TodoItem(id="i1", description="Task")])
    state.set_todo_list(todo)
    state.window.calls.clear()
    # New direction should mark todo as interrupted
    state.set_interrupt_with_push("new_direction", "Do something else")
    assert state.get_interrupt() == "new_direction"
    assert state.get_new_direction_message() == "Do something else"
    # Todo should be marked as interrupted
    updated_todo = state.get_todo_list()
    assert updated_todo.interrupted_at is not None
    assert updated_todo.interrupt_reason == "new_direction"
    # Push events should fire
    assert any("__onTodoInterrupted" in c for c in state.window.calls)


def test_set_interrupt_with_push_pause_does_not_mark_todo_interrupted():
    state = BridgeState()
    state.window = MockWindow()
    # Set up an active todo list
    todo = TodoList(id="t1", title="Test Todo", items=[TodoItem(id="i1", description="Task")])
    state.set_todo_list(todo)
    state.window.calls.clear()
    # Pause should NOT mark todo as interrupted (pause is not interruption)
    state.set_interrupt_with_push("pause")
    assert state.get_interrupt() == "pause"
    # Todo should NOT be marked as interrupted
    updated_todo = state.get_todo_list()
    assert updated_todo.interrupted_at is None
    assert updated_todo.interrupt_reason is None
    # No todo interrupted push
    assert not any("__onTodoInterrupted" in c for c in state.window.calls)


def test_push_todo_interrupted():
    state = BridgeState()
    state.window = MockWindow()
    todo = TodoList(id="t1", title="Test", items=[], interrupt_reason="stop")
    state._push_todo_interrupted(todo)
    assert any("__onTodoInterrupted" in c for c in state.window.calls)
    assert any('"reason": "stop"' in c for c in state.window.calls)
