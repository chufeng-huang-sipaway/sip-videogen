"""Progress tracking hooks for Brand Marketing Advisor.
This module handles progress tracking and event capture during agent execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from agents import Agent, RunHooks, Tool
from agents.run_context import RunContextWrapper

from sip_videogen.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AdvisorProgress:
    """Progress update from the advisor agent.
    Event types:
        - "thinking": LLM is generating a response
        - "tool_start": Agent started using a tool
        - "tool_end": Tool call completed
        - "skill_loaded": A skill was matched and loaded for the request
        - "thinking_step": Agent reported a thinking step via report_thinking tool
        - "response": Agent completed responding
    """

    event_type: str  # thinking, tool_start, tool_end, skill_loaded, thinking_step, response
    message: str
    detail: str = ""
    expertise: str | None = None
    step_id: str | None = None


ProgressCallback = Callable[[AdvisorProgress], None]


class AdvisorHooks(RunHooks):
    """Hooks for tracking advisor progress."""

    def __init__(self, callback: ProgressCallback | None = None):
        self.callback = callback
        self.captured_interaction: dict | None = None
        self.captured_memory_update: dict | None = None
        self._tool_descriptions = {
            "generate_image": "Generating image with Gemini",
            "read_file": "Reading file",
            "write_file": "Writing file",
            "list_files": "Listing directory contents",
            "load_brand": "Loading brand context",
            "propose_choices": "Presenting options to the user",
            "propose_images": "Showing images for selection",
            "update_memory": "Recording a preference",
        }

    def _report(self, progress: AdvisorProgress) -> None:
        """Report progress to callback if set."""
        if self.callback:
            self.callback(progress)
        logger.debug(f"[{progress.event_type}] {progress.message}")

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        """Called when the agent starts using a tool."""
        tool_name = tool.name
        # Skip progress reporting for report_thinking (meta tool, not useful to show as tool_start)
        if tool_name == "report_thinking":
            return
        description = self._tool_descriptions.get(tool_name, f"Running {tool_name}")
        self._report(
            AdvisorProgress(
                event_type="tool_start", message=f"Using {tool_name}", detail=description
            )
        )

    async def on_tool_end(
        self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str
    ) -> None:
        """Called when a tool call completes."""
        from sip_videogen.advisor.tools import (
            get_pending_interaction,
            get_pending_memory_update,
            parse_thinking_step_result,
        )

        tool_name = tool.name
        # Handle report_thinking specially - emit thinking_step event instead of tool_end
        if tool_name == "report_thinking":
            step_data = parse_thinking_step_result(str(result))
            if step_data:
                self._report(
                    AdvisorProgress(
                        event_type="thinking_step",
                        message=step_data["step"],
                        detail=step_data["detail"],
                        expertise=step_data.get("expertise"),
                        step_id=step_data.get("id"),
                    )
                )
            return  # Skip normal tool_end reporting
        if tool_name in ("propose_choices", "propose_images"):
            interaction = get_pending_interaction()
            if interaction:
                self.captured_interaction = interaction
        if tool_name == "update_memory":
            mem_update = get_pending_memory_update()
            if mem_update:
                self.captured_memory_update = mem_update
        result_preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        self._report(
            AdvisorProgress(
                event_type="tool_end", message=f"{tool_name} completed", detail=result_preview
            )
        )

    async def on_llm_start(self, context: RunContextWrapper, agent: Agent, *args, **kwargs) -> None:
        """Called when the LLM starts generating."""
        self._report(AdvisorProgress(event_type="thinking", message="Thinking..."))
