#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8000}"
cd "$ROOT_DIR"

# Local credentials/config belong in .env (gitignored). Loading it here keeps
# Google OAuth, account email delivery, and other provider configuration
# consistent between the Python dev server and Docker Compose.
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

RUNTIME_PY="$ROOT_DIR/.venv/bin/python"
SHARED_PY="$ROOT_DIR/../.venv/bin/python"
if [[ ! -x "$RUNTIME_PY" ]] || ! "$RUNTIME_PY" -c 'import uvicorn' >/dev/null 2>&1; then
  if [[ -x "$SHARED_PY" ]] && "$SHARED_PY" -c 'import uvicorn' >/dev/null 2>&1; then
    RUNTIME_PY="$SHARED_PY"
  else
    echo "Run ./scripts/setup.sh first." >&2
    exit 1
  fi
fi

if [[ ! -x "$RUNTIME_PY" ]]; then
  echo "Run ./scripts/setup.sh first." >&2
  exit 1
fi

if [[ "${GOOGLE_AUTH_ENABLED:-false}" == "true" ]]; then
  if [[ -z "${GOOGLE_OIDC_CLIENT_ID:-}" || -z "${GOOGLE_OIDC_CLIENT_SECRET:-}" || -z "${GOOGLE_OIDC_REDIRECT_URI:-}" ]]; then
    echo "Google OAuth is enabled but GOOGLE_OIDC_CLIENT_ID, GOOGLE_OIDC_CLIENT_SECRET, or GOOGLE_OIDC_REDIRECT_URI is missing." >&2
    exit 1
  fi
fi

echo "Snowflake Certification Guide"
echo "http://127.0.0.1:${PORT}"
exec "$RUNTIME_PY" -m uvicorn app.main:app --reload --host 127.0.0.1 --port "$PORT"
