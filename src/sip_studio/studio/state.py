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
