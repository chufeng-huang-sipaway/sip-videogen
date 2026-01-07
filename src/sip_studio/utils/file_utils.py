"""File utility functions for atomic writes and safe file operations."""

from __future__ import annotations

import os
from pathlib import Path


def write_atomically(path: Path, content: str | bytes, mode: int | None = None) -> None:
    """Atomically write content to file using temp file + fsync + os.replace.

    Args:
        path: Target file path.
        content: Content to write (str or bytes).
        mode: Optional file permissions (e.g., 0o600 for secrets).

    Pattern:
        - Write to temp file in same directory.
        - Flush + fsync for durability.
        - Atomic rename via os.replace.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")

    try:
        if isinstance(content, bytes):
            with open(tmp, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
        else:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

        if mode is not None:
            os.chmod(tmp, mode)

        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
