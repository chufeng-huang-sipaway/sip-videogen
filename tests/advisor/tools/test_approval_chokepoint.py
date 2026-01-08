"""Tests for approval chokepoint in image_tools and bridge approval methods."""

from __future__ import annotations

import threading
import time

from sip_studio.advisor.tools.image_tools import _request_approval_if_supervised
from sip_studio.advisor.tools.todo_tools import clear_tool_context, set_tool_context
from sip_studio.studio.bridge import StudioBridge
from sip_studio.studio.state import ApprovalRequest, BridgeState


class MockWindow:
    """Mock pywebview window for testing."""

    def __init__(self):
        self.calls: list[str] = []

    def evaluate_js(self, js: str) -> None:
        self.calls.append(js)


# =========================================================================
# _request_approval_if_supervised Tests
# =========================================================================
def test_approval_no_state_proceeds():
    """Without state context, should proceed (autonomy mode by default)."""
    clear_tool_context()
    prompt, proceed = _request_approval_if_supervised("Test prompt")
    assert proceed is True
    assert prompt == "Test prompt"


def test_approval_autonomy_mode_skips():
    """In autonomy mode, should proceed without approval."""
    state = BridgeState()
    state.set_autonomy_mode(True)
    set_tool_context(state)
    try:
        prompt, proceed = _request_approval_if_supervised("Test prompt")
        assert proceed is True
        assert prompt == "Test prompt"
    finally:
        clear_tool_context()


def test_approval_interrupt_skips():
    """If interrupted, should not proceed."""
    state = BridgeState()
    state.set_interrupt("stop")
    set_tool_context(state)
    try:
        prompt, proceed = _request_approval_if_supervised("Test prompt")
        assert proceed is False
    finally:
        clear_tool_context()


def test_approval_approve_action():
    """User approving should proceed with original prompt."""
    state = BridgeState()
    state.APPROVAL_TIMEOUT_SEC = 1.0
    set_tool_context(state)

    def responder():
        time.sleep(0.05)
        state.respond_approval("approve")

    try:
        t = threading.Thread(target=responder)
        t.start()
        prompt, proceed = _request_approval_if_supervised("Test prompt")
        t.join()
        assert proceed is True
        assert prompt == "Test prompt"
    finally:
        clear_tool_context()


def test_approval_modify_action():
    """User modifying should proceed with modified prompt."""
    state = BridgeState()
    state.APPROVAL_TIMEOUT_SEC = 1.0
    set_tool_context(state)

    def responder():
        time.sleep(0.05)
        state.respond_approval("modify", "Modified prompt")

    try:
        t = threading.Thread(target=responder)
        t.start()
        prompt, proceed = _request_approval_if_supervised("Original prompt")
        t.join()
        assert proceed is True
        assert prompt == "Modified prompt"
    finally:
        clear_tool_context()


def test_approval_skip_action():
    """User skipping should not proceed."""
    state = BridgeState()
    state.APPROVAL_TIMEOUT_SEC = 1.0
    set_tool_context(state)

    def responder():
        time.sleep(0.05)
        state.respond_approval("skip")

    try:
        t = threading.Thread(target=responder)
        t.start()
        prompt, proceed = _request_approval_if_supervised("Test prompt")
        t.join()
        assert proceed is False
    finally:
        clear_tool_context()


def test_approval_timeout_skips():
    """Timeout should not proceed."""
    state = BridgeState()
    state.APPROVAL_TIMEOUT_SEC = 0.05  # Very short timeout
    set_tool_context(state)
    try:
        prompt, proceed = _request_approval_if_supervised("Test prompt")
        assert proceed is False
    finally:
        clear_tool_context()


def test_approval_approve_all_enables_autonomy():
    """approve_all should enable autonomy mode."""
    state = BridgeState()
    state.APPROVAL_TIMEOUT_SEC = 1.0
    assert not state.is_autonomy_mode()
    set_tool_context(state)

    def responder():
        time.sleep(0.05)
        state.respond_approval("approve_all")

    try:
        t = threading.Thread(target=responder)
        t.start()
        prompt, proceed = _request_approval_if_supervised("Test prompt")
        t.join()
        assert proceed is True
        assert state.is_autonomy_mode()
    finally:
        clear_tool_context()


# =========================================================================
# Bridge Approval Methods Tests
# =========================================================================
def test_bridge_set_autonomy_mode():
    """Bridge set_autonomy_mode should update state."""
    bridge = StudioBridge()
    result = bridge.set_autonomy_mode(True)
    assert result.get("success") is True
    assert result.get("data", {}).get("autonomy_mode") is True
    assert bridge._state.is_autonomy_mode()
    result = bridge.set_autonomy_mode(False)
    assert result.get("success") is True
    assert result.get("data", {}).get("autonomy_mode") is False
    assert not bridge._state.is_autonomy_mode()


def test_bridge_get_pending_approval_none():
    """get_pending_approval should return None when no pending."""
    bridge = StudioBridge()
    result = bridge.get_pending_approval()
    assert result.get("success") is True
    assert result.get("data") is None


