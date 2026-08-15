-- Native PostgreSQL equivalents of the SQLite trigger boundaries that protect
-- candidate-visible history and entitlement reconciliation.

CREATE OR REPLACE FUNCTION trg_question_version_after_insert_fn()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO question_versions(
    question_id, version_number, question, options_json, correct_json,
    explanation, source_path, source_kind, assessment_type,
    difficulty, multiple, test_title
  )
  VALUES (
    NEW.id, 1, NEW.question, NEW.options_json, NEW.correct_json,
    NEW.explanation, NEW.source_path, NEW.source_kind,
    NEW.assessment_type, NEW.difficulty, NEW.multiple, NEW.test_title
  )
  ON CONFLICT(question_id, version_number) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_question_version_after_insert ON questions;
CREATE TRIGGER trg_question_version_after_insert
AFTER INSERT ON questions
FOR EACH ROW EXECUTE FUNCTION trg_question_version_after_insert_fn();

CREATE OR REPLACE FUNCTION trg_served_question_content_immutable_fn()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF (
       OLD.question IS DISTINCT FROM NEW.question
    OR OLD.options_json IS DISTINCT FROM NEW.options_json
    OR OLD.correct_json IS DISTINCT FROM NEW.correct_json
    OR OLD.explanation IS DISTINCT FROM NEW.explanation
    OR OLD.difficulty IS DISTINCT FROM NEW.difficulty
    OR OLD.multiple IS DISTINCT FROM NEW.multiple
  ) AND (
    EXISTS (SELECT 1 FROM exam_session_questions sq WHERE sq.question_id=OLD.id)
    OR EXISTS (SELECT 1 FROM candidate_question_history h WHERE h.question_id=OLD.id)
  ) THEN
    RAISE EXCEPTION 'served question content is immutable; create a new question revision';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_served_question_content_immutable ON questions;
CREATE TRIGGER trg_served_question_content_immutable
BEFORE UPDATE OF question, options_json, correct_json, explanation, difficulty, multiple
ON questions
FOR EACH ROW EXECUTE FUNCTION trg_served_question_content_immutable_fn();

CREATE OR REPLACE FUNCTION trg_question_version_after_content_update_fn()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF (
       OLD.question IS DISTINCT FROM NEW.question
    OR OLD.options_json IS DISTINCT FROM NEW.options_json
    OR OLD.correct_json IS DISTINCT FROM NEW.correct_json
    OR OLD.explanation IS DISTINCT FROM NEW.explanation
    OR OLD.difficulty IS DISTINCT FROM NEW.difficulty
    OR OLD.multiple IS DISTINCT FROM NEW.multiple
  ) THEN
    INSERT INTO question_versions(
      question_id, version_number, question, options_json, correct_json,
      explanation, source_path, source_kind, assessment_type,
      difficulty, multiple, test_title
    )
    VALUES (
      NEW.id,
      COALESCE((SELECT MAX(version_number) FROM question_versions WHERE question_id=NEW.id),0)+1,
      NEW.question, NEW.options_json, NEW.correct_json, NEW.explanation,
      NEW.source_path, NEW.source_kind, NEW.assessment_type,
      NEW.difficulty, NEW.multiple, NEW.test_title
    );
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_question_version_after_content_update ON questions;
CREATE TRIGGER trg_question_version_after_content_update
AFTER UPDATE OF question, options_json, correct_json, explanation, difficulty, multiple
ON questions
FOR EACH ROW EXECUTE FUNCTION trg_question_version_after_content_update_fn();

CREATE OR REPLACE FUNCTION trg_exam_session_question_version_fn()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.question_version_id IS NULL THEN
    UPDATE exam_session_questions
       SET question_version_id=(
         SELECT v.id
           FROM question_versions v
          WHERE v.question_id=NEW.question_id
          ORDER BY v.version_number DESC
          LIMIT 1
       )
     WHERE session_id=NEW.session_id AND question_id=NEW.question_id;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_exam_session_question_version ON exam_session_questions;
CREATE TRIGGER trg_exam_session_question_version
AFTER INSERT ON exam_session_questions
FOR EACH ROW EXECUTE FUNCTION trg_exam_session_question_version_fn();

CREATE OR REPLACE FUNCTION trg_exam_question_version_link_immutable_fn()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF OLD.question_version_id IS NOT NULL
     AND OLD.question_version_id IS DISTINCT FROM NEW.question_version_id THEN
    RAISE EXCEPTION 'exam question version link is immutable';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_exam_question_version_link_immutable ON exam_session_questions;
CREATE TRIGGER trg_exam_question_version_link_immutable
BEFORE UPDATE OF question_version_id ON exam_session_questions
FOR EACH ROW EXECUTE FUNCTION trg_exam_question_version_link_immutable_fn();

CREATE OR REPLACE FUNCTION trg_restore_exam_pack_after_membership_expiry_fn()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  next_version integer;
BEGIN
  IF OLD.status = 'active'
     AND NEW.status = 'expired'
     AND EXISTS (
       SELECT 1 FROM billing_purchases p
        WHERE p.candidate_id = NEW.candidate_id
          AND p.product_type = 'exam_pack_35'
          AND p.status = 'paid'
     )
     AND NOT EXISTS (
       SELECT 1 FROM candidate_memberships m
        WHERE m.candidate_id = NEW.candidate_id
          AND m.status = 'active'
          AND datetime(m.starts_at) <= datetime('now')
          AND (m.expires_at IS NULL OR datetime(m.expires_at) > datetime('now'))
     )
  THEN
    SELECT COALESCE(MAX(entitlement_version),0)+1
      INTO next_version
      FROM candidate_memberships
     WHERE candidate_id=NEW.candidate_id;

    INSERT INTO candidate_memberships(
      candidate_id,tier,plan_code,status,starts_at,expires_at,source,entitlement_version
    ) VALUES (
      NEW.candidate_id,'premium','exam_pack_35','active',datetime('now'),NULL,
      'entitlement_reconciliation',next_version
    );

    UPDATE candidate_accounts
       SET plan='premium',updated_at=datetime('now')
     WHERE id=NEW.candidate_id;

    INSERT INTO membership_audit_log(
      candidate_id,old_plan,new_plan,reason,source,provider_event_id,entitlement_version
    ) VALUES (
      NEW.candidate_id,NEW.plan_code,'exam_pack_35',
      'expired_subscription_exam_pack_fallback','entitlement_reconciliation',NULL,next_version
    );
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_restore_exam_pack_after_membership_expiry ON candidate_memberships;
CREATE TRIGGER trg_restore_exam_pack_after_membership_expiry
AFTER UPDATE OF status ON candidate_memberships
FOR EACH ROW EXECUTE FUNCTION trg_restore_exam_pack_after_membership_expiry_fn();
