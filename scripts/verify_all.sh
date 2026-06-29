#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="${NODE_BIN:-/Users/297159/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node}"

cd "$ROOT_DIR"

echo "== Backend compile =="
python3 -m compileall app

echo "== Database migrations =="
python3 -c "from app.database import run_migrations; run_migrations(); print('migrations ok')"

echo "== API smoke tests =="
python3 scripts/smoke_api.py

echo "== Source boundary check =="
python3 scripts/check_source_boundaries.py

echo "== Question count check =="
python3 scripts/check_question_counts.py

echo "== Frontend syntax =="
"$NODE_BIN" --check frontend/router.js
"$NODE_BIN" --check frontend/api.js
"$NODE_BIN" --check frontend/components/nav.js
"$NODE_BIN" --check frontend/views/dashboard.js
"$NODE_BIN" --check frontend/views/video.js
"$NODE_BIN" --check frontend/views/quiz.js
"$NODE_BIN" --check frontend/views/analytics.js
"$NODE_BIN" --check frontend/views/plan.js

echo "== Package check =="
scripts/package_review.sh >/tmp/snowflake_brain_package_path.txt
python3 scripts/check_package.py "$(cat /tmp/snowflake_brain_package_path.txt)"

echo "All verification checks passed."
