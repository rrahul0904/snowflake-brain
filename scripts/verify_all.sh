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

echo "== Candidate API route uniqueness =="
"$PYTHON_BIN" scripts/test_unique_api_routes.py

echo "== COF-C03 blueprint/content contract =="
"$PYTHON_BIN" scripts/smoke_core_guide.py

echo "== Certification-native architecture =="
"$PYTHON_BIN" scripts/smoke_certification_native.py

echo "== Production mock exam contract =="
"$PYTHON_BIN" scripts/test_mock_exam.py

echo "== V26 functional and visual contract =="
"$PYTHON_BIN" scripts/smoke_v26.py

echo "== Candidate authentication and membership =="
"$PYTHON_BIN" scripts/test_auth_membership.py

echo "== Login-required certification content boundary =="
"$PYTHON_BIN" scripts/test_authenticated_content_boundary.py

echo "== Google identity and trusted billing authority =="
"$PYTHON_BIN" scripts/test_google_billing_security.py

echo "== Google OAuth browser transaction binding =="
"$PYTHON_BIN" scripts/test_google_browser_state.py

echo "== Google identity continuity =="
"$PYTHON_BIN" scripts/test_google_identity_continuity.py

echo "== Paid tier transition hardening =="
"$PYTHON_BIN" scripts/test_billing_tier_transitions.py

echo "== Exam Pack expiry reconciliation =="
"$PYTHON_BIN" scripts/test_exam_pack_expiry_reconciliation.py

echo "== Concurrent identity/billing schema bootstrap =="
"$PYTHON_BIN" scripts/test_identity_schema_concurrency.py

echo "== Private question bank tiers and exam allocation =="
"$PYTHON_BIN" scripts/test_question_bank_tiers.py

echo "== Tier resets and fresh timed mock rotation =="
"$PYTHON_BIN" scripts/test_tier_reset_full_exams.py

echo "== Affiliate disclosure and permanent no-ad-network policy =="
"$PYTHON_BIN" scripts/test_affiliate_no_ads.py

echo "== Retired media UI guard =="
if rg -n -i '/api/(courses|lessons|media)|#/academy|#/video|course-player|video-player|transcript-player' frontend --glob '!*.map'; then
  echo "Retired course/media runtime identifiers remain in the active frontend." >&2
  exit 1
fi

echo "== Frontend syntax =="
while IFS= read -r -d '' file; do
  "$NODE_BIN" --check "$file"
done < <(find frontend -type f -name '*.js' -print0)

echo "All Snowflake Certification Guide checks passed."
