"""OS-specific utility functions."""
import subprocess
import sys
from pathlib import Path
def reveal_in_file_manager(path:Path)->None:
    """Reveal a file or directory in the system file manager."""
    if sys.platform=="darwin":
        subprocess.run(["open","-R",str(path)],check=True)
    elif sys.platform=="win32":
        subprocess.run(["explorer","/select,",str(path)],check=True)
    else:
        #Linux: open parent directory
        subprocess.run(["xdg-open",str(path.parent)],check=True)
