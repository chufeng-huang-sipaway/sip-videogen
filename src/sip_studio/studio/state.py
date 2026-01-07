"""Shared state for bridge services."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sip_studio.studio.job_state import (
    ApprovalRequest,
    ApprovalResult,
    InterruptAction,
    JobState,
    TodoItem,
    TodoList,
    is_valid_transition,
)

if TYPE_CHECKING:
    from pathlib import Path

    from sip_studio.advisor.agent import BrandAdvisor


class JobConflictError(Exception):
    """Raised when trying to start a job while another is running."""

    pass


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
    # Per-run thinking step storage with thread-safe access
    _steps_by_run: dict[str, list[ThinkingStep]] = field(default_factory=dict, repr=False)
    _current_run_id: str | None = field(default=None, repr=False)
    _thinking_seq: int = field(default=0, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    # Job lifecycle state (global mutex - single active job slot)
    _jobs: dict[str, JobState] = field(default_factory=dict, repr=False)
    _active_job_run_id: str | None = field(default=None, repr=False)
    _autonomy_mode: bool = field(default=False, repr=False)
    _approval_index: dict[str, str] = field(
        default_factory=dict, repr=False
    )  # approval_id → run_id

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

    # === Job Lifecycle Methods (A4, A8) ===
    def can_start_job(self) -> bool:
        """Check if a new job can be started (global mutex)."""
        with self._lock:
            return self._active_job_run_id is None

    def create_job(self, run_id: str, job_type: str) -> JobState:
        """Create and register a new job. Raises JobConflictError if busy."""
        with self._lock:
            if self._active_job_run_id:
                raise JobConflictError("A job is already running")
            jt = "chat" if job_type == "chat" else "quick_generate"
            job = JobState(run_id=run_id, job_type=jt)  # type: ignore[arg-type]
            self._jobs[run_id] = job
            self._active_job_run_id = run_id
            return job

    def get_job(self, run_id: str) -> JobState | None:
        """Get a job by run_id."""
        with self._lock:
            return self._jobs.get(run_id)

    def get_active_job(self) -> JobState | None:
        """Get the currently active job, if any."""
        with self._lock:
            if self._active_job_run_id:
                return self._jobs.get(self._active_job_run_id)
            return None

    def cleanup_job(self, run_id: str) -> None:
        """Clean up a completed/cancelled job."""
        with self._lock:
            self._jobs.pop(run_id, None)
            if self._active_job_run_id == run_id:
                self._active_job_run_id = None
            # Clean approval index entries for this job
            self._approval_index = {k: v for k, v in self._approval_index.items() if v != run_id}

    # === Approval Methods (A4, A10) ===
    def set_pending_approval(self, run_id: str, request: ApprovalRequest) -> None:
        """Set pending approval for a job (single-slot invariant)."""
        with self._lock:
            job = self._jobs.get(run_id)
            if not job:
                return
            # Clear previous approval if exists (single-slot)
            if job.pending_approval:
                self._approval_index.pop(job.pending_approval.id, None)
            job.pending_approval = request
            job.approval_response = None
            self._approval_index[request.id] = run_id
        self._push_event("__onApprovalRequest", request.model_dump(by_alias=True))

    def submit_approval_response(
        self, request_id: str, action: str, modified_prompt: str | None = None
    ) -> bool:
        """Submit user response to an approval request. Returns False if expired/invalid."""
        with self._lock:
            run_id = self._approval_index.get(request_id)
            if not run_id:
                return False  # Expired or invalid
            job = self._jobs.get(run_id)
            if not job or not job.pending_approval or job.pending_approval.id != request_id:
                return False  # Expired
            job.approval_response = ApprovalResult(action=action, modified_prompt=modified_prompt)  # type: ignore[arg-type]
            if action == "approve_all":
                self._autonomy_mode = True
                self._push_event("__onAutonomyChanged", {"enabled": True})
            return True

    def clear_approval(self, run_id: str, request_id: str) -> None:
        """Clear a resolved approval request."""
        with self._lock:
            job = self._jobs.get(run_id)
            if job:
                job.pending_approval = None
                job.approval_response = None
            self._approval_index.pop(request_id, None)
        self._push_event("__onApprovalCleared", {"runId": run_id, "requestId": request_id})

    def get_pending_approval(self, run_id: str) -> ApprovalRequest | None:
        """Get pending approval for a job."""
        with self._lock:
            job = self._jobs.get(run_id)
            return job.pending_approval if job else None

    def get_approval_response(self, run_id: str) -> ApprovalResult | None:
        """Get approval response for a job."""
        with self._lock:
            job = self._jobs.get(run_id)
            return job.approval_response if job else None

    # === Interrupt Methods (A4) ===
    def request_interrupt(self, action: InterruptAction, message: str | None = None) -> bool:
        """Request interrupt on active job. Returns False if no active job."""
        with self._lock:
            if not self._active_job_run_id:
                return False
            job = self._jobs.get(self._active_job_run_id)
            if not job:
                return False
            job.interrupt_requested = action
            job.interrupt_message = message
            if action == "pause":
                job.is_paused = True
        self._push_event(
            "__onJobPaused" if action == "pause" else "__onJobInterrupted",
            {"action": action, "message": message},
        )
        return True

    def get_interrupt_requested(self, run_id: str) -> InterruptAction | None:
        """Get interrupt action for a job."""
        with self._lock:
            job = self._jobs.get(run_id)
            return job.interrupt_requested if job else None

    def get_interrupt_message(self, run_id: str) -> str | None:
        """Get interrupt message for a job."""
        with self._lock:
            job = self._jobs.get(run_id)
            return job.interrupt_message if job else None

    def clear_interrupt(self, run_id: str) -> None:
        """Clear interrupt state after handling."""
        with self._lock:
            job = self._jobs.get(run_id)
            if job:
                job.interrupt_requested = None
                job.interrupt_message = None

    def set_paused(self, run_id: str, paused: bool) -> None:
        """Set job paused state."""
        with self._lock:
            job = self._jobs.get(run_id)
            if job:
                job.is_paused = paused
        self._push_event("__onJobPaused" if paused else "__onJobResumed", {"runId": run_id})

    def is_paused(self, run_id: str) -> bool:
        """Check if job is paused."""
        with self._lock:
            job = self._jobs.get(run_id)
            return job.is_paused if job else False

    # === Todo Methods (A4, A5) ===
    def set_todo_list(self, run_id: str, todo_list: TodoList) -> None:
        """Set todo list for a job."""
        with self._lock:
            job = self._jobs.get(run_id)
            if job:
                job.todo_list = todo_list
        self._push_event("__onTodoListCreated", todo_list.model_dump(by_alias=True))

    def get_todo_list(self, run_id: str) -> TodoList | None:
        """Get todo list for a job."""
        with self._lock:
            job = self._jobs.get(run_id)
            return job.todo_list if job else None

    def update_todo_item(
        self,
        run_id: str,
        item_id: str,
        status: str,
        outputs: list[str] | None = None,
        error: str | None = None,
    ) -> bool:
        """Update a todo item. Returns False if invalid transition or item not found."""
        with self._lock:
            job = self._jobs.get(run_id)
            if not job or not job.todo_list:
                return False
            item = job.todo_list.get_item(item_id)
            if not item:
                return False
            if not is_valid_transition(item.status.value, status):
                return False
            item.status = status  # type: ignore[assignment]
            if outputs is not None:
                item.outputs = outputs
            if error is not None:
                item.error = error
            from datetime import datetime

            item.updated_at = datetime.utcnow().isoformat() + "Z"
            job.todo_list.updated_at = item.updated_at
        self._push_event(
            "__onTodoItemUpdated",
            {
                "runId": run_id,
                "itemId": item_id,
                "status": status,
                "outputs": outputs,
                "error": error,
            },
        )
        return True

    def add_todo_item(
        self, run_id: str, description: str, id: str | None = None
    ) -> TodoItem | None:
        """Add a todo item to a job's list. Returns None if no todo list."""
        with self._lock:
            job = self._jobs.get(run_id)
            if not job or not job.todo_list:
                return None
            item = job.todo_list.add_item(description, id)
        self._push_event(
            "__onTodoItemAdded", {"runId": run_id, "item": item.model_dump(by_alias=True)}
        )
        return item

    # === Autonomy Methods (A11) ===
    @property
    def autonomy_mode(self) -> bool:
        """Get autonomy mode status."""
        with self._lock:
            return self._autonomy_mode

    def set_autonomy_mode(self, enabled: bool) -> None:
        """Set autonomy mode and notify frontend."""
        with self._lock:
            self._autonomy_mode = enabled
        self._push_event("__onAutonomyChanged", {"enabled": enabled})

    # === Hydration (A9) ===
    def get_session_state(self) -> dict[str, Any]:
        """Get full session state for frontend hydration."""
        with self._lock:
            active_job: dict[str, Any] | None = None
            if self._active_job_run_id:
                job = self._jobs.get(self._active_job_run_id)
                if job:
                    active_job = job.to_dict()
            pending: dict[str, Any] | None = None
            for job in self._jobs.values():
                if job.pending_approval:
                    pending = job.pending_approval.model_dump(by_alias=True)
                    break
            return {
                "autonomyMode": self._autonomy_mode,
                "activeJob": active_job,
                "pendingApproval": pending,
            }

    # === Push Event Helper ===
    def _push_event(self, event_name: str, data: dict[str, Any] | None = None) -> None:
        """Push event to frontend via evaluate_js."""
        w = self.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            payload = json.dumps(data) if data else "{}"
            w.evaluate_js(f"window.{event_name}&&window.{event_name}({payload})")  # type: ignore[union-attr]
        except Exception:
            pass  # Ignore errors - window may not be ready
