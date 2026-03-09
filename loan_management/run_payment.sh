#!/bin/bash
# Run payment workflow: uses local .venv and runs payment_workflow.py.
# Usage: ./run_payment.sh [csv_file]
# Default CSV: wisr_payment_test.csv (or set PAYMENT_CSV in env).

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

CSV="${1:-}"
if [ -n "$CSV" ]; then
    exec "${VENV_DIR}/bin/python" payment_workflow.py "$CSV"
else
    exec "${VENV_DIR}/bin/python" payment_workflow.py
fi
