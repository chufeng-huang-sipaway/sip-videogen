"""Auto-update system for Brand Studio using GitHub Releases."""

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx
from packaging import version

from sip_videogen.studio import __version__ as current_version_str

# GitHub repository info - update this to match your repo
GITHUB_OWNER = "chufeng-huang-sipaway"
GITHUB_REPO = "sip-videogen"

# Update manifest file name (uploaded to each release)
MANIFEST_FILENAME = "update-manifest.json"


@dataclass
class UpdateInfo:
    """Information about an available update."""

    version: str
    download_url: str
    changelog: str
    release_url: str
    file_size: int  # bytes


@dataclass
class DownloadProgress:
    """Progress information during download."""

    downloaded_bytes: int
    total_bytes: int
    percent: float


def get_current_version() -> str:
    """Get the current app version."""
    return current_version_str


def is_bundled_app() -> bool:
    """Check if running as a bundled macOS .app."""
    # py2app sets sys.frozen
    if getattr(sys, "frozen", False):
        return True
    # Also check if we're in a .app bundle structure
    if ".app/Contents" in __file__:
        return True
    return False


def get_app_path() -> Path | None:
    """Get the path to the running .app bundle, if bundled."""
    if not is_bundled_app():
        return None

    # Find the .app directory by walking up from current file
    current = Path(__file__).resolve()
    for parent in current.parents:
        if parent.suffix == ".app":
            return parent
    return None


