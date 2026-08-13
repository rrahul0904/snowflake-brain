#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"
cd "$ROOT_DIR"

if [[ -z "$NODE_BIN" || ! -x "$NODE_BIN" ]]; then
  echo "Node.js is required for frontend verification. Set NODE_BIN or install node." >&2
  exit 1
fi

echo "== Python compile =="
python3 -m compileall app scripts/smoke_core_guide.py scripts/smoke_certification_native.py

echo "== COF-C03 blueprint/content contract =="
python3 scripts/smoke_core_guide.py

echo "== Certification-native architecture =="
python3 scripts/smoke_certification_native.py

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
  frontend/views/quiz.js
  frontend/views/labs.js
  frontend/views/journal.js
)
for file in "${FRONTEND_FILES[@]}"; do
  "$NODE_BIN" --check "$file"
done

echo "All V24 Snowflake Certification Guide checks passed."
