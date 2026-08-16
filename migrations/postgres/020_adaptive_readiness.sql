-- Evidence-based candidate readiness snapshots and adaptive recommendations.

CREATE TABLE IF NOT EXISTS candidate_readiness_snapshots (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  readiness_score REAL NOT NULL CHECK(readiness_score BETWEEN 0 AND 100),
  evidence_confidence TEXT NOT NULL CHECK(evidence_confidence IN ('low','medium','high')),
  readiness_band TEXT NOT NULL,
  mastery_score REAL NOT NULL DEFAULT 0,
  retention_score REAL NOT NULL DEFAULT 0,
  calibration_score REAL NOT NULL DEFAULT 0,
  mock_score REAL NOT NULL DEFAULT 0,
  coverage_score REAL NOT NULL DEFAULT 0,
  pace_score REAL NOT NULL DEFAULT 0,
  unique_questions_seen INTEGER NOT NULL DEFAULT 0,
  recent_mock_count INTEGER NOT NULL DEFAULT 0,
  exam_date TEXT,
  runway_days INTEGER,
  recommended_daily_minutes INTEGER NOT NULL DEFAULT 0,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS candidate_adaptive_recommendations (
  id BIGSERIAL PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  track_id TEXT NOT NULL,
  recommendation_type TEXT NOT NULL,
  domain_id TEXT NOT NULL DEFAULT '',
  skill_id TEXT NOT NULL DEFAULT '',
  priority_score REAL NOT NULL DEFAULT 0,
  reason_code TEXT NOT NULL,
  reason_text TEXT NOT NULL,
  action_json TEXT NOT NULL DEFAULT '{}',
  source_snapshot_id BIGINT REFERENCES candidate_readiness_snapshots(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE INDEX IF NOT EXISTS idx_readiness_candidate_track
  ON candidate_readiness_snapshots(candidate_id,track_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_adaptive_recommendation_candidate
  ON candidate_adaptive_recommendations(candidate_id,track_id,priority_score DESC,created_at DESC);

INSERT INTO schema_migrations(version,name)
VALUES ('20260815_070_adaptive_readiness_v2','Evidence-based adaptive readiness intelligence')
ON CONFLICT(version) DO NOTHING;
