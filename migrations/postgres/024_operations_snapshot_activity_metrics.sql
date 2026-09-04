-- Expand daily operational snapshots with the learner activity measures used by
-- the production control plane.  Values remain aggregates and contain no PII.

ALTER TABLE operations_daily_snapshots
  ADD COLUMN IF NOT EXISTS daily_active_users INTEGER NOT NULL DEFAULT 0;
ALTER TABLE operations_daily_snapshots
  ADD COLUMN IF NOT EXISTS weekly_active_users INTEGER NOT NULL DEFAULT 0;
ALTER TABLE operations_daily_snapshots
  ADD COLUMN IF NOT EXISTS monthly_active_users INTEGER NOT NULL DEFAULT 0;
ALTER TABLE operations_daily_snapshots
  ADD COLUMN IF NOT EXISTS practice_sessions INTEGER NOT NULL DEFAULT 0;
ALTER TABLE operations_daily_snapshots
  ADD COLUMN IF NOT EXISTS review_completions INTEGER NOT NULL DEFAULT 0;
