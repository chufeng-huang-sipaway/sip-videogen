"""Tests for bridge interruption methods (pause/stop/resume)."""

from __future__ import annotations

from sip_studio.studio.bridge import StudioBridge


# =========================================================================
# Bridge Interruption Methods Tests
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
