"""PyWebView application setup."""

import os
import sys
from pathlib import Path


def is_dev_mode() -> bool:
    """Check if running in development mode."""
    return os.environ.get("STUDIO_DEV", "0") == "1"


def is_bundled_app() -> bool:
    """Check if running as a py2app-bundled .app."""
    # py2app sets __file__ to be inside the .app bundle
    # The bundle structure is: .app/Contents/Resources/
    return getattr(sys, "frozen", False) or ".app/Contents" in __file__


def get_frontend_url() -> str:
    """Get the frontend URL based on mode."""
    if is_dev_mode():
        return "http://localhost:5173"

    # Check for py2app bundle (resources in .app/Contents/Resources/dist/)
    if is_bundled_app():
        # Find the Resources directory in the bundle
        # __file__ is typically: .app/Contents/Resources/lib/python3.x/sip_videogen/studio/app.py
        app_path = Path(__file__)
        # Walk up to find Resources directory
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
        print("ERROR: Frontend not built.")
        print("Run: cd src/sip_videogen/studio/frontend && npm run build")
        sys.exit(1)
    return str(dist_path)


def main():
    """Launch the Brand Studio application."""
    try:
        import webview
    except ImportError:
        print("ERROR: pywebview is not installed.")
        print("Run: pip install pywebview>=5.0")
        sys.exit(1)

    from .bridge import StudioBridge

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

    api._window = window
    webview.start(debug=is_dev_mode())


if __name__ == "__main__":
    main()
