-- Public globe data is written only by a trusted aggregation pipeline.  The
-- request-serving role reads this coarse, privacy-safe projection and must
-- never create or repair it at request time.

CREATE TABLE IF NOT EXISTS learner_activity_aggregates (
  id BIGSERIAL PRIMARY KEY,
  bucket_key TEXT NOT NULL,
  label TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  active_count INTEGER NOT NULL DEFAULT 0 CHECK(active_count >= 0),
  observed_at TEXT NOT NULL DEFAULT to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'),
  source TEXT NOT NULL DEFAULT 'aggregate'
);

CREATE INDEX IF NOT EXISTS idx_learner_activity_public_window
  ON learner_activity_aggregates(observed_at DESC, active_count DESC);
