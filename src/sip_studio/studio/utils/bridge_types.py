"""Shared types and constants for bridge layer."""

from dataclasses import asdict, dataclass
from typing import Any

from sip_studio.constants import (
    ALLOWED_IMAGE_EXTS,
    ALLOWED_TEXT_EXTS,
    ALLOWED_VIDEO_EXTS,
    ASSET_CATEGORIES,
    MIME_TYPES,
    VIDEO_MIME_TYPES,
)

__all__ = [
    "ALLOWED_IMAGE_EXTS",
    "ALLOWED_VIDEO_EXTS",
    "ALLOWED_TEXT_EXTS",
    "ASSET_CATEGORIES",
    "MIME_TYPES",
    "VIDEO_MIME_TYPES",
    "BridgeResponse",
    "bridge_ok",
    "bridge_error",
]


@dataclass
class BridgeResponse:
    """Standard response format for bridge methods."""

    success: bool
    data: Any = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# Helper functions for common response patterns
def bridge_ok(data: Any = None) -> dict:
    """Return a success response."""
    return BridgeResponse(success=True, data=data).to_dict()


def bridge_error(error: str) -> dict:
    """Return an error response."""
    return BridgeResponse(success=False, error=error).to_dict()
