"""
py2app setup script for Sip Studio.
Usage:
    # First, build the frontend:
    cd src/sip_studio/studio/frontend && npm run build
    # Then build the .app bundle:
    python setup.py py2app
    # Development alias build (faster, uses symlinks):
    python setup.py py2app --alias
    # The app will be in dist/Sip Studio.app
    open "dist/Sip Studio.app"
Notes:
- This script temporarily moves pyproject.toml to avoid setuptools conflicts
- Use --alias for development builds (faster, but requires Python env)
- Full builds may require additional configuration for production deployment
"""
import os,sys
try:import py2app
except ImportError:print("Error: py2app is not installed. Install it with:\n  pip install py2app");sys.exit(1)
_pyproject_path=os.path.join(os.path.dirname(__file__),"pyproject.toml")
_pyproject_backup=_pyproject_path+".bak"
_moved_pyproject=False
if os.path.exists(_pyproject_path) and "py2app" in sys.argv:
    os.rename(_pyproject_path,_pyproject_backup);_moved_pyproject=True
try:
    from setuptools import setup
    APP=["src/sip_studio/studio/app.py"]
    DATA_FILES=[]
    OPTIONS={
        "argv_emulation":False,"packages":["sip_studio","webview"],
        "resources":["src/sip_studio/studio/frontend/dist"],
        "plist":{
            "CFBundleName":"Sip Studio","CFBundleDisplayName":"Sip Studio",
            "CFBundleIdentifier":"com.sip.sipstudio",
            "CFBundleShortVersionString":"0.9.0","CFBundleVersion":"0.9.0",
            "NSHighResolutionCapable":True,"NSRequiresAquaSystemAppearance":False,
        },
        "excludes":["test","tests","unittest","setuptools._vendor"],
    }
    setup(name="Sip Studio",app=APP,data_files=DATA_FILES,options={"py2app":OPTIONS},setup_requires=["py2app"],)
finally:
    if _moved_pyproject and os.path.exists(_pyproject_backup):os.rename(_pyproject_backup,_pyproject_path)
