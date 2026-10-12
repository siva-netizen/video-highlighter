#!/usr/bin/env bash
# Fixed host ports for ReelBite (Docker publish + local dev defaults).
set -euo pipefail

API_PORT=8800
WEB_PORT=5174

is_free() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    ! lsof -iTCP:"$port" -sTCP:LISTEN -P -n >/dev/null 2>&1
  else
    ! nc -z 127.0.0.1 "$port" >/dev/null 2>&1
  fi
}

port_published_by_docker() {
  local port="$1"
  docker ps --format '{{.Ports}}' 2>/dev/null | grep -qE ":${port}->"
}

for port in "$API_PORT" "$WEB_PORT"; do
  if is_free "$port"; then
    continue
  fi
  if port_published_by_docker "$port"; then
    echo "Port $port already used by Docker — will recreate this stack." >&2
    continue
  fi
  echo "Port $port is in use by a non-Docker process. Stop it, then retry." >&2
  exit 1
done

export HOST_API_PORT="$API_PORT"
export HOST_WEB_PORT="$WEB_PORT"

echo "HOST_API_PORT=$HOST_API_PORT"
echo "HOST_WEB_PORT=$HOST_WEB_PORT"
