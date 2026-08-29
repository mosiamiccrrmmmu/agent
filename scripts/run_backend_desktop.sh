#!/usr/bin/env bash
# Dev helper: run backend in desktop mode (Linux/macOS CI or local).
set -euo pipefail
cd "$(dirname "$0")/.."
export APP_ENV=desktop
export DESKTOP_MODE=true
export HOST=127.0.0.1
export PORT=8765
export SECRET_KEY="${SECRET_KEY:-desktop-dev-secret-key-32chars!!}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./personal_ai.db}"
export DATABASE_URL_SYNC="${DATABASE_URL_SYNC:-sqlite:///./personal_ai.db}"
export DEFAULT_LLM_PROVIDER="${DEFAULT_LLM_PROVIDER:-mock}"
export DEBUG="${DEBUG:-true}"
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
