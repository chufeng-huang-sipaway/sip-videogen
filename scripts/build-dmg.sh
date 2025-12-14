#!/bin/bash
# Build DMG installer for Brand Studio
#
# Prerequisites:
#   - Build the .app first: python setup.py py2app (or py2app --alias for dev)
#
# Usage:
#   ./scripts/build-dmg.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
APP_NAME="Brand Studio"
VERSION="0.1.0"
DMG_NAME="Brand-Studio-${VERSION}.dmg"
APP_PATH="$PROJECT_ROOT/dist/$APP_NAME.app"
DMG_PATH="$PROJECT_ROOT/dist/$DMG_NAME"
TEMP_DMG="$PROJECT_ROOT/dist/temp.dmg"
MOUNT_POINT="/Volumes/$APP_NAME"

# Check if the .app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found."
    echo "Please build the app first:"
    echo "  cd $PROJECT_ROOT"
    echo "  cd src/sip_videogen/studio/frontend && npm run build && cd -"
    echo "  python setup.py py2app"
    exit 1
fi

# Remove existing DMG if present
if [ -f "$DMG_PATH" ]; then
    echo "Removing existing DMG..."
    rm -f "$DMG_PATH"
fi
rm -f "$TEMP_DMG"

# Unmount if already mounted
if [ -d "$MOUNT_POINT" ]; then
    echo "Unmounting existing volume..."
    hdiutil detach "$MOUNT_POINT" -force 2>/dev/null || true
fi

echo "Creating DMG installer using hdiutil..."

# Calculate size (app size + 20MB buffer)
APP_SIZE_KB=$(du -sk "$APP_PATH" | cut -f1)
DMG_SIZE_KB=$((APP_SIZE_KB + 20480))
echo "App size: ${APP_SIZE_KB}KB, DMG size: ${DMG_SIZE_KB}KB"

# Create a temporary read-write DMG
hdiutil create -size "${DMG_SIZE_KB}k" -fs HFS+ -volname "$APP_NAME" "$TEMP_DMG"

# Mount the temporary DMG
hdiutil attach "$TEMP_DMG" -mountpoint "$MOUNT_POINT"

# Copy the app to the DMG
echo "Copying app to DMG..."
cp -R "$APP_PATH" "$MOUNT_POINT/"

# Create Applications symlink for drag-and-drop install
ln -s /Applications "$MOUNT_POINT/Applications"

# Unmount
echo "Finalizing DMG..."
hdiutil detach "$MOUNT_POINT"

# Convert to compressed read-only DMG
hdiutil convert "$TEMP_DMG" -format UDZO -o "$DMG_PATH"

# Clean up temp DMG
rm -f "$TEMP_DMG"

echo ""
echo "DMG created successfully: $DMG_PATH"
echo ""
echo "To test on a clean machine/VM:"
echo "  1. Copy $DMG_NAME to the test machine"
echo "  2. Double-click to mount"
echo "  3. Drag Brand Studio to Applications"
echo "  4. Open from Applications folder"
