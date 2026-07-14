#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -z "${JAVA_HOME:-}" ]]; then
  if [[ "$(uname -s)" == "Darwin" ]] && /usr/libexec/java_home -v 21 >/dev/null 2>&1; then
    export JAVA_HOME="$(/usr/libexec/java_home -v 21)"
  elif command -v java >/dev/null 2>&1; then
    JAVA_BIN="$(command -v java)"
    export JAVA_HOME="$(cd "$(dirname "$JAVA_BIN")/.." && pwd)"
  else
    echo "JDK 21 was not found. Install it or set JAVA_HOME." >&2
    exit 1
  fi
fi

cd "$PROJECT_DIR"
exec ./mvnw spring-boot:run
