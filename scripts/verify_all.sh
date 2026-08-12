#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"

cd "$ROOT_DIR"

if [[ -z "$NODE_BIN" || ! -x "$NODE_BIN" ]]; then
  echo "Node.js is required for frontend verification. Set NODE_BIN or install node." >&2
  exit 1
fi

echo "== Backend compile =="
python3 -m compileall app

echo "== Database migrations =="
python3 -c "from app.database import run_migrations; run_migrations(); print('migrations ok')"

echo "== Evidence workflow smoke =="
python3 scripts/smoke_evidence.py

echo "== API smoke tests =="
python3 scripts/smoke_api.py

echo "== Source boundary check =="
python3 scripts/check_source_boundaries.py

echo "== Question count check =="
python3 scripts/check_question_counts.py

echo "== Frontend syntax =="
FRONTEND_FILES=(
  frontend/app.js
  frontend/router.js
  frontend/api.js
  frontend/ui.js
  frontend/components/nav.js
  frontend/components/topbar.js
  frontend/components/toast.js
  frontend/views/curriculum.js
  frontend/views/lesson.js
  frontend/views/quiz.js
  frontend/views/reference.js
  frontend/views/journal.js
)
for file in "${FRONTEND_FILES[@]}"; do
  "$NODE_BIN" --check "$file"
done

echo "== Static route contract =="
"$NODE_BIN" scripts/smoke_static_routes.mjs

echo "== Package check =="
scripts/package_review.sh >/tmp/snowflake_brain_package_path.txt
python3 scripts/check_package.py "$(cat /tmp/snowflake_brain_package_path.txt)"

echo "All verification checks passed."
