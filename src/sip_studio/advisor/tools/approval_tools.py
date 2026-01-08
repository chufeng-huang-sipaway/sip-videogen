"""Approval tools for sensitive operation authorization.
Tools for requesting and waiting for user approval before executing
sensitive operations like image generation, file writes, etc.
Uses monotonic timeout to prevent stale requests and supports
autonomy mode for auto-approval.
"""

from __future__ import annotations

import asyncio
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from agents import function_tool

from sip_studio.advisor.context import RunContext, get_active_context
from sip_studio.config.logging import get_logger
from sip_studio.studio.job_state import (
    ApprovalRequest,
    ApprovalResult,
    InterruptAction,
    InterruptedError,
    JobState,
)

if TYPE_CHECKING:
    pass
logger = get_logger(__name__)
# Default timeout for approval requests (5 minutes)
DEFAULT_APPROVAL_TIMEOUT_SEC = 300.0
# Poll interval when waiting for approval response
APPROVAL_POLL_INTERVAL_SEC = 0.1
F = TypeVar("F", bound=Callable[..., Any])


def _get_ctx_and_state() -> tuple[RunContext | None, JobState | None, str | None]:
    """Get active context and job state. Returns (ctx, job_state, error)."""
    ctx = get_active_context()
    if not ctx:
        return None, None, "No active run context"
    if not ctx.job_state:
        return ctx, None, "No job state available"
    return ctx, ctx.job_state, None


def _check_interrupt(ctx: RunContext) -> None:
    """Check for interrupt and raise if found."""
    action = ctx.check_interrupt()
    if action:
        # Cast string to InterruptAction type
        iaction: InterruptAction = action  # type: ignore[assignment]
        raise InterruptedError(iaction, ctx.get_interrupt_message())


async def request_approval(
    tool_name: str,
    prompt: str,
    preview_url: str | None = None,
    timeout_sec: float = DEFAULT_APPROVAL_TIMEOUT_SEC,
) -> ApprovalResult:
    """Request user approval for a sensitive operation.
    Blocks until user responds or timeout expires. Uses monotonic clock
    for reliable timeout even across system clock changes.
    Args:
        tool_name: Name of the tool requesting approval
        prompt: The prompt/action to approve (shown to user)
        preview_url: Optional URL to preview (e.g., image preview)
        timeout_sec: Timeout in seconds (default 5 minutes)
    Returns:
        ApprovalResult with action ('approve', 'reject', 'edit', 'approve_all', 'auto_approved')
    Raises:
        InterruptedError: If job is interrupted during wait
        TimeoutError: If approval times out
    """
    ctx, job_state, err = _get_ctx_and_state()
    if err or ctx is None or job_state is None:
        raise RuntimeError(f"Cannot request approval: {err}")
    _check_interrupt(ctx)
    # Check autonomy mode (skip approval)
    if ctx.autonomy_mode:
        logger.info("Auto-approved (autonomy mode): %s", tool_name)
        return ApprovalResult(action="auto_approved")
    # Create approval request
    request = ApprovalRequest.create(ctx.run_id, tool_name, prompt, preview_url, timeout_sec)
    # Fix #6: Use BridgeState for thread-safe approval management
    if ctx.bridge_state:
        ctx.bridge_state.set_pending_approval(ctx.run_id, request)
    else:
        # Fallback for tests without bridge_state
        job_state.pending_approval = request
        job_state.approval_response = None
        if ctx.push_event:
            ctx.push_event("__onApprovalRequest", request.model_dump(by_alias=True))
    logger.info("Approval requested: %s (timeout=%ds)", tool_name, int(timeout_sec))
    # Wait for response with monotonic timeout
    start_time = time.monotonic()
    deadline = start_time + timeout_sec
    try:
        while True:
            # Check for interrupt
            _check_interrupt(ctx)
            # Fix #6: Use BridgeState for thread-safe response check
            response = None
            if ctx.bridge_state:
                response = ctx.bridge_state.get_approval_response(ctx.run_id)
            else:
                response = job_state.approval_response
            if response:
                logger.info("Approval response: %s for %s", response.action, tool_name)
                return response
            # Check timeout
            if time.monotonic() >= deadline:
                logger.warning("Approval timed out after %ds: %s", int(timeout_sec), tool_name)
                raise TimeoutError(f"Approval request timed out after {int(timeout_sec)}s")
            # Poll sleep
            await asyncio.sleep(APPROVAL_POLL_INTERVAL_SEC)
    finally:
        # Fix #6: Use BridgeState for thread-safe cleanup
        if ctx.bridge_state:
            ctx.bridge_state.clear_approval(ctx.run_id, request.id)
        else:
            job_state.pending_approval = None
            job_state.approval_response = None
            if ctx.push_event:
                ctx.push_event(
                    "__onApprovalCleared", {"runId": ctx.run_id, "requestId": request.id}
                )


def approval_required(
    tool_name: str | None = None, timeout_sec: float = DEFAULT_APPROVAL_TIMEOUT_SEC
) -> Callable[[F], F]:
    """Decorator to require approval before executing a function.
    Wraps an async function to request approval before execution.
    If rejected, returns an error message. If edited, passes the
    modified prompt to the function (if it accepts 'prompt' parameter).
    Args:
        tool_name: Name shown in approval UI (defaults to function name)
        timeout_sec: Approval timeout in seconds
    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        name = tool_name or func.__name__

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx, job_state, err = _get_ctx_and_state()
            # If no context, run without approval (e.g., testing)
            if err or ctx is None or job_state is None:
                return await func(*args, **kwargs)
            _check_interrupt(ctx)
            # Check autonomy mode
            if ctx.autonomy_mode:
                logger.debug("Auto-approved via decorator (autonomy mode): %s", name)
                return await func(*args, **kwargs)
            # Get prompt from kwargs for approval display
            prompt = kwargs.get("prompt", "")
            if not prompt and args:
                prompt = str(args[0])[:200]
            try:
                result = await request_approval(name, prompt, timeout_sec=timeout_sec)
            except TimeoutError:
                return f"Error: Approval timed out for {name}"
            if result.action == "reject":
                return f"Action rejected by user: {name}"
            if result.action == "edit" and result.modified_prompt:
                # Replace prompt with edited version
                if "prompt" in kwargs:
                    kwargs["prompt"] = result.modified_prompt
                elif args:
                    args = (result.modified_prompt,) + args[1:]
            # Approved (approve, approve_all, edit, auto_approved)
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


@function_tool
async def check_approval_status() -> str:
    """Check if there's a pending approval request.
    Returns:
        Status of pending approval or 'No pending approval'.
    """
    ctx, job_state, err = _get_ctx_and_state()
    if err or ctx is None or job_state is None:
        return f"Error: {err}"
    if not job_state.pending_approval:
        return "No pending approval"
    req = job_state.pending_approval
    return f"Pending approval for '{req.tool_name}': {req.prompt[:100]}..."


@function_tool
def get_autonomy_status() -> str:
    """Check current autonomy mode status.
    Returns:
        'enabled' if auto-approving, 'disabled' if requiring approval.
    """
    ctx, _, err = _get_ctx_and_state()
    if err or ctx is None:
        return f"Error: {err}"
    return "enabled" if ctx.autonomy_mode else "disabled"


# Exports for __init__.py
__all__ = [
    "request_approval",
    "approval_required",
    "check_approval_status",
    "get_autonomy_status",
    "DEFAULT_APPROVAL_TIMEOUT_SEC",
    "APPROVAL_POLL_INTERVAL_SEC",
]
