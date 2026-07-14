#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_DIR="$(cd "$PROJECT_DIR/../.." && pwd)"

"$PROJECT_DIR/scripts/start-mongodb.sh"

export AI_MODE="${AI_MODE:-remote}"
export AI_BASE_URL="${AI_BASE_URL:-http://127.0.0.1:5000}"
export JWT_SECRET="${JWT_SECRET:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')}"
export DEMO_USER_ENABLED="${DEMO_USER_ENABLED:-false}"

cleanup() {
  kill "${FRONTEND_PID:-}" "${BACKEND_PID:-}" "${AI_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd "$ROOT_DIR/代码文件/ai-service" && python3 app.py) &
AI_PID=$!
(cd "$PROJECT_DIR" && "$PROJECT_DIR/scripts/run-backend.sh") &
BACKEND_PID=$!
(cd "$ROOT_DIR/代码文件/frontend/frontend" && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort) &
FRONTEND_PID=$!

echo "Full stack started at http://127.0.0.1:5173"
wait "$FRONTEND_PID"
