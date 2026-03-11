#!/bin/bash
set -euo pipefail

APP_DIR="/home/potrzebuje/Projects/anonymous_app"
LOG="$APP_DIR/sure_runtime_check_$(date +%F_%H%M%S).log"

# Bez /dev/fd/* (u Ciebie to nie działa). Robimy prosty log:
{
  echo "=== SURE RUNTIME CHECK (Anonymous) ==="
  echo "DATE: $(date)"
  echo "APP_DIR: $APP_DIR"
  echo

  echo "1) Detect venv candidates in app dir:"
  ls -d "$APP_DIR"/.venv* 2>/dev/null || echo "No .venv* directories"
  echo

  echo "2) Check which python is used WITHOUT venv:"
  command -v python3 || true
  python3 --version 2>/dev/null || true
  echo

  echo "3) Test imports using each local venv (activate -> import flask -> import wsgi):"
  found_ok=0
  for V in "$APP_DIR"/.venv*; do
    [ -d "$V" ] || continue
    if [ -f "$V/bin/activate" ]; then
      echo "--- Testing venv: $V"
      # shellcheck disable=SC1090
      source "$V/bin/activate"
      echo "python: $(command -v python)"
      python --version
      python -c "import flask; print('OK flask', flask.__version__)" && \
      python -c "import wsgi; print('OK wsgi import'); print('application type:', type(wsgi.application))"
      deactivate
      echo "RESULT: PASS ($V)"
      found_ok=1
      break
    else
      echo "--- $V has no bin/activate -> SKIP"
    fi
  done
  echo

  echo "4) If local venv passed: show which one:"
  if [ "$found_ok" -eq 1 ]; then
    echo "LOCAL_VENV_RESULT: OK"
  else
    echo "LOCAL_VENV_RESULT: NOT OK"
  fi
  echo

  echo "5) cPanel/Passenger logs quick check (if present):"
  echo "--- stderr.log (tail 80) ---"
  tail -80 "$APP_DIR/stderr.log" 2>/dev/null || echo "No stderr.log or cannot read"
  echo

  echo "=============================="
  if [ "$found_ok" -eq 1 ]; then
    echo "FINAL RESULT: OK (code + local venv can import Flask + wsgi.application)"
    echo "NEXT ACTION: Point cPanel Python App to this venv OR reinstall deps in cPanel venv."
  else
    echo "FINAL RESULT: NOT OK"
    echo "WHY: None of local venvs could import Flask and wsgi together."
    echo "FIX: Install requirements into the venv that cPanel uses OR rebuild .venv_prod properly."
  fi
  echo "LOG: $LOG"
  echo "=============================="
} >"$LOG" 2>&1

cat "$LOG"
