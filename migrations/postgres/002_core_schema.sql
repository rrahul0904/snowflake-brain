-- Core certification-native schema. IDs remain integer-compatible with the
-- existing API while PostgreSQL owns sequence generation in production.

CREATE TABLE IF NOT EXISTS certification_tracks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  exam_code TEXT DEFAULT '',
  description TEXT DEFAULT '',
  position INTEGER DEFAULT 0,
  created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS certification_task_progress (
  track_id TEXT NOT NULL,
  skill_id TEXT NOT NULL,
  completed INTEGER NOT NULL DEFAULT 0,
  completed_at TEXT,
  updated_at TEXT DEFAULT datetime('now'),
  PRIMARY KEY(track_id, skill_id)
);

CREATE TABLE IF NOT EXISTS candidate_accounts (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  display_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  password_salt TEXT NOT NULL,
  password_algorithm TEXT NOT NULL DEFAULT 'scrypt',
  password_login_enabled INTEGER NOT NULL DEFAULT 1,
  plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free', 'premium')),
  status TEXT NOT NULL DEFAULT 'active',
  last_login_at TEXT,
  created_at TEXT DEFAULT datetime('now'),
  updated_at TEXT DEFAULT datetime('now')
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_accounts_email_nocase
  ON candidate_accounts(lower(email));

CREATE TABLE IF NOT EXISTS candidate_sessions (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  created_at TEXT DEFAULT datetime('now'),
  last_seen_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS membership_events (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  previous_plan TEXT NOT NULL,
  next_plan TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'prototype',
  created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS candidate_memberships (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  tier TEXT NOT NULL DEFAULT 'free' CHECK(tier IN ('free', 'premium')),
  plan_code TEXT NOT NULL DEFAULT 'free',
  status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'expired', 'cancelled')),
  starts_at TEXT NOT NULL DEFAULT datetime('now'),
  expires_at TEXT,
  source TEXT NOT NULL DEFAULT 'registration',
  entitlement_version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT DEFAULT datetime('now'),
  updated_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS candidate_task_progress (
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  skill_id TEXT NOT NULL,
  completed INTEGER NOT NULL DEFAULT 0,
  completed_at TEXT,
  updated_at TEXT DEFAULT datetime('now'),
  PRIMARY KEY(candidate_id, track_id, skill_id)
);

CREATE TABLE IF NOT EXISTS candidate_daily_activity (
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  date TEXT NOT NULL,
  questions_answered INTEGER DEFAULT 0,
  correct_answers INTEGER DEFAULT 0,
  minutes_studied INTEGER DEFAULT 0,
  PRIMARY KEY(candidate_id, date)
);

CREATE TABLE IF NOT EXISTS candidate_daily_question_usage (
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  usage_date TEXT NOT NULL,
  questions_consumed INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT DEFAULT datetime('now'),
  PRIMARY KEY(candidate_id, usage_date)
);

CREATE TABLE IF NOT EXISTS practice_tests (
  id TEXT PRIMARY KEY,
  track_id TEXT NOT NULL,
  title TEXT NOT NULL,
  exam_code TEXT DEFAULT '',
  source_kind TEXT NOT NULL DEFAULT 'curated',
  source_path TEXT DEFAULT '',
  position INTEGER DEFAULT 0,
  question_count INTEGER DEFAULT 0,
  version TEXT DEFAULT '',
  is_legacy INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY,
  track_id TEXT NOT NULL,
  test_id TEXT REFERENCES practice_tests(id) ON DELETE SET NULL,
  test_title TEXT DEFAULT '',
  question TEXT NOT NULL,
  options_json TEXT NOT NULL DEFAULT '[]',
  correct_json TEXT NOT NULL DEFAULT '[]',
  explanation TEXT DEFAULT '',
  source_path TEXT DEFAULT '',
  source_kind TEXT NOT NULL DEFAULT 'curated',
  assessment_type TEXT NOT NULL DEFAULT 'practice',
  tags TEXT NOT NULL DEFAULT '[]',
  difficulty TEXT NOT NULL DEFAULT 'medium',
  multiple INTEGER NOT NULL DEFAULT 0,
  question_position INTEGER DEFAULT 0,
  created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS question_skill_map (
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  domain_id TEXT DEFAULT '',
  skill_id TEXT NOT NULL,
  confidence DOUBLE PRECISION DEFAULT 0.5,
  evidence_json TEXT DEFAULT '{}',
  reviewed INTEGER DEFAULT 0,
  created_at TEXT DEFAULT datetime('now'),
  updated_at TEXT DEFAULT datetime('now'),
  PRIMARY KEY(question_id, skill_id)
);

CREATE TABLE IF NOT EXISTS question_attempts (
  id BIGSERIAL PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  selected TEXT NOT NULL DEFAULT '[]',
  correct INTEGER NOT NULL,
  mode TEXT DEFAULT 'practice',
  candidate_id BIGINT REFERENCES candidate_accounts(id) ON DELETE SET NULL,
  response_time_ms INTEGER,
  confidence INTEGER,
  attempted_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS exam_sessions (
  id BIGSERIAL PRIMARY KEY,
  track_id TEXT NOT NULL,
  practice_test_id TEXT REFERENCES practice_tests(id) ON DELETE SET NULL,
  candidate_id BIGINT REFERENCES candidate_accounts(id) ON DELETE SET NULL,
  mode TEXT NOT NULL DEFAULT 'practice',
  started_at TEXT DEFAULT datetime('now'),
  finished_at TEXT,
  score INTEGER DEFAULT 0,
  total_questions INTEGER DEFAULT 0,
  status TEXT DEFAULT 'in_progress',
  duration_seconds INTEGER NOT NULL DEFAULT 0,
  submitted_reason TEXT DEFAULT '',
  raw_correct INTEGER NOT NULL DEFAULT 0,
  raw_accuracy DOUBLE PRECISION NOT NULL DEFAULT 0,
  weighted_accuracy DOUBLE PRECISION NOT NULL DEFAULT 0,
  scaled_score INTEGER NOT NULL DEFAULT 0,
  elapsed_seconds INTEGER NOT NULL DEFAULT 0,
  configuration_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS exam_session_questions (
  session_id BIGINT NOT NULL REFERENCES exam_sessions(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  options_json TEXT NOT NULL DEFAULT '[]',
  correct_positions_json TEXT NOT NULL DEFAULT '[]',
  flagged INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(session_id, question_id),
  UNIQUE(session_id, position)
);

CREATE TABLE IF NOT EXISTS exam_session_answers (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES exam_sessions(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  selected_json TEXT NOT NULL DEFAULT '[]',
  correct INTEGER DEFAULT 0,
  confidence INTEGER,
  response_time_ms INTEGER,
  answered_at TEXT DEFAULT datetime('now'),
  reviewed INTEGER DEFAULT 0,
  UNIQUE(session_id, question_id)
);

CREATE TABLE IF NOT EXISTS question_bank_metadata (
  question_id TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
  certification_id TEXT NOT NULL,
  exam_version TEXT NOT NULL,
  domain_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  task_code TEXT NOT NULL DEFAULT '',
  question_type TEXT NOT NULL DEFAULT 'standard_mcq',
  cognitive_level TEXT NOT NULL DEFAULT 'apply',
  difficulty_band TEXT NOT NULL DEFAULT 'applied'
    CHECK(difficulty_band IN ('foundation','applied','exam','challenge')),
  bank_pool TEXT NOT NULL DEFAULT 'practice'
    CHECK(bank_pool IN ('free','practice','diagnostic','mock_reserved')),
  authoring_status TEXT NOT NULL DEFAULT 'draft'
    CHECK(authoring_status IN ('draft','review','active','retired')),
  authoring_version TEXT NOT NULL DEFAULT '1',
  concepts_json TEXT NOT NULL DEFAULT '[]',
  trap_tags_json TEXT NOT NULL DEFAULT '[]',
  distractor_rationales_json TEXT NOT NULL DEFAULT '[]',
  source_refs_json TEXT NOT NULL DEFAULT '[]',
  source_verified_at TEXT,
  content_hash TEXT NOT NULL DEFAULT '',
  created_at TEXT DEFAULT datetime('now'),
  updated_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS question_exposure_stats (
  question_id TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
  served_count INTEGER NOT NULL DEFAULT 0,
  correct_count INTEGER NOT NULL DEFAULT 0,
  incorrect_count INTEGER NOT NULL DEFAULT 0,
  last_served_at TEXT,
  lifecycle_status TEXT NOT NULL DEFAULT 'active'
    CHECK(lifecycle_status IN ('active','cooldown','retired')),
  updated_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS candidate_question_history (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  session_id BIGINT REFERENCES exam_sessions(id) ON DELETE SET NULL,
  mode TEXT NOT NULL DEFAULT 'practice',
  pool TEXT NOT NULL DEFAULT 'fallback',
  served_at TEXT NOT NULL DEFAULT datetime('now'),
  answered_at TEXT,
  selected_json TEXT NOT NULL DEFAULT '[]',
  correct INTEGER,
  response_time_ms INTEGER,
  confidence INTEGER,
  question_version TEXT NOT NULL DEFAULT 'legacy'
);

CREATE TABLE IF NOT EXISTS candidate_exam_pack_sets (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  set_kind TEXT NOT NULL CHECK(set_kind IN ('lifetime_practice','full_exam')),
  created_at TEXT DEFAULT datetime('now'),
  UNIQUE(candidate_id, track_id, set_kind)
);

CREATE TABLE IF NOT EXISTS candidate_exam_pack_set_questions (
  set_id BIGINT NOT NULL REFERENCES candidate_exam_pack_sets(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
  position INTEGER NOT NULL,
  PRIMARY KEY(set_id, question_id),
  UNIQUE(set_id, position)
);

CREATE TABLE IF NOT EXISTS question_bank_imports (
  id BIGSERIAL PRIMARY KEY,
  source_name TEXT NOT NULL,
  track_id TEXT NOT NULL,
  bank_version TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  question_count INTEGER NOT NULL,
  imported_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS candidate_bookmarks (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  created_at TEXT DEFAULT datetime('now'),
  UNIQUE(candidate_id, question_id)
);

CREATE TABLE IF NOT EXISTS candidate_notes (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS bookmarks (
  id BIGSERIAL PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  created_at TEXT DEFAULT datetime('now'),
  UNIQUE(question_id)
);

CREATE TABLE IF NOT EXISTS notes (
  id BIGSERIAL PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  created_at TEXT DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS daily_activity (
  date TEXT PRIMARY KEY,
  questions_answered INTEGER DEFAULT 0,
  correct_answers INTEGER DEFAULT 0,
  minutes_studied INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS learning_events (
  id BIGSERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  track_id TEXT DEFAULT '',
  practice_test_id TEXT,
  question_id TEXT,
  lab_id TEXT,
  skill_id TEXT,
  metadata_json TEXT DEFAULT '{}',
  candidate_id BIGINT REFERENCES candidate_accounts(id) ON DELETE SET NULL,
  created_at TEXT DEFAULT datetime('now')
);

CREATE INDEX IF NOT EXISTS idx_questions_track_test
  ON questions(track_id, test_id, question_position);
CREATE INDEX IF NOT EXISTS idx_questions_source
  ON questions(track_id, source_kind, assessment_type);
CREATE INDEX IF NOT EXISTS idx_practice_tests_track
  ON practice_tests(track_id, is_legacy, position);
CREATE INDEX IF NOT EXISTS idx_attempts_question_time
  ON question_attempts(question_id, attempted_at);
CREATE INDEX IF NOT EXISTS idx_task_progress_track
  ON certification_task_progress(track_id, completed);
CREATE INDEX IF NOT EXISTS idx_question_skill_map_skill
  ON question_skill_map(track_id, domain_id, skill_id, confidence, reviewed);
CREATE INDEX IF NOT EXISTS idx_exam_sessions_track
  ON exam_sessions(track_id, mode, status, finished_at);
CREATE INDEX IF NOT EXISTS idx_exam_sessions_candidate
  ON exam_sessions(candidate_id, status, started_at);
CREATE INDEX IF NOT EXISTS idx_exam_session_questions_order
  ON exam_session_questions(session_id, position);
CREATE INDEX IF NOT EXISTS idx_question_bank_track_pool
  ON question_bank_metadata(certification_id, authoring_status, bank_pool, domain_id, task_id);
CREATE INDEX IF NOT EXISTS idx_question_bank_difficulty
  ON question_bank_metadata(certification_id, difficulty_band, authoring_status);
CREATE INDEX IF NOT EXISTS idx_candidate_question_history_candidate
  ON candidate_question_history(candidate_id, question_id, served_at);
CREATE INDEX IF NOT EXISTS idx_candidate_question_history_session
  ON candidate_question_history(session_id, question_id);
CREATE INDEX IF NOT EXISTS idx_question_exposure_served
  ON question_exposure_stats(lifecycle_status, served_count, last_served_at);
CREATE INDEX IF NOT EXISTS idx_exam_pack_sets_candidate
  ON candidate_exam_pack_sets(candidate_id, track_id, set_kind);
CREATE INDEX IF NOT EXISTS idx_learning_events_track
  ON learning_events(track_id, event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_learning_events_candidate
  ON learning_events(candidate_id, created_at);
CREATE INDEX IF NOT EXISTS idx_candidate_sessions_candidate
  ON candidate_sessions(candidate_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_membership_events_candidate
  ON membership_events(candidate_id, created_at);
CREATE INDEX IF NOT EXISTS idx_candidate_memberships_candidate
  ON candidate_memberships(candidate_id, status, tier, starts_at, expires_at);
CREATE INDEX IF NOT EXISTS idx_candidate_progress_track
  ON candidate_task_progress(candidate_id, track_id, completed);
CREATE INDEX IF NOT EXISTS idx_candidate_bookmarks_question
  ON candidate_bookmarks(candidate_id, question_id);
CREATE INDEX IF NOT EXISTS idx_candidate_notes_question
  ON candidate_notes(candidate_id, question_id, created_at);
CREATE INDEX IF NOT EXISTS idx_question_attempts_candidate
  ON question_attempts(candidate_id, attempted_at);
CREATE INDEX IF NOT EXISTS idx_daily_question_usage_candidate
  ON candidate_daily_question_usage(candidate_id, usage_date);
