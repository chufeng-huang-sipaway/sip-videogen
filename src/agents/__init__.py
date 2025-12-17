"""Lightweight shim for the external `agents` package used by tests.

This stub provides minimal Agent/Runner/Tool/function_tool definitions so the
rest of the codebase (and unit tests) can import `agents` without pulling the
real dependency. It is NOT a full replacement of the production library; it
only implements the small surface area exercised in this repository.
"""

from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Iterable

# Public API expected by the codebase
__all__ = [
    "Agent",
    "RunHooks",
    "Runner",
    "Tool",
    "function_tool",
]


class Tool:
    """Simple callable wrapper with a name/description."""

    def __init__(self, name: str, func: Callable[..., Any], description: str | None = None):
        self.name = name
        self.func = func
        self.description = description or getattr(func, "__doc__", "") or ""

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        result = self.func(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result  # type: ignore[func-returns-value]
        return result


class Agent:
    """Minimal Agent container used for configuration in tests."""

    def __init__(
        self,
        name: str,
        instructions: str,
        tools: Iterable[Any] | None = None,
        model: str | None = None,
        output_type: Any | None = None,
        **_: Any,
    ):
        self.name = name
        self.instructions = instructions
        self.tools = list(tools or [])
        self.model = model
        self.output_type = output_type

    def as_tool(self, tool_name: str | None = None, tool_description: str | None = None) -> Tool:
        """Expose this agent as a Tool. The callable delegates to Runner.run."""

        async def _call(*args: Any, **kwargs: Any) -> Any:
            return await Runner.run(self, *args, **kwargs)

        return Tool(tool_name or self.name, _call, tool_description)


class RunHooks:
    """Base hooks class; real implementations override hook methods."""

    async def on_agent_start(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - stub
        return None

    async def on_agent_end(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - stub
        return None

    async def on_tool_start(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - stub
        return None

    async def on_tool_end(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - stub
        return None

    async def on_llm_start(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - stub
        return None


class Runner:
    """Stub runner; real behavior is patched in tests."""

    @staticmethod
    async def run(agent: Agent, prompt: str, hooks: RunHooks | None = None, **_: Any) -> Any:
        raise RuntimeError(
            "Stub Runner.run called. In production, install the real `agents` package "
            "or patch Runner.run in tests."
        )

    @staticmethod
    async def run_streamed(
        agent: Agent, prompt: str, hooks: RunHooks | None = None, **_: Any
    ) -> Awaitable[Any]:
        async def _empty():
            if False:
                yield None  # pragma: no cover

        return _empty()


def function_tool(func: Callable[..., Any] | None = None, *, name: str | None = None) -> Callable:
    """Decorator to mark a function as a tool with a stable name."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn.name = name or fn.__name__  # type: ignore[attr-defined]
        fn.is_tool = True  # type: ignore[attr-defined]
        return fn

    if func is None:
        return decorator
    return decorator(func)
