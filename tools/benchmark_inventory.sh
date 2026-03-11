#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)/benchmarks/anonymization}"
find "$BASE_DIR" -type f | sort | while read -r f; do
  sha256sum "$f"
done
