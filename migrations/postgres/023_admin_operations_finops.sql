-- Server-authorized operational control plane.  All timestamps are UTC.

ALTER TABLE candidate_accounts
  ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'candidate'
  CHECK (role IN ('candidate', 'admin'));

CREATE TABLE IF NOT EXISTS admin_audit_events (
  id BIGSERIAL PRIMARY KEY,
  actor_candidate_id BIGINT REFERENCES candidate_accounts(id) ON DELETE SET NULL,
  event TEXT NOT NULL,
  target_type TEXT NOT NULL DEFAULT '',
  target_id TEXT NOT NULL DEFAULT '',
  result TEXT NOT NULL DEFAULT 'success',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_events_created
  ON admin_audit_events(created_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS finops_cost_snapshots (
  id BIGSERIAL PRIMARY KEY,
  service_provider TEXT NOT NULL,
  service_name TEXT NOT NULL,
  cost_category TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  amount NUMERIC(14,4),
  currency TEXT NOT NULL DEFAULT 'USD',
  measurement_source TEXT NOT NULL,
  evidence_classification TEXT NOT NULL CHECK (evidence_classification IN ('ACTUAL','ESTIMATED','NOT_CONNECTED')),
  usage_quantity NUMERIC(18,4),
  usage_unit TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX IF NOT EXISTS idx_finops_period
  ON finops_cost_snapshots(period_start, service_provider, cost_category);

CREATE TABLE IF NOT EXISTS operations_daily_snapshots (
  snapshot_date TEXT PRIMARY KEY,
  registrations INTEGER NOT NULL DEFAULT 0,
  active_users INTEGER NOT NULL DEFAULT 0,
  paid_users INTEGER NOT NULL DEFAULT 0,
  new_subscribers INTEGER NOT NULL DEFAULT 0,
  mrr NUMERIC(14,4),
  revenue NUMERIC(14,4),
  questions_answered INTEGER NOT NULL DEFAULT 0,
  mock_submissions INTEGER NOT NULL DEFAULT 0,
  average_readiness NUMERIC(8,4),
  api_errors INTEGER NOT NULL DEFAULT 0,
  estimated_cost NUMERIC(14,4),
  generated_at TEXT NOT NULL DEFAULT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS deployment_records (
  id BIGSERIAL PRIMARY KEY,
  deployment_sha TEXT NOT NULL,
  environment TEXT NOT NULL,
  status TEXT NOT NULL,
  source_branch TEXT NOT NULL DEFAULT '',
  deployment_reason TEXT NOT NULL DEFAULT '',
  release_candidate TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'),
  UNIQUE(deployment_sha, environment, created_at)
);
CREATE INDEX IF NOT EXISTS idx_deployment_records_created
  ON deployment_records(created_at DESC, environment);
