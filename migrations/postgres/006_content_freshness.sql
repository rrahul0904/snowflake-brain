-- Official-source provenance, change detection and release freshness gate.
-- The policy is opt-in per track so installing the system does not invalidate an
-- existing bank before its source links have been editorially populated.

CREATE TABLE IF NOT EXISTS content_sources (
  id BIGSERIAL PRIMARY KEY,
  source_key TEXT NOT NULL UNIQUE,
  source_url TEXT NOT NULL,
  source_title TEXT NOT NULL DEFAULT '',
  source_section TEXT NOT NULL DEFAULT '',
  authority_host TEXT NOT NULL,
  document_version TEXT NOT NULL DEFAULT '',
  document_date TEXT NOT NULL DEFAULT '',
  current_fingerprint TEXT NOT NULL DEFAULT '',
  previous_fingerprint TEXT NOT NULL DEFAULT '',
  etag TEXT NOT NULL DEFAULT '',
  last_modified TEXT NOT NULL DEFAULT '',
  last_checked_at TEXT,
  last_changed_at TEXT,
  last_verified_at TEXT,
  verified_by TEXT NOT NULL DEFAULT '',
  confidence INTEGER NOT NULL DEFAULT 0 CHECK(confidence BETWEEN 0 AND 100),
  editorial_status TEXT NOT NULL DEFAULT 'unverified'
    CHECK(editorial_status IN ('unverified','verified','needs_review','blocked','retired')),
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  updated_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS content_source_snapshots (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES content_sources(id) ON DELETE CASCADE,
  fingerprint TEXT NOT NULL,
  retrieved_at TEXT NOT NULL DEFAULT datetime('now'),
  http_status INTEGER NOT NULL DEFAULT 200,
  etag TEXT NOT NULL DEFAULT '',
  last_modified TEXT NOT NULL DEFAULT '',
  normalized_length INTEGER NOT NULL DEFAULT 0,
  change_summary TEXT NOT NULL DEFAULT '',
  UNIQUE(source_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS content_source_links (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES content_sources(id) ON DELETE CASCADE,
  artifact_type TEXT NOT NULL CHECK(artifact_type IN ('question','lesson','skill','reference')),
  artifact_key TEXT NOT NULL,
  track_id TEXT NOT NULL DEFAULT 'snowpro-core',
  source_section TEXT NOT NULL DEFAULT '',
  assertion_kind TEXT NOT NULL DEFAULT 'supports',
  editorial_status TEXT NOT NULL DEFAULT 'unverified'
    CHECK(editorial_status IN ('unverified','verified','needs_review','blocked','retired')),
  confidence INTEGER NOT NULL DEFAULT 0 CHECK(confidence BETWEEN 0 AND 100),
  last_verified_at TEXT,
  verified_by TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  updated_at TEXT NOT NULL DEFAULT datetime('now'),
  UNIQUE(source_id, artifact_type, artifact_key)
);

CREATE TABLE IF NOT EXISTS content_review_queue (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES content_sources(id) ON DELETE CASCADE,
  artifact_type TEXT NOT NULL DEFAULT 'source',
  artifact_key TEXT NOT NULL DEFAULT '',
  track_id TEXT NOT NULL DEFAULT 'snowpro-core',
  reason TEXT NOT NULL,
  old_fingerprint TEXT NOT NULL DEFAULT '',
  new_fingerprint TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open'
    CHECK(status IN ('open','acknowledged','resolved','ignored')),
  detected_at TEXT NOT NULL DEFAULT datetime('now'),
  resolved_at TEXT,
  resolved_by TEXT NOT NULL DEFAULT '',
  resolution_notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS content_source_checks (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES content_sources(id) ON DELETE CASCADE,
  checked_at TEXT NOT NULL DEFAULT datetime('now'),
  result TEXT NOT NULL CHECK(result IN ('unchanged','changed','initialized','not_modified','error')),
  http_status INTEGER,
  fingerprint TEXT NOT NULL DEFAULT '',
  elapsed_ms INTEGER NOT NULL DEFAULT 0,
  error_type TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS content_freshness_policies (
  track_id TEXT PRIMARY KEY,
  enforcement_enabled INTEGER NOT NULL DEFAULT 0 CHECK(enforcement_enabled IN (0,1)),
  require_all_questions INTEGER NOT NULL DEFAULT 1 CHECK(require_all_questions IN (0,1)),
  max_verification_age_days INTEGER NOT NULL DEFAULT 120 CHECK(max_verification_age_days BETWEEN 1 AND 3650),
  updated_at TEXT NOT NULL DEFAULT datetime('now'),
  updated_by TEXT NOT NULL DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_content_sources_status
  ON content_sources(editorial_status,last_checked_at);
CREATE INDEX IF NOT EXISTS idx_content_links_artifact
  ON content_source_links(track_id,artifact_type,artifact_key,editorial_status);
CREATE INDEX IF NOT EXISTS idx_content_review_open
  ON content_review_queue(track_id,status,detected_at);
CREATE INDEX IF NOT EXISTS idx_content_checks_source
  ON content_source_checks(source_id,checked_at DESC);

CREATE OR REPLACE FUNCTION enforce_content_freshness_on_release()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  policy_row record;
  bad_count integer;
BEGIN
  IF NEW.status <> 'active' OR OLD.status = 'active' THEN
    RETURN NEW;
  END IF;

  SELECT * INTO policy_row
    FROM content_freshness_policies
   WHERE track_id=NEW.track_id AND enforcement_enabled=1;
  IF NOT FOUND THEN
    RETURN NEW;
  END IF;

  IF policy_row.require_all_questions=1 THEN
    SELECT COUNT(*) INTO bad_count
      FROM question_bank_release_questions rqi
     WHERE rqi.release_id=NEW.id
       AND NOT EXISTS (
         SELECT 1
           FROM content_source_links l
           JOIN content_sources s ON s.id=l.source_id
          WHERE l.track_id=NEW.track_id
            AND l.artifact_type='question'
            AND l.artifact_key=rqi.question_id
            AND l.editorial_status='verified'
            AND s.editorial_status='verified'
            AND l.last_verified_at IS NOT NULL
            AND s.last_verified_at IS NOT NULL
            AND l.last_verified_at::timestamptz >= clock_timestamp() - make_interval(days => policy_row.max_verification_age_days)
            AND s.last_verified_at::timestamptz >= clock_timestamp() - make_interval(days => policy_row.max_verification_age_days)
       );
    IF bad_count > 0 THEN
      RAISE EXCEPTION 'content freshness gate blocked release activation: % question(s) lack current verified provenance', bad_count;
    END IF;
  ELSE
    SELECT COUNT(*) INTO bad_count
      FROM question_bank_release_questions rqi
      JOIN content_source_links l
        ON l.track_id=NEW.track_id
       AND l.artifact_type='question'
       AND l.artifact_key=rqi.question_id
      JOIN content_sources s ON s.id=l.source_id
     WHERE rqi.release_id=NEW.id
       AND (
         l.editorial_status <> 'verified'
         OR s.editorial_status <> 'verified'
         OR l.last_verified_at IS NULL
         OR s.last_verified_at IS NULL
         OR l.last_verified_at::timestamptz < clock_timestamp() - make_interval(days => policy_row.max_verification_age_days)
         OR s.last_verified_at::timestamptz < clock_timestamp() - make_interval(days => policy_row.max_verification_age_days)
       );
    IF bad_count > 0 THEN
      RAISE EXCEPTION 'content freshness gate blocked release activation: linked provenance requires editorial review';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_content_freshness_release_gate ON question_bank_releases;
CREATE TRIGGER trg_content_freshness_release_gate
BEFORE UPDATE OF status ON question_bank_releases
FOR EACH ROW
EXECUTE FUNCTION enforce_content_freshness_on_release();

INSERT INTO schema_migrations(version,name)
VALUES ('20260815_050_content_freshness_v1','Official source provenance and content freshness')
ON CONFLICT(version) DO NOTHING;
