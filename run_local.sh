#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

export FLASK_ENV=development
export PYTHONPATH="$(pwd)"

python -c "from app.main import create_app; app=create_app(); app.run(host='127.0.0.1', port=8001, debug=True)"
