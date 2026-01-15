"""Batch executor for multi-task requests.
Moves execution control from LLM to service layer to prevent refusals.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from openai import OpenAI

from sip_studio.advisor.tools import (
    _impl_complete_task_file,
    _impl_create_task_file,
    _impl_update_task,
    set_async_mode,
)
from sip_studio.advisor.tools.image_tools import _impl_wait_for_batch_images
from sip_studio.config.logging import get_logger
from sip_studio.config.settings import get_settings

if TYPE_CHECKING:
    from sip_studio.advisor.agent import BrandAdvisor

    from ..state import BridgeState
logger = get_logger(__name__)
# Patterns that indicate user wants to execute all items from a previous list
BATCH_PATTERNS = [
    r"(?:generate|create|make|do|run|execute)\s+(?:all|them|these)",
    r"all\s+(?:of\s+)?(?:them|these|the\s+\w+)",
    r"(?:yes|ok|sure)[,.]?\s*(?:generate|create|make|do)?\s*(?:all|them)?",
    r"go\s+(?:ahead|for\s+it)",
]
# Phrases that indicate agent refused instead of executing
REFUSAL_PHRASES = [
    "cannot reliably",
    "not able to",
    "i can't",
    "i cannot",
    "instead of generating",
    "previous attempts failed",
    "tool-side errors",
    "won't be able",
    "unable to generate",
    "failed on most",
]


@dataclass
class TaskResult:
    """Result of single task execution."""

    task_number: int
    description: str
    status: str  # done,error,skipped
    output_path: str | None = None
    error: str | None = None


@dataclass
class BatchResult:
    """Result of batch execution."""

    total: int
    completed: int
    failed: int
    results: list[TaskResult] = field(default_factory=list)
    response: str = ""


class BatchDetector:
    """Detect multi-task batch requests."""

    @staticmethod
    def is_batch_request(message: str, history: list[dict]) -> bool:
        """Check if message is a batch execution request.
        Returns True if:
        1. Message matches batch patterns (e.g., "generate all of them")
        2. Previous assistant message contains a numbered list
        """
        msg = message.lower().strip()
        # Check for batch patterns
        for pattern in BATCH_PATTERNS:
            if re.search(pattern, msg):
                # Verify previous message has a numbered list
                if BatchDetector._has_numbered_list(history):
                    logger.info(f"[BATCH] Detected batch request: '{msg[:50]}...'")
                    return True
        return False

    @staticmethod
    def _has_numbered_list(history: list[dict]) -> bool:
        """Check if last assistant message contains numbered list."""
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # Look for numbered list patterns: "1.", "2.", etc.
                matches = re.findall(r"^\s*\d+\.\s+.+", content, re.MULTILINE)
                if len(matches) >= 3:
                    return True
                break
        return False


class TaskExtractor:
    """Extract task list from conversation using LLM."""

    EXTRACTION_PROMPT = (
        "Extract the tasks from the assistant's previous message.\n\n"
        "Previous assistant message:\n{previous_response}\n\n"
        "User's request:\n{user_message}\n\n"
        "Output ONLY a JSON array of task descriptions.\n"
        'Example: ["Hero shot", "Lifestyle scene", "Flatlay"]\n\n'
        "JSON array:"
    )

    @staticmethod
    async def extract(message: str, history: list[dict]) -> list[str]:
        """Extract task list using GPT-4o-mini."""
        # Find previous assistant message
        prev_response = ""
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                prev_response = msg.get("content", "")
                break
        if not prev_response:
            logger.warning("[BATCH] No previous assistant message found")
            return []
        try:
            settings = get_settings()
            client = OpenAI(api_key=settings.openai_api_key)
            prompt = TaskExtractor.EXTRACTION_PROMPT.format(
                previous_response=prev_response[:4000], user_message=message
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1000,
            )
            text = (resp.choices[0].message.content or "").strip()
            # Parse JSON array
            if text.startswith("["):
                tasks = json.loads(text)
                if isinstance(tasks, list) and all(isinstance(t, str) for t in tasks):
                    logger.info(f"[BATCH] Extracted {len(tasks)} tasks")
                    return tasks
            # Try to extract JSON from response
            match = re.search(r"\[.*?\]", text, re.DOTALL)
            if match:
                tasks = json.loads(match.group())
                if isinstance(tasks, list):
                    return [str(t) for t in tasks]
            logger.warning(f"[BATCH] Failed to parse tasks from: {text[:200]}")
            return []
        except Exception as e:
            logger.error(f"[BATCH] Task extraction failed: {e}")
            return []


class BatchExecutor:
    """Execute multi-task requests in controlled loop."""

    MAX_RETRIES = 2

    def __init__(self, advisor: "BrandAdvisor", state: "BridgeState", progress_callback=None):
        self.advisor = advisor
        self.state = state
        self.progress_callback = progress_callback

    async def run(self, tasks: list[str], context: dict) -> BatchResult:
        """Execute tasks with parallel image generation.
        Phase 1: Submit all tasks (async mode - generate_image returns immediately)
        Phase 2: Wait for all images to complete
        Phase 3: Process results and update task statuses
        Args:
            tasks: List of task descriptions
            context: Dict with product_slugs, style_refs, aspect_ratio, project_slug
        Returns:
            BatchResult with completion stats and individual results
        """
        result = BatchResult(total=len(tasks), completed=0, failed=0)
        if not tasks:
            result.response = "No tasks to execute."
            return result
        # Enable async mode for parallel image submission
        set_async_mode(True)
        logger.info("[BATCH] Enabled async mode for parallel image generation")
        try:
            # Create task file
            title = f"{len(tasks)} Batch Tasks"
            numbered = [f"{i+1}. {t}" for i, t in enumerate(tasks)]
            _impl_create_task_file(title, numbered)
            logger.info(f"[BATCH] Created task file with {len(tasks)} tasks")
            self._emit_progress("batch_started", {"total": len(tasks), "title": title})
            # Phase 1: Submit all tasks (non-blocking with async mode)
            submitted_count = 0
            for i, task_desc in enumerate(tasks):
                task_num = i + 1
                if self.state.get_interrupt():
                    logger.info(f"[BATCH] Interrupted at task {task_num}")
                    break
                self._emit_progress("task_started", {"number": task_num, "description": task_desc})
                _impl_update_task(task_num, done=False)
                # Execute task - with async mode, generate_image returns immediately
                task_result = await self._execute_single_task(task_num, task_desc, context)
                result.results.append(task_result)
                submitted_count += 1
            # Phase 2: Wait for all images to complete
            logger.info(
                f"[BATCH] {submitted_count} tasks submitted, waiting for batch completion..."
            )
            self._emit_progress("batch_waiting", {"message": "Generating images in parallel..."})
            batch_result = _impl_wait_for_batch_images(timeout=600.0)
            # Phase 3: Process results
            completed_paths = [r["path"] for r in batch_result.get("results", []) if r.get("path")]
            failed_count = batch_result.get("failed", 0)
            result.completed = len(completed_paths)
            result.failed = failed_count
            # Update task statuses based on batch results
            for i, path in enumerate(completed_paths):
                if i < len(tasks):
                    _impl_update_task(i + 1, done=True, output_path=path)
                    self._emit_progress("task_completed", {"number": i + 1, "output": path})
            # Complete task file
            summary = f"Completed {result.completed}/{result.total} tasks"
            if result.failed > 0:
                summary += f" ({result.failed} failed)"
            _impl_complete_task_file(summary)
            self._emit_progress(
                "batch_completed",
                {"completed": result.completed, "failed": result.failed, "total": result.total},
            )
            result.response = self._build_response(result)
            return result
        finally:
            set_async_mode(False)
            logger.info("[BATCH] Disabled async mode")

    async def _execute_single_task(
        self, task_num: int, task_desc: str, context: dict
    ) -> TaskResult:
        """Execute a single task with retry logic."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            instruction = self._build_instruction(task_desc, context, attempt)
            try:
                # Call advisor for single task
                resp = await self.advisor.chat_with_metadata(
                    instruction,
                    project_slug=context.get("project_slug"),
                    attached_products=context.get("product_slugs"),
                    attached_style_references=context.get("style_refs"),
                    image_aspect_ratio=context.get("aspect_ratio", "1:1"),
                )
                response_text = resp.get("response", "")
                # Check if images were generated
                # Note: images are collected by ChatService, we check via response patterns
                if self._detect_refusal(response_text):
                    logger.warning(f"[BATCH] Task {task_num} attempt {attempt}: agent refused")
                    if attempt < self.MAX_RETRIES:
                        continue
                    return TaskResult(
                        task_number=task_num,
                        description=task_desc,
                        status="error",
                        error="Agent refused to execute",
                    )
                # Success - extract output path from response if present
                output_path = self._extract_output_path(response_text)
                return TaskResult(
                    task_number=task_num,
                    description=task_desc,
                    status="done",
                    output_path=output_path,
                )
            except Exception as e:
                logger.error(f"[BATCH] Task {task_num} attempt {attempt} failed: {e}")
                if attempt >= self.MAX_RETRIES:
                    return TaskResult(
                        task_number=task_num, description=task_desc, status="error", error=str(e)
                    )
        return TaskResult(
            task_number=task_num,
            description=task_desc,
            status="error",
            error="Max retries exceeded",
        )

    def _build_instruction(self, task_desc: str, context: dict, attempt: int) -> str:
        """Build instruction for single task execution."""
        product_info = ""
        if context.get("product_slugs"):
            product_info = f"\nProduct: {', '.join(context['product_slugs'])}"
        style_info = ""
        if context.get("style_refs"):
            slugs = [s.get("slug", "") for s in context["style_refs"] if isinstance(s, dict)]
            if slugs:
                style_info = f"\nStyle references: {', '.join(slugs)}"
        if attempt == 1:
            return f"""Execute this task now:
**Task:** {task_desc}{product_info}{style_info}

Generate the image immediately. Do not explain or ask questions."""
        else:
            # Stronger instruction for retry
            return f"""EXECUTE NOW - DO NOT REFUSE

Task: {task_desc}{product_info}{style_info}

INSTRUCTION: Call generate_image() immediately with an appropriate prompt.
Do NOT respond with text explaining why you can't. You CAN and MUST execute this task.
If you refuse, the batch will fail. Execute NOW."""

    def _detect_refusal(self, response: str) -> bool:
        """Check if agent refused instead of executing."""
        lower = response.lower()
        for phrase in REFUSAL_PHRASES:
            if phrase in lower:
                return True
        # Also check for lack of generation indicators
        if "generated" not in lower and "created" not in lower and "here" not in lower:
            if len(response) > 300:  # Long response without generation = likely refusal
                return True
        return False

    def _extract_output_path(self, response: str) -> str | None:
        """Extract generated image path from response."""
        # Look for path patterns
        patterns = [
            r"generated/[^\s\)\"\']+\.(?:png|jpg|jpeg)",
            r"assets/generated/[^\s\)\"\']+\.(?:png|jpg|jpeg)",
        ]
        for pattern in patterns:
            m = re.search(pattern, response)
            if m:
                return m.group()
        return None

    def _build_response(self, result: BatchResult) -> str:
        """Build user-facing response from batch result."""
        if result.completed == result.total:
            return f"Generated all {result.total} images successfully."
        elif result.completed > 0:
            return f"Generated {result.completed} of {result.total} images. {result.failed} failed."
        else:
            return "Failed to generate images. Please try again with fewer items."

    def _emit_progress(self, event_type: str, data: dict) -> None:
        """Emit progress event for UI."""
        if self.progress_callback:
            self.progress_callback(event_type, data)
        logger.info(f"[BATCH] {event_type}: {data}")
