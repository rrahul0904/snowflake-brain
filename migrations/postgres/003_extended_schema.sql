-- Extended production schema: identity/billing authority, immutable question
-- versions, release management, entitlement reservations, and learning state.

CREATE TABLE IF NOT EXISTS candidate_identities (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  provider_subject TEXT NOT NULL,
  provider_email TEXT DEFAULT '',
  provider_email_verified INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT datetime('now'),
  last_login_at TEXT DEFAULT datetime('now'),
  UNIQUE(provider, provider_subject)
);

CREATE TABLE IF NOT EXISTS oauth_login_flows (
  state_hash TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  nonce TEXT NOT NULL,
  code_verifier TEXT NOT NULL,
  created_at TEXT DEFAULT datetime('now'),
  expires_at TEXT NOT NULL,
  consumed_at TEXT
);

CREATE TABLE IF NOT EXISTS pending_identity_links (
  token_hash TEXT PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  provider_subject TEXT NOT NULL,
  provider_email TEXT NOT NULL,
  provider_email_verified INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT datetime('now'),
  expires_at TEXT NOT NULL,
  consumed_at TEXT,
  UNIQUE(provider, provider_subject)
);

CREATE TABLE IF NOT EXISTS billing_customers (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  provider_customer_id TEXT NOT NULL,
  created_at TEXT DEFAULT datetime('now'),
  updated_at TEXT DEFAULT datetime('now'),
  UNIQUE(provider, candidate_id),
  UNIQUE(provider, provider_customer_id)
);

CREATE TABLE IF NOT EXISTS billing_checkout_sessions (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  provider_checkout_session_id TEXT NOT NULL,
  provider_customer_id TEXT NOT NULL,
  provider_price_id TEXT NOT NULL,
  internal_plan TEXT NOT NULL,
  checkout_mode TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT DEFAULT datetime('now'),
  completed_at TEXT,
  UNIQUE(provider, provider_checkout_session_id)
);

CREATE TABLE IF NOT EXISTS billing_subscriptions (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  provider_customer_id TEXT NOT NULL,
  provider_subscription_id TEXT NOT NULL,
  provider_price_id TEXT NOT NULL,
  internal_plan TEXT NOT NULL,
  status TEXT NOT NULL,
  current_period_start TEXT,
  current_period_end TEXT,
  cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
  last_provider_event_created INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT datetime('now'),
  updated_at TEXT DEFAULT datetime('now'),
  UNIQUE(provider, provider_subscription_id)
);

CREATE TABLE IF NOT EXISTS billing_purchases (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  provider_payment_id TEXT NOT NULL,
  product_type TEXT NOT NULL,
  status TEXT NOT NULL,
  purchased_at TEXT DEFAULT datetime('now'),
  expires_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(provider, provider_payment_id)
);

CREATE TABLE IF NOT EXISTS billing_events (
  id BIGSERIAL PRIMARY KEY,
  provider TEXT NOT NULL,
  provider_event_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  received_at TEXT DEFAULT datetime('now'),
  processed_at TEXT,
  processing_status TEXT NOT NULL DEFAULT 'received',
  payload_hash TEXT NOT NULL,
  error_message TEXT DEFAULT '',
  UNIQUE(provider, provider_event_id)
);

