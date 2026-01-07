#!/bin/bash
# Sip Studio Launcher - Launches the Sip Studio app for testing
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
echo "=== Sip Studio ==="
echo ""
# Launch the app
cd "$PROJECT_DIR"
if [ -f ".venv/bin/python" ]; then
    echo "Starting Sip Studio..."
    echo "(Logs will appear below)"
    echo ""
    .venv/bin/python -m sip_studio.studio
else
    echo "ERROR: Virtual environment not found."
    echo "Run: python -m venv .venv && .venv/bin/pip install -e ."
    exit 1
fi
