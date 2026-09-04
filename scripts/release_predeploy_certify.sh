#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! "$PYTHON_BIN" -c 'import fastapi, pydantic' >/dev/null 2>&1 && [[ -x .venv/bin/python ]] && .venv/bin/python -c 'import fastapi, pydantic' >/dev/null 2>&1; then
  PYTHON_BIN=".venv/bin/python"
elif ! "$PYTHON_BIN" -c 'import fastapi, pydantic' >/dev/null 2>&1 && [[ -x ../.venv/bin/python ]] && ../.venv/bin/python -c 'import fastapi, pydantic' >/dev/null 2>&1; then
  PYTHON_BIN="../.venv/bin/python"
fi
"$PYTHON_BIN" scripts/predeployment_certify.py
