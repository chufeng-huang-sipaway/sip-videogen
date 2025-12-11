#!/bin/bash
# Publish sip-videogen to PyPI
#
# Usage:
#   ./scripts/publish.sh         # Publish to PyPI
#   ./scripts/publish.sh test    # Publish to Test PyPI first

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== sip-videogen Publisher ===${NC}"
echo

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: pyproject.toml not found. Run from project root.${NC}"
    exit 1
fi

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf dist/ build/ *.egg-info src/*.egg-info

# Build the package
echo -e "${YELLOW}Building package...${NC}"
python -m build

# Show what was built
echo
echo -e "${GREEN}Built packages:${NC}"
ls -la dist/

# Check the package
echo
echo -e "${YELLOW}Checking package...${NC}"
python -m twine check dist/*

echo

if [ "$1" = "test" ]; then
    # Upload to Test PyPI
    echo -e "${YELLOW}Uploading to Test PyPI...${NC}"
    echo -e "${YELLOW}You'll need your Test PyPI API token.${NC}"
    python -m twine upload --repository testpypi dist/*
    echo
    echo -e "${GREEN}Done! Test install with:${NC}"
    echo "  pip install --index-url https://test.pypi.org/simple/ sip-videogen"
else
    # Upload to PyPI
    echo -e "${YELLOW}Uploading to PyPI...${NC}"
    echo -e "${YELLOW}You'll need your PyPI API token.${NC}"
    python -m twine upload dist/*
    echo
    echo -e "${GREEN}Done! Install with:${NC}"
    echo "  pipx install sip-videogen"
fi
