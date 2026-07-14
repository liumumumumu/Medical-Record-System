#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${MONGODB_PORT:-27017}"
DB_PATH="${MONGODB_DATA_DIR:-$PROJECT_DIR/data/mongodb}"
LOG_PATH="${MONGODB_LOG_PATH:-$PROJECT_DIR/data/logs/mongodb.log}"

if [[ -n "${MONGOD_BIN:-}" && -x "$MONGOD_BIN" ]]; then
  MONGOD="$MONGOD_BIN"
elif command -v mongod >/dev/null 2>&1; then
  MONGOD="$(command -v mongod)"
else
  echo "MongoDB was not found. Install MongoDB Community or set MONGOD_BIN." >&2
  exit 1
fi

mkdir -p "$DB_PATH" "$(dirname "$LOG_PATH")"

if command -v nc >/dev/null 2>&1 && nc -z 127.0.0.1 "$PORT" >/dev/null 2>&1; then
  echo "MongoDB is already available at mongodb://127.0.0.1:$PORT"
  exit 0
fi

if "$MONGOD" --dbpath "$DB_PATH" --bind_ip 127.0.0.1 --port "$PORT" \
  --logpath "$LOG_PATH" --fork; then
  echo "MongoDB started at mongodb://127.0.0.1:$PORT"
else
  if grep -q "Address already in use" "$LOG_PATH" 2>/dev/null; then
    echo "MongoDB port $PORT is already in use; continuing with the existing service."
  else
    echo "MongoDB failed to start. See $LOG_PATH" >&2
    exit 1
  fi
fi
