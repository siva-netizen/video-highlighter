#!/usr/bin/env bash
# Pick host ports not in use (Docker publish + local listeners).
set -euo pipefail

is_free() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    ! lsof -iTCP:"$port" -sTCP:LISTEN -P -n >/dev/null 2>&1
  else
    ! nc -z 127.0.0.1 "$port" >/dev/null 2>&1
  fi
}

pick_from() {
  local chosen=""
  for p in "$@"; do
    if is_free "$p"; then
      chosen="$p"
      break
    fi
  done
  if [[ -z "$chosen" ]]; then
    echo "No free port in candidates: $*" >&2
    exit 1
  fi
  echo "$chosen"
}

# Prefer defaults; fall through if occupied (common dev stack conflicts).
API_PORT="$(pick_from 8800 8000 8001 8080 8888)"
WEB_PORT="$(pick_from 5173 5174 3000 3001 8081)"

export HOST_API_PORT="$API_PORT"
export HOST_WEB_PORT="$WEB_PORT"

echo "HOST_API_PORT=$HOST_API_PORT"
echo "HOST_WEB_PORT=$HOST_WEB_PORT"
