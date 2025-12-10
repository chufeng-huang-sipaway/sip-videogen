#!/bin/bash
# sip-videogen - One script to rule them all
# Usage: ./start.sh [command] [args]

set -e
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_step() { echo -e "${GREEN}▶${NC} $1"; }
echo_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
echo_error() { echo -e "${RED}✖${NC} $1"; }

# 1. Check Python version
check_python() {
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
    elif command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if [[ $(echo "$PYTHON_VERSION >= 3.11" | bc -l) -eq 1 ]]; then
            PYTHON_CMD="python3"
        else
            echo_error "Python 3.11+ required (found $PYTHON_VERSION)"
            echo "Install with: brew install python@3.11"
            exit 1
        fi
    else
        echo_error "Python 3 not found"
        echo "Install with: brew install python@3.11"
        exit 1
    fi
}

# 2. Setup virtual environment
setup_venv() {
    if [ ! -d ".venv" ]; then
        echo_step "Creating virtual environment..."
        $PYTHON_CMD -m venv .venv
    fi
    source .venv/bin/activate
}

# 3. Install dependencies
install_deps() {
    # Check if package is installed by looking for the entry point
    if ! .venv/bin/pip show sip-videogen &> /dev/null; then
        echo_step "Installing dependencies (first run)..."
        .venv/bin/pip install --quiet --upgrade pip
        .venv/bin/pip install --quiet -e .
        echo_step "Dependencies installed!"
    fi
}

# 4. Check environment file
check_env() {
    if [ ! -f ".env" ]; then
        echo_warn "No .env file found!"
        echo ""
        echo "Create one by copying the example:"
        echo "  cp .env.example .env"
        echo ""
        echo "Then fill in your API keys in .env"
        echo ""
        exit 1
    fi

    # Load environment variables
    set -a
    source .env
    set +a
}

# Main setup
check_python
setup_venv
install_deps
check_env

# Run the CLI
exec sip-videogen "$@"