def test_bridge_get_pending_approval_with_request():
    """get_pending_approval should return request data."""
    bridge = StudioBridge()
    req = ApprovalRequest(
        id="a1", action_type="generate_image", description="Test", prompt="Prompt"
    )
    bridge._state.set_pending_approval(req)
    result = bridge.get_pending_approval()
    assert result.get("success") is True
    data = result.get("data")
    assert data is not None
    assert data["id"] == "a1"
    assert data["actionType"] == "generate_image"


def test_bridge_respond_to_approval_no_pending():
    """respond_to_approval should error when no pending."""
    bridge = StudioBridge()
    result = bridge.respond_to_approval("a1", "approve")
    assert result.get("success") is False
    assert "No pending" in result.get("error", "")


def test_bridge_respond_to_approval_invalid_action():
    """respond_to_approval should error on invalid action."""
    bridge = StudioBridge()
    req = ApprovalRequest(id="a1", action_type="generate_image", description="Test")
    bridge._state.set_pending_approval(req)
    result = bridge.respond_to_approval("a1", "invalid")
    assert result.get("success") is False
    assert "Invalid action" in result.get("error", "")


def test_bridge_respond_to_approval_id_mismatch():
    """respond_to_approval should error on ID mismatch."""
    bridge = StudioBridge()
    req = ApprovalRequest(id="a1", action_type="generate_image", description="Test")
    bridge._state.set_pending_approval(req)
    result = bridge.respond_to_approval("wrong_id", "approve")
    assert result.get("success") is False
    assert "mismatch" in result.get("error", "")


def test_bridge_respond_to_approval_success():
    """respond_to_approval should signal waiting thread."""
    bridge = StudioBridge()
    bridge._state.APPROVAL_TIMEOUT_SEC = 1.0
    req = ApprovalRequest(id="a1", action_type="generate_image", description="Test")
    response_holder = {}

    def waiter():
        result = bridge._state.wait_for_approval(req)
        response_holder["result"] = result

    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.1)  # Let waiter start waiting
    result = bridge.respond_to_approval("a1", "approve")
    t.join()
    assert result.get("success") is True
    assert result.get("data", {}).get("responded") is True
    assert response_holder.get("result", {}).get("action") == "approve"


def test_bridge_respond_to_approval_with_modify():
    """respond_to_approval with modify should pass modified_prompt."""
    bridge = StudioBridge()
    bridge._state.APPROVAL_TIMEOUT_SEC = 1.0
    req = ApprovalRequest(id="a2", action_type="generate_image", description="Test")
    response_holder = {}

    def waiter():
        result = bridge._state.wait_for_approval(req)
        response_holder["result"] = result

    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.1)
    result = bridge.respond_to_approval("a2", "modify", "New prompt")
    t.join()
    assert result.get("success") is True
    assert response_holder.get("result", {}).get("action") == "modify"
    assert response_holder.get("result", {}).get("modified_prompt") == "New prompt"


# =========================================================================
# Bridge Interruption Methods Tests (Stage 4)
# =========================================================================
def test_bridge_interrupt_task_pause():
    """interrupt_task with pause should set interrupt signal."""
    bridge = StudioBridge()
    result = bridge.interrupt_task("pause")
    assert result.get("success") is True
    assert result.get("data", {}).get("interrupted") is True
    assert result.get("data", {}).get("action") == "pause"
    assert bridge._state.get_interrupt() == "pause"


def test_bridge_interrupt_task_stop():
    """interrupt_task with stop should set interrupt signal."""
    bridge = StudioBridge()
    result = bridge.interrupt_task("stop")
    assert result.get("success") is True
    assert result.get("data", {}).get("action") == "stop"
    assert bridge._state.get_interrupt() == "stop"


def test_bridge_interrupt_task_new_direction():
    """interrupt_task with new_direction should set interrupt and message."""
    bridge = StudioBridge()
    result = bridge.interrupt_task("new_direction", "Do something else")
    assert result.get("success") is True
    assert result.get("data", {}).get("action") == "new_direction"
    assert bridge._state.get_interrupt() == "new_direction"
    assert bridge._state.get_new_direction_message() == "Do something else"


def test_bridge_interrupt_task_invalid_action():
    """interrupt_task should error on invalid action."""
    bridge = StudioBridge()
    result = bridge.interrupt_task("invalid")
    assert result.get("success") is False
    assert "Invalid action" in result.get("error", "")


def test_bridge_resume_task_success():
    """resume_task should clear pause and return success."""
    bridge = StudioBridge()
    bridge._state.set_interrupt("pause")
    assert bridge._state.get_interrupt() == "pause"
    result = bridge.resume_task()
    assert result.get("success") is True
    assert result.get("data", {}).get("resumed") is True
    assert bridge._state.get_interrupt() is None


def test_bridge_resume_task_not_paused():
    """resume_task should error when not paused."""
    bridge = StudioBridge()
    result = bridge.resume_task()
    assert result.get("success") is False
    assert "not paused" in result.get("error", "")


def test_bridge_resume_task_when_stopped():
    """resume_task should error when stopped (not paused)."""
    bridge = StudioBridge()
    bridge._state.set_interrupt("stop")
    result = bridge.resume_task()
    assert result.get("success") is False
    assert "not paused" in result.get("error", "")
