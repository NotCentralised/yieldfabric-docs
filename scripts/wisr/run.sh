#!/bin/bash
# Self-contained runner: use a local .venv in this folder and run Python scripts.
# Usage: ./run.sh [script.py] [args...]
# Default script: issue_workflow.py

set -e
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

VENV_DIR="${SCRIPT_DIR}/.venv"
REQUIREMENTS="${SCRIPT_DIR}/requirements.txt"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at ${VENV_DIR}..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing dependencies from requirements.txt..."
"${VENV_DIR}/bin/pip" install -q -r "$REQUIREMENTS"

SCRIPT="${1:-issue_workflow.py}"
shift 2>/dev/null || true
exec "${VENV_DIR}/bin/python" "$SCRIPT" "$@"
