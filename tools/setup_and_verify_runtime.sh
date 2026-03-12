#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/setup_and_verify_runtime_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

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
  cd "$PROJECT_ROOT" || fail "Cannot cd to project root"

  section "ANONYMOUS SETUP AND VERIFY START"
  date
  echo "PROJECT_ROOT=$PROJECT_ROOT"
  echo "LOG_FILE=$LOG_FILE"

  section "[1] PYTHON DISCOVERY"

  detect_python() {
    local candidates=(
      /home/potrzebuje/virtualenv/Projects/anonymous_app/3.11/bin/python
      "${PYTHON_BIN:-}"
      python3.11
      /usr/bin/python3.11
      /bin/python3.11
      /opt/alt/python311/bin/python3.11
      python3.10
      /usr/bin/python3.10
      /bin/python3.10
      python3.9
      /usr/bin/python3.9
      /bin/python3.9
      python3.8
      /usr/bin/python3.8
      /bin/python3.8
      python3
      /usr/bin/python3
      /bin/python3
    )
    local c
    for c in "${candidates[@]}"; do
      [ -n "$c" ] || continue
      if command -v "$c" >/dev/null 2>&1; then
        command -v "$c"
        return 0
      elif [ -x "$c" ]; then
        echo "$c"
        return 0
      fi
    done
    return 1
  }

  PYTHON="$(detect_python || true)"
  [ -n "$PYTHON" ] || fail "No suitable Python found"

  echo "SELECTED_PYTHON=$PYTHON"
  "$PYTHON" --version || fail "Python not runnable"

  "$PYTHON" - <<'PY' || fail "Python too old; require >= 3.8"
import sys
assert sys.version_info >= (3, 8), sys.version
print("PYTHON_VERSION_OK")
print(sys.version.replace("\n"," "))
PY

  section "[2] ENSURE .venv"
  if [ ! -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    "$PYTHON" -m venv "$PROJECT_ROOT/.venv" || fail "Failed to create .venv"
  else
    echo "REUSING_EXISTING_.venv"
  fi

  [ -x "$PROJECT_ROOT/.venv/bin/python" ] || fail ".venv/bin/python missing"
  "$PROJECT_ROOT/.venv/bin/python" --version
  "$PROJECT_ROOT/.venv/bin/pip" --version || fail "pip missing"

  section "[3] INSTALL REQUIREMENTS"
  [ -f "$PROJECT_ROOT/requirements.txt" ] || fail "requirements.txt missing"
  "$PROJECT_ROOT/.venv/bin/pip" install --upgrade pip setuptools wheel || fail "pip bootstrap failed"
  "$PROJECT_ROOT/.venv/bin/pip" install -r "$PROJECT_ROOT/requirements.txt" || fail "requirements install failed"

  section "[4] ENSURE RUNTIME DIRS"
  for d in data storage logs tmp reports; do
    mkdir -p "$PROJECT_ROOT/$d"
    ls -lad "$PROJECT_ROOT/$d"
  done

  section "[5] ENSURE wsgi.py"
  if [ ! -f "$PROJECT_ROOT/wsgi.py" ]; then
    cat > "$PROJECT_ROOT/wsgi.py" <<'PYEOF'
from app.main import create_app

application = create_app()
PYEOF
  fi
  ls -l "$PROJECT_ROOT/wsgi.py"
  sed -n '1,20p' "$PROJECT_ROOT/wsgi.py"

  section "[6] IMPORT TEST"
  (
    cd "$PROJECT_ROOT"
    "$PROJECT_ROOT/.venv/bin/python" - <<'PY'
import wsgi
import app.main as m
app = m.create_app()
print("IMPORT_app.main_OK")
print("CREATE_APP_OK")
print("APP_NAME:", getattr(app, "name", None))
print("IMPORT_wsgi_OK")
print("HAS_APPLICATION:", hasattr(wsgi, "application"))
PY
  ) || fail "Import or create_app failed"

  section "[7] SUMMARY"
  echo "PROJECT_ROOT=$PROJECT_ROOT"
  echo "PYTHON=$PYTHON"
  echo "VENV=$PROJECT_ROOT/.venv"
  echo "LOG_FILE=$LOG_FILE"

  echo
  echo "**********************************"
  echo "FINAL OK"
  echo "LOG_FILE=$LOG_FILE"
  echo "**********************************"

} > "$LOG_FILE" 2>&1

echo "LOG SAVED TO: $LOG_FILE"
tail -n 120 "$LOG_FILE"