CREATE TABLE IF NOT EXISTS membership_audit_log (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  old_plan TEXT NOT NULL,
  new_plan TEXT NOT NULL,
  reason TEXT NOT NULL,
  source TEXT NOT NULL,
  provider_event_id TEXT,
  entitlement_version INTEGER NOT NULL,
  created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS question_versions (
  id BIGSERIAL PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,
  question TEXT NOT NULL,
  options_json TEXT NOT NULL DEFAULT '[]',
  correct_json TEXT NOT NULL DEFAULT '[]',
  explanation TEXT DEFAULT '',
  source_path TEXT DEFAULT '',
  source_kind TEXT NOT NULL DEFAULT 'curated',
  assessment_type TEXT NOT NULL DEFAULT 'practice',
  difficulty TEXT NOT NULL DEFAULT 'medium',
  multiple INTEGER NOT NULL DEFAULT 0,
  test_title TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  UNIQUE(question_id, version_number)
);

ALTER TABLE exam_session_questions
  ADD COLUMN IF NOT EXISTS question_version_id BIGINT REFERENCES question_versions(id);

CREATE TABLE IF NOT EXISTS question_bank_releases (
  id BIGSERIAL PRIMARY KEY,
  release_key TEXT NOT NULL UNIQUE,
  track_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK(status IN ('draft','qa_passed','sme_approved','staging','active','retired')),
  question_count INTEGER NOT NULL DEFAULT 0,
  source_fingerprint TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  created_by TEXT NOT NULL DEFAULT 'system',
  approved_by TEXT,
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  qa_passed_at TEXT,
  approved_at TEXT,
  staged_at TEXT,
  activated_at TEXT,
  retired_at TEXT
);

CREATE TABLE IF NOT EXISTS question_bank_release_questions (
  release_id BIGINT NOT NULL REFERENCES question_bank_releases(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id),
  question_version_id BIGINT NOT NULL REFERENCES question_versions(id),
  PRIMARY KEY(release_id, question_id)
);

CREATE TABLE IF NOT EXISTS question_bank_release_events (
  id BIGSERIAL PRIMARY KEY,
  release_id BIGINT NOT NULL REFERENCES question_bank_releases(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  actor TEXT NOT NULL DEFAULT 'system',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS candidate_srs_state (
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  domain_id TEXT NOT NULL DEFAULT '',
  skill_id TEXT NOT NULL DEFAULT '',
  repetitions INTEGER NOT NULL DEFAULT 0,
  interval_days INTEGER NOT NULL DEFAULT 0,
  ease_factor DOUBLE PRECISION NOT NULL DEFAULT 2.3,
  lapses INTEGER NOT NULL DEFAULT 0,
  due_at TEXT NOT NULL DEFAULT datetime('now'),
  last_reviewed_at TEXT,
  last_correct INTEGER,
  last_confidence INTEGER,
  updated_at TEXT NOT NULL DEFAULT datetime('now'),
  PRIMARY KEY(candidate_id, question_id)
);

CREATE TABLE IF NOT EXISTS candidate_mistake_notebook (
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  domain_id TEXT NOT NULL DEFAULT '',
  skill_id TEXT NOT NULL DEFAULT '',
  miss_count INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK(status IN ('open','reviewing','mastered')),
  root_cause TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  first_missed_at TEXT NOT NULL DEFAULT datetime('now'),
  last_missed_at TEXT NOT NULL DEFAULT datetime('now'),
  last_reviewed_at TEXT,
  mastered_at TEXT,
  updated_at TEXT NOT NULL DEFAULT datetime('now'),
  PRIMARY KEY(candidate_id, question_id)
);

CREATE TABLE IF NOT EXISTS candidate_study_preferences (
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  exam_date TEXT,
  daily_minutes INTEGER NOT NULL DEFAULT 45,
  days_per_week INTEGER NOT NULL DEFAULT 6,
  updated_at TEXT NOT NULL DEFAULT datetime('now'),
  PRIMARY KEY(candidate_id, track_id)
);

CREATE TABLE IF NOT EXISTS candidate_learning_attempt_sync (
  attempt_id BIGINT PRIMARY KEY REFERENCES question_attempts(id) ON DELETE CASCADE,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  processed_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS exam_entitlement_reservations (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  plan_code TEXT NOT NULL,
  exam_type TEXT NOT NULL CHECK(exam_type IN ('weekly_mock','full_exam')),
  window_key TEXT NOT NULL,
  attempt_number INTEGER NOT NULL,
  session_id BIGINT REFERENCES exam_sessions(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'reserved'
    CHECK(status IN ('reserved','committed','released')),
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  committed_at TEXT,
  released_at TEXT,
  UNIQUE(candidate_id, track_id, exam_type, window_key, attempt_number),
  UNIQUE(session_id)
);

CREATE TABLE IF NOT EXISTS feedback_submissions (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  contact TEXT DEFAULT '',
  route TEXT NOT NULL DEFAULT '#/home',
  track_id TEXT NOT NULL DEFAULT 'snowpro-core',
  candidate_id BIGINT REFERENCES candidate_accounts(id) ON DELETE SET NULL,
  created_at TEXT DEFAULT datetime('now')
);

CREATE INDEX IF NOT EXISTS idx_candidate_identities_candidate
  ON candidate_identities(candidate_id, provider);
CREATE INDEX IF NOT EXISTS idx_pending_identity_links_candidate
  ON pending_identity_links(candidate_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_billing_customers_candidate
  ON billing_customers(candidate_id, provider);
CREATE INDEX IF NOT EXISTS idx_billing_checkout_candidate
  ON billing_checkout_sessions(candidate_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_candidate
  ON billing_subscriptions(candidate_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_billing_purchases_candidate
  ON billing_purchases(candidate_id, product_type, status);
CREATE INDEX IF NOT EXISTS idx_membership_audit_candidate
  ON membership_audit_log(candidate_id, created_at);
CREATE INDEX IF NOT EXISTS idx_question_versions_logical
  ON question_versions(question_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_question_bank_releases_track_status
  ON question_bank_releases(track_id, status, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_question_bank_active_release_per_track
  ON question_bank_releases(track_id) WHERE status='active';
CREATE INDEX IF NOT EXISTS idx_question_bank_release_questions_version
  ON question_bank_release_questions(question_version_id);
CREATE INDEX IF NOT EXISTS idx_candidate_srs_due
  ON candidate_srs_state(candidate_id, track_id, due_at);
CREATE INDEX IF NOT EXISTS idx_candidate_srs_skill
  ON candidate_srs_state(candidate_id, track_id, skill_id, due_at);
CREATE INDEX IF NOT EXISTS idx_candidate_mistakes_status
  ON candidate_mistake_notebook(candidate_id, track_id, status, last_missed_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_mistakes_skill
  ON candidate_mistake_notebook(candidate_id, track_id, skill_id, status);
CREATE INDEX IF NOT EXISTS idx_candidate_learning_attempt_sync_candidate
  ON candidate_learning_attempt_sync(candidate_id, processed_at);
CREATE INDEX IF NOT EXISTS idx_exam_entitlement_reservation_window
  ON exam_entitlement_reservations(candidate_id, track_id, exam_type, window_key, status, created_at);

-- These markers make the existing additive SQLite-era ensure_* boundaries
-- no-ops on PostgreSQL after the equivalent production schema is installed.
INSERT INTO schema_migrations(version, name) VALUES
  ('20260814_006_question_bank_v1', 'PostgreSQL core equivalent for private question bank metadata'),
  ('20260814_009_google_identity_billing_authority_v26', 'PostgreSQL identity and billing authority equivalent'),
  ('20260815_010_immutable_question_versions_v1', 'PostgreSQL immutable question versions equivalent'),
  ('20260815_020_question_bank_releases_v1', 'PostgreSQL question-bank releases equivalent'),
  ('20260815_031_candidate_learning_attempt_sync_v1', 'PostgreSQL candidate learning synchronization equivalent'),
  ('20260815_032_candidate_learning_intelligence_hardening', 'PostgreSQL candidate learning intelligence equivalent')
ON CONFLICT(version) DO NOTHING;
