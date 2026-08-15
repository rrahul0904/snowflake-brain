from __future__ import annotations

import sqlite3
import threading

from .database import connect


SCHEMA_VERSION = "20260815_010_immutable_question_versions_v1"
_SCHEMA_LOCK = threading.RLock()
_READY_DATABASES: set[str] = set()


def _database_key(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    if not row:
        return "unknown"
    try:
        return str(row["file"] or row[2] or "memory")
    except (KeyError, TypeError, IndexError):
        return str(row[2] or "memory")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, declaration: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def ensure_question_version_schema() -> None:
    """Install the immutable question/version boundary.

    `questions.id` remains the logical identity used by the existing runtime.
    `question_versions` records immutable physical content revisions and every
    timed sitting points at the revision current when the question was added.

    Until all read paths are migrated to join the version table directly, a
    served question's content columns are also protected from mutation. This
    guarantees that historical results cannot become a hybrid of an old score
    and newly overwritten wording/options/explanations.
    """
    with _SCHEMA_LOCK:
        with connect() as conn:
            database_key = _database_key(conn)
            if database_key in _READY_DATABASES:
                return

            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS question_versions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                  version_number INTEGER NOT NULL,
                  question TEXT NOT NULL,
                  options_json TEXT NOT NULL DEFAULT '[]',
                  correct_json TEXT NOT NULL DEFAULT '[]',
                  explanation TEXT DEFAULT '',
                  source_path TEXT DEFAULT '',
                  source_kind TEXT NOT NULL DEFAULT 'curated',
                  assessment_type TEXT NOT NULL DEFAULT 'practice',
                  difficulty TEXT NOT NULL DEFAULT 'medium',
                  multiple INTEGER NOT NULL DEFAULT 0,
                  test_title TEXT DEFAULT '',
                  created_at TEXT NOT NULL DEFAULT (datetime('now')),
                  UNIQUE(question_id, version_number)
                );

                CREATE INDEX IF NOT EXISTS idx_question_versions_logical
                  ON question_versions(question_id, version_number DESC);
                """
            )
            _ensure_column(
                conn,
                "exam_session_questions",
                "question_version_id",
                "INTEGER REFERENCES question_versions(id)",
            )

            # Establish the current repository/database state as version 1.
            # Existing historical sittings cannot be reconstructed more exactly
            # than the content that survived before this migration, so they are
            # explicitly baselined to this version once.
            conn.execute(
                """
                INSERT INTO question_versions(
                  question_id, version_number, question, options_json, correct_json,
                  explanation, source_path, source_kind, assessment_type,
                  difficulty, multiple, test_title
                )
                SELECT q.id, 1, q.question, q.options_json, q.correct_json,
                       q.explanation, q.source_path, q.source_kind, q.assessment_type,
                       q.difficulty, q.multiple, q.test_title
                  FROM questions q
                 WHERE NOT EXISTS (
                   SELECT 1 FROM question_versions v WHERE v.question_id=q.id
                 )
                """
            )
            conn.execute(
                """
                UPDATE exam_session_questions
                   SET question_version_id=(
                     SELECT v.id
                       FROM question_versions v
                      WHERE v.question_id=exam_session_questions.question_id
                      ORDER BY v.version_number DESC
                      LIMIT 1
                   )
                 WHERE question_version_id IS NULL
                """
            )

            conn.executescript(
                """
                DROP TRIGGER IF EXISTS trg_question_version_after_content_update;
                CREATE TRIGGER trg_question_version_after_content_update
                AFTER UPDATE OF
                  question, options_json, correct_json, explanation, source_path,
                  source_kind, assessment_type, difficulty, multiple, test_title
                ON questions
                WHEN OLD.question IS NOT NEW.question
                  OR OLD.options_json IS NOT NEW.options_json
                  OR OLD.correct_json IS NOT NEW.correct_json
                  OR OLD.explanation IS NOT NEW.explanation
                  OR OLD.source_path IS NOT NEW.source_path
                  OR OLD.source_kind IS NOT NEW.source_kind
                  OR OLD.assessment_type IS NOT NEW.assessment_type
                  OR OLD.difficulty IS NOT NEW.difficulty
                  OR OLD.multiple IS NOT NEW.multiple
                  OR OLD.test_title IS NOT NEW.test_title
                BEGIN
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
                END;

                DROP TRIGGER IF EXISTS trg_served_question_content_immutable;
                CREATE TRIGGER trg_served_question_content_immutable
                BEFORE UPDATE OF
                  question, options_json, correct_json, explanation, source_path,
                  source_kind, assessment_type, difficulty, multiple, test_title
                ON questions
                WHEN (
                    OLD.question IS NOT NEW.question
                    OR OLD.options_json IS NOT NEW.options_json
                    OR OLD.correct_json IS NOT NEW.correct_json
                    OR OLD.explanation IS NOT NEW.explanation
                    OR OLD.source_path IS NOT NEW.source_path
                    OR OLD.source_kind IS NOT NEW.source_kind
                    OR OLD.assessment_type IS NOT NEW.assessment_type
                    OR OLD.difficulty IS NOT NEW.difficulty
                    OR OLD.multiple IS NOT NEW.multiple
                    OR OLD.test_title IS NOT NEW.test_title
                  )
                  AND (
                    EXISTS (SELECT 1 FROM exam_session_questions sq WHERE sq.question_id=OLD.id)
                    OR EXISTS (SELECT 1 FROM candidate_question_history h WHERE h.question_id=OLD.id)
                  )
                BEGIN
                  SELECT RAISE(ABORT, 'served question content is immutable; create a new question revision');
                END;

                DROP TRIGGER IF EXISTS trg_exam_session_question_version;
                CREATE TRIGGER trg_exam_session_question_version
                AFTER INSERT ON exam_session_questions
                WHEN NEW.question_version_id IS NULL
                BEGIN
                  UPDATE exam_session_questions
                     SET question_version_id=(
                       SELECT v.id
                         FROM question_versions v
                        WHERE v.question_id=NEW.question_id
                        ORDER BY v.version_number DESC
                        LIMIT 1
                     )
                   WHERE session_id=NEW.session_id AND question_id=NEW.question_id;
                END;

                DROP TRIGGER IF EXISTS trg_exam_question_version_link_immutable;
                CREATE TRIGGER trg_exam_question_version_link_immutable
                BEFORE UPDATE OF question_version_id ON exam_session_questions
                WHEN OLD.question_version_id IS NOT NULL
                  AND OLD.question_version_id IS NOT NEW.question_version_id
                BEGIN
                  SELECT RAISE(ABORT, 'exam question version link is immutable');
                END;
                """
            )

            migrated = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version=? LIMIT 1",
                (SCHEMA_VERSION,),
            ).fetchone()
            if not migrated:
                conn.execute(
                    "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
                    (
                        SCHEMA_VERSION,
                        "Immutable question versions, timed-sitting revision links, and served-content mutation guard",
                    ),
                )

            _READY_DATABASES.add(database_key)
