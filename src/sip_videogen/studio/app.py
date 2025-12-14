"""PyWebView application setup."""

import os
import sys
from pathlib import Path


def is_dev_mode() -> bool:
    """Check if running in development mode."""
    return os.environ.get("STUDIO_DEV", "0") == "1"


def get_frontend_url() -> str:
    """Get the frontend URL based on mode."""
    studio_dir = Path(__file__).parent
    if is_dev_mode():
        return "http://localhost:5173"
    else:
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
