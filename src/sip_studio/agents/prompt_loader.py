"""Shared prompt loading utility for agents."""

from __future__ import annotations

import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_VALID_AGENT_NAME = re.compile(r"^[a-z0-9_-]+$")


def load_agent_prompt(agent_name: str, fallback: str = "") -> str:
    """Load agent prompt from prompts/{agent_name}.md file.

    Args:
        agent_name: Name of the agent (e.g., "screenwriter"). Must match pattern [a-z0-9_-]+.
        fallback: Fallback prompt if file doesn't exist or is unreadable.

    Returns:
        Prompt text from file or fallback.

    Raises:
        ValueError: If agent_name contains invalid characters.
        FileNotFoundError: If no prompt file and no fallback provided.
    """
    if not _VALID_AGENT_NAME.match(agent_name):
        raise ValueError(f"Invalid agent name: {agent_name}")
    p = _PROMPTS_DIR / f"{agent_name}.md"
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            if fallback:
                return fallback
            raise FileNotFoundError(f"Cannot read prompt for {agent_name}: {e}") from e
    if fallback:
        return fallback
    raise FileNotFoundError(f"No prompt file found for agent: {agent_name}")
