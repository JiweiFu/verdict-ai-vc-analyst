#!/usr/bin/env bash
# One-command launcher for Verdict (backend + frontend, dev mode).
#
# Prereqs (run once):
#   cd backend  && uv sync
#   cd frontend && npm install
#
# Your real LLM API key is entered in the app's Settings page (bring-your-own-
# key); it stays in your browser's localStorage and never touches this repo.
# The placeholder key below only lets the backend boot.

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "▶ Freeing ports 5001 / 5173 ..."
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

echo "▶ Starting backend  → http://127.0.0.1:5001"
cd "$ROOT/backend"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-placeholder-for-boot}" \
  uv run uvicorn app.main:app --host 127.0.0.1 --port 5001 &
BACKEND_PID=$!

cleanup() {
  echo ""
  echo "▶ Stopping backend (pid $BACKEND_PID) ..."
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "▶ Starting frontend → http://localhost:5173   (open this in your browser)"
echo "  (Ctrl+C stops both)"
cd "$ROOT/frontend"
npm run dev:web
