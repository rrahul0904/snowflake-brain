-- Optional hard gate for release lifecycle transitions. Installing editorial
-- maturity does not break today's active bank: enforcement is explicitly enabled
-- per certification track only after the bank has current QA + human approvals.

CREATE TABLE IF NOT EXISTS question_editorial_policies (
  track_id TEXT PRIMARY KEY,
  enforcement_enabled INTEGER NOT NULL DEFAULT 0 CHECK(enforcement_enabled IN (0,1)),
  minimum_qa_score REAL NOT NULL DEFAULT 70 CHECK(minimum_qa_score BETWEEN 0 AND 100),
  require_content_review INTEGER NOT NULL DEFAULT 1 CHECK(require_content_review IN (0,1)),
  require_sme_review INTEGER NOT NULL DEFAULT 1 CHECK(require_sme_review IN (0,1)),
  updated_at TEXT NOT NULL DEFAULT datetime('now'),
  updated_by TEXT NOT NULL DEFAULT 'system'
);

CREATE OR REPLACE FUNCTION enforce_question_editorial_release_gate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  policy_row record;
  invalid_count integer;
BEGIN
  IF NEW.status NOT IN ('qa_passed','sme_approved','staging','active') OR NEW.status=OLD.status THEN
    RETURN NEW;
  END IF;

  SELECT * INTO policy_row
    FROM question_editorial_policies
   WHERE track_id=NEW.track_id AND enforcement_enabled=1;
  IF NOT FOUND THEN
    RETURN NEW;
  END IF;

  SELECT COUNT(*) INTO invalid_count
    FROM question_bank_release_questions item
    LEFT JOIN question_editorial_state state ON state.question_id=item.question_id
   WHERE item.release_id=NEW.id
     AND (
       state.question_id IS NULL
       OR state.qa_status<>'passed'
       OR COALESCE(state.qa_score,0)<policy_row.minimum_qa_score
       OR COALESCE(state.qa_question_version_id,0)<>COALESCE(item.question_version_id,0)
       OR (
         NEW.status IN ('sme_approved','staging','active')
         AND policy_row.require_content_review=1
         AND (
           state.content_review_status<>'approved'
           OR COALESCE(state.content_review_question_version_id,0)<>COALESCE(item.question_version_id,0)
         )
       )
       OR (
         NEW.status IN ('sme_approved','staging','active')
         AND policy_row.require_sme_review=1
         AND (
           state.sme_review_status<>'approved'
           OR COALESCE(state.sme_review_question_version_id,0)<>COALESCE(item.question_version_id,0)
         )
       )
     );

  IF invalid_count>0 THEN
    RAISE EXCEPTION 'question editorial gate blocked release transition to %: % release question(s) lack current required approval', NEW.status, invalid_count;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_question_editorial_release_gate ON question_bank_releases;
CREATE TRIGGER trg_question_editorial_release_gate
BEFORE UPDATE OF status ON question_bank_releases
FOR EACH ROW
EXECUTE FUNCTION enforce_question_editorial_release_gate();

INSERT INTO schema_migrations(version,name)
VALUES ('20260815_061_question_editorial_gate_v1','Optional version-bound question editorial release gate')
ON CONFLICT(version) DO NOTHING;
