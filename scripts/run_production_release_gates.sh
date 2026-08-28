#!/usr/bin/env bash
set -euo pipefail

python -m compileall -q app scripts
python scripts/test_tracked_secret_scan.py

# Existing certification, auth, billing, release, entitlement, learning and
# frontend contracts.
bash scripts/verify_all.sh

# Roadmap-specific production gates added after the original regression bundle.
python scripts/test_account_lifecycle.py
python scripts/test_content_freshness_pipeline.py
python scripts/test_question_editorial_maturity.py
python scripts/test_adaptive_readiness_intelligence.py
python scripts/test_adaptive_frontend_contract.py
python scripts/test_authenticated_bank_isolation.py
python scripts/test_vercel_production_database_boundary.py
python scripts/test_cloud_only_production.py
python scripts/test_production_startup_boundary.py
python scripts/test_serverless_postgres_pool.py
python scripts/test_production_migration_privileges.py
python scripts/test_production_launch_gate.py

echo "Production release gates: PASS"
