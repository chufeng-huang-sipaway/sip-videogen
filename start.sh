#!/bin/bash
# sip-videogen startup script

cd "$(dirname "$0")"

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Activate virtual environment
source .venv/bin/activate

# Run the CLI
sip-videogen "$@"
