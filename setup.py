"""
py2app setup script for Brand Studio.

Usage:
    # First, build the frontend:
    cd src/sip_videogen/studio/frontend && npm run build

    # Then build the .app bundle:
    python setup.py py2app

    # Development alias build (faster, uses symlinks):
    python setup.py py2app --alias

    # The app will be in dist/Brand Studio.app
    open "dist/Brand Studio.app"

Notes:
- This script temporarily moves pyproject.toml to avoid setuptools conflicts
- Use --alias for development builds (faster, but requires Python env)
- Full builds may require additional configuration for production deployment
"""

import os
import sys

# Ensure py2app is available
try:
    import py2app  # noqa: F401
except ImportError:
    print("Error: py2app is not installed. Install it with:")
    print("  pip install py2app")
    sys.exit(1)

# Move pyproject.toml temporarily to avoid setuptools conflicts
_pyproject_path = os.path.join(os.path.dirname(__file__), "pyproject.toml")
_pyproject_backup = _pyproject_path + ".bak"
_moved_pyproject = False

if os.path.exists(_pyproject_path) and "py2app" in sys.argv:
    os.rename(_pyproject_path, _pyproject_backup)
    _moved_pyproject = True

try:
    from setuptools import setup

    APP = ["src/sip_videogen/studio/app.py"]
    DATA_FILES = []
    OPTIONS = {
        "argv_emulation": False,
        "packages": ["sip_videogen", "webview"],
        # Bundle the built frontend
        "resources": ["src/sip_videogen/studio/frontend/dist"],
        "plist": {
            "CFBundleName": "Brand Studio",
            "CFBundleDisplayName": "Brand Studio",
            "CFBundleIdentifier": "com.sip.brandstudio",
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
        },
        # Exclude packages that cause issues with py2app
        "excludes": [
            "test",
            "tests",
            "unittest",
            "setuptools._vendor",  # Avoid vendored package conflicts
        ],
    }

    setup(
        name="Brand Studio",
        app=APP,
        data_files=DATA_FILES,
        options={"py2app": OPTIONS},
        setup_requires=["py2app"],
    )
finally:
    # Restore pyproject.toml
    if _moved_pyproject and os.path.exists(_pyproject_backup):
        os.rename(_pyproject_backup, _pyproject_path)
