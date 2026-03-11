#!/bin/sh
set -u

REPO_DIR="${REPO_DIR:-/home/potrzebuje/Projects/anonymous_app}"
PYBIN="${PYBIN:-/home/potrzebuje/virtualenv/Projects/anonymous_app/3.11/bin/python}"
TS="$(date +%Y%m%d_%H%M%S 2>/dev/null || echo now)"
OUT_JSON="$REPO_DIR/data/benchmark_report_${TS}.json"

# Try to auto-find benchmark files
IN_FILE=""
OUT_FILE=""

for cand in \
  "$HOME/anonimizacja_test_100_podmiotow.txt" \
  "$HOME/Downloads/anonimizacja_test_100_podmiotow.txt" \
  "$REPO_DIR/data/anonimizacja_test_100_podmiotow.txt" \
  "$REPO_DIR/storage/anonimizacja_test_100_podmiotow.txt"
do
  if [ -f "$cand" ]; then IN_FILE="$cand"; break; fi
done

if [ -z "$IN_FILE" ]; then
  IN_FILE="$(find "$HOME" "$REPO_DIR" -maxdepth 5 -type f -name 'anonimizacja_test_100_podmiotow*.txt' 2>/dev/null | grep -v '__ANON__' | sed -n '1p')"
fi

OUT_FILE="$(find "$REPO_DIR/storage" "$HOME" -maxdepth 8 -type f -name '*__ANON__*anonimizacja_test_100_podmiotow*.txt*' 2>/dev/null | tail -n 1)"

if [ -z "$IN_FILE" ] || [ -z "$OUT_FILE" ]; then
  echo "AUTO_FIND_FAILED"
  echo "IN_FILE=$IN_FILE"
  echo "OUT_FILE=$OUT_FILE"
  echo "MANUAL_RUN:"
  echo "\"$PYBIN\" \"$REPO_DIR/scripts/benchmark_anonymization.py\" /absolute/input.txt /absolute/output.txt \"$OUT_JSON\""
  exit 2
fi

echo "AUTO_INPUT=$IN_FILE"
echo "AUTO_OUTPUT=$OUT_FILE"
exec "$PYBIN" "$REPO_DIR/scripts/benchmark_anonymization.py" "$IN_FILE" "$OUT_FILE" "$OUT_JSON"
