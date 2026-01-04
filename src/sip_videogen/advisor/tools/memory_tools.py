"""Memory and user interaction tools."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

from agents import function_tool

from sip_videogen.config.logging import get_logger
from sip_videogen.utils.file_utils import write_atomically

from . import _common

logger = get_logger(__name__)
# Module-level state for pending interactions and memory updates
_pending_interaction: dict | None = None
_pending_memory_update: dict | None = None
# Progress callback for emitting thinking steps from within tools
_tool_progress_callback: "Callable[[str,str],None]|None" = None


def set_tool_progress_callback(cb: "Callable[[str,str],None]|None") -> None:
    """Set callback for tools to emit thinking steps. Called by agent before running."""
    global _tool_progress_callback
    _tool_progress_callback = cb


def emit_tool_thinking(step: str, detail: str = "") -> None:
    """Emit a thinking step from within a tool. No-op if no callback set."""
    if _tool_progress_callback:
        _tool_progress_callback(step, detail)


def get_pending_interaction() -> dict | None:
    """Get and clear any pending interaction."""
    global _pending_interaction
    result = _pending_interaction
    _pending_interaction = None
    return result


def get_pending_memory_update() -> dict | None:
    """Get and clear any pending memory update."""
    global _pending_memory_update
    result = _pending_memory_update
    _pending_memory_update = None
    return result


@function_tool
def propose_choices(question: str, choices: list[str], allow_custom: bool = False) -> str:
    """Present a multiple-choice question to the user with clickable options.
    Use this tool when you want the user to select from specific options.
    The user will see clickable buttons in the UI. Their selection will be
    returned as the next message in the conversation.
    Args:
        question: The question to ask (e.g., "Which logo style do you prefer?")
        choices: List of 2-5 choices to present as buttons
        allow_custom: If True, show an input field for custom response
    Returns:
        Confirmation that choices are being presented.
    """
    global _pending_interaction
    if len(choices) < 2:
        return "Error: Please provide at least 2 choices"
    if len(choices) > 5:
        choices = choices[:5]
    _pending_interaction = {
        "type": "choices",
        "question": question,
        "choices": choices,
        "allow_custom": allow_custom,
    }
    return f"[Presenting choices to user: {question}]"


@function_tool
def update_memory(key: str, value: str, display_message: str) -> str:
    """Record a user preference or learning for future reference.
    Use this when the user expresses a preference, gives feedback,
    or makes a decision that should be remembered for future interactions.
    Examples:
    - User says "I prefer minimalist designs" -> remember style preference
    - User says "Don't use red" -> remember color restriction
    - User picks a direction -> remember that preference
    Args:
        key: Short identifier (e.g., "style_preference", "color_avoid")
        value: The actual preference/learning to store
        display_message: User-friendly confirmation (e.g., "Noted: You prefer minimalist designs")
    Returns:
        Confirmation of memory update.
    """
    global _pending_memory_update
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return "No active brand - cannot save memory"
    memory_path = _common.get_brand_dir(brand_slug) / "memory.json"
    memory = {}
    if memory_path.exists():
        try:
            memory = json.loads(memory_path.read_text())
        except json.JSONDecodeError:
            memory = {}
    memory[key] = {"value": value, "updated_at": datetime.utcnow().isoformat()}
    write_atomically(memory_path, json.dumps(memory, indent=2))
    _pending_memory_update = {"message": display_message}
    return f"Memory updated: {key}"
