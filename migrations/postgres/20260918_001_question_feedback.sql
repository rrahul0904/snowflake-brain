-- Candidate question correction reports and editorial triage.
-- Reports never store answer keys and never mutate immutable question content.

CREATE TABLE IF NOT EXISTS question_feedback (
  id BIGSERIAL PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  category TEXT NOT NULL
    CHECK(category IN ('ambiguous','incorrect_answer','outdated','explanation','typo','other')),
  description TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open'
    CHECK(status IN ('open','triaged','resolved','rejected')),
  resolution_notes TEXT NOT NULL DEFAULT '',
  resolved_by TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  updated_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE INDEX IF NOT EXISTS idx_question_feedback_candidate
  ON question_feedback(candidate_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_question_feedback_editorial
  ON question_feedback(status,question_id,created_at);
