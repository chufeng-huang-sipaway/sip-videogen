"""Auto-update functionality for sip-videogen.

Checks PyPI for newer versions and provides update mechanism.
"""

import subprocess
import sys
from importlib.metadata import version as get_installed_version

import httpx
from packaging.version import Version
from rich.console import Console
from rich.panel import Panel

console = Console()

# PyPI package name
PYPI_PACKAGE_NAME = "sip-videogen"

# Timeout for PyPI requests (fast, non-blocking)
PYPI_TIMEOUT = 2.0


def get_current_version() -> str:
    """Get the currently installed version.

    Returns:
        Version string (e.g., "0.1.0")
    """
    try:
        return get_installed_version("sip-videogen")
    except Exception:
        # Fallback to reading from __init__.py
        try:
            from sip_videogen import __version__
            return __version__
        except Exception:
            return "0.0.0"


def get_latest_version() -> str | None:
    """Fetch the latest version from PyPI.

    Returns:
        Latest version string, or None if fetch failed
    """
    try:
        url = f"https://pypi.org/pypi/{PYPI_PACKAGE_NAME}/json"
        response = httpx.get(url, timeout=PYPI_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data["info"]["version"]
    except Exception:
        # Silently fail - don't interrupt the user
        return None


def check_for_update() -> tuple[bool, str | None, str]:
    """Check if a newer version is available.

    Returns:
        Tuple of (update_available, latest_version, current_version)
    """
    current = get_current_version()
    latest = get_latest_version()

    if latest is None:
        return False, None, current

    try:
        current_v = Version(current)
        latest_v = Version(latest)
        update_available = latest_v > current_v
        return update_available, latest, current
    except Exception:
        return False, latest, current


def show_update_banner(latest_version: str, current_version: str) -> None:
    """Display an update available banner.

    Args:
        latest_version: The latest available version
        current_version: The currently installed version
    """
    console.print()
    console.print(Panel(
        f"[bold yellow]Update available![/bold yellow]\n\n"
        f"Current version: [dim]{current_version}[/dim]\n"
        f"Latest version:  [bold green]{latest_version}[/bold green]\n\n"
        f"Run [bold cyan]sipvid update[/bold cyan] to update",
        border_style="yellow",
        title="[bold]New Version[/bold]",
    ))


def run_update() -> bool:
    """Run the update process.

    Attempts to update via pipx, falls back to pip if needed.

    Returns:
        True if update succeeded, False otherwise
    """
    console.print()
    console.print("[bold cyan]Updating sip-videogen...[/bold cyan]")

    # Try pipx first (preferred for CLI tools)
    try:
        result = subprocess.run(
            ["pipx", "upgrade", PYPI_PACKAGE_NAME],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            console.print("[green]Update successful![/green]")
            console.print(result.stdout)
            return True
        # pipx might not be installed or package not installed via pipx
    except FileNotFoundError:
        pass  # pipx not installed
    except subprocess.TimeoutExpired:
        console.print("[yellow]Update timed out.[/yellow]")
        return False

    # Try pip as fallback
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", PYPI_PACKAGE_NAME],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            console.print("[green]Update successful![/green]")
            return True
        else:
            console.print(f"[red]Update failed:[/red] {result.stderr}")
            return False
    except FileNotFoundError:
        console.print("[red]pip not found.[/red]")
        return False
    except subprocess.TimeoutExpired:
        console.print("[yellow]Update timed out.[/yellow]")
        return False


def prompt_for_update(latest_version: str, current_version: str) -> bool:
    """Show update banner and prompt user to update.

    Args:
        latest_version: The latest available version
        current_version: The currently installed version

    Returns:
        True if user chose to update and it succeeded
    """
    import questionary

    show_update_banner(latest_version, current_version)

    update_now = questionary.confirm(
        "Update now?",
        default=False,
    ).ask()

    if update_now:
        success = run_update()
        if success:
            console.print()
            console.print("[bold green]Please restart sipvid to use the new version.[/bold green]")
            return True
        else:
            console.print()
            console.print("[yellow]Update failed. You can try manually:[/yellow]")
            console.print(f"  pipx upgrade {PYPI_PACKAGE_NAME}")
            console.print("  or")
            console.print(f"  pip install --upgrade {PYPI_PACKAGE_NAME}")
            return False

    return False


def check_and_notify() -> None:
    """Check for updates and show banner if available.

    This is the main function to call at startup.
    Non-blocking - will timeout quickly if PyPI is slow.
    """
    update_available, latest, current = check_for_update()

    if update_available and latest:
        show_update_banner(latest, current)
