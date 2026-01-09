"""Thread-based pool for parallel image generation.
Uses ThreadPoolExecutor because Gemini client is synchronous.
Thread-safe with proper locking and cancel token pattern.
"""

import queue
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable


class TicketStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    def is_terminal(self) -> bool:
        return self in (
            TicketStatus.COMPLETED,
            TicketStatus.FAILED,
            TicketStatus.CANCELLED,
            TicketStatus.TIMEOUT,
        )


@dataclass
class Ticket:
    id: str
    prompt: str
    config: dict
    batch_id: str | None
    status: TicketStatus = TicketStatus.QUEUED
    result_path: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)


@dataclass
class TicketResult:
    """Result for a single ticket."""

    ticket_id: str
    status: TicketStatus
    path: str | None = None
    error: str | None = None


@dataclass
class BatchResult:
    batch_id: str
    tickets: list[TicketResult]
    completed_count: int
    failed_count: int
    cancelled_count: int


class ImageGenerationPool:
    """Thread-based pool for parallel image generation."""

    def __init__(
        self,
        max_workers: int = 5,
        default_timeout: float = 60.0,
        generator_fn: Callable[[Ticket], str] | None = None,
    ):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tickets: dict[str, Ticket] = {}
        self._futures: dict[str, Future] = {}
        self._cancelled: set[str] = set()
        self._ticket_events: dict[str, threading.Event] = {}
        self._batch_events: dict[str, threading.Event] = {}
        self._lock = threading.RLock()
        self._progress_callback: Callable[[dict], None] | None = None
        self._main_thread_queue: queue.Queue | None = None
        self._default_timeout = default_timeout
        self._generator_fn = generator_fn or self._default_generate
        self._last_status: dict[str, TicketStatus] = {}

    def set_main_thread_queue(self, q: queue.Queue):
        """Set queue for dispatching callbacks to main thread (PyWebView requirement)."""
        self._main_thread_queue = q

    def submit(self, prompt: str, config: dict, batch_id: str | None = None) -> str:
        """Submit a ticket for processing. Returns ticket_id immediately."""
        tid = str(uuid.uuid4())
        ticket = Ticket(id=tid, prompt=prompt, config=config, batch_id=batch_id)
        with self._lock:
            self._tickets[tid] = ticket
            self._ticket_events[tid] = threading.Event()
            if batch_id and batch_id not in self._batch_events:
                self._batch_events[batch_id] = threading.Event()
        future = self._executor.submit(self._process_ticket, tid)
        with self._lock:
            self._futures[tid] = future
        self._emit_progress(tid, TicketStatus.QUEUED, {})
        return tid

    def _process_ticket(self, ticket_id: str):
        """Process a single ticket (runs in worker thread)."""
        try:
            with self._lock:
                if ticket_id in self._cancelled:
                    ticket = self._tickets.get(ticket_id)
                    if ticket:
                        ticket.status = TicketStatus.CANCELLED
                    self._emit_progress(ticket_id, TicketStatus.CANCELLED, {})
                    return
                ticket = self._tickets.get(ticket_id)
                if not ticket:
                    return
                ticket.status = TicketStatus.PROCESSING
            self._emit_progress(ticket_id, TicketStatus.PROCESSING, {})
            result_path = self._generator_fn(ticket)
            with self._lock:
                ticket = self._tickets.get(ticket_id)
                if ticket:
                    ticket.status = TicketStatus.COMPLETED
                    ticket.result_path = result_path
            file_uri = None
            if result_path:
                try:
                    file_uri = Path(result_path).as_uri()
                except Exception:
                    file_uri = f"file://{result_path}"
            self._emit_progress(
                ticket_id, TicketStatus.COMPLETED, {"path": file_uri, "rawPath": result_path}
            )
        except Exception as e:
            with self._lock:
                ticket = self._tickets.get(ticket_id)
                if ticket:
                    ticket.status = TicketStatus.FAILED
                    ticket.error = str(e)
            self._emit_progress(ticket_id, TicketStatus.FAILED, {"error": str(e)})
        finally:
            self._on_ticket_done(ticket_id)

    def _default_generate(self, ticket: Ticket) -> str:
        """Default image generation - placeholder for Stage 3 integration."""
        # Stage 3 will wire this to actual image generation
        raise NotImplementedError(
            "ImageGenerationPool requires generator_fn - will be provided in Stage 3 integration"
        )

    def _on_ticket_done(self, ticket_id: str):
        """Called when ticket processing completes (success, fail, or cancel)."""
        with self._lock:
            event = self._ticket_events.get(ticket_id)
            if event:
                event.set()
            ticket = self._tickets.get(ticket_id)
            if ticket and ticket.batch_id:
                batch_tickets = [t for t in self._tickets.values() if t.batch_id == ticket.batch_id]
                if all(t.status.is_terminal() for t in batch_tickets):
                    be = self._batch_events.get(ticket.batch_id)
                    if be:
                        be.set()

    def wait_for_ticket(self, ticket_id: str, timeout: float | None = None) -> TicketResult:
        """Block until a single ticket completes. Returns result."""
        event = self._ticket_events.get(ticket_id)
        if event:
            event.wait(timeout=timeout or self._default_timeout)
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if not ticket:
                return TicketResult(
                    ticket_id=ticket_id, status=TicketStatus.CANCELLED, error="Ticket not found"
                )
            return TicketResult(
                ticket_id=ticket_id,
                status=ticket.status,
                path=ticket.result_path,
                error=ticket.error,
            )

    def wait_for_batch(self, batch_id: str, timeout: float | None = None) -> BatchResult:
        """Block until all tickets in batch complete. Returns results."""
        event = self._batch_events.get(batch_id)
        if event:
            event.wait(timeout=timeout or self._default_timeout * 10)
        with self._lock:
            tickets = [t for t in self._tickets.values() if t.batch_id == batch_id]
            results = [
                TicketResult(ticket_id=t.id, status=t.status, path=t.result_path, error=t.error)
                for t in tickets
            ]
            return BatchResult(
                batch_id=batch_id,
                tickets=results,
                completed_count=sum(1 for t in tickets if t.status == TicketStatus.COMPLETED),
                failed_count=sum(1 for t in tickets if t.status == TicketStatus.FAILED),
                cancelled_count=sum(1 for t in tickets if t.status == TicketStatus.CANCELLED),
            )

    def cancel_batch(self, batch_id: str) -> int:
        """Mark all non-terminal tickets in batch for cancellation. Returns count."""
        cancelled = 0
        with self._lock:
            for tid, ticket in self._tickets.items():
                if ticket.batch_id == batch_id and not ticket.status.is_terminal():
                    self._cancelled.add(tid)
                    if ticket.status == TicketStatus.QUEUED:
                        ticket.status = TicketStatus.CANCELLED
                        event = self._ticket_events.get(tid)
                        if event:
                            event.set()
                        self._emit_progress(tid, TicketStatus.CANCELLED, {})
                        cancelled += 1
            batch_tickets = [t for t in self._tickets.values() if t.batch_id == batch_id]
            if all(t.status.is_terminal() for t in batch_tickets):
                be = self._batch_events.get(batch_id)
                if be:
                    be.set()
        return cancelled

    def _emit_progress(self, ticket_id: str, status: TicketStatus, data: dict):
        """Emit progress update. Throttles by status change, not time."""
        if not self._progress_callback:
            return
        last = self._last_status.get(ticket_id)
        if last == status and not status.is_terminal():
            return
        self._last_status[ticket_id] = status
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            batch_id = ticket.batch_id if ticket else None
        payload = {"ticketId": ticket_id, "batchId": batch_id, "status": status.value, **data}
        if self._main_thread_queue:
            self._main_thread_queue.put(("image_progress", payload))
        else:
            try:
                self._progress_callback(payload)
            except Exception:
                pass

    def set_progress_callback(self, callback: Callable[[dict], None]):
        """Set callback for progress updates."""
        self._progress_callback = callback

    def shutdown(self, wait: bool = True):
        """Shutdown the pool."""
        self._executor.shutdown(wait=wait)

    def cleanup_batch(self, batch_id: str):
        """Remove ONLY terminal tickets from memory. Safe to call anytime."""
        with self._lock:
            to_remove = [
                tid
                for tid, t in self._tickets.items()
                if t.batch_id == batch_id and t.status.is_terminal()
            ]
            for tid in to_remove:
                self._tickets.pop(tid, None)
                self._futures.pop(tid, None)
                self._ticket_events.pop(tid, None)
                self._cancelled.discard(tid)
                self._last_status.pop(tid, None)
            remaining = [t for t in self._tickets.values() if t.batch_id == batch_id]
            if not remaining:
                self._batch_events.pop(batch_id, None)


# Singleton
_image_pool: ImageGenerationPool | None = None
_pool_lock = threading.Lock()


def get_image_pool(
    max_workers: int = 5, generator_fn: Callable[[Ticket], str] | None = None, _reset: bool = False
) -> ImageGenerationPool:
    """Get or create the global image pool singleton."""
    global _image_pool
    with _pool_lock:
        if _image_pool is None or _reset:
            _image_pool = ImageGenerationPool(max_workers=max_workers, generator_fn=generator_fn)
        return _image_pool
