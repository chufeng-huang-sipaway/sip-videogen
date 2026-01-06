"""Base progress tracking for agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from agents import Agent, RunHooks, Tool
from agents.run_context import RunContextWrapper

from sip_videogen.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentProgressEvent:
    """Progress update from agent orchestration."""

    event_type: str  # agent_start, agent_end, tool_start, tool_end, thinking
    agent_name: str
    message: str
    detail: str = ""


# Named differently from showrunner.ProgressCallback to avoid collision
AgentProgressCallback = Callable[[AgentProgressEvent], None]


class BaseProgressTracker(RunHooks):
    """Base class for agent progress tracking hooks.

    Subclasses can override tool_descriptions and customize event messages.
    """

    def __init__(
        self,
        callback: AgentProgressCallback | None = None,
        tool_descriptions: dict[str, str] | None = None,
    ):
        self.callback = callback
        self._tool_descriptions = tool_descriptions or {}

    def _report(self, progress: AgentProgressEvent) -> None:
        """Report progress to callback if set. Guarded to prevent breaking agent runs."""
        if self.callback:
            try:
                self.callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback error (ignored): {e}")
        logger.debug(f"[{progress.event_type}] {progress.agent_name}: {progress.message}")

    async def on_agent_start(
        self, context: RunContextWrapper, agent: Agent, *args, **kwargs
    ) -> None:
        self._report(
            AgentProgressEvent(
                event_type="agent_start",
                agent_name=agent.name,
                message=f"{agent.name} is analyzing...",
            )
        )

    async def on_agent_end(
        self, context: RunContextWrapper, agent: Agent, output: Any, *args, **kwargs
    ) -> None:
        self._report(
            AgentProgressEvent(
                event_type="agent_end", agent_name=agent.name, message=f"{agent.name} completed"
            )
        )

    async def on_tool_start(
        self, context: RunContextWrapper, agent: Agent, tool: Tool, *args, **kwargs
    ) -> None:
        n = tool.name
        d = self._tool_descriptions.get(n, f"Running {n}")
        self._report(
            AgentProgressEvent(
                event_type="tool_start",
                agent_name=agent.name,
                message=f"Delegating to {n.replace('_', ' ').title()}",
                detail=d,
            )
        )

    async def on_tool_end(
        self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str, *args, **kwargs
    ) -> None:
        n = tool.name
        r = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        self._report(
            AgentProgressEvent(
                event_type="tool_end",
                agent_name=agent.name,
                message=f"{n.replace('_', ' ').title()} finished",
                detail=r,
            )
        )

    async def on_llm_start(self, context: RunContextWrapper, agent: Agent, *args, **kwargs) -> None:
        self._report(
            AgentProgressEvent(event_type="thinking", agent_name=agent.name, message="Thinking...")
        )
