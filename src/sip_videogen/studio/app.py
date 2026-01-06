"""PyWebView application setup."""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _patch_pywebview_cocoa_drag() -> None:
    """Work around PyWebView Cocoa bug that breaks HTML drag events."""
    if sys.platform != "darwin":
        return
    try:
        import webview.platforms.cocoa as cocoa
    except Exception:
        return
    try:
        host_cls = cocoa.BrowserView.WebKitHost
        mouse_dragged = getattr(host_cls, "mouseDragged_", None)
        code = getattr(mouse_dragged, "__code__", None)
    except Exception:
        return
    # pywebview 6.1 calls `super(...).mouseDown_(event)` inside `mouseDragged_`, which
    # prevents native WebKit drag handling (HTML5 dragstart/dragover/drop never fire).
    if not code or "mouseDown_" not in code.co_names:
        return

    AppKit = cocoa.AppKit  # noqa: N806
    BrowserView = cocoa.BrowserView  # noqa: N806
    state = cocoa._state

    def mouseDragged_(self, event):  # noqa: N802
        i = BrowserView.get_instance("webview", self)
        window = self.window()
        if i and i.frameless and i.easy_drag:
            screenFrame = i.screen  # noqa: N806
            if screenFrame is None:
                raise RuntimeError("Failed to obtain screen")
            windowFrame = window.frame()  # noqa: N806
            if windowFrame is None:
                raise RuntimeError("Failed to obtain frame")
            currentLocation = window.convertBaseToScreen_(  # noqa: N806
                window.mouseLocationOutsideOfEventStream()
            )
            newOrigin = AppKit.NSMakePoint(  # noqa: N806
                (currentLocation.x - self.initialLocation.x),
                (currentLocation.y - self.initialLocation.y),
            )
            if (newOrigin.y + windowFrame.size.height) > (
                screenFrame.origin.y + screenFrame.size.height
            ):
                newOrigin.y = screenFrame.origin.y + (
                    screenFrame.size.height + windowFrame.size.height
                )
            window.setFrameOrigin_(newOrigin)

        if event.modifierFlags() & getattr(AppKit, "NSEventModifierFlagControl", 1 << 18):
            if not state.get("debug"):
                return

        return super(BrowserView.WebKitHost, self).mouseDragged_(event)

    host_cls.mouseDragged_ = mouseDragged_  # noqa: N802
    logger.info("Patched PyWebView Cocoa drag handler (mouseDragged_)")


def is_dev_mode() -> bool:
    """Check if running in development mode (uses Vite dev server)."""
    return os.environ.get("STUDIO_DEV", "0") == "1"


def is_debug_mode() -> bool:
    """Check if debug mode enabled (right-click dev tools)."""
    return os.environ.get("STUDIO_DEBUG", "0") == "1" or is_dev_mode()


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
    # Set up logging with file output for debugging
    from sip_videogen.config.logging import setup_logging

    log_file = Path.home() / ".sip-videogen" / "studio.log"
    setup_logging(level="INFO", log_file=log_file)
    logging.getLogger("sip_videogen").info(f"=== Brand Studio started, logging to {log_file} ===")
    try:
        import webview
    except ImportError:
        logger.error("pywebview is not installed. Run: pip install pywebview>=5.0")
        sys.exit(1)

    _patch_pywebview_cocoa_drag()

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
    webview.start(debug=is_debug_mode(), http_server=True)


if __name__ == "__main__":
    main()
