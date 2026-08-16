-- Account recovery, verification, portable export and privacy lifecycle.

ALTER TABLE candidate_accounts
  ADD COLUMN IF NOT EXISTS email_verified INTEGER NOT NULL DEFAULT 1;
ALTER TABLE candidate_accounts
  ADD COLUMN IF NOT EXISTS email_verified_at TEXT;
ALTER TABLE candidate_accounts
  ADD COLUMN IF NOT EXISTS password_changed_at TEXT;

UPDATE candidate_accounts
   SET email_verified_at=COALESCE(email_verified_at, created_at)
 WHERE email_verified=1;

CREATE TABLE IF NOT EXISTS account_action_tokens (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  purpose TEXT NOT NULL CHECK(purpose IN ('verify_email','password_reset','change_email')),
  token_hash TEXT NOT NULL UNIQUE,
  target_value TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  expires_at TEXT NOT NULL,
  consumed_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS account_audit_events (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS development_account_outbox (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  recipient TEXT NOT NULL,
  purpose TEXT NOT NULL,
  action_url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  delivered_at TEXT
);

CREATE TABLE IF NOT EXISTS account_deletion_receipts (
  receipt_id TEXT PRIMARY KEY,
  reason TEXT NOT NULL DEFAULT 'candidate_request',
  created_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE INDEX IF NOT EXISTS idx_account_action_tokens_candidate
  ON account_action_tokens(candidate_id, purpose, expires_at, consumed_at);
CREATE INDEX IF NOT EXISTS idx_account_audit_candidate
  ON account_audit_events(candidate_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_account_outbox_candidate
  ON development_account_outbox(candidate_id, created_at DESC);

INSERT INTO schema_migrations(version,name)
VALUES ('20260815_040_account_lifecycle_v1','PostgreSQL account lifecycle and recovery')
ON CONFLICT(version) DO NOTHING;
