"""Session context for generation settings."""

from __future__ import annotations

from sip_studio.config.logging import get_logger

logger = get_logger(__name__)
# Module-level mutable state for session context
_active_aspect_ratio: str = "16:9"


def get_active_aspect_ratio() -> str:
    """Get the currently active aspect ratio for generation."""
    return _active_aspect_ratio


def set_active_aspect_ratio(ratio: str) -> None:
    """Set the active aspect ratio for generation."""
    global _active_aspect_ratio
    _active_aspect_ratio = ratio
    logger.debug(f"Active aspect ratio set to: {ratio}")
