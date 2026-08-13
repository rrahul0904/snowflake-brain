#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
cd "$ROOT_DIR"

if [[ -z "$NODE_BIN" || ! -x "$NODE_BIN" ]]; then
  echo "Node.js is required for frontend verification. Set NODE_BIN or install node." >&2
  exit 1
fi
if [[ ! -x "$PYTHON_BIN" ]] || ! "$PYTHON_BIN" -c 'import fastapi, pydantic' >/dev/null 2>&1; then
  if [[ -x "$ROOT_DIR/../.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT_DIR/../.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

echo "== Python compile =="
"$PYTHON_BIN" -m compileall app scripts

echo "== COF-C03 blueprint/content contract =="
"$PYTHON_BIN" scripts/smoke_core_guide.py

echo "== Certification-native architecture =="
"$PYTHON_BIN" scripts/smoke_certification_native.py

echo "== Production mock exam contract =="
"$PYTHON_BIN" scripts/test_mock_exam.py

echo "== Retired media UI guard =="
if rg -n -i 'course|video|transcript|academy|archive' frontend --glob '!*.map'; then
  echo "Retired course/media UI tokens remain in the active frontend." >&2
  exit 1
fi

echo "== Frontend syntax =="
FRONTEND_FILES=(
  frontend/app.js
  frontend/router.js
  frontend/api.js
  frontend/ui.js
  frontend/components/nav.js
  frontend/components/topbar.js
  frontend/components/toast.js
  frontend/views/guide.js
  frontend/views/mock.js
  frontend/views/quiz.js
  frontend/views/labs.js
  frontend/views/journal.js
)
for file in "${FRONTEND_FILES[@]}"; do
  "$NODE_BIN" --check "$file"
done

echo "All V25 Snowflake Certification Guide checks passed."
