#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
cd "$ROOT_DIR"

RUNTIME_PY="$ROOT_DIR/.venv/bin/python"
SHARED_PY="$ROOT_DIR/../.venv/bin/python"

if [[ ! -x "$RUNTIME_PY" ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

if ! "$RUNTIME_PY" -c 'import fastapi, pydantic, uvicorn' >/dev/null 2>&1; then
  if [[ -x "$SHARED_PY" ]] && "$SHARED_PY" -c 'import fastapi, pydantic, uvicorn' >/dev/null 2>&1; then
    RUNTIME_PY="$SHARED_PY"
    echo "Using the existing workspace Python environment."
  else
    "$RUNTIME_PY" -m pip install -r requirements.txt
  fi
fi

"$RUNTIME_PY" -c 'from app.database import run_migrations; run_migrations()'

BANK_PATH="$(find "$ROOT_DIR" -maxdepth 3 -type f -name 'snowflake_practice_exam_bank_normalized.json' -print -quit)"
if [[ -n "$BANK_PATH" ]]; then
  "$RUNTIME_PY" scripts/import_practice_bank.py "$BANK_PATH" --replace
else
  echo "Normalized practice bank not found; source exams were not imported."
fi

echo "Snowflake Certification Guide"
echo "Setup complete. Run ./scripts/dev.sh"