async def check_for_updates() -> UpdateInfo | None:
    """Check GitHub Releases for a newer version.

    Returns UpdateInfo if an update is available, None otherwise.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch latest release from GitHub API
            api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
            response = await client.get(
                api_url,
                headers={"Accept": "application/vnd.github.v3+json"},
            )

            if response.status_code == 404:
                # No releases yet
                return None

            response.raise_for_status()
            release = response.json()

            # Extract version from tag (strip 'v' prefix if present)
            tag = release.get("tag_name", "")
            release_version = tag.lstrip("v")

            # Compare versions
            try:
                if version.parse(release_version) <= version.parse(current_version_str):
                    return None  # Already up to date
            except version.InvalidVersion:
                return None

            # Find DMG asset
            dmg_asset = None
            for asset in release.get("assets", []):
                if asset.get("name", "").endswith(".dmg"):
                    dmg_asset = asset
                    break

            if not dmg_asset:
                return None  # No DMG in this release

            return UpdateInfo(
                version=release_version,
                download_url=dmg_asset["browser_download_url"],
                changelog=release.get("body", ""),
                release_url=release.get("html_url", ""),
                file_size=dmg_asset.get("size", 0),
            )

    except Exception as e:
        print(f"[UPDATER] Error checking for updates: {e}")
        return None


async def download_update(
    update_info: UpdateInfo,
    progress_callback: Callable[[DownloadProgress], None] | None = None,
) -> Path | None:
    """Download the update DMG file.

    Args:
        update_info: Information about the update to download.
        progress_callback: Optional callback for progress updates.

    Returns:
        Path to the downloaded DMG file, or None if download failed.
    """
    try:
        # Create temp file for DMG
        temp_dir = Path(tempfile.gettempdir()) / "brand-studio-update"
        temp_dir.mkdir(parents=True, exist_ok=True)
        dmg_path = temp_dir / f"Brand-Studio-{update_info.version}.dmg"

        # Download with progress tracking
        async with httpx.AsyncClient(timeout=600.0, follow_redirects=True) as client:
            async with client.stream("GET", update_info.download_url) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(dmg_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(
                                DownloadProgress(
                                    downloaded_bytes=downloaded,
                                    total_bytes=total_size,
                                    percent=(downloaded / total_size) * 100,
                                )
                            )

        return dmg_path

    except Exception as e:
        print(f"[UPDATER] Error downloading update: {e}")
        return None


def install_update(dmg_path: Path) -> bool:
    """Install the update from a DMG file.

    This mounts the DMG, copies the new app to /Applications,
    and launches a helper script that will:
    1. Wait for this app to quit
    2. Replace the app bundle
    3. Relaunch the new version

    Args:
        dmg_path: Path to the downloaded DMG file.

    Returns:
        True if the update process was started successfully.
    """
    try:
        # Create the update helper script
        helper_script = _create_update_helper_script(dmg_path)

        # Launch the helper script in background
        subprocess.Popen(
            ["/bin/bash", str(helper_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        return True

    except Exception as e:
        print(f"[UPDATER] Error starting update: {e}")
        return False


def _create_update_helper_script(dmg_path: Path) -> Path:
    """Create a shell script that performs the actual update.

    The script runs after the main app quits and:
    1. Mounts the DMG
    2. Copies new app to /Applications
    3. Unmounts the DMG
    4. Relaunches the app
    """
    app_path = get_app_path()
    app_name = app_path.name if app_path else "Brand Studio.app"
    install_path = Path("/Applications") / app_name

    # Fallback if not running from bundle
    if not app_path:
        app_path = install_path

    script_content = f'''#!/bin/bash
# Brand Studio Update Helper
# This script is auto-generated and runs after the app quits

set -e

DMG_PATH="{dmg_path}"
APP_NAME="{app_name}"
INSTALL_PATH="{install_path}"
MOUNT_POINT="/Volumes/Brand Studio"

echo "[UPDATE] Waiting for Brand Studio to quit..."
sleep 2

# Wait for the app to fully quit (max 30 seconds)
for i in {{1..30}}; do
    if ! pgrep -f "Brand Studio" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "[UPDATE] Mounting DMG..."
hdiutil attach "$DMG_PATH" -nobrowse -quiet || exit 1

# Find the .app in the mounted volume
APP_SOURCE=""
for f in "$MOUNT_POINT"/*.app; do
    if [ -d "$f" ]; then
        APP_SOURCE="$f"
        break
    fi
done

if [ -z "$APP_SOURCE" ]; then
    echo "[UPDATE] ERROR: No .app found in DMG"
    hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true
    exit 1
fi

echo "[UPDATE] Installing update..."

# Remove old app if it exists
if [ -d "$INSTALL_PATH" ]; then
    rm -rf "$INSTALL_PATH"
fi

# Copy new app
cp -R "$APP_SOURCE" "$INSTALL_PATH"

echo "[UPDATE] Cleaning up..."
hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true

# Clean up DMG
rm -f "$DMG_PATH"

echo "[UPDATE] Launching updated app..."
open "$INSTALL_PATH"

# Clean up this script
rm -f "$0"
'''

    # Write script to temp location
    script_path = Path(tempfile.gettempdir()) / "brand-studio-update" / "update-helper.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_content)
    os.chmod(script_path, 0o755)

    return script_path


def get_update_settings() -> dict:
    """Get update-related settings from config."""
    from sip_videogen.studio.utils.config_store import _load_config

    config = _load_config()
    return {
        "check_on_startup": config.get("update_check_on_startup", True),
        "last_check": config.get("last_update_check"),
        "skipped_version": config.get("skipped_update_version"),
    }


def save_update_settings(
    check_on_startup: bool | None = None,
    skipped_version: str | None = None,
) -> None:
    """Save update-related settings to config."""
    from sip_videogen.studio.utils.config_store import _load_config, _save_config

    config = _load_config()

    if check_on_startup is not None:
        config["update_check_on_startup"] = check_on_startup

    if skipped_version is not None:
        config["skipped_update_version"] = skipped_version

    _save_config(config)


def mark_update_checked() -> None:
    """Mark that we just checked for updates (for rate limiting)."""
    import time

    from sip_videogen.studio.utils.config_store import _load_config, _save_config

    config = _load_config()
    config["last_update_check"] = int(time.time())
    _save_config(config)


def should_check_for_updates() -> bool:
    """Check if we should check for updates (rate limited to once per day)."""
    import time

    settings = get_update_settings()

    if not settings.get("check_on_startup", True):
        return False

    last_check = settings.get("last_check")
    if last_check:
        # Only check once per day
        seconds_since_check = int(time.time()) - last_check
        if seconds_since_check < 86400:  # 24 hours
            return False

    return True
