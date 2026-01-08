"""Background chat job execution."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

from sip_studio.advisor.agent import BrandAdvisor
from sip_studio.advisor.context import RunContext, clear_active_context, set_active_context
from sip_studio.advisor.tools import get_image_metadata, get_video_metadata
from sip_studio.brands.memory import list_brand_assets, list_brand_videos
from sip_studio.brands.storage import (
    get_active_brand,
    get_active_project,
    get_brand_dir,
    set_active_project,
)
from sip_studio.brands.storage import list_style_references as storage_list_style_refs
from sip_studio.config.logging import get_logger
from sip_studio.models.aspect_ratio import validate_aspect_ratio
from sip_studio.studio.job_state import InterruptedError, JobState, TodoItemStatus

from ..state import BridgeState, ThinkingStep
from ..utils.chat_utils import (
    analyze_and_format_attachments,
    encode_new_images,
    encode_new_videos,
    process_attachments,
)
from ..utils.path_utils import resolve_assets_path, resolve_docs_path

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)
ChatResultCallback = Callable[[dict[str, Any]], None]


class ChatJob:
    """Encapsulates a single chat execution that runs in background."""

    def __init__(
        self,
        run_id: str,
        state: BridgeState,
        job_state: JobState,
        on_result: ChatResultCallback | None = None,
    ):
        self._run_id = run_id
        self._state = state
        self._job_state = job_state
        self._on_result = on_result
        self._advisor: BrandAdvisor | None = None

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def job_state(self) -> JobState:
        return self._job_state

    def _progress_callback(self, progress) -> None:
        """Called by BrandAdvisor during execution."""
        ts = int(time.time() * 1000)
        event = {
            "type": progress.event_type,
            "timestamp": ts,
            "message": progress.message,
            "detail": progress.detail or "",
        }
        self._state.execution_trace.append(event)
        if progress.event_type == "skill_loaded":
            skill_name = progress.message.replace("Loading ", "").replace(" skill", "")
            if skill_name not in self._state.matched_skills:
                self._state.matched_skills.append(skill_name)
        if progress.event_type == "thinking_step":
            step_id = progress.step_id or f"{ts}-{len(self._state.thinking_steps)}"
            source = "auto" if step_id and len(step_id) == 36 and "-" in step_id else "agent"
            step = ThinkingStep(
                id=step_id,
                run_id=self._run_id,
                step=progress.message,
                detail=progress.detail or None,
                expertise=progress.expertise,
                status=progress.status or "complete",
                source=source,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self._state.add_thinking_step(step)
        elif progress.event_type == "tool_end":
            self._state.current_progress = ""
            self._state.current_progress_type = ""
        else:
            self._state.current_progress = progress.message
            self._state.current_progress_type = progress.event_type

    def _ensure_advisor(self) -> tuple[BrandAdvisor | None, str | None]:
        """Initialize or get the brand advisor."""
        if self._advisor is None:
            active = get_active_brand()
            if not active:
                return None, "No brand selected"
            self._advisor = BrandAdvisor(
                brand_slug=active, progress_callback=self._progress_callback
            )
        return self._advisor, None

    def _collect_new_images(self, slug: str, before: set[str]) -> list[dict]:
        """Find newly generated images and encode them."""
        after = {a["path"] for a in list_brand_assets(slug, category="generated")}
        new_paths = sorted(after - before)
        return encode_new_images(new_paths, get_image_metadata)

    def _collect_new_videos(self, slug: str, before: set[str]) -> list[dict]:
        """Find newly generated videos and encode them."""
        after = {a["path"] for a in list_brand_videos(slug)}
        new_paths = sorted(after - before)
        return encode_new_videos(new_paths, get_video_metadata)

    def _collect_new_style_references(self, slug: str, before: set[str]) -> list[str]:
        """Find newly created style references."""
        after = {t.slug for t in storage_list_style_refs(slug)}
        return sorted(after - before)

    def _check_interrupt(self) -> None:
        """Check for interrupt request and raise if found."""
        action = self._job_state.interrupt_requested
        if action:
            raise InterruptedError(action, self._job_state.interrupt_message)

    def _push_result(self, result: dict[str, Any]) -> None:
        """Push result to frontend via callback and event."""
        if self._on_result:
            self._on_result(result)
        self._state._push_event("__onChatResult", {**result, "runId": self._run_id})

    def _push_error(self, error: str) -> None:
        """Push error to frontend."""
        self._state._push_event("__onChatError", {"runId": self._run_id, "error": error})

    def run(
        self,
        message: str,
        attachments: list[dict] | None = None,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_style_references: list[dict] | None = None,
        aspect_ratio: str | None = None,
        generation_mode: str | None = None,
    ) -> dict[str, Any]:
        """Execute chat job synchronously (meant to be called from thread)."""
        self._state.execution_trace = []
        self._state.matched_skills = []
        initial_step = ThinkingStep(
            id=f"initial-{self._run_id[:8]}",
            run_id=self._run_id,
            step="Let me think about this...",
            expertise="Research",
            status="pending",
            source="auto",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._state.add_thinking_step(initial_step)
        # Set up RunContext for tools to access job state (Fix #1)
        ctx = RunContext(
            run_id=self._run_id,
            job_state=self._job_state,
            bridge_state=self._state,
            push_event=self._state._push_event,
            autonomy_mode=self._state.autonomy_mode,
        )
        set_active_context(ctx)
        try:
            self._check_interrupt()
            advisor, err = self._ensure_advisor()
            if err or advisor is None:
                return {"error": err or "No brand selected"}
            slug = self._state.get_active_slug()
            if not slug:
                return {"error": "No brand selected"}
            logger.info(
                "ChatJob.run(): slug=%s, project=%s, products=%s, style_refs=%s",
                slug,
                project_slug,
                attached_products,
                attached_style_references,
            )
            if project_slug is not None:
                logger.debug("ChatJob.run(): Setting active project to %s", project_slug)
                set_active_project(slug, project_slug)
            effective_project = (
                project_slug if project_slug is not None else get_active_project(slug)
            )
            if project_slug is None:
                logger.info("ChatJob.run(): effective_project: %s", effective_project)
            brand_dir = get_brand_dir(slug)
            self._check_interrupt()
            saved = asyncio.run(
                process_attachments(
                    attachments,
                    brand_dir,
                    lambda p: resolve_assets_path(brand_dir, p),
                    lambda p: resolve_docs_path(brand_dir, p),
                )
            )
            prepared = message.strip() or "Please review the attached files."
            if saved:
                analysis = asyncio.run(analyze_and_format_attachments(saved, brand_dir))
                if analysis:
                    prepared = f"{prepared}\n\n{analysis}".strip()
            before_images = {a["path"] for a in list_brand_assets(slug, category="generated")}
            before_videos = {a["path"] for a in list_brand_videos(slug)}
            before_style_refs = {t.slug for t in storage_list_style_refs(slug)}
            self._check_interrupt()
            validated_ratio = validate_aspect_ratio(aspect_ratio)
            mode = generation_mode if generation_mode in ("image", "video") else "image"
            result = asyncio.run(
                advisor.chat_with_metadata(
                    prepared,
                    project_slug=effective_project,
                    attached_products=attached_products,
                    attached_style_references=attached_style_references,
                    aspect_ratio=validated_ratio.value,
                    generation_mode=mode,
                )
            )
            self._check_interrupt()
            response = result["response"]
            interaction = result.get("interaction")
            memory_update = result.get("memory_update")
            images = self._collect_new_images(slug, before_images)
            videos = self._collect_new_videos(slug, before_videos)
            style_refs = self._collect_new_style_references(slug, before_style_refs)
            initial_complete = ThinkingStep(
                id=f"initial-{self._run_id[:8]}",
                run_id=self._run_id,
                step="Let me think about this...",
                expertise="Research",
                status="complete",
                source="auto",
            )
            self._state.add_thinking_step(initial_complete)
            out = {
                "response": response,
                "images": images,
                "videos": videos,
                "style_references": style_refs,
                "execution_trace": self._state.execution_trace,
                "interaction": interaction,
                "memory_update": memory_update,
            }
            self._push_result(out)
            return out
        except InterruptedError as e:
            return self._handle_interrupt(e)
        except Exception as e:
            self._push_error(str(e))
            return {"error": str(e)}
        finally:
            clear_active_context()
            self._state.current_progress = ""

    def _handle_interrupt(self, e: InterruptedError) -> dict[str, Any]:
        """Handle interrupt exceptions."""
        if e.interrupt_type == "new_direction":
            if self._job_state.todo_list:
                for item in self._job_state.todo_list.items:
                    if item.status in (TodoItemStatus.PENDING, TodoItemStatus.IN_PROGRESS):
                        self._state.update_todo_item(self._run_id, item.id, "cancelled")
            out = {
                "response": "Redirecting to your new request...",
                "newDirection": True,
                "newMessage": e.message,
            }
            self._push_result(out)
            return out
        elif e.interrupt_type == "stop":
            if self._job_state.todo_list:
                for item in self._job_state.todo_list.items:
                    if item.status in (TodoItemStatus.PENDING, TodoItemStatus.IN_PROGRESS):
                        self._state.update_todo_item(self._run_id, item.id, "cancelled")
            out = {"response": "Task stopped.", "stopped": True}
            self._push_result(out)
            return out
        elif e.interrupt_type == "pause":
            if self._job_state.todo_list:
                for item in self._job_state.todo_list.items:
                    if item.status == TodoItemStatus.IN_PROGRESS:
                        self._state.update_todo_item(self._run_id, item.id, "paused")
            out = {"response": "Task paused.", "paused": True}
            self._push_result(out)
            return out
        raise e
