"""Shared state for bridge services."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from pathlib import Path

    from sip_studio.advisor.agent import BrandAdvisor
# Sanitization constants
MAX_STEP_LEN = 100
MAX_DETAIL_LEN = 500
URL_PATTERN = re.compile(r"https?://\S+|/[\w/.-]+")


def _sanitize(step: str, detail: str | None) -> tuple[str, str | None]:
    """Sanitize thinking step text, truncating and removing URLs/paths."""
    s = step[:MAX_STEP_LEN]
    d = URL_PATTERN.sub("[redacted]", detail)[:MAX_DETAIL_LEN] if detail else None
    return s, d


@dataclass
class TodoItem:
    """Single task item in a todo list."""

    id: str
    description: str
    status: str = "pending"  # pending | in_progress | done | error | paused
    outputs: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "description": self.description, "status": self.status}
        if self.outputs:
            d["outputs"] = self.outputs
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class TodoList:
    """Multi-step task list for complex requests."""

    id: str
    title: str
    items: list[TodoItem] = field(default_factory=list)
    created_at: str = ""
    completed_at: str | None = None
    interrupted_at: str | None = None
    interrupt_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "items": [i.to_dict() for i in self.items],
            "createdAt": self.created_at,
        }
        if self.completed_at:
            d["completedAt"] = self.completed_at
        if self.interrupted_at:
            d["interruptedAt"] = self.interrupted_at
            d["interruptReason"] = self.interrupt_reason
        return d


@dataclass
class ApprovalRequest:
    """Request for user approval before executing an action."""

    id: str
    action_type: str  # generate_image | create_style_reference | etc.
    description: str
    prompt: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "actionType": self.action_type,
            "description": self.description,
            "prompt": self.prompt,
            "details": self.details,
        }


@dataclass
class ThinkingStep:
    """Single thinking step from agent or tool.
    Attributes:
        id: UUID for deduplication/upsert
        run_id: Scopes step to current chat turn
        seq: Monotonic sequence number (assigned by BridgeState only), -1 until assigned
        step: Short label (2-10 words)
        detail: Optional explanation (1-2 sentences)
        expertise: Plain label: "Visual Design", "Strategy" (UI adds emoji)
        status: "pending" | "complete" | "failed"
        source: "agent" | "auto"
        timestamp: ISO timestamp (optional, for display only)
    """

    id: str
    run_id: str
    seq: int = -1
    step: str = ""
    detail: str | None = None
    expertise: str | None = None
    status: str = "pending"
    source: str = "auto"
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON with snake_case -> camelCase mapping."""
        d: dict[str, Any] = {
            "id": self.id,
            "runId": self.run_id,
            "step": self.step,
            "status": self.status,
            "source": self.source,
        }
        if self.seq >= 0:
            d["seq"] = self.seq
        if self.detail:
            d["detail"] = self.detail
        if self.expertise:
            d["expertise"] = self.expertise
        if self.timestamp:
            d["timestamp"] = self.timestamp
        return d


