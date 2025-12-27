"""PyWebView application setup."""
import logging
import os
import sys
from pathlib import Path

logger=logging.getLogger(__name__)


def is_dev_mode() -> bool:
    """Check if running in development mode."""
    return os.environ.get("STUDIO_DEV", "0") == "1"


def is_bundled_app() -> bool:
    """Check if running as a bundled .app (py2app or PyInstaller)."""
    # Both py2app and PyInstaller set sys.frozen
    return getattr(sys, "frozen", False) or ".app/Contents" in __file__


def get_bundle_dir() -> Path:
    """Get the directory where bundled resources are located."""
    if getattr(sys, "frozen", False):
        # PyInstaller: resources are in _MEIPASS (onefile) or Resources folder (macOS bundle)
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        # PyInstaller macOS bundle: resources in .app/Contents/Resources/
        exe_path = Path(sys.executable)
        # Check if we're in a .app bundle (exe is in MacOS folder)
        if exe_path.parent.name == "MacOS":
            resources_path = exe_path.parent.parent / "Resources"
            if resources_path.exists():
                return resources_path
        # Fallback: resources near executable
        return exe_path.parent
    return Path(__file__).parent


def get_frontend_url() -> str:
    """Get the frontend URL based on mode."""
    if is_dev_mode():
        return "http://localhost:5173"

    # Check for bundled app (PyInstaller or py2app)
    if is_bundled_app():
        bundle_dir = get_bundle_dir()

        # PyInstaller: look in frontend/dist/ relative to bundle
        dist_path = bundle_dir / "frontend" / "dist" / "index.html"
        if dist_path.exists():
            return str(dist_path)

        # py2app: look in Resources/dist/
        # __file__ is typically: .app/Contents/Resources/lib/python3.x/sip_videogen/studio/app.py
        app_path = Path(__file__)
        for parent in app_path.parents:
            if parent.name == "Resources":
                dist_path = parent / "dist" / "index.html"
                if dist_path.exists():
                    return str(dist_path)
                break

    # Fallback: look relative to the Python module (development install)
    studio_dir = Path(__file__).parent
    dist_path = studio_dir / "frontend" / "dist" / "index.html"
    if not dist_path.exists():
        logger.error("Frontend not built. Run: npm run build in studio/frontend")
        sys.exit(1)
    return str(dist_path)


def main():
    """Launch the Brand Studio application."""
    try:
        import webview
    except ImportError:
        logger.error("pywebview is not installed. Run: pip install pywebview>=5.0")
        sys.exit(1)

    from sip_videogen.studio.bridge import StudioBridge

    api = StudioBridge()
    frontend = get_frontend_url()

    window = webview.create_window(
        title="Brand Studio",
        url=frontend,
        js_api=api,
        width=1400,
        height=900,
        min_size=(900, 600),
        resizable=True,
        frameless=False,
        text_select=True,
    )

    api.set_window(window)
    webview.start(debug=is_dev_mode(), http_server=True)


if __name__ == "__main__":
    main()
