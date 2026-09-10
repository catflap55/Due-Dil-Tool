#!/bin/bash
# Right-click this file in Finder -> Open. You do not need to type commands.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

export PATH="/usr/local/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:${HOME}/.local/bin:${PATH}"

pause() {
  echo ""
  echo "Press Return to close this window."
  read -r _
}

fail() {
  echo ""
  echo "$1"
  echo ""
  pause
  exit 1
}

PY=""
if command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  fail "Python is not installed. Open https://www.python.org/downloads/ , install it (keep the defaults), then open this file again."
fi

if curl -sf --max-time 1 "http://127.0.0.1:8765/" >/dev/null 2>&1 \
  || curl -sf --max-time 1 "http://localhost:8765/" >/dev/null 2>&1; then
  fail "Port 8765 is already in use. Right-click Stop.command, then Open, then start again."
fi

echo "Leave this window open. The first start can take a few minutes while packages install."
echo ""

if [ ! -d .venv ]; then
  echo "Creating a local Python environment..."
  "$PY" -m venv .venv || fail "Could not create a Python environment. Install Python from python.org."
fi
# shellcheck disable=SC1091
source .venv/bin/activate || fail "Could not start the Python environment."
python -m pip install -q -r requirements.txt || fail "Could not install Python packages."

python -m app &
DEV_PID=$!

ready=0
i=0
while [ "$i" -lt 180 ]; do
  if ! kill -0 "$DEV_PID" 2>/dev/null; then
    fail "The app stopped before it was ready. Scroll up in this window for the error."
  fi
  if curl -sf "http://127.0.0.1:8765/" >/dev/null 2>&1; then
    ready=1
    break
  fi
  if curl -sf "http://localhost:8765/" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
  i=$((i + 1))
done

if [ "$ready" -ne 1 ] || ! kill -0 "$DEV_PID" 2>/dev/null; then
  kill "$DEV_PID" 2>/dev/null || true
  fail "The app did not become ready in time. Keep this window open and read the lines above."
fi

echo "Ready. Opening the workstation."
echo "If the page fails, try http://localhost:8765 then http://127.0.0.1:8765 (same app)."
open "http://localhost:8765/" 2>/dev/null || open "http://127.0.0.1:8765/"

if [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${CI:-}" ]; then
  exit 0
fi

wait "$DEV_PID"
echo "Stopped."
pause
