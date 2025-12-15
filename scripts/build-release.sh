#!/bin/bash
#
# Build and prepare a new Brand Studio release
#
# This script:
#   1. Updates version numbers in all relevant files
#   2. Builds the frontend (React)
#   3. Builds the macOS app (py2app)
#   4. Creates the DMG installer
#   5. Provides instructions for creating a GitHub Release
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

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${BLUE}==>${NC} $1"
}

echo_success() {
    echo -e "${GREEN}✓${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    echo_step "Checking prerequisites..."

    local missing=0

    if ! command -v python &> /dev/null; then
        echo_error "Python is not installed"
        missing=1
    fi

    if ! command -v npm &> /dev/null; then
        echo_error "npm is not installed"
        missing=1
    fi

    if ! python -c "import py2app" &> /dev/null; then
        echo_error "py2app is not installed. Run: pip install py2app"
        missing=1
    fi

    if ! command -v hdiutil &> /dev/null; then
        echo_error "hdiutil is not available (macOS only)"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        exit 1
    fi

    echo_success "All prerequisites satisfied"
}

# Get current version from studio/__init__.py
get_current_version() {
    grep -oP '__version__\s*=\s*"\K[^"]+' "$PROJECT_ROOT/src/sip_videogen/studio/__init__.py" || echo "0.1.0"
}

# Update version in all relevant files
update_version() {
    local version="$1"
    echo_step "Updating version to $version..."

    # Update studio/__init__.py
    sed -i.bak "s/__version__\s*=\s*\"[^\"]*\"/__version__ = \"$version\"/" \
        "$PROJECT_ROOT/src/sip_videogen/studio/__init__.py"
    rm -f "$PROJECT_ROOT/src/sip_videogen/studio/__init__.py.bak"
    echo_success "Updated src/sip_videogen/studio/__init__.py"

    # Update setup.py (py2app config)
    sed -i.bak "s/CFBundleShortVersionString\": \"[^\"]*\"/CFBundleShortVersionString\": \"$version\"/" \
        "$PROJECT_ROOT/setup.py"
    sed -i.bak "s/CFBundleVersion\": \"[^\"]*\"/CFBundleVersion\": \"$version\"/" \
        "$PROJECT_ROOT/setup.py"
    rm -f "$PROJECT_ROOT/setup.py.bak"
    echo_success "Updated setup.py"

    # Update build-dmg.sh
    sed -i.bak "s/VERSION=\"[^\"]*\"/VERSION=\"$version\"/" \
        "$PROJECT_ROOT/scripts/build-dmg.sh"
    rm -f "$PROJECT_ROOT/scripts/build-dmg.sh.bak"
    echo_success "Updated scripts/build-dmg.sh"
}

# Build frontend
build_frontend() {
    echo_step "Building frontend..."
    cd "$PROJECT_ROOT/src/sip_videogen/studio/frontend"

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi

    # Build
    npm run build
    cd "$PROJECT_ROOT"
    echo_success "Frontend built successfully"
}

# Build macOS app
build_app() {
    echo_step "Building macOS app with py2app..."
    cd "$PROJECT_ROOT"

    # Clean previous build
    rm -rf dist build

    # Build the app
    python setup.py py2app

    if [ ! -d "dist/$APP_NAME.app" ]; then
        echo_error "Failed to build $APP_NAME.app"
        exit 1
    fi

    echo_success "App built: dist/$APP_NAME.app"
}

# Build DMG
build_dmg() {
    local version="$1"
    echo_step "Creating DMG installer..."

    "$SCRIPT_DIR/build-dmg.sh"

    local dmg_path="$PROJECT_ROOT/dist/Brand-Studio-${version}.dmg"
    if [ ! -f "$dmg_path" ]; then
        echo_error "Failed to create DMG"
        exit 1
    fi

    echo_success "DMG created: $dmg_path"
}

# Main
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           Brand Studio Release Builder                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    check_prerequisites

    # Get version
    local current_version=$(get_current_version)
    local version="${1:-$current_version}"

    echo ""
    echo_step "Release version: $version"
    echo ""

    # Confirm
    read -p "Continue with version $version? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi

    echo ""

    # Update version
    update_version "$version"

    # Build
    build_frontend
    build_app
    build_dmg "$version"

    # Final instructions
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
    echo "     - Go to: https://github.com/chufeng-huang-sipaway/sip-videogen/releases/new"
    echo "     - Select tag: v$version"
    echo "     - Title: Brand Studio v$version"
    echo "     - Upload: dist/$dmg_file"
    echo "     - Add release notes"
    echo "     - Publish release"
    echo ""
    echo "  Or use GitHub CLI:"
    echo "     gh release create v$version dist/$dmg_file \\"
    echo "       --title \"Brand Studio v$version\" \\"
    echo "       --notes \"Release notes here\""
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo ""
    echo "  Once published, users will see the update notification"
    echo "  when they open Brand Studio!"
    echo ""
}

main "$@"
