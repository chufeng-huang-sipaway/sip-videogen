"""Background quick generate job execution."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from sip_studio.advisor.context import RunContext, clear_active_context, set_active_context
from sip_studio.advisor.tools.image_tools import _impl_generate_image
from sip_studio.brands.storage import get_active_brand
from sip_studio.config.logging import get_logger
from sip_studio.studio.job_state import InterruptedError, JobState

from ..state import BridgeState

if TYPE_CHECKING:
    pass
logger = get_logger(__name__)
QuickGenerateResultCallback = Callable[[dict[str, Any]], None]


@dataclass
class QuickGenerateProgress:
    """Progress state for quick generation."""

    total: int = 0
    completed: int = 0
    current_prompt: str = ""
    generated_paths: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "completed": self.completed,
            "currentPrompt": self.current_prompt,
            "generatedPaths": self.generated_paths,
            "errors": self.errors,
        }


class QuickGenerateJob:
    """Encapsulates a single quick generation that runs in background."""

    def __init__(
        self,
        run_id: str,
        state: BridgeState,
        job_state: JobState,
        on_result: QuickGenerateResultCallback | None = None,
    ):
        self._run_id = run_id
        self._state = state
        self._job_state = job_state
        self._on_result = on_result
        self._progress = QuickGenerateProgress()

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def job_state(self) -> JobState:
        return self._job_state

    @property
    def progress(self) -> QuickGenerateProgress:
        return self._progress

    def _check_interrupt(self) -> None:
        """Check for interrupt request and raise if found."""
        action = self._job_state.interrupt_requested
        if action:
            raise InterruptedError(action, self._job_state.interrupt_message)

    def _push_progress(self) -> None:
        """Push progress to frontend via event."""
        self._state._push_event(
            "__onQuickGenerateProgress", {**self._progress.to_dict(), "runId": self._run_id}
        )

    def _push_result(self, result: dict[str, Any]) -> None:
        """Push result to frontend via callback and event."""
        if self._on_result:
            self._on_result(result)
        self._state._push_event("__onQuickGenerateResult", {**result, "runId": self._run_id})

    def _push_error(self, error: str) -> None:
        """Push error to frontend."""
        self._state._push_event("__onQuickGenerateError", {"runId": self._run_id, "error": error})

    def run(
        self,
        prompts: list[str],
        aspect_ratio: str = "1:1",
        product_slug: str | None = None,
        template_slug: str | None = None,
        strict: bool = True,
    ) -> dict[str, Any]:
        """Execute quick generation job synchronously (meant to be called from thread).
        Args:
                prompts: List of prompts to generate images for.
                aspect_ratio: Aspect ratio for all generated images.
                product_slug: Optional product slug for reference images.
                template_slug: Optional style reference slug for constraints.
                strict: Whether to enforce strict style reference matching.
        Returns:
                Dict with generated paths, errors, and statistics.
        """
        slug = get_active_brand()
        if not slug:
            return {"error": "No brand selected"}
        # Fix #5: Set up RunContext for interrupt checks in image generation
        ctx = RunContext(
            run_id=self._run_id,
            job_state=self._job_state,
            bridge_state=self._state,
            push_event=self._state._push_event,
            autonomy_mode=self._state.autonomy_mode,
        )
        set_active_context(ctx)
        self._progress.total = len(prompts)
        self._push_progress()
        try:
            for i, prompt in enumerate(prompts):
                self._check_interrupt()
                self._progress.current_prompt = prompt
                self._push_progress()
                try:
                    result = asyncio.run(
                        _impl_generate_image(
                            prompt=prompt,
                            aspect_ratio=aspect_ratio,
                            product_slug=product_slug,
                            template_slug=template_slug,
                            strict=strict,
                            validate_identity=bool(product_slug),
                            max_retries=3,
                        )
                    )
                    self._check_interrupt()
                    if isinstance(result, str) and result.startswith("Error"):
                        self._progress.errors.append(f"Prompt {i + 1}: {result}")
                        logger.warning(f"Quick generate error for prompt {i + 1}: {result}")
                    else:
                        path = result.split("\n")[0] if "\n" in result else result
                        self._progress.generated_paths.append(path)
                        logger.info(f"Quick generate success for prompt {i + 1}: {path}")
                except InterruptedError:
                    raise
                except Exception as e:
                    self._progress.errors.append(f"Prompt {i + 1}: {str(e)}")
                    logger.error(f"Quick generate exception for prompt {i + 1}: {e}")
                self._progress.completed = i + 1
                self._push_progress()
            out = {
                "generatedPaths": self._progress.generated_paths,
                "errors": self._progress.errors,
                "total": self._progress.total,
                "completed": self._progress.completed,
                "cancelled": False,
            }
            self._push_result(out)
            return out
        except InterruptedError as e:
            out = {
                "generatedPaths": self._progress.generated_paths,
                "errors": self._progress.errors,
                "total": self._progress.total,
                "completed": self._progress.completed,
                "cancelled": True,
                "interruptType": e.interrupt_type,
            }
            self._push_result(out)
            return out
        except Exception as e:
            self._push_error(str(e))
            return {
                "error": str(e),
                "generatedPaths": self._progress.generated_paths,
                "errors": self._progress.errors,
                "total": self._progress.total,
                "completed": self._progress.completed,
            }
        finally:
            clear_active_context()
