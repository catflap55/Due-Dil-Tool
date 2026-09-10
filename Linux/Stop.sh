#!/bin/bash
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

echo "Stopping Due Diligence Workstation..."
pids=$(lsof -ti tcp:8765 2>/dev/null || fuser -n tcp 8765 2>/dev/null || true)
if [ -n "$pids" ]; then
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  echo "Stopped what was using port 8765."
else
  echo "Nothing was using port 8765."
fi
echo "Done."
