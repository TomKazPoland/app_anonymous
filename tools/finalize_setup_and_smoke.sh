#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/home/potrzebuje/Projects/anonymous_app"
LOG_DIR="$ROOT/logs"
TMP_DIR="$ROOT/tmp"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/finalize_setup_and_smoke_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR" "$TMP_DIR"

fail() {
  echo
  echo "**********************************"
  echo "FINAL FAIL: $*"
  echo "LOG_FILE=$LOG_FILE"
  echo "**********************************"
  exit 1
}

section() {
  echo
  echo "**********************************"
  echo "$*"
  echo "**********************************"
}

trap 'echo; echo "ERROR near line $LINENO"; echo "LOG_FILE=$LOG_FILE"' ERR

{
  cd "$ROOT" || fail "Cannot cd to $ROOT"

  section "FINALIZE SETUP AND SMOKE START"
  date
  echo "ROOT=$ROOT"
  echo "LOG_FILE=$LOG_FILE"

  section "[1] RUN install.sh"
  [ -x "$ROOT/install.sh" ] || fail "install.sh missing or not executable"
  bash "$ROOT/install.sh" || fail "install.sh failed"

  section "[2] FLASK TEST_CLIENT SMOKE TEST"
  SMOKE_INPUT="$TMP_DIR/smoke_input_${TIMESTAMP}.txt"
  cat > "$SMOKE_INPUT" <<'TXT'
Jan Kowalski
PESEL: 85010112345
Telefon: 600 700 800
Email: jan.kowalski@example.com
Rachunek: PL61109010140000071219812874
TXT

  "$ROOT/.venv/bin/python" - <<'PY'
import io
from pathlib import Path
from app.main import create_app

root = Path("/home/potrzebuje/Projects/anonymous_app")
tmp = root / "tmp"

inputs = sorted(tmp.glob("smoke_input_*.txt"))
assert inputs, "No smoke input file found"
smoke_input = inputs[-1]

encoded_out = tmp / smoke_input.name.replace("input", "encoded")
decoded_out = tmp / smoke_input.name.replace("input", "decoded")

app = create_app()
client = app.test_client()

raw = smoke_input.read_bytes()

resp = client.post(
    "/encode",
    data={"file": (io.BytesIO(raw), smoke_input.name)},
    content_type="multipart/form-data",
)
print("ENCODE_STATUS:", resp.status_code)
assert resp.status_code == 200, f"Encode failed: {resp.status_code}"
encoded_out.write_bytes(resp.data)
print("ENCODED_FILE:", encoded_out)

resp2 = client.post(
    "/decode",
    data={"file": (io.BytesIO(resp.data), encoded_out.name)},
    content_type="multipart/form-data",
)
print("DECODE_STATUS:", resp2.status_code)
assert resp2.status_code == 200, f"Decode failed: {resp2.status_code}"
decoded_out.write_bytes(resp2.data)
print("DECODED_FILE:", decoded_out)

orig = smoke_input.read_text(encoding="utf-8")
encoded = encoded_out.read_text(encoding="utf-8")
decoded = decoded_out.read_text(encoding="utf-8")

assert "## ANON_JOB:" in encoded, "Missing ANON_JOB header"
assert "jan.kowalski@example.com" not in encoded, "Email leaked in encoded output"
assert orig.strip() in decoded, "Decoded content does not contain original payload"

print("SMOKE_COMPARE_OK")
PY

  echo "--- SMOKE INPUT ---"
  sed -n '1,40p' "$SMOKE_INPUT"
  echo "--- SMOKE ENCODED PREVIEW ---"
  ENCODED_LAST="$(ls -1t "$TMP_DIR"/smoke_encoded_*.txt 2>/dev/null | head -n 1 || true)"
  [ -n "$ENCODED_LAST" ] && sed -n '1,40p' "$ENCODED_LAST" || true
  echo "--- SMOKE DECODED PREVIEW ---"
  DECODED_LAST="$(ls -1t "$TMP_DIR"/smoke_decoded_*.txt 2>/dev/null | head -n 1 || true)"
  [ -n "$DECODED_LAST" ] && sed -n '1,40p' "$DECODED_LAST" || true

  section "[3] OPTIONAL HTTP CHECK"
  curl -I -L --max-time 20 https://potrzebuje.pl/apps/anonymous/ || fail "HTTP check failed"

  section "[4] GIT STATUS"
  if [ -d "$ROOT/.git" ]; then
    git -C "$ROOT" status --short || true
    git -C "$ROOT" branch --show-current || true
    git -C "$ROOT" rev-parse --short HEAD || true
  fi

  section "FINALIZE SETUP AND SMOKE END"
  date
  echo
  echo "**********************************"
  echo "FINAL OK"
  echo "LOG_FILE=$LOG_FILE"
  echo "**********************************"

} > "$LOG_FILE" 2>&1

echo
echo "LOG SAVED TO: $LOG_FILE"
echo "**********************************"
tail -n 160 "$LOG_FILE"
echo "**********************************"
