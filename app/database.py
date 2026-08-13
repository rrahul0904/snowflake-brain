import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import BRAIN_DB


SCHEMA_VERSION = "20260812_000_certification_native_v24"


def _db_path() -> Path:
    BRAIN_DB.parent.mkdir(parents=True, exist_ok=True)
    return BRAIN_DB


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def run_migrations() -> None:
    """Create the certification-native persistence model.

    V24 intentionally uses a new default database file. No course, lesson,
    video, transcript, archive, or content-root tables are created here.
    """
    with connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              applied_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS certification_tracks (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              exam_code TEXT DEFAULT '',
              description TEXT DEFAULT '',
              position INTEGER DEFAULT 0,
              created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS certification_task_progress (
              track_id TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              completed INTEGER NOT NULL DEFAULT 0,
              completed_at TEXT,
              updated_at TEXT DEFAULT (datetime('now')),
              PRIMARY KEY(track_id, skill_id)
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
              created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS questions (
              id TEXT PRIMARY KEY,
              track_id TEXT NOT NULL,
              test_id TEXT DEFAULT '',
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
              created_at TEXT DEFAULT (datetime('now')),
              FOREIGN KEY(test_id) REFERENCES practice_tests(id) ON DELETE SET DEFAULT
            );

            CREATE TABLE IF NOT EXISTS question_skill_map (
              question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
              track_id TEXT NOT NULL,
              domain_id TEXT DEFAULT '',
              skill_id TEXT NOT NULL,
              confidence REAL DEFAULT 0.5,
              evidence_json TEXT DEFAULT '{}',
              reviewed INTEGER DEFAULT 0,
              created_at TEXT DEFAULT (datetime('now')),
              updated_at TEXT DEFAULT (datetime('now')),
              PRIMARY KEY(question_id, skill_id)
            );

            CREATE TABLE IF NOT EXISTS question_attempts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
              selected TEXT NOT NULL DEFAULT '[]',
              correct INTEGER NOT NULL,
              mode TEXT DEFAULT 'practice',
              attempted_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS exam_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              track_id TEXT NOT NULL,
              practice_test_id TEXT REFERENCES practice_tests(id) ON DELETE SET NULL,
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
              question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
              selected_json TEXT NOT NULL DEFAULT '[]',
              correct INTEGER DEFAULT 0,
              answered_at TEXT DEFAULT (datetime('now')),
              reviewed INTEGER DEFAULT 0,
              UNIQUE(session_id, question_id)
            );

            CREATE TABLE IF NOT EXISTS bookmarks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
              created_at TEXT DEFAULT (datetime('now')),
              UNIQUE(question_id)
            );

            CREATE TABLE IF NOT EXISTS notes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
              body TEXT NOT NULL,
              created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS daily_activity (
              date TEXT PRIMARY KEY,
              questions_answered INTEGER DEFAULT 0,
              correct_answers INTEGER DEFAULT 0,
              minutes_studied INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS learning_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_type TEXT NOT NULL,
              track_id TEXT DEFAULT '',
              practice_test_id TEXT,
              question_id TEXT,
              lab_id TEXT,
              skill_id TEXT,
              metadata_json TEXT DEFAULT '{}',
              created_at TEXT DEFAULT (datetime('now'))
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
            CREATE INDEX IF NOT EXISTS idx_learning_events_track
              ON learning_events(track_id, event_type, created_at);
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations(version, name)
            VALUES (?, ?)
            """,
            (SCHEMA_VERSION, "Certification-native V24 schema; course/video architecture removed"),
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None
