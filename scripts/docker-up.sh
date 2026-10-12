#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon not running. Start Docker Desktop, then retry." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example and set GROQ_API_KEY." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/scripts/pick-docker-ports.sh"

echo "Building and starting (API → localhost:${HOST_API_PORT}, UI → http://localhost:${HOST_WEB_PORT})"
HOST_API_PORT="$HOST_API_PORT" HOST_WEB_PORT="$HOST_WEB_PORT" docker compose up --build -d

echo ""
docker compose ps
echo ""
echo "Open: http://localhost:${HOST_WEB_PORT}"
