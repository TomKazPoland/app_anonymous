#!/bin/bash
set -u

LOG="$HOME/entrypoint_finder_$(date +%F_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

echo "=== ENTRYPOINT FINDER (SURE) ==="
echo "DATE: $(date)"
echo "PWD: $(pwd)"
echo

FOUND=0

echo "1) Top-level listing (interesting files):"
ls -la | egrep -i 'wsgi|passenger|asgi|app\.py|main\.py|run|manage|gunicorn|uwsgi|nginx|apache|htaccess|env' || true
echo

echo "2) Find candidate files (maxdepth 6):"
find . -maxdepth 6 -type f \( \
  -iname '*wsgi*.py' -o -iname '*passenger*.py' -o -iname '*asgi*.py' -o \
  -iname 'app.py' -o -iname 'main.py' -o -iname 'run.py' -o -iname 'manage.py' -o \
  -iname '.htaccess' -o -iname 'Procfile' -o -iname 'gunicorn.conf.py' -o -iname '*.ini' \
\) -print | sed 's|^\./||'
echo

echo "3) Search for WSGI callable patterns:"
grep -RIn --exclude-dir=.git -E '^\s*application\s*=|create_app\s*\(|Flask\s*\(|passenger_wsgi|WSGI_APPLICATION' . | head -300
echo

echo "4) Check .gitignore for ignored entrypoints:"
if [ -f .gitignore ]; then
  echo "--- .gitignore (relevant lines) ---"
  egrep -n 'wsgi|passenger|\.env|venv|\.venv|__pycache__' .gitignore || echo "(no relevant lines)"
else
  echo "No .gitignore"
fi
echo

echo "5) Check if repository contains generated artifacts that should NOT be there:"
ls -la | egrep -i '\.venv|venv|__pycache__|\.pyc|\.log' || true
echo

echo "6) Decision logic: does repo already have a real WSGI entrypoint?"
# We consider it FOUND if any file contains 'application =' or 'passenger_wsgi.py' exists AND contains application callable
CAND_FILES=$(find . -maxdepth 6 -type f \( -iname 'wsgi.py' -o -iname 'passenger_wsgi.py' -o -iname '*wsgi*.py' \) 2>/dev/null || true)

for f in $CAND_FILES; do
  if grep -qE '^\s*application\s*=' "$f"; then
    echo "FOUND: WSGI callable in: $f"
    FOUND=1
  fi
done

if [ "$FOUND" -eq 1 ]; then
  echo
  echo "=============================="
  echo "FINAL RESULT: FOUND"
  echo "Repo already contains a usable WSGI entrypoint."
  echo "Next: point Passenger/cPanel to that file."
  echo "=============================="
else
  echo
  echo "=============================="
  echo "FINAL RESULT: NOT FOUND"
  echo "Repo does NOT contain a usable WSGI entrypoint (application=...)."
  echo "Meaning: previous hosting likely had manual config OR file was never committed."
  echo "Next: add wsgi.py to repo (one-time fix)."
  echo "=============================="
fi

echo
echo "LOG: $LOG"
