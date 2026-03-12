#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo
echo "======================================"
echo "Anonymous automatic setup starting"
echo "======================================"
echo

bash "$SCRIPT_DIR/tools/setup_and_verify_runtime.sh"

echo
echo "======================================"
echo "Setup finished."
echo "If the setup log ends with FINAL OK the system is ready."
echo "======================================"
