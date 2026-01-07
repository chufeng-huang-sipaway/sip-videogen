"""Job state models for background execution and UI synchronization.
This module defines data structures for managing job lifecycle,
to-do lists, approval flows, and interruption handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


# Todo item status enum with 7 values
class TodoItemStatus(str, Enum):
    """Status of a to-do item in the execution list."""

    PENDING = "pending"  # Not started
    IN_PROGRESS = "in_progress"  # Currently executing
    DONE = "done"  # Completed successfully (TERMINAL)
    ERROR = "error"  # Failed with error (TERMINAL)
    PAUSED = "paused"  # Paused by user, can resume
    CANCELLED = "cancelled"  # Cancelled by stop (TERMINAL)
    SKIPPED = "skipped"  # Skipped by user (TERMINAL)


# Terminal states that cannot transition
TERMINAL_STATES = {"done", "error", "cancelled", "skipped"}
# Valid status transitions
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress", "cancelled", "skipped"},
    "in_progress": {"done", "error", "paused", "cancelled"},
    "paused": {"in_progress", "cancelled"},
}


def is_valid_transition(current: str, target: str) -> bool:
    """Validate status transition. Terminal states cannot transition."""
    if current in TERMINAL_STATES:
        return False
    return target in VALID_TRANSITIONS.get(current, set())


class TodoItem(BaseModel):
    """Single to-do item in an execution list."""

    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(description="Unique identifier for the item")
    description: str = Field(description="Human-readable task description")
    status: TodoItemStatus = Field(default=TodoItemStatus.PENDING, description="Current status")
    outputs: list[str] = Field(
        default_factory=list, description="Output artifacts (e.g., image paths)"
    )
    error: str | None = Field(default=None, description="Error message if status is ERROR")
    created_at: str = Field(
        serialization_alias="createdAt", description="ISO timestamp when created"
    )
    updated_at: str = Field(
        serialization_alias="updatedAt", description="ISO timestamp when last updated"
    )

    @classmethod
    def create(cls, description: str, id: str | None = None) -> "TodoItem":
        """Factory to create a new TodoItem with timestamps."""
        now = datetime.utcnow().isoformat() + "Z"
        return cls(id=id or str(uuid4()), description=description, created_at=now, updated_at=now)


class TodoList(BaseModel):
    """Collection of to-do items for a job run."""

    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(description="Unique identifier for the list")
    run_id: str = Field(serialization_alias="runId", description="Associated job run ID")
    title: str = Field(default="Tasks", description="Display title for the list")
    items: list[TodoItem] = Field(default_factory=list, description="Ordered list of items")
    created_at: str = Field(
        serialization_alias="createdAt", description="ISO timestamp when created"
    )
    updated_at: str = Field(
        serialization_alias="updatedAt", description="ISO timestamp when last updated"
    )

    @classmethod
    def create(cls, run_id: str, title: str = "Tasks", id: str | None = None) -> "TodoList":
        """Factory to create a new TodoList with timestamps."""
        now = datetime.utcnow().isoformat() + "Z"
        return cls(
            id=id or str(uuid4()), run_id=run_id, title=title, created_at=now, updated_at=now
        )

    def add_item(self, description: str, id: str | None = None) -> TodoItem:
        """Add a new item and update timestamps."""
        item = TodoItem.create(description, id)
        self.items.append(item)
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        return item

    def get_item(self, item_id: str) -> TodoItem | None:
        """Find item by ID."""
        return next((i for i in self.items if i.id == item_id), None)

    def get_next_pending(self) -> TodoItem | None:
        """Get next pending item in order."""
        return next((i for i in self.items if i.status == TodoItemStatus.PENDING), None)

    @property
    def progress(self) -> dict[str, int]:
        """Calculate completion progress."""
        done = sum(1 for i in self.items if i.status in TERMINAL_STATES)
        return {"done": done, "total": len(self.items)}


class ApprovalRequest(BaseModel):
    """Request for user approval before executing a sensitive action."""

    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(description="Unique request identifier")
    run_id: str = Field(serialization_alias="runId", description="Associated job run ID")
    tool_name: str = Field(serialization_alias="toolName", description="Tool requesting approval")
    prompt: str = Field(description="The prompt or action to approve")
    preview_url: str | None = Field(
        default=None, serialization_alias="previewUrl", description="Optional preview image URL"
    )
    created_at: str = Field(
        serialization_alias="createdAt", description="ISO timestamp when created"
    )
    expires_at: str | None = Field(
        default=None,
        serialization_alias="expiresAt",
        description="ISO timestamp when request expires",
    )

    @classmethod
    def create(
        cls,
        run_id: str,
        tool_name: str,
        prompt: str,
        preview_url: str | None = None,
        timeout_sec: float = 300,
    ) -> "ApprovalRequest":
        """Factory to create a new ApprovalRequest with expiration."""
        now = datetime.utcnow()
        exp = datetime.utcnow().timestamp() + timeout_sec
        return cls(
            id=str(uuid4()),
            run_id=run_id,
            tool_name=tool_name,
            prompt=prompt,
            preview_url=preview_url,
            created_at=now.isoformat() + "Z",
            expires_at=datetime.fromtimestamp(exp).isoformat() + "Z",
        )


# Approval action types
ApprovalAction = Literal["approve", "reject", "edit", "approve_all", "auto_approved"]


class ApprovalResult(BaseModel):
    """Result of an approval request."""

    model_config = ConfigDict(populate_by_name=True)
    action: ApprovalAction = Field(description="User's decision")
    modified_prompt: str | None = Field(
        default=None,
        serialization_alias="modifiedPrompt",
        description="Edited prompt if action is 'edit'",
    )


# Interrupt action types
InterruptAction = Literal["pause", "stop", "new_direction"]


@dataclass
class JobState:
    """Mutable state for a running job (chat or quick_generate).
    Attributes:
            run_id: Unique identifier for this job run
            job_type: Type of job ('chat' or 'quick_generate')
            pending_approval: Current approval request awaiting response
            approval_response: User's response to pending approval
            interrupt_requested: Interrupt action requested by user
            interrupt_message: Message for new_direction interrupt
            todo_list: Current to-do list for the job
            is_paused: Whether job is currently paused
            created_at: ISO timestamp when job was created
    """

    run_id: str
    job_type: Literal["chat", "quick_generate"]
    pending_approval: ApprovalRequest | None = None
    approval_response: ApprovalResult | None = None
    interrupt_requested: InterruptAction | None = None
    interrupt_message: str | None = None
    todo_list: TodoList | None = None
    is_paused: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON with snake_case -> camelCase mapping."""
        d: dict[str, Any] = {
            "runId": self.run_id,
            "jobType": self.job_type,
            "isPaused": self.is_paused,
            "createdAt": self.created_at,
        }
        if self.todo_list:
            d["todoList"] = self.todo_list.model_dump(by_alias=True)
        if self.pending_approval:
            d["pendingApproval"] = self.pending_approval.model_dump(by_alias=True)
        if self.interrupt_requested:
            d["interruptRequested"] = self.interrupt_requested
        if self.interrupt_message:
            d["interruptMessage"] = self.interrupt_message
        return d


class InterruptedError(Exception):
    """Exception raised when job execution is interrupted."""

    def __init__(self, interrupt_type: InterruptAction, message: str | None = None):
        self.interrupt_type = interrupt_type
        self.message = message
        super().__init__(
            f"Job interrupted: {interrupt_type}" + (f" - {message}" if message else "")
        )
