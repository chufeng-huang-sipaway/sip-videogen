"""Chat coordination service."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from sip_studio.advisor.agent import BrandAdvisor
from sip_studio.advisor.tools import (
    clear_tool_context,
    get_image_metadata,
    get_video_metadata,
    set_tool_context,
)
from sip_studio.brands.memory import list_brand_assets, list_brand_videos
from sip_studio.brands.storage import (
    get_active_brand,
    get_active_project,
    get_brand_dir,
    set_active_project,
)
from sip_studio.brands.storage import list_style_references as storage_list_style_references
from sip_studio.config.logging import get_logger
from sip_studio.models.aspect_ratio import validate_aspect_ratio

from ..state import BridgeState, ThinkingStep
from ..utils.bridge_types import bridge_error, bridge_ok
from ..utils.chat_utils import (
    analyze_and_format_attachments,
    encode_new_images,
    encode_new_videos,
    process_attachments,
)
from ..utils.path_utils import resolve_assets_path, resolve_docs_path

logger = get_logger(__name__)


class ChatService:
    """Chat coordination with BrandAdvisor."""

    def __init__(self, state: BridgeState):
        self._state = state

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
        # Accumulate thinking steps using new ThinkingStep model
        if progress.event_type == "thinking_step":
            step_id = progress.step_id or f"{ts}-{len(self._state.thinking_steps)}"
            run_id = self._state.current_run_id or ""
            # Determine source: report_thinking (agent) vs emit_tool_thinking (auto)
            # If step_id looks like a UUID (36 chars with dashes), it's from emit_tool_thinking
            source = "auto" if step_id and len(step_id) == 36 and "-" in step_id else "agent"
            step = ThinkingStep(
                id=step_id,
                run_id=run_id,
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
        if self._state.advisor is None:
            active = get_active_brand()
            if not active:
                return None, "No brand selected"
            self._state.advisor = BrandAdvisor(
                brand_slug=active, progress_callback=self._progress_callback
            )
        return self._state.advisor, None

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
        after = {t.slug for t in storage_list_style_references(slug)}
        return sorted(after - before)

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
        """Send a message to the Brand Advisor with optional context."""
        self._state.execution_trace = []
        self._state.matched_skills = []
        run_id = self._state.start_chat_turn()  # Generates run_id, clears thinking_steps
        # Add initial thinking step so timeline shows immediately
        initial_step = ThinkingStep(
            id=f"initial-{run_id[:8]}",
            run_id=run_id,
            step="Let me think about this...",
            expertise="Research",
            status="pending",
            source="auto",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._state.add_thinking_step(initial_step)
        try:
            advisor, err = self._ensure_advisor()
            if err or advisor is None:
                return bridge_error(err or "No brand selected")
            slug = self._state.get_active_slug()
            if not slug:
                return bridge_error("No brand selected")
            logger.info(
                "chat(): slug=%s, project_slug=%s, attached_products=%s, attached_style_refs=%s",
                slug,
                project_slug,
                attached_products,
                attached_style_references,
            )
            if project_slug is not None:
                logger.debug("chat(): Setting active project to %s", project_slug)
                set_active_project(slug, project_slug)
            effective_project = (
                project_slug if project_slug is not None else get_active_project(slug)
            )
            if project_slug is None:
                logger.info("chat(): effective_project from storage: %s", effective_project)
            brand_dir = get_brand_dir(slug)
            # Process attachments
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
            # Snapshot generated assets before running
            before_images = {a["path"] for a in list_brand_assets(slug, category="generated")}
            before_videos = {a["path"] for a in list_brand_videos(slug)}
            before_style_refs = {t.slug for t in storage_list_style_references(slug)}
            # Set tool context for todo tools (uses contextvars for thread safety)
            set_tool_context(self._state)
            # Run advisor
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
            response = result["response"]
            interaction = result.get("interaction")
            memory_update = result.get("memory_update")
            images = self._collect_new_images(slug, before_images)
            videos = self._collect_new_videos(slug, before_videos)
            style_refs = self._collect_new_style_references(slug, before_style_refs)
            # Mark initial step as complete
            initial_complete = ThinkingStep(
                id=f"initial-{run_id[:8]}",
                run_id=run_id,
                step="Let me think about this...",
                expertise="Research",
                status="complete",
                source="auto",
            )
            self._state.add_thinking_step(initial_complete)
            return bridge_ok(
                {
                    "response": response,
                    "images": images,
                    "videos": videos,
                    "style_references": style_refs,
                    "execution_trace": self._state.execution_trace,
                    "interaction": interaction,
                    "memory_update": memory_update,
                }
            )
        except Exception as e:
            return bridge_error(str(e))
        finally:
            clear_tool_context()
            self._state.current_progress = ""

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
            slug = get_active_brand()
            if not slug:
                return bridge_error("No brand selected")
            if self._state.advisor is None:
                self._state.advisor = BrandAdvisor(
                    brand_slug=slug, progress_callback=self._progress_callback
                )
            else:
                self._state.advisor.set_brand(slug, preserve_history=True)
            return bridge_ok({"message": "Brand context refreshed"})
        except Exception as e:
            return bridge_error(str(e))