@dataclass
class BridgeState:
    """Shared state across bridge services."""

    advisor: "BrandAdvisor|None" = None
    current_progress: str = ""
    current_progress_type: str = ""
    matched_skills: list[str] = field(default_factory=list)
    execution_trace: list[dict[str, Any]] = field(default_factory=list)
    thinking_steps: list[dict[str, Any]] = field(default_factory=list)  # Legacy, kept for compat
    update_progress: dict[str, Any] | None = None
    window: object = None
    background_analysis_slug: str | None = None
    _cached_slug: str | None = field(default=None, repr=False)
    _cache_valid: bool = field(default=False, repr=False)
    # New: Per-run thinking step storage with thread-safe access
    _steps_by_run: dict[str, list[ThinkingStep]] = field(default_factory=dict, repr=False)
    _current_run_id: str | None = field(default=None, repr=False)
    _thinking_seq: int = field(default=0, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    # TodoList state
    _active_todo_list: TodoList | None = field(default=None, repr=False)
    _todo_seq: int = field(default=0, repr=False)
    # Autonomy and approval state
    _autonomy_mode: bool = field(default=False, repr=False)
    _pending_approval: ApprovalRequest | None = field(default=None, repr=False)
    _approval_response: dict[str, Any] | None = field(default=None, repr=False)
    _approval_event: threading.Event = field(default_factory=threading.Event, repr=False)
    APPROVAL_TIMEOUT_SEC: float = 300.0  # 5 minutes, configurable for tests
    # Interruption state
    _interrupt_signal: str | None = field(default=None, repr=False)  # pause | stop | new_direction
    _new_direction_message: str | None = field(default=None, repr=False)

    def start_chat_turn(self) -> str:
        """Start a new chat turn, generating run_id and clearing steps."""
        with self._lock:
            rid = str(uuid4())
            self._current_run_id = rid
            self._steps_by_run[rid] = []
            self._thinking_seq = 0
            # Also clear legacy thinking_steps for backward compat
            self.thinking_steps = []
            return rid

    def add_thinking_step(self, step: ThinkingStep) -> None:
        """Add or update a thinking step (upsert by id). Thread-safe."""
        with self._lock:
            rid = step.run_id or self._current_run_id or ""
            if rid not in self._steps_by_run:
                self._steps_by_run[rid] = []
            steps = self._steps_by_run[rid]
            existing = next((s for s in steps if s.id == step.id), None)
            if existing:
                # Status monotonicity: pending -> complete/failed only
                if existing.status == "pending" and step.status in ("complete", "failed"):
                    existing.status = step.status
                # Update detail if richer
                if step.detail and len(step.detail) > len(existing.detail or ""):
                    existing.detail = step.detail
            else:
                # New step: assign seq
                step.seq = self._thinking_seq
                self._thinking_seq += 1
                steps.append(step)
            # Sync to legacy thinking_steps for backward compat
            self._sync_legacy_steps(rid)
        # Push to frontend via evaluate_js (works around PyWebView concurrency)
        self._push_thinking_step(step)

    def _push_thinking_step(self, step: ThinkingStep) -> None:
        """Push thinking step to frontend via evaluate_js."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            import json

            data = json.dumps(step.to_dict())
            w.evaluate_js(f"window.__onThinkingStep&&window.__onThinkingStep({data})")  # type: ignore[union-attr]
        except Exception:
            pass  # Ignore errors - window may not be ready

    def _sync_legacy_steps(self, rid: str) -> None:
        """Sync new format to legacy thinking_steps list (for backward compat)."""
        if rid == self._current_run_id:
            self.thinking_steps = [s.to_dict() for s in self._steps_by_run.get(rid, [])]

    def finalize_chat_turn(self) -> list[ThinkingStep]:
        """Finalize current turn and return steps."""
        with self._lock:
            rid = self._current_run_id
            if not rid:
                return []
            return list(self._steps_by_run.get(rid, []))

    def get_thinking_steps_for_run(self, rid: str | None = None) -> list[ThinkingStep]:
        """Get thinking steps for a run (current run if None)."""
        with self._lock:
            r = rid or self._current_run_id or ""
            return list(self._steps_by_run.get(r, []))

    @property
    def current_run_id(self) -> str | None:
        """Get the current run_id."""
        return self._current_run_id

    def get_active_slug(self) -> str | None:
        """Get the active brand slug, using cache when available."""
        if not self._cache_valid:
            from sip_studio.brands.storage import get_active_brand

            self._cached_slug = get_active_brand()
            self._cache_valid = True
        return self._cached_slug

    def set_active_slug(self, slug: str | None) -> None:
        """Set the active brand slug, updating both disk and cache."""
        from sip_studio.brands.storage import set_active_brand

        set_active_brand(slug)
        self._cached_slug = slug
        self._cache_valid = True

    def invalidate_cache(self) -> None:
        """Invalidate the cached slug, forcing next get to read from disk."""
        self._cache_valid = False

    def get_brand_dir(self) -> "tuple[Path|None,str|None]":
        """Get the active brand directory."""
        from sip_studio.brands.storage import get_brand_dir

        s = self.get_active_slug()
        if not s:
            return None, "No brand selected"
        return get_brand_dir(s), None

    # =========================================================================
    # TodoList Management
    # =========================================================================
    def set_todo_list(self, todo: TodoList | None) -> None:
        """Set or clear the active todo list."""
        with self._lock:
            self._active_todo_list = todo
            self._todo_seq = 0
        if todo:
            self._push_todo_list(todo)

    def get_todo_list(self) -> TodoList | None:
        """Get the active todo list."""
        with self._lock:
            return self._active_todo_list

    def update_todo_item(
        self,
        item_id: str,
        status: str,
        outputs: list[dict[str, Any]] | None = None,
        error: str | None = None,
    ) -> None:
        """Update a todo item status and push to frontend."""
        with self._lock:
            if not self._active_todo_list:
                return
            for item in self._active_todo_list.items:
                if item.id == item_id:
                    item.status = status
                    if outputs:
                        item.outputs.extend(outputs)
                    if error:
                        item.error = error
                    break
        self._push_todo_update(item_id, status, outputs, error)

    def _push_todo_list(self, todo: TodoList) -> None:
        """Push full todo list to frontend via evaluate_js."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            import json

            data = json.dumps(todo.to_dict())
            w.evaluate_js(f"window.__onTodoList&&window.__onTodoList({data})")
        except Exception:
            pass

    def _push_todo_update(
        self, item_id: str, status: str, outputs: list[dict[str, Any]] | None, error: str | None
    ) -> None:
        """Push todo item update to frontend."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            import json

            data = json.dumps(
                {"itemId": item_id, "status": status, "outputs": outputs, "error": error}
            )
            w.evaluate_js(f"window.__onTodoUpdate&&window.__onTodoUpdate({data})")
        except Exception:
            pass

    def _push_todo_cleared(self) -> None:
        """Push todo list cleared event to frontend."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            w.evaluate_js("window.__onTodoCleared&&window.__onTodoCleared()")
        except Exception:
            pass

    def _push_todo_completed(self, todo: TodoList) -> None:
        """Push todo list completed event to frontend."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            import json

            data = json.dumps({"id": todo.id, "completedAt": todo.completed_at})
            w.evaluate_js(f"window.__onTodoCompleted&&window.__onTodoCompleted({data})")
        except Exception:
            pass

    def clear_todo_list(self) -> None:
        """Clear the active todo list and push event to frontend."""
        with self._lock:
            self._active_todo_list = None
        self._push_todo_cleared()

    # =========================================================================
    # Autonomy and Approval Management
    # =========================================================================
    def set_autonomy_mode(self, enabled: bool) -> None:
        """Set autonomy mode."""
        with self._lock:
            self._autonomy_mode = enabled

    def is_autonomy_mode(self) -> bool:
        """Check if autonomy mode is enabled."""
        with self._lock:
            return self._autonomy_mode

    def set_pending_approval(self, approval: ApprovalRequest | None) -> None:
        """Set or clear pending approval request."""
        with self._lock:
            self._pending_approval = approval
            self._approval_response = None
        if approval:
            self._push_approval_request(approval)

    def get_pending_approval(self) -> ApprovalRequest | None:
        """Get pending approval request."""
        with self._lock:
            return self._pending_approval

    def set_approval_response(self, response: dict[str, Any]) -> None:
        """Set approval response from user."""
        with self._lock:
            self._approval_response = response

    def get_approval_response(self) -> dict[str, Any] | None:
        """Get and clear approval response."""
        with self._lock:
            r = self._approval_response
            self._approval_response = None
            return r

    def _push_approval_request(self, approval: ApprovalRequest) -> None:
        """Push approval request to frontend."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            import json

            data = json.dumps(approval.to_dict())
            w.evaluate_js(f"window.__onApprovalRequest&&window.__onApprovalRequest({data})")
        except Exception:
            pass

    def _push_approval_cleared(self) -> None:
        """Push approval cleared event to frontend."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            w.evaluate_js("window.__onApprovalCleared&&window.__onApprovalCleared()")
        except Exception:
            pass

    def wait_for_approval(self, request: ApprovalRequest) -> dict[str, Any]:
        """Block until user responds to approval request. Thread-safe.
        Returns: {"action": "approve|approve_all|modify|skip|timeout", "modified_prompt": str|None}
        """
        with self._lock:
            self._pending_approval = request
            self._approval_response = None
            self._approval_event.clear()
        self._push_approval_request(request)
        signaled = self._approval_event.wait(timeout=self.APPROVAL_TIMEOUT_SEC)
        with self._lock:
            if not signaled:
                self._pending_approval = None
                self._push_approval_cleared()
                return {"action": "timeout", "modified_prompt": None}
            response = self._approval_response or {"action": "skip", "modified_prompt": None}
            self._pending_approval = None
            self._approval_response = None
        self._push_approval_cleared()
        if response.get("action") == "approve_all":
            self.set_autonomy_mode(True)
        return response

    def respond_approval(self, action: str, modified_prompt: str | None = None) -> None:
        """Set approval response and signal waiting thread."""
        with self._lock:
            self._approval_response = {"action": action, "modified_prompt": modified_prompt}
            self._approval_event.set()

    # =========================================================================
    # Interruption Management
    # =========================================================================
    def set_interrupt(self, signal: str | None, new_message: str | None = None) -> None:
        """Set interrupt signal. None to clear."""
        with self._lock:
            self._interrupt_signal = signal
            self._new_direction_message = new_message

    def get_interrupt(self) -> str | None:
        """Get current interrupt signal."""
        with self._lock:
            return self._interrupt_signal

    def is_interrupted(self) -> bool:
        """Check if interrupted."""
        with self._lock:
            return self._interrupt_signal is not None

    def get_new_direction_message(self) -> str | None:
        """Get new direction message if interrupt is new_direction."""
        with self._lock:
            return self._new_direction_message

    def clear_interrupt(self) -> None:
        """Clear interrupt signal."""
        with self._lock:
            self._interrupt_signal = None
            self._new_direction_message = None

    def _push_interrupt_status(self, signal: str | None) -> None:
        """Push interrupt status to frontend via evaluate_js."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            import json

            data = json.dumps({"signal": signal})
            w.evaluate_js(f"window.__onInterruptStatus&&window.__onInterruptStatus({data})")
        except Exception:
            pass

    def set_interrupt_with_push(self, signal: str | None, new_message: str | None = None) -> None:
        """Set interrupt and push to frontend.
        On stop/new_direction, auto-skip pending approval and mark todo as interrupted.
        Pause just sets the signal - doesn't mark todo as interrupted."""
        from datetime import datetime, timezone

        self.set_interrupt(signal, new_message)
        self._push_interrupt_status(signal)
        # On stop/new_direction, auto-skip any pending approval to prevent hangs
        if signal in ("stop", "new_direction") and self._pending_approval:
            self.respond_approval("skip")
        # Mark todo list as interrupted ONLY for stop/new_direction (NOT pause)
        if signal in ("stop", "new_direction") and self._active_todo_list:
            with self._lock:
                self._active_todo_list.interrupted_at = datetime.now(timezone.utc).isoformat()
                self._active_todo_list.interrupt_reason = signal
            self._push_todo_interrupted(self._active_todo_list)

    def _push_todo_interrupted(self, todo: TodoList) -> None:
        """Push todo list interrupted event to frontend."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            import json

            data = json.dumps({"id": todo.id, "reason": todo.interrupt_reason})
            w.evaluate_js(f"window.__onTodoInterrupted&&window.__onTodoInterrupted({data})")
        except Exception:
            pass
