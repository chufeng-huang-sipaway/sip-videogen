"""Run context shim for the stub agents package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RunContextWrapper:
    """Placeholder context wrapper used by hooks in tests."""

    data: dict[str, Any] | None = None
