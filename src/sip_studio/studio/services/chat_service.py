"""Chat coordination service."""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sip_studio.advisor.agent import BrandAdvisor
from sip_studio.advisor.session_manager import SessionManager
from sip_studio.advisor.tools import (
    _impl_archive_existing_tasks,
    _impl_complete_task_file,
    _impl_create_task_file,
    _impl_update_task,
    clear_tool_context,
    get_image_metadata,
    get_pending_research_clarification,
    get_video_metadata,
    set_current_batch_id,
    set_tool_context,
)
from sip_studio.brands.memory import list_brand_assets, list_brand_videos
from sip_studio.brands.storage import (
    get_active_brand,
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
from .batch_executor import BatchDetector, BatchExecutor, IdeaPlanner, TaskExtractor
from .image_pool import get_image_pool

logger = get_logger(__name__)


class ChatService:
    """Chat coordination with BrandAdvisor."""

    def __init__(self, state: BridgeState):
        self._state = state
        self._current_batch_id: str | None = None

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
            # Enable session-aware mode: get or create active session
            mgr = SessionManager(active)
            session = mgr.get_active_session()
            session_id = session.id if session else None
            if not session_id:
                new_session = mgr.create_session()
                session_id = new_session.id
                logger.info(f"Auto-created session {session_id} for brand {active}")
            self._state.advisor = BrandAdvisor(
                brand_slug=active,
                progress_callback=self._progress_callback,
                session_aware=True,
                session_id=session_id,
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

    def _get_conversation_history(self, advisor: BrandAdvisor) -> list[dict]:
        """Get conversation history for batch detection."""
        if advisor.session_history:
            messages = advisor.session_history.get_messages()
            return [{"role": m.role, "content": m.content} for m in messages[-10:]]
        return []

    def _batch_progress_callback(self, event_type: str, data: dict) -> None:
        """Handle batch executor progress events."""
        ts = int(time.time() * 1000)
        self._state.execution_trace.append({"type": f"batch_{event_type}", "timestamp": ts, **data})
        if event_type == "task_started":
            self._state.current_progress = (
                f"Task {data.get('number')}: {data.get('description', '')[:30]}"
            )
            self._state.current_progress_type = "batch_task"
        elif event_type in ("task_completed", "task_failed"):
            self._state.current_progress = ""

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

    def _emit_image_batch_start(self, batch_id: str, expected_count: int) -> None:
        """Emit an image batch start event to frontend (powers virtual TodoList placeholders)."""
        w = self._state.window
        if not w or not hasattr(w, "evaluate_js"):
            return
        try:
            payload = {"type": "batchStart", "batchId": batch_id, "expectedCount": expected_count}
            w.evaluate_js(
                f"window.__onImageProgress && window.__onImageProgress({json.dumps(payload)})"
            )
        except Exception:
            return

    def _detect_idea_batch_request(self, message: str) -> int | None:
        """Detect single-turn requests like: 'give me 5 images' or
        'give me 5 ideas and generate images for each'."""
        msg = message.lower()
        if not re.search(r"\b(images?|shots?|photos?|visuals?)\b", msg):
            return None
        # Must look like a request to provide/generate images (avoid false positives like
        # "I uploaded 5 images")
        if not re.search(
            r"\b(generate|create|make|render|produce|execute|give|show|provide|send|deliver)\b",
            msg,
        ):
            return None
        # Prefer explicit counts for images/ideas
        m = re.search(r"(\d+)\s*(?:image\s*sets?|images?|shots?|photos?|visuals?)\b", msg)
        if m:
            try:
                return max(1, min(int(m.group(1)), 20))
            except Exception:
                pass
        m = re.search(r"(\d+)\s*(?:ideas?|concepts?|options?)\b", msg)
        if m:
            try:
                return max(1, min(int(m.group(1)), 20))
            except Exception:
                pass
        words = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        m = re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b\s*(?:image\s*sets?|images?|shots?|photos?|visuals?)\b",
            msg,
        )
        if m:
            return words.get(m.group(1), 5)
        m = re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b\s*(?:ideas?|concepts?)\b",
            msg,
        )
        if m:
            return words.get(m.group(1), 5)
        # No explicit count: only trigger batch mode if the user clearly asked for multiple.
        if re.search(r"\b(ideas?|concepts?|options?)\b", msg):
            return 5
        if re.search(r"\b(images|shots|photos|visuals)\b", msg) and re.search(
            r"\b(a few|some|several|multiple|all)\b", msg
        ):
            return 5
        return None

    def _relativize_output_path(self, brand_dir: Path, raw_path: str | None) -> str | None:
        """Convert absolute paths under brand dir to stable relative paths (assets/...)."""
        if not raw_path:
            return None
        try:
            p = Path(raw_path).resolve()
            rel = p.relative_to(brand_dir.resolve())
            return rel.as_posix()
        except Exception:
            return raw_path

    def chat(
        self,
        message: str,
        attachments: list[dict] | None = None,
        project_slug: str | None = None,
        attached_products: list[str] | None = None,
        attached_style_references: list[dict] | None = None,
        image_aspect_ratio: str | None = None,
        video_aspect_ratio: str | None = None,
        web_search_enabled: bool = False,
        deep_research_enabled: bool = False,
    ) -> dict:
        """Send a message to the Brand Advisor with optional context."""
        self._state.execution_trace = []
        self._state.matched_skills = []
        run_id = self._state.start_chat_turn()
        # Cancel previous batch if exists (user sent new message)
        pool = get_image_pool()
        logger.debug("[CHAT] previous batch_id=%s", self._current_batch_id)
        if self._current_batch_id:
            cancelled = pool.cancel_batch(self._current_batch_id)
            pool.cleanup_batch(self._current_batch_id)
            if cancelled > 0:
                logger.info(f"Cancelled {cancelled} pending images from previous batch")
            self._current_batch_id = None
        # Generate new batch ID for this chat turn
        self._current_batch_id = str(uuid.uuid4())
        logger.debug("[CHAT] new batch_id=%s", self._current_batch_id)
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
            # Archive any existing TASKS.md from previous conversation to start fresh
            set_tool_context(self._state)
            _impl_archive_existing_tasks()
            logger.info(
                "chat(): slug=%s, project_slug=%s, attached_products=%s, attached_style_refs=%s",
                slug,
                project_slug,
                attached_products,
                attached_style_references,
            )
            # Always sync storage with frontend's project selection (fixes stale project bug)
            # This ensures tools like list_projects() see the correct active project
            set_active_project(slug, project_slug)
            effective_project = project_slug
            logger.debug("chat(): active project set to %s", effective_project)
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
            # Set batch ID for image pool (uses contextvars)
            set_current_batch_id(self._current_batch_id)
            logger.debug("[CHAT] set_current_batch_id(%s)", self._current_batch_id)
            validated_image_ratio = validate_aspect_ratio(image_aspect_ratio)
            validated_video_ratio = (
                video_aspect_ratio if video_aspect_ratio in ("16:9", "9:16") else "16:9"
            )
            # Single-turn: "give me N ideas and generate images for each" → plan + parallel execute
            idea_count = self._detect_idea_batch_request(prepared)
            if idea_count and idea_count >= 3:
                logger.info(f"[BATCH] Detected idea+generate request ({idea_count} ideas)")
                try:
                    from sip_studio.brands.context import HierarchicalContextBuilder

                    turn_context = ""
                    try:
                        builder = HierarchicalContextBuilder(
                            brand_slug=slug,
                            product_slugs=attached_products,
                            project_slug=effective_project,
                            attached_style_references=attached_style_references,
                        )
                        turn_context = builder.build_turn_context()
                    except Exception:
                        turn_context = ""
                    planned = asyncio.run(IdeaPlanner.plan(prepared, idea_count, turn_context))
                    if planned and len(planned) >= 3:
                        # TASKS.md: 1 planning step + N image tasks
                        title = f"{idea_count} Image Concepts"
                        task_items = [f"Generate {idea_count} image concepts"] + [
                            f"Image: {p.get('title','').strip()}" for p in planned
                        ]
                        created_msg = _impl_create_task_file(
                            title, task_items, context=prepared[:2000]
                        )
                        if not created_msg.startswith("Created task file"):
                            raise RuntimeError(created_msg)
                        _impl_update_task(1, done=True)
                        if self._current_batch_id:
                            self._emit_image_batch_start(self._current_batch_id, idea_count)
                        # Submit all images to pool in parallel
                        pool = get_image_pool()
                        config: dict = {
                            "aspect_ratio": validated_image_ratio.value,
                            "filename": None,
                            "reference_image": None,
                            "product_slug": attached_products[0]
                            if attached_products and len(attached_products) == 1
                            else None,
                            "product_slugs": attached_products
                            if attached_products and len(attached_products) > 1
                            else None,
                            "template_slug": None,
                            "strict": True,
                            "validate_identity": False,
                            "max_retries": 3,
                        }
                        ticket_ids: list[str] = []
                        for p in planned[:idea_count]:
                            prompt_text = str(p.get("prompt") or "").strip()
                            if not prompt_text or not self._current_batch_id:
                                continue
                            ticket_ids.append(
                                pool.submit(prompt_text, config, batch_id=self._current_batch_id)
                            )
                        id_to_task = {tid: idx + 2 for idx, tid in enumerate(ticket_ids)}
                        completed = 0
                        failed = 0
                        pending = set(ticket_ids)
                        start = time.time()
                        timeout_s = 600.0
                        while pending and (time.time() - start) < timeout_s:
                            # Cooperative interruption: stop cancels outstanding tickets.
                            if (
                                self._state.get_interrupt() in ("stop", "new_direction")
                                and self._current_batch_id
                            ):
                                pool.cancel_batch(self._current_batch_id)
                                break
                            for tid in list(pending):
                                res = pool.wait_for_ticket(tid, timeout=0.2)
                                if not res.status.is_terminal():
                                    continue
                                pending.discard(tid)
                                task_num = id_to_task.get(tid)
                                if not task_num:
                                    continue
                                if res.status.value == "completed" and res.path:
                                    rel = self._relativize_output_path(brand_dir, res.path)
                                    _impl_update_task(task_num, done=True, output_path=rel)
                                    completed += 1
                                elif res.status.value in ("failed", "cancelled", "timeout"):
                                    failed += 1
                            if pending:
                                time.sleep(0.2)
                        summary = f"Completed {completed}/{idea_count} images"
                        if failed:
                            summary += f" ({failed} failed)"
                        _impl_complete_task_file(summary)
                        ideas_text = "\n".join(
                            f"{i+1}. {p.get('title','').strip()}"
                            for i, p in enumerate(planned[:idea_count])
                        )
                        response_text = (
                            f"Here are {idea_count} concepts:\n{ideas_text}\n\n{summary}."
                        )
                        images = self._collect_new_images(slug, before_images)
                        videos = self._collect_new_videos(slug, before_videos)
                        style_refs = self._collect_new_style_references(slug, before_style_refs)
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
                                "response": response_text,
                                "images": images,
                                "videos": videos,
                                "style_references": style_refs,
                                "execution_trace": self._state.execution_trace,
                                "interaction": None,
                                "memory_update": None,
                            }
                        )
                except Exception as e:
                    logger.warning(f"[BATCH] Idea batch mode failed, falling back to agent: {e}")
            # Check for batch request follow-up (e.g., "generate all of them")
            history = self._get_conversation_history(advisor)
            if BatchDetector.is_batch_request(prepared, history):
                tasks = asyncio.run(TaskExtractor.extract(prepared, history))
                if len(tasks) >= 3:
                    logger.info(f"[BATCH] Executing batch mode with {len(tasks)} tasks")
                    if self._current_batch_id:
                        self._emit_image_batch_start(self._current_batch_id, len(tasks))
                    executor = BatchExecutor(advisor, self._state, self._batch_progress_callback)
                    batch_result = asyncio.run(
                        executor.run(
                            tasks,
                            {
                                "product_slugs": attached_products,
                                "style_refs": attached_style_references,
                                "aspect_ratio": validated_image_ratio.value,
                                "project_slug": effective_project,
                            },
                        )
                    )
                    images = self._collect_new_images(slug, before_images)
                    videos = self._collect_new_videos(slug, before_videos)
                    style_refs = self._collect_new_style_references(slug, before_style_refs)
                    return bridge_ok(
                        {
                            "response": batch_result.response,
                            "images": images,
                            "videos": videos,
                            "style_references": style_refs,
                            "execution_trace": self._state.execution_trace,
                            "interaction": None,
                            "memory_update": None,
                        }
                    )
            # Build extra tools list based on research flags
            extra_tools = []
            # DEBUG: Log research flags before building extra_tools
            logger.info(
                "[ChatService.chat] RESEARCH FLAGS: web_search=%s, deep_research=%s",
                web_search_enabled,
                deep_research_enabled,
            )
            if web_search_enabled or deep_research_enabled:
                from sip_studio.advisor.tools import search_research_cache, web_search

                extra_tools.extend([web_search, search_research_cache])
            if deep_research_enabled:
                from sip_studio.advisor.tools import get_research_status, request_deep_research

                extra_tools.extend([request_deep_research, get_research_status])
            # DEBUG: Log what extra_tools are being passed to the agent
            logger.info(
                "[ChatService.chat] EXTRA_TOOLS being passed: %s",
                [t.name if hasattr(t, "name") else str(t) for t in extra_tools],
            )
            # Build research mode context to prepend to message
            research_context = ""
            if web_search_enabled and not deep_research_enabled:
                research_context = (
                    "## Research Mode: Web Search Enabled\n\n"
                    "**IMPORTANT**: The user has enabled web search mode. "
                    "You MUST use the `web_search` tool to find current, up-to-date "
                    "information from the internet before answering. "
                    "Do NOT answer from your training data alone - search the web first."
                    "\n\n---\n\n"
                )
            elif deep_research_enabled:
                research_context = (
                    "## Research Mode: Deep Research Enabled\n\n"
                    "**IMPORTANT**: The user has enabled deep research mode. "
                    "For questions requiring comprehensive investigation "
                    "(market trends, competitor analysis, best practices), "
                    "you MUST use the `request_deep_research` tool to trigger "
                    "a thorough investigation. This will present clarification options "
                    "to the user and then perform extensive web research (10-30 min). "
                    "Do NOT answer complex research questions from training data alone.\n\n"
                    "For quick factual queries, use `web_search` for faster results."
                    "\n\n---\n\n"
                )
            # Prepend research context to the message if enabled
            if research_context:
                prepared = research_context + prepared
                logger.info(
                    "[ChatService.chat] Research context prepended (%d chars)",
                    len(research_context),
                )
            # Run advisor - pass aspect ratios as passive defaults (not instructions)
            result = asyncio.run(
                advisor.chat_with_metadata(
                    prepared,
                    project_slug=effective_project,
                    attached_products=attached_products,
                    attached_style_references=attached_style_references,
                    image_aspect_ratio=validated_image_ratio.value,
                    video_aspect_ratio=validated_video_ratio,
                    extra_tools=extra_tools if extra_tools else None,
                )
            )
            response = result["response"]
            interaction = result.get("interaction")
            memory_update = result.get("memory_update")
            # Check for research clarification (similar to interaction capture)
            research_clarification = get_pending_research_clarification()
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
                    "research_clarification": research_clarification,
                }
            )
        except Exception as e:
            return bridge_error(str(e))
        finally:
            clear_tool_context()
            set_current_batch_id(None)
            # Cleanup completed batch
            if self._current_batch_id:
                pool.cleanup_batch(self._current_batch_id)
                self._current_batch_id = None
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
                # Enable session-aware mode
                mgr = SessionManager(slug)
                session = mgr.get_active_session()
                session_id = session.id if session else None
                if not session_id:
                    new_session = mgr.create_session()
                    session_id = new_session.id
                self._state.advisor = BrandAdvisor(
                    brand_slug=slug,
                    progress_callback=self._progress_callback,
                    session_aware=True,
                    session_id=session_id,
                )
            else:
                self._state.advisor.set_brand(slug, preserve_history=True)
            return bridge_ok({"message": "Brand context refreshed"})
        except Exception as e:
            return bridge_error(str(e))
