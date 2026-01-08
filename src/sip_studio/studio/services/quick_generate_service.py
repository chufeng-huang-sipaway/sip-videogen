"""Quick generate coordination service with background execution."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sip_studio.brands.storage import get_active_brand
from sip_studio.config.logging import get_logger

from ..state import BridgeState
from ..utils.bridge_types import bridge_error, bridge_ok
from .quick_generate_job import QuickGenerateJob

logger = get_logger(__name__)


class QuickGenerateService:
    """Quick image generation coordination with background execution.
    Uses ThreadPoolExecutor to run generation jobs without blocking PyWebView.
    Results are pushed to frontend via events.
    """

    def __init__(self, state: BridgeState):
        self._state = state
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="quick-gen-")
        self._current_job: QuickGenerateJob | None = None

    def quick_generate(
        self,
        prompts: list[str],
        aspect_ratio: str = "1:1",
        product_slug: str | None = None,
        template_slug: str | None = None,
        strict: bool = True,
    ) -> dict:
        """Start quick generation job in background. Returns immediately with runId.
        Args:
                prompts: List of prompts to generate images for.
                aspect_ratio: Aspect ratio for all generated images.
                product_slug: Optional product slug for reference images.
                template_slug: Optional style reference slug for constraints.
                strict: Whether to enforce strict style reference matching.
        Returns:
                Dict with started=True and runId, or error if busy.
        """
        if not self._state.can_start_job():
            return {"success": False, "error": "A job is already running", "busy": True}
        slug = get_active_brand()
        if not slug:
            return bridge_error("No brand selected")
        if not prompts:
            return bridge_error("No prompts provided")
        run_id = str(uuid4())
        try:
            job_state = self._state.create_job(run_id, "quick_generate")
        except Exception as e:
            return bridge_error(str(e))
        job = QuickGenerateJob(run_id, self._state, job_state)
        self._current_job = job

        def run_job():
            try:
                job.run(prompts, aspect_ratio, product_slug, template_slug, strict)
            finally:
                self._state.cleanup_job(run_id)
                self._current_job = None

        self._executor.submit(run_job)
        return bridge_ok({"started": True, "runId": run_id, "total": len(prompts)})

    def cancel_quick_generate(self) -> dict:
        """Cancel current quick generation job."""
        ok = self._state.request_interrupt("stop")
        if not ok:
            return bridge_error("No active job")
        return bridge_ok({"cancelled": True})

    def get_quick_generate_progress(self) -> dict:
        """Get current quick generation progress."""
        if not self._current_job:
            return bridge_ok({"active": False})
        return bridge_ok(
            {
                "active": True,
                **self._current_job.progress.to_dict(),
                "runId": self._current_job.run_id,
            }
        )
