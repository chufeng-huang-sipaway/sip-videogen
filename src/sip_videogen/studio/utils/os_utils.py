"""OS-specific utility functions."""

import subprocess
import sys
from pathlib import Path


def reveal_in_file_manager(path: Path) -> None:
    """Reveal a file or directory in the system file manager."""
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)], check=True)
    elif sys.platform == "win32":
        subprocess.run(["explorer", "/select,", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path.parent)], check=True)


def copy_image_to_clipboard_macos(path: Path) -> None:
    """Copy image file to system clipboard (macOS). Raises CalledProcessError on failure."""
    script = f"""osascript -e 'set the clipboard to (read (POSIX file "{path}") as «class PNGf»)' 2>/dev/null || osascript -e 'set the clipboard to (read (POSIX file "{path}") as JPEG picture)' """
    subprocess.run(script, shell=True, check=True, capture_output=True)
