-- Automated QA findings and explicit human content/SME approvals.
-- Every approval is bound to an immutable question_version_id so editing a
-- question invalidates prior approval rather than silently carrying it forward.

CREATE TABLE IF NOT EXISTS question_editorial_state (
  question_id TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
  qa_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(qa_status IN ('pending','passed','failed')),
  qa_score REAL NOT NULL DEFAULT 0 CHECK(qa_score BETWEEN 0 AND 100),
  qa_question_version_id BIGINT REFERENCES question_versions(id) ON DELETE SET NULL,
  last_qa_run_id BIGINT,
  content_review_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(content_review_status IN ('pending','approved','changes_requested')),
  content_review_question_version_id BIGINT REFERENCES question_versions(id) ON DELETE SET NULL,
  content_reviewer TEXT NOT NULL DEFAULT '',
  content_reviewed_at TEXT,
  sme_review_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(sme_review_status IN ('pending','approved','changes_requested')),
  sme_review_question_version_id BIGINT REFERENCES question_versions(id) ON DELETE SET NULL,
  sme_reviewer TEXT NOT NULL DEFAULT '',
  sme_reviewed_at TEXT,
  updated_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS editorial_qa_runs (
  id BIGSERIAL PRIMARY KEY,
  track_id TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT 'bank',
  started_at TEXT NOT NULL DEFAULT datetime('now'),
  completed_at TEXT,
  question_count INTEGER NOT NULL DEFAULT 0,
  passed_count INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  blocker_count INTEGER NOT NULL DEFAULT 0,
  warning_count INTEGER NOT NULL DEFAULT 0,
  info_count INTEGER NOT NULL DEFAULT 0,
  metrics_json TEXT NOT NULL DEFAULT '{}'
);

ALTER TABLE question_editorial_state
  DROP CONSTRAINT IF EXISTS question_editorial_state_last_qa_run_id_fkey;
ALTER TABLE question_editorial_state
  ADD CONSTRAINT question_editorial_state_last_qa_run_id_fkey
  FOREIGN KEY(last_qa_run_id) REFERENCES editorial_qa_runs(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS editorial_findings (
  id BIGSERIAL PRIMARY KEY,
  qa_run_id BIGINT NOT NULL REFERENCES editorial_qa_runs(id) ON DELETE CASCADE,
  question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,
  dimension TEXT NOT NULL,
  check_code TEXT NOT NULL,
  severity TEXT NOT NULL CHECK(severity IN ('blocker','warning','info')),
  message TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS editorial_review_events (
  id BIGSERIAL PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  question_version_id BIGINT NOT NULL REFERENCES question_versions(id) ON DELETE CASCADE,
  stage TEXT NOT NULL CHECK(stage IN ('content','sme')),
  action TEXT NOT NULL CHECK(action IN ('approved','changes_requested')),
  actor TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE INDEX IF NOT EXISTS idx_editorial_state_qa
  ON question_editorial_state(qa_status,qa_score);
CREATE INDEX IF NOT EXISTS idx_editorial_state_content
  ON question_editorial_state(content_review_status,sme_review_status);
CREATE INDEX IF NOT EXISTS idx_editorial_findings_question
  ON editorial_findings(question_id,severity,check_code);
CREATE INDEX IF NOT EXISTS idx_editorial_review_events_question
  ON editorial_review_events(question_id,created_at DESC);

INSERT INTO schema_migrations(version,name)
VALUES ('20260815_060_question_editorial_maturity_v1','Question editorial maturity and version-bound approvals')
ON CONFLICT(version) DO NOTHING;
