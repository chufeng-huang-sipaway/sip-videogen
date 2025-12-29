#!/bin/bash
#
# Build and prepare a new Brand Studio release
#
# This script:
#   1. Updates version numbers in all relevant files
#   2. Builds the frontend (React)
#   3. Builds the macOS app (PyInstaller)
#   4. Runs a smoke test to verify the app launches
#   5. Creates the DMG installer
#   6. Validates DMG size to catch bloat
#
# Usage:
#   ./scripts/build-release.sh [version]
#
# Examples:
#   ./scripts/build-release.sh 0.2.0
#   ./scripts/build-release.sh        # Uses current version from studio/__init__.py
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
APP_NAME="Brand Studio"
VENV_DIR="$PROJECT_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PYINSTALLER="$VENV_DIR/bin/pyinstaller"
#DMG size limits (in MB)
DMG_MAX_SIZE_MB=100
DMG_EXPECTED_SIZE_MB=50
#Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
echo_step(){echo -e "${BLUE}==>${NC} $1";}
echo_success(){echo -e "${GREEN}✓${NC} $1";}
echo_warning(){echo -e "${YELLOW}⚠${NC} $1";}
echo_error(){echo -e "${RED}✗${NC} $1";}
#Check prerequisites - MUST use project venv
check_prerequisites(){
    echo_step "Checking prerequisites..."
    local missing=0
    #Check .venv exists
    if [ ! -d "$VENV_DIR" ];then
        echo_error "Virtual environment not found at $VENV_DIR"
        echo "       Run: python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
        missing=1
    fi
    #Check venv Python
    if [ ! -f "$VENV_PYTHON" ];then
        echo_error "Python not found in venv: $VENV_PYTHON"
        missing=1
    fi
    #Check PyInstaller in venv
    if [ ! -f "$VENV_PYINSTALLER" ];then
        echo_error "PyInstaller not found in venv. Run: .venv/bin/pip install pyinstaller"
        missing=1
    fi
    #Check pywebview in venv
    if ! "$VENV_PYTHON" -c "import webview" &>/dev/null;then
        echo_error "pywebview not installed in venv. Run: .venv/bin/pip install pywebview"
        missing=1
    fi
    if ! command -v npm &>/dev/null;then
        echo_error "npm is not installed"
        missing=1
    fi
    if ! command -v hdiutil &>/dev/null;then
        echo_error "hdiutil is not available (macOS only)"
        missing=1
    fi
    if [ $missing -eq 1 ];then exit 1;fi
    echo_success "All prerequisites satisfied"
    echo "       Using Python: $("$VENV_PYTHON" --version)"
    echo "       Using PyInstaller: $("$VENV_PYINSTALLER" --version 2>&1 | head -1)"
}
#Get current version from studio/__init__.py
get_current_version(){
    grep -o '__version__ = "[^"]*"' "$PROJECT_ROOT/src/sip_videogen/studio/__init__.py" | cut -d'"' -f2 || echo "0.1.0"
}
#Update version in all relevant files
update_version(){
    local version="$1"
    echo_step "Updating version to $version..."
    sed -i.bak "s/__version__[[:space:]]*=[[:space:]]*\"[^\"]*\"/__version__ = \"$version\"/" \
        "$PROJECT_ROOT/src/sip_videogen/studio/__init__.py"
    rm -f "$PROJECT_ROOT/src/sip_videogen/studio/__init__.py.bak"
    echo_success "Updated src/sip_videogen/studio/__init__.py"
    sed -i.bak "s/'CFBundleVersion': '[^']*'/'CFBundleVersion': '$version'/" "$PROJECT_ROOT/BrandStudio.spec"
    sed -i.bak "s/'CFBundleShortVersionString': '[^']*'/'CFBundleShortVersionString': '$version'/" "$PROJECT_ROOT/BrandStudio.spec"
    rm -f "$PROJECT_ROOT/BrandStudio.spec.bak"
    echo_success "Updated BrandStudio.spec"
}
#Build frontend
build_frontend(){
    echo_step "Building frontend..."
    cd "$PROJECT_ROOT/src/sip_videogen/studio/frontend"
    if [ ! -d "node_modules" ];then
        echo "Installing npm dependencies..."
        npm install
    fi
    npm run build
    cd "$PROJECT_ROOT"
    echo_success "Frontend built successfully"
}
#Build macOS app using VENV PyInstaller
build_app(){
    echo_step "Building macOS app with PyInstaller (using .venv)..."
    cd "$PROJECT_ROOT"
    rm -rf dist build
    #CRITICAL: Use venv's pyinstaller to ensure correct dependencies
    "$VENV_PYINSTALLER" BrandStudio.spec --clean --noconfirm
    if [ ! -d "dist/$APP_NAME.app" ];then
        echo_error "Failed to build $APP_NAME.app"
        exit 1
    fi
    echo_success "App built: dist/$APP_NAME.app"
}
#Smoke test - verify app launches without errors
smoke_test(){
    echo_step "Running smoke test..."
    local app_executable="$PROJECT_ROOT/dist/$APP_NAME.app/Contents/MacOS/$APP_NAME"
    if [ ! -f "$app_executable" ];then
        echo_error "App executable not found: $app_executable"
        exit 1
    fi
    #Start app in background and capture output
    local test_log=$(mktemp)
    "$app_executable" >"$test_log" 2>&1 &
    local app_pid=$!
    #Wait a few seconds for app to start
    sleep 5
    #Check if process is still running
    if ! ps -p $app_pid >/dev/null 2>&1;then
        echo_error "App crashed during startup. Log:"
        cat "$test_log"
        rm -f "$test_log"
        exit 1
    fi
    #Check for common error patterns in output
    if grep -q "ModuleNotFoundError\|ImportError\|No module named" "$test_log";then
        echo_error "App has missing dependencies. Log:"
        cat "$test_log"
        kill $app_pid 2>/dev/null || true
        rm -f "$test_log"
        exit 1
    fi
    #Kill the test app
    kill $app_pid 2>/dev/null || true
    rm -f "$test_log"
    echo_success "Smoke test passed - app launches correctly"
}
#Build DMG
build_dmg(){
    local version="$1"
    echo_step "Creating DMG installer..."
    cd "$PROJECT_ROOT"
    rm -rf dist/dmg-staging
    mkdir -p dist/dmg-staging
    cp -R "dist/$APP_NAME.app" dist/dmg-staging/
    ln -s /Applications dist/dmg-staging/Applications
    local dmg_path="dist/Brand-Studio-${version}.dmg"
    hdiutil create -volname "Brand Studio" -srcfolder dist/dmg-staging -ov -format UDZO "$dmg_path"
    rm -rf dist/dmg-staging
    if [ ! -f "$dmg_path" ];then
        echo_error "Failed to create DMG"
        exit 1
    fi
    echo_success "DMG created: $dmg_path"
}
#Validate DMG size to catch bloat
validate_dmg_size(){
    local version="$1"
    local dmg_path="$PROJECT_ROOT/dist/Brand-Studio-${version}.dmg"
    echo_step "Validating DMG size..."
    #Get size in MB
    local size_bytes=$(stat -f%z "$dmg_path" 2>/dev/null || stat --printf="%s" "$dmg_path" 2>/dev/null)
    local size_mb=$((size_bytes/1024/1024))
    if [ $size_mb -gt $DMG_MAX_SIZE_MB ];then
        echo_error "DMG size (${size_mb}MB) exceeds maximum (${DMG_MAX_SIZE_MB}MB)!"
        echo "       This likely indicates bloated dependencies."
        echo "       Expected size: ~${DMG_EXPECTED_SIZE_MB}MB"
        echo ""
        echo "       Common causes:"
        echo "       - Using system Python instead of .venv"
        echo "       - Unnecessary packages installed in .venv"
        echo ""
        echo "       To fix: Ensure you're using .venv/bin/pyinstaller"
        exit 1
    elif [ $size_mb -gt $DMG_EXPECTED_SIZE_MB ];then
        echo_warning "DMG size (${size_mb}MB) is larger than expected (~${DMG_EXPECTED_SIZE_MB}MB)"
        echo "       Consider reviewing bundled dependencies."
    else
        echo_success "DMG size is healthy: ${size_mb}MB"
    fi
}
#Main
main(){
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           Brand Studio Release Builder                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    check_prerequisites
    local current_version=$(get_current_version)
    local version="${1:-$current_version}"
    echo ""
    echo_step "Release version: $version"
    echo ""
    read -p "Continue with version $version? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]];then
        echo "Aborted."
        exit 0
    fi
    echo ""
    update_version "$version"
    build_frontend
    build_app
    smoke_test
    build_dmg "$version"
    validate_dmg_size "$version"
    local dmg_file="Brand-Studio-${version}.dmg"
    local dmg_path="$PROJECT_ROOT/dist/$dmg_file"
    local dmg_size=$(du -h "$dmg_path" | cut -f1)
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    BUILD COMPLETE                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  DMG file: dist/$dmg_file"
    echo "  Size: $dmg_size"
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo "  NEXT STEPS: Create a GitHub Release"
    echo "─────────────────────────────────────────────────────────────"
    echo ""
    echo "  1. Commit the version changes:"
    echo "     git add -A && git commit -m \"Release v$version\""
    echo ""
    echo "  2. Create a git tag:"
    echo "     git tag v$version"
    echo ""
    echo "  3. Push to GitHub:"
    echo "     git push && git push --tags"
    echo ""
    echo "  4. Create a GitHub Release:"
    echo "     gh release create v$version dist/$dmg_file \\"
    echo "       --title \"Brand Studio $version\" \\"
    echo "       --notes \"Release notes here\""
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo ""
}
main "$@"
