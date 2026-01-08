"""Run context for agent execution with job state access.
This module provides RunContext - a lightweight context object passed to tools
during agent execution to enable run-scoped state access for to-do lists,
approvals, and interruption handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from sip_studio.studio.job_state import ApprovalRequest, ApprovalResult, JobState
    from sip_studio.studio.state import BridgeState

# Callback types for push events
PushEventCallback = Callable[[str, dict[str, Any]], None]


@dataclass
class RunContext:
    """Context for a single agent run, providing access to job state.
    This context is passed to tools during execution, allowing them to:
    - Check for interruption requests
    - Update to-do list items
    - Request and wait for approvals
    - Push events to frontend
    Attributes:
        run_id: Unique identifier for this run
        job_state: Reference to mutable job state (shared with BridgeState)
        bridge_state: Reference to BridgeState for thread-safe operations
        push_event: Callback to push events to frontend via PyWebView
        autonomy_mode: Whether to auto-approve sensitive operations
    """

    run_id: str
    job_state: "JobState|None" = None
    bridge_state: "BridgeState|None" = None
    push_event: PushEventCallback | None = None
    autonomy_mode: bool = False

    def check_interrupt(self) -> "str|None":
        """Check if an interrupt has been requested.
        Returns:
            Interrupt action ('pause', 'stop', 'new_direction') or None if no interrupt
        """
        if not self.job_state:
            return None
        return self.job_state.interrupt_requested

    def is_paused(self) -> bool:
        """Check if the job is currently paused."""
        if not self.job_state:
            return False
        return self.job_state.is_paused

    def get_interrupt_message(self) -> "str|None":
        """Get the message for new_direction interrupt."""
        if not self.job_state:
            return None
        return self.job_state.interrupt_message

    def has_pending_approval(self) -> bool:
        """Check if there's a pending approval request."""
        if not self.job_state:
            return False
        return self.job_state.pending_approval is not None

    def get_pending_approval(self) -> "ApprovalRequest|None":
        """Get current pending approval request."""
        if not self.job_state:
            return None
        return self.job_state.pending_approval

    def get_approval_response(self) -> "ApprovalResult|None":
        """Get response to pending approval (if any)."""
        if not self.job_state:
            return None
        return self.job_state.approval_response

    def emit_event(self, event_name: str, data: dict[str, Any]) -> None:
        """Emit event to frontend via push callback.
        Args:
            event_name: Name of event (e.g., '__onTodoUpdate')
            data: Event payload
        """
        if self.push_event:
            self.push_event(event_name, data)

    @classmethod
    def create_standalone(cls, run_id: str) -> "RunContext":
        """Create a standalone context without job state (for testing/simple use)."""
        return cls(run_id=run_id)


# Module-level context storage for tools that need access
_active_context: RunContext | None = None


def get_active_context() -> RunContext | None:
    """Get the currently active run context.
    Tools can use this to access job state without explicit parameter passing.
    Returns None if no context is active.
    """
    return _active_context


def set_active_context(ctx: RunContext | None) -> None:
    """Set the active run context for the current execution.
    Should be called at the start of agent execution and cleared at the end.
    """
    global _active_context
    _active_context = ctx


def clear_active_context() -> None:
    """Clear the active run context."""
    global _active_context
    _active_context = None
