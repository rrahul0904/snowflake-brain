import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import BRAIN_DB


def _db_path() -> Path:
    BRAIN_DB.parent.mkdir(parents=True, exist_ok=True)
    return BRAIN_DB


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.DatabaseError:
        return set()


def _add_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if column not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _create_fts(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
          title,
          body,
          type UNINDEXED,
          ref_id UNINDEXED,
          course_id UNINDEXED,
          path UNINDEXED
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS question_fts USING fts5(
          question,
          explanation,
          tags,
          content='questions',
          content_rowid='rowid'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS lesson_fts USING fts5(
          title,
          section,
          content='lessons',
          content_rowid='rowid'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
          text,
          content='transcript_chunks',
          content_rowid='id'
        );
        """
    )


def _seed_quality_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        INSERT OR IGNORE INTO practice_test_classification(test_id, classification, reason, confidence)
        SELECT
          pt.id,
          CASE
            WHEN COALESCE(pt.question_count, 0) = 0 THEN 'empty_shell'
            WHEN LOWER(COALESCE(pt.title, '') || ' ' || COALESCE(pt.original_title, '') || ' ' || COALESCE(pt.source_path, '')) LIKE '%assignment%' THEN 'assignment'
            WHEN LOWER(COALESCE(pt.title, '') || ' ' || COALESCE(pt.original_title, '') || ' ' || COALESCE(pt.source_path, '')) LIKE '%hands on%' THEN 'lab'
            WHEN COALESCE(pt.question_count, 0) >= 50 THEN 'full_mock_exam'
            WHEN COALESCE(pt.question_count, 0) >= 20 THEN 'practice_test'
            WHEN COALESCE(pt.question_count, 0) > 0 THEN 'section_quiz'
            ELSE 'empty_shell'
          END,
          CASE
            WHEN COALESCE(pt.question_count, 0) = 0 THEN 'No questions attached to this source test record.'
            WHEN LOWER(COALESCE(pt.title, '') || ' ' || COALESCE(pt.original_title, '') || ' ' || COALESCE(pt.source_path, '')) LIKE '%assignment%' THEN 'Source title/path looks like an assignment.'
            WHEN LOWER(COALESCE(pt.title, '') || ' ' || COALESCE(pt.original_title, '') || ' ' || COALESCE(pt.source_path, '')) LIKE '%hands on%' THEN 'Source title/path looks like a hands-on lab.'
            WHEN COALESCE(pt.question_count, 0) >= 50 THEN 'Question count is large enough for a full mock exam.'
            WHEN COALESCE(pt.question_count, 0) >= 20 THEN 'Question count is suitable for a course practice test.'
            ELSE 'Small non-empty assessment; treat as a section quiz.'
          END,
          CASE
            WHEN COALESCE(pt.question_count, 0) = 0 THEN 0.95
            WHEN COALESCE(pt.question_count, 0) >= 50 THEN 0.85
            ELSE 0.65
          END
        FROM practice_tests pt;

        INSERT OR IGNORE INTO content_quality_audit(content_type, ref_id, course_id, track_id, quality_status, reason)
        SELECT
          'lesson',
          l.id,
          l.course_id,
          COALESCE(c.track_id, ''),
          CASE
            WHEN l.transcript_text LIKE 'English study notes.%' THEN 'generated_notes'
            WHEN l.transcript_text IS NULL OR TRIM(l.transcript_text) = '' THEN 'missing_transcript'
            ELSE 'transcript_like'
          END,
          CASE
            WHEN l.transcript_text LIKE 'English study notes.%' THEN 'Generated English study notes are being used as fallback.'
            WHEN l.transcript_text IS NULL OR TRIM(l.transcript_text) = '' THEN 'No transcript text is available.'
            ELSE 'Transcript-like text is available.'
          END
        FROM lessons l
        LEFT JOIN courses c ON c.id = l.course_id;

        INSERT OR IGNORE INTO content_quality_audit(content_type, ref_id, course_id, track_id, quality_status, reason)
        SELECT
          'practice_test',
          pt.id,
          pt.course_id,
          COALESCE(pt.track_id, ''),
          CASE
            WHEN COALESCE(pt.question_count, 0) = 0 THEN 'empty_shell'
            WHEN COALESCE(pt.question_count, 0) >= 50 THEN 'full_mock_exam'
            WHEN COALESCE(pt.question_count, 0) >= 20 THEN 'practice_test'
            ELSE 'micro_quiz'
          END,
          CASE
            WHEN COALESCE(pt.question_count, 0) = 0 THEN 'Practice test record has no questions.'
            WHEN COALESCE(pt.question_count, 0) >= 50 THEN 'Large enough to present as a full mock exam.'
            WHEN COALESCE(pt.question_count, 0) >= 20 THEN 'Suitable for a practice test.'
            ELSE 'Small quiz; do not present as a full practice test.'
          END
        FROM practice_tests pt;
        """
    )

    duplicate_rows = conn.execute(
        """
        SELECT
          LOWER(TRIM(question)) AS signature,
          MIN(id) AS representative_question_id,
          MIN(question) AS representative_question,
          COUNT(*) AS duplicate_count,
          GROUP_CONCAT(id) AS question_ids
        FROM questions
        GROUP BY LOWER(TRIM(question))
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    for row in duplicate_rows:
        question_ids = [item for item in (row["question_ids"] or "").split(",") if item]
        conn.execute(
            """
            INSERT INTO question_duplicates(
              signature,
              representative_question_id,
              representative_question,
              duplicate_count,
              question_ids_json
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(signature) DO UPDATE SET
              representative_question_id = excluded.representative_question_id,
              representative_question = excluded.representative_question,
              duplicate_count = excluded.duplicate_count,
              question_ids_json = excluded.question_ids_json,
              updated_at = datetime('now')
            """,
            (
                row["signature"],
                row["representative_question_id"],
                row["representative_question"],
                row["duplicate_count"],
                json.dumps(question_ids),
            ),
        )


def run_migrations() -> None:
    with connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              applied_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS courses (
              id TEXT PRIMARY KEY,
              track_id TEXT DEFAULT '',
              track_title TEXT DEFAULT '',
              title TEXT NOT NULL,
              slug TEXT DEFAULT '',
              path TEXT DEFAULT '',
              source_url TEXT,
              indexed_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS certification_tracks (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              description TEXT DEFAULT '',
              position INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS course_sections (
              id TEXT PRIMARY KEY,
              course_id TEXT NOT NULL REFERENCES courses(id),
              title TEXT NOT NULL,
              path TEXT DEFAULT '',
              position INTEGER DEFAULT 0,
              lesson_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS lessons (
              id TEXT PRIMARY KEY,
              course_id TEXT NOT NULL REFERENCES courses(id),
              section_id TEXT DEFAULT '',
              course_title TEXT DEFAULT '',
              title TEXT NOT NULL,
              sort_key INTEGER DEFAULT 0,
              video_path TEXT,
              transcript_path TEXT,
              info_path TEXT,
              duration REAL,
              transcript_text TEXT,
              excerpt TEXT
            );

            CREATE TABLE IF NOT EXISTS questions (
              id TEXT PRIMARY KEY,
              course_id TEXT REFERENCES courses(id),
              course_title TEXT DEFAULT '',
              test_id TEXT DEFAULT '',
              test_title TEXT DEFAULT '',
              question TEXT NOT NULL,
              options_json TEXT NOT NULL DEFAULT '[]',
              correct_json TEXT NOT NULL DEFAULT '[]',
              explanation TEXT,
              source_path TEXT,
              assessment_type TEXT
            );

            CREATE TABLE IF NOT EXISTS practice_tests (
              id TEXT PRIMARY KEY,
              course_id TEXT NOT NULL REFERENCES courses(id),
              course_title TEXT DEFAULT '',
              track_id TEXT DEFAULT '',
              track_title TEXT DEFAULT '',
              title TEXT NOT NULL,
              original_title TEXT DEFAULT '',
              position INTEGER DEFAULT 0,
              question_count INTEGER DEFAULT 0,
              source_path TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS documents (
              id TEXT PRIMARY KEY,
              course_id TEXT NOT NULL REFERENCES courses(id),
              course_title TEXT NOT NULL,
              title TEXT NOT NULL,
              path TEXT NOT NULL,
              body TEXT NOT NULL,
              excerpt TEXT
            );

            CREATE TABLE IF NOT EXISTS transcript_chunks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              lesson_id TEXT NOT NULL REFERENCES lessons(id),
              chunk_idx INTEGER NOT NULL,
              text TEXT NOT NULL,
              start_s REAL,
              end_s REAL
            );

            CREATE TABLE IF NOT EXISTS question_attempts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              question_id TEXT NOT NULL REFERENCES questions(id),
              selected TEXT NOT NULL,
              correct INTEGER NOT NULL,
              mode TEXT DEFAULT 'practice',
              attempted_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS lesson_progress (
              lesson_id TEXT PRIMARY KEY REFERENCES lessons(id),
              watched_s INTEGER DEFAULT 0,
              completed INTEGER DEFAULT 0,
              last_watched TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS notes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              lesson_id TEXT REFERENCES lessons(id),
              question_id TEXT REFERENCES questions(id),
              body TEXT NOT NULL,
              created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS bookmarks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              question_id TEXT REFERENCES questions(id),
              lesson_id TEXT REFERENCES lessons(id),
              created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS flashcards (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              front TEXT NOT NULL,
              back TEXT NOT NULL,
              source TEXT DEFAULT 'manual',
              source_id TEXT,
              tags TEXT DEFAULT '[]',
              easiness REAL DEFAULT 2.5,
              interval INTEGER DEFAULT 1,
              repetitions INTEGER DEFAULT 0,
              next_review TEXT DEFAULT (date('now')),
              created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS lab_exercises (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              starter_sql TEXT NOT NULL,
              solution_sql TEXT,
              expected_output TEXT,
              hint TEXT,
              tags TEXT DEFAULT '[]',
              difficulty TEXT DEFAULT 'medium',
              position INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS lab_submissions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              exercise_id INTEGER NOT NULL REFERENCES lab_exercises(id),
              submitted_sql TEXT NOT NULL,
              passed INTEGER DEFAULT 0,
              feedback TEXT,
              submitted_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS daily_activity (
              date TEXT PRIMARY KEY,
              questions_answered INTEGER DEFAULT 0,
              correct_answers INTEGER DEFAULT 0,
              minutes_studied INTEGER DEFAULT 0,
              videos_watched INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS content_quality_audit (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              content_type TEXT NOT NULL,
              ref_id TEXT NOT NULL,
              course_id TEXT REFERENCES courses(id),
              track_id TEXT DEFAULT '',
              quality_status TEXT NOT NULL,
              reason TEXT DEFAULT '',
              details_json TEXT DEFAULT '{}',
              audited_at TEXT DEFAULT (datetime('now')),
              UNIQUE(content_type, ref_id)
            );

            CREATE TABLE IF NOT EXISTS course_track_overrides (
              course_id TEXT PRIMARY KEY REFERENCES courses(id),
              original_track_id TEXT DEFAULT '',
              override_track_id TEXT NOT NULL REFERENCES certification_tracks(id),
              reason TEXT DEFAULT '',
              reviewed_by TEXT DEFAULT 'local',
              reviewed_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS practice_test_classification (
              test_id TEXT PRIMARY KEY REFERENCES practice_tests(id),
              classification TEXT NOT NULL DEFAULT 'practice_test',
              reason TEXT DEFAULT '',
              confidence REAL DEFAULT 0.5,
              reviewed INTEGER DEFAULT 0,
              reviewed_at TEXT,
              created_at TEXT DEFAULT (datetime('now')),
              updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS question_duplicates (
              signature TEXT PRIMARY KEY,
              representative_question_id TEXT REFERENCES questions(id),
              representative_question TEXT NOT NULL,
              duplicate_count INTEGER NOT NULL DEFAULT 0,
              question_ids_json TEXT NOT NULL DEFAULT '[]',
              status TEXT DEFAULT 'unreviewed',
              reviewed_at TEXT,
              created_at TEXT DEFAULT (datetime('now')),
              updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS exam_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              track_id TEXT DEFAULT '' REFERENCES certification_tracks(id),
              course_id TEXT REFERENCES courses(id),
              practice_test_id TEXT REFERENCES practice_tests(id),
              mode TEXT NOT NULL DEFAULT 'practice',
              started_at TEXT DEFAULT (datetime('now')),
              finished_at TEXT,
              score INTEGER DEFAULT 0,
              total_questions INTEGER DEFAULT 0,
              status TEXT DEFAULT 'in_progress'
            );

            CREATE TABLE IF NOT EXISTS exam_session_answers (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id INTEGER NOT NULL REFERENCES exam_sessions(id) ON DELETE CASCADE,
              question_id TEXT NOT NULL REFERENCES questions(id),
              selected_json TEXT NOT NULL DEFAULT '[]',
              correct INTEGER DEFAULT 0,
              answered_at TEXT DEFAULT (datetime('now')),
              reviewed INTEGER DEFAULT 0,
              UNIQUE(session_id, question_id)
            );

            CREATE TABLE IF NOT EXISTS topic_objectives (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              track_id TEXT DEFAULT '' REFERENCES certification_tracks(id),
              domain TEXT NOT NULL,
              objective TEXT NOT NULL,
              weight REAL DEFAULT 0,
              source TEXT DEFAULT 'local',
              created_at TEXT DEFAULT (datetime('now')),
              UNIQUE(track_id, domain, objective)
            );

            CREATE TABLE IF NOT EXISTS learning_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_type TEXT NOT NULL,
              track_id TEXT DEFAULT '',
              course_id TEXT,
              lesson_id TEXT,
              practice_test_id TEXT,
              question_id TEXT,
              lab_id INTEGER,
              flashcard_id INTEGER,
              study_plan_item_id INTEGER REFERENCES study_plan_items(id),
              metadata_json TEXT DEFAULT '{}',
              created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS study_goals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              track_id TEXT NOT NULL REFERENCES certification_tracks(id),
              target_exam_date TEXT,
              weekly_hours INTEGER DEFAULT 8,
              daily_question_target INTEGER DEFAULT 30,
              status TEXT DEFAULT 'active',
              created_at TEXT DEFAULT (datetime('now')),
              updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS study_plan_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              goal_id INTEGER NOT NULL REFERENCES study_goals(id) ON DELETE CASCADE,
              due_date TEXT NOT NULL,
              item_type TEXT NOT NULL,
              title TEXT NOT NULL,
              course_id TEXT REFERENCES courses(id),
              lesson_id TEXT REFERENCES lessons(id),
              practice_test_id TEXT REFERENCES practice_tests(id),
              question_count INTEGER DEFAULT 0,
              position INTEGER DEFAULT 0,
              completed INTEGER DEFAULT 0,
              completed_at TEXT
            );
            """
        )

        for column, ddl in {
            "track_id": "TEXT DEFAULT ''",
            "track_title": "TEXT DEFAULT ''",
            "folder": "TEXT DEFAULT ''",
            "thumbnail": "TEXT",
            "section_count": "INTEGER DEFAULT 0",
            "lesson_count": "INTEGER DEFAULT 0",
            "question_count": "INTEGER DEFAULT 0",
        }.items():
            _add_column(conn, "courses", column, ddl)

        for column, ddl in {
            "section_id": "TEXT DEFAULT ''",
            "section": "TEXT",
            "vtt_path": "TEXT",
            "duration_s": "INTEGER",
            "position": "INTEGER DEFAULT 0",
        }.items():
            _add_column(conn, "lessons", column, ddl)

        for column, ddl in {
            "tags": "TEXT DEFAULT '[]'",
            "difficulty": "TEXT DEFAULT 'medium'",
            "multiple": "INTEGER DEFAULT 0",
            "test_id": "TEXT DEFAULT ''",
            "test_position": "INTEGER DEFAULT 0",
            "question_position": "INTEGER DEFAULT 0",
        }.items():
            _add_column(conn, "questions", column, ddl)

        for column, ddl in {
            "weekly_hours": "INTEGER DEFAULT 8",
            "daily_question_target": "INTEGER DEFAULT 30",
            "updated_at": "TEXT DEFAULT (datetime('now'))",
        }.items():
            _add_column(conn, "study_goals", column, ddl)

        for column, ddl in {
            "position": "INTEGER DEFAULT 0",
            "completed_at": "TEXT",
        }.items():
            _add_column(conn, "study_plan_items", column, ddl)

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_courses_track ON courses(track_id);
            CREATE INDEX IF NOT EXISTS idx_lessons_course_order ON lessons(course_id, position, sort_key);
            CREATE INDEX IF NOT EXISTS idx_questions_track_course_test ON questions(course_id, test_id, question_position);
            CREATE INDEX IF NOT EXISTS idx_practice_tests_scope ON practice_tests(track_id, course_id, position);
            CREATE INDEX IF NOT EXISTS idx_study_goals_status ON study_goals(status, track_id);
            CREATE INDEX IF NOT EXISTS idx_study_plan_due ON study_plan_items(goal_id, due_date, completed);
            CREATE INDEX IF NOT EXISTS idx_content_quality_scope ON content_quality_audit(content_type, quality_status, track_id, course_id);
            CREATE INDEX IF NOT EXISTS idx_practice_classification_type ON practice_test_classification(classification, reviewed);
            CREATE INDEX IF NOT EXISTS idx_exam_sessions_scope ON exam_sessions(track_id, course_id, practice_test_id, status);
            CREATE INDEX IF NOT EXISTS idx_exam_answers_session ON exam_session_answers(session_id, correct, reviewed);
            CREATE INDEX IF NOT EXISTS idx_learning_events_type_time ON learning_events(event_type, created_at);
            CREATE INDEX IF NOT EXISTS idx_learning_events_scope ON learning_events(track_id, course_id, lesson_id, practice_test_id);
            """
        )

        _seed_quality_tables(conn)

        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations(version, name)
            VALUES (?, ?)
            """,
            ("20260629_000_guardrail_foundation", "Guardrail baseline, quality tables, exam sessions, and study plan"),
        )

        _create_fts(conn)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None
