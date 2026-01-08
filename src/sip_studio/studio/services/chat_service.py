"""Chat coordination service with background execution."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sip_studio.brands.storage import get_active_brand
from sip_studio.config.logging import get_logger
from sip_studio.studio.job_state import TodoItemStatus, TodoList

from ..state import BridgeState
from ..utils.bridge_types import bridge_error, bridge_ok
from .chat_job import ChatJob

logger = get_logger(__name__)


class ChatService:
    """Chat coordination with BrandAdvisor using background execution.

    Uses ThreadPoolExecutor to run chat jobs without blocking PyWebView.
    Results are pushed to frontend via events.
    """

    def __init__(self, state: BridgeState):
        self._state = state
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="chat-")
        self._current_job: ChatJob | None = None

    def get_progress(self) -> dict:
        """Get current operation progress."""
        return bridge_ok(
            {
                "status": self._state.current_progress,
                "type": self._state.current_progress_type,
                "skills": self._state.matched_skills,
                "thinking_steps": self._state.thinking_steps,
            }
        )

    def chat(
        self,
        message: str,
        attachments: list[dict] | None = None,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_style_references: list[dict] | None = None,
        aspect_ratio: str | None = None,
        generation_mode: str | None = None,
    ) -> dict:
        """Start chat job in background. Returns immediately with runId."""
        if not self._state.can_start_job():
            return {"success": False, "error": "A job is already running", "busy": True}
        run_id = str(uuid4())
        try:
            job_state = self._state.create_job(run_id, "chat")
        except Exception as e:
            return bridge_error(str(e))
        self._state.start_chat_turn()
        job = ChatJob(run_id, self._state, job_state)
        self._current_job = job

        def run_job():
            try:
                job.run(
                    message,
                    attachments,
                    project_slug,
                    attached_products,
                    attached_style_references,
                    aspect_ratio,
                    generation_mode,
                )
            finally:
                self._state.cleanup_job(run_id)
                self._current_job = None

        self._executor.submit(run_job)
        return bridge_ok({"started": True, "runId": run_id})

    def chat_sync(
        self,
        message: str,
        attachments: list[dict] | None = None,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_style_references: list[dict] | None = None,
        aspect_ratio: str | None = None,
        generation_mode: str | None = None,
        preserved_todo: TodoList | None = None,
    ) -> dict:
        """Synchronous chat for backward compatibility. Blocks until complete.
        Args:
            preserved_todo: Optional todo list from paused job to preserve across resume.
        """
        if not self._state.can_start_job():
            return {"success": False, "error": "A job is already running", "busy": True}
        run_id = str(uuid4())
        try:
            job_state = self._state.create_job(run_id, "chat")
        except Exception as e:
            return bridge_error(str(e))
        # Attach preserved todo list to new job (Fix: resume was losing todo list)
        if preserved_todo:
            preserved_todo.run_id = run_id
            self._state.set_todo_list(run_id, preserved_todo)
        self._state.start_chat_turn()
        job = ChatJob(run_id, self._state, job_state)
        self._current_job = job
        try:
            result = job.run(
                message,
                attachments,
                project_slug,
                attached_products,
                attached_style_references,
                aspect_ratio,
                generation_mode,
            )
            if "error" in result:
                return bridge_error(result["error"])
            # Fix #4: Don't cleanup on pause - preserve job state for resume
            if result.get("paused"):
                return bridge_ok(result)
            return bridge_ok(result)
        finally:
            # Fix #4: Only cleanup if not paused (job state needed for resume)
            if not self._state.is_paused(run_id):
                self._state.cleanup_job(run_id)
                self._current_job = None

    def interrupt_task(self, action: str, message: str | None = None) -> dict:
        """Interrupt current chat task (pause/stop/new_direction)."""
        if action not in ("pause", "stop", "new_direction"):
            return bridge_error("Invalid action")
        ok = self._state.request_interrupt(action, message)  # type: ignore[arg-type]
        if not ok:
            return bridge_error("No active job")
        return bridge_ok({"interrupted": True, "action": action})

    def resume_task(self) -> dict:
        """Resume a paused chat task (Fix #4).
        Preserves todo list across resume by passing it to the new job.
        """
        job = self._state.get_active_job()
        if not job:
            return bridge_error("No active job")
        if not job.is_paused:
            return bridge_error("Job is not paused")
        # Mark paused todo items as pending (ready to restart)
        if job.todo_list:
            for item in job.todo_list.items:
                if item.status == TodoItemStatus.PAUSED:
                    self._state.update_todo_item(job.run_id, item.id, "pending")
        # Clear pause/interrupt state
        self._state.set_paused(job.run_id, False)
        self._state.clear_interrupt(job.run_id)
        # Build resume prompt from pending items
        pending_items = []
        if job.todo_list:
            for item in job.todo_list.items:
                if item.status in (TodoItemStatus.PENDING, TodoItemStatus.IN_PROGRESS):
                    pending_items.append(item.description)
        if pending_items:
            resume_msg = "Continue with remaining tasks: " + ", ".join(pending_items)
        else:
            resume_msg = "Continue with the task."
        # Preserve todo list before cleanup
        preserved_todo = job.todo_list
        # Cleanup old job state before starting new chat
        self._state.cleanup_job(job.run_id)
        self._current_job = None
        # Start new chat with resume message and preserved todo list
        return self.chat_sync(resume_msg, preserved_todo=preserved_todo)

    def clear_chat(self) -> dict:
        """Clear conversation history."""
        try:
            if self._state.advisor:
                slug = self._state.get_active_slug()
                if slug:
                    self._state.advisor.set_brand(slug, preserve_history=False)
                else:
                    self._state.advisor.clear_history()
            self._state.current_progress = ""
            self._state.execution_trace = []
            return bridge_ok()
        except Exception as e:
            return bridge_error(str(e))

    def refresh_brand_memory(self) -> dict:
        """Refresh the agent's brand context."""
        try:
            from sip_studio.advisor.agent import BrandAdvisor

            slug = get_active_brand()
            if not slug:
                return bridge_error("No brand selected")
            if self._state.advisor is None:
                self._state.advisor = BrandAdvisor(
                    brand_slug=slug, progress_callback=self._progress_callback_stub
                )
            else:
                self._state.advisor.set_brand(slug, preserve_history=True)
            return bridge_ok({"message": "Brand context refreshed"})
        except Exception as e:
            return bridge_error(str(e))

    def _progress_callback_stub(self, _progress) -> None:
        """Stub callback for advisor init - actual callback is in ChatJob."""
        pass
