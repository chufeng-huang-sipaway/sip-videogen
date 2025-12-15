#!/bin/bash
#
# Brand Studio Installer
#
# One-line installation:
#   curl -sSL https://raw.githubusercontent.com/chufeng-huang-sipaway/sip-videogen/main/scripts/install-brand-studio.sh | bash
#
# Or download and run:
#   curl -sSLO https://raw.githubusercontent.com/chufeng-huang-sipaway/sip-videogen/main/scripts/install-brand-studio.sh
#   chmod +x install-brand-studio.sh
#   ./install-brand-studio.sh
#

set -e

# Configuration
GITHUB_OWNER="chufeng-huang-sipaway"
GITHUB_REPO="sip-videogen"
APP_NAME="Brand Studio"
INSTALL_DIR="/Applications"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Check if running on macOS
check_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        echo_error "This installer is for macOS only."
        exit 1
    fi
}

# Get latest release info from GitHub API
get_latest_release() {
    echo_step "Fetching latest release info..."

    local api_url="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest"
    local release_info

    release_info=$(curl -sSL "$api_url")

    if [[ -z "$release_info" ]] || echo "$release_info" | grep -q "Not Found"; then
        echo_error "No releases found. Please check if releases exist on GitHub."
        exit 1
    fi

    # Extract version (tag name without 'v' prefix)
    VERSION=$(echo "$release_info" | grep -o '"tag_name": *"[^"]*"' | cut -d'"' -f4 | sed 's/^v//')

    # Extract DMG download URL
    DOWNLOAD_URL=$(echo "$release_info" | grep -o '"browser_download_url": *"[^"]*\.dmg"' | head -1 | cut -d'"' -f4)

    if [[ -z "$DOWNLOAD_URL" ]]; then
        echo_error "No DMG file found in the latest release."
        exit 1
    fi

    echo_success "Found version: $VERSION"
}

# Download the DMG
download_dmg() {
    echo_step "Downloading Brand Studio $VERSION..."

    TEMP_DIR=$(mktemp -d)
    DMG_PATH="$TEMP_DIR/Brand-Studio.dmg"

    curl -sSL -o "$DMG_PATH" "$DOWNLOAD_URL"

    if [[ ! -f "$DMG_PATH" ]]; then
        echo_error "Download failed."
        exit 1
    fi

    echo_success "Downloaded successfully"
}

# Install the app
install_app() {
    echo_step "Installing to $INSTALL_DIR..."

    # Mount the DMG
    MOUNT_POINT=$(hdiutil attach "$DMG_PATH" -nobrowse -quiet | grep "/Volumes" | awk '{print $NF}')

    if [[ -z "$MOUNT_POINT" ]]; then
        echo_error "Failed to mount DMG."
        exit 1
    fi

    # Find the .app in the mounted volume
    APP_SOURCE=""
    for f in "$MOUNT_POINT"/*.app; do
        if [[ -d "$f" ]]; then
            APP_SOURCE="$f"
            break
        fi
    done

    if [[ -z "$APP_SOURCE" ]]; then
        echo_error "No .app found in DMG."
        hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true
        exit 1
    fi

    # Remove existing installation
    if [[ -d "$INSTALL_DIR/$APP_NAME.app" ]]; then
        echo_warning "Removing existing installation..."
        rm -rf "$INSTALL_DIR/$APP_NAME.app"
    fi

    # Copy to Applications
    cp -R "$APP_SOURCE" "$INSTALL_DIR/"

    # Unmount and cleanup
    hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true
    rm -rf "$TEMP_DIR"

    echo_success "Installed to $INSTALL_DIR/$APP_NAME.app"
}

# Remove quarantine attribute (for apps downloaded outside App Store)
remove_quarantine() {
    echo_step "Removing quarantine attribute..."
    xattr -rd com.apple.quarantine "$INSTALL_DIR/$APP_NAME.app" 2>/dev/null || true
    echo_success "Quarantine attribute removed"
}

# Main
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           Brand Studio Installer                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    check_macos
    get_latest_release
    download_dmg
    install_app
    remove_quarantine

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║               INSTALLATION COMPLETE                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Brand Studio $VERSION has been installed!"
    echo ""
    echo "  To launch:"
    echo "    - Open Finder → Applications → Brand Studio"
    echo "    - Or run: open -a \"Brand Studio\""
    echo ""
    echo "  First time setup:"
    echo "    1. Open the app"
    echo "    2. Enter your API keys (OpenAI, Gemini)"
    echo "    3. Create or select a brand"
    echo ""
    echo "  The app will automatically check for updates."
    echo ""
}

main "$@"
