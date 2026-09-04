-- Final Study Command Center convergence: persisted task review scheduling and privacy-safe mock replay events.

CREATE TABLE IF NOT EXISTS candidate_task_reviews (
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  skill_id TEXT NOT NULL,
  source_type TEXT NOT NULL DEFAULT 'task' CHECK(source_type IN ('task')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  next_review_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 day'),
  interval_days INTEGER NOT NULL DEFAULT 1 CHECK(interval_days >= 0),
  review_count INTEGER NOT NULL DEFAULT 0 CHECK(review_count >= 0),
  last_reviewed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(candidate_id, track_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_candidate_task_reviews_due
  ON candidate_task_reviews(candidate_id, track_id, status, next_review_at);

CREATE TABLE IF NOT EXISTS exam_session_events (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES exam_sessions(id) ON DELETE CASCADE,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  question_id TEXT REFERENCES questions(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL CHECK(event_type IN (
    'question_viewed','answer_selected','answer_changed','answer_cleared',
    'flag_added','flag_removed','question_navigated_from','question_navigated_to',
    'session_resumed','session_submitted','timer_expired'
  )),
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_exam_session_events_session
  ON exam_session_events(session_id, occurred_at, id);
CREATE INDEX IF NOT EXISTS idx_exam_session_events_candidate
  ON exam_session_events(candidate_id, session_id, occurred_at);
