#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-cert-v24-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "certification.sqlite")

from app.config import BRAIN_DB, DATABASE_BACKEND  # noqa: E402
from app.database import connect, database_health, run_migrations  # noqa: E402
from app.evidence import evidence_audit  # noqa: E402
from app.routers.certification_practice import CertificationQuizStart, certification_quiz_start  # noqa: E402
from app.routers.questions import QuizAnswer, QuizGradeRequest, quiz_grade  # noqa: E402
from app.skill_brain import flatten_skills, load_skill_map  # noqa: E402


FORBIDDEN_TABLES = {
    "courses",
    "course_sections",
    "lessons",
    "documents",
    "transcript_chunks",
    "lesson_progress",
    "lab_exercises",
    "lab_submissions",
}

FORBIDDEN_RUNTIME_TOKENS = {
    "CONTENT_ROOT",
    "AUTO_INGEST",
    "VIDEO_EXTENSIONS",
    "video_path",
    "vtt_path",
    "transcript_path",
    "transcript_chunks",
    "course_sections",
    "lesson_progress",
    "#/video",
    "#/archive",
}

RUNTIME_FILES = [
    ROOT / "app" / "config.py",
    ROOT / "app" / "database.py",
    ROOT / "app" / "main.py",
    ROOT / "app" / "serializers.py",
    ROOT / "app" / "intelligence.py",
    ROOT / "app" / "evidence.py",
    *sorted((ROOT / "app" / "routers").glob("*.py")),
    ROOT / "frontend" / "api.js",
    ROOT / "frontend" / "router.js",
    ROOT / "frontend" / "components" / "nav.js",
    *sorted((ROOT / "frontend" / "views").glob("*.js")),
]


def assert_no_legacy_runtime_tokens() -> None:
    violations: list[str] = []
    for path in RUNTIME_FILES:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_RUNTIME_TOKENS:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)} contains {token!r}")
    assert not violations, "Legacy course/video runtime tokens remain:\n" + "\n".join(violations)


def table_names(conn) -> set[str]:
    if DATABASE_BACKEND == "postgresql":
        rows = conn.execute(
            "SELECT table_name AS name FROM information_schema.tables WHERE table_schema=current_schema()"
        ).fetchall()
    else:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(row["name"]) for row in rows}


def question_column_names(conn) -> set[str]:
    if DATABASE_BACKEND == "postgresql":
        rows = conn.execute(
            """
            SELECT column_name AS name
            FROM information_schema.columns
            WHERE table_schema=current_schema() AND table_name='questions'
            """
        ).fetchall()
    else:
        rows = conn.execute("PRAGMA table_info(questions)").fetchall()
    return {str(row["name"]) for row in rows}


def main() -> None:
    run_migrations()
    health = database_health()
    assert health.get("status") == "ok"
    assert health.get("backend") == DATABASE_BACKEND
    if DATABASE_BACKEND == "sqlite":
        assert Path(BRAIN_DB).exists()

    with connect() as conn:
        tables = table_names(conn)
        leaked = sorted(FORBIDDEN_TABLES & tables)
        assert not leaked, f"Legacy tables still exist in clean certification DB: {leaked}"

        required = {
            "certification_tracks",
            "certification_task_progress",
            "practice_tests",
            "questions",
            "question_skill_map",
            "question_attempts",
            "exam_sessions",
            "exam_session_answers",
            "bookmarks",
            "notes",
            "daily_activity",
            "learning_events",
        }
        assert required <= tables, f"Missing certification-native tables: {sorted(required - tables)}"

        question_columns = question_column_names(conn)
        assert "track_id" in question_columns
        assert "source_kind" in question_columns
        assert "course_id" not in question_columns
        assert "course_title" not in question_columns

        cert = next(item for item in load_skill_map()["certifications"] if item["id"] == "snowpro-core")
        assert [domain["weight"] for domain in cert["domains"]] == [31, 20, 18, 21, 10]
        skills = flatten_skills("snowpro-core")
        assert len(skills) == 19
        assert [skill["task_code"] for skill in skills] == [
            "1.1", "1.2", "1.3", "1.4", "1.5", "1.6",
            "2.1", "2.2", "2.3",
            "3.1", "3.2", "3.3",
            "4.1", "4.2", "4.3", "4.4",
            "5.1", "5.2", "5.3",
        ]

        started = certification_quiz_start(
            CertificationQuizStart(track_id="snowpro-core", count=15, mode="drill"),
            {"id": 0},
        )
        assert started["total"] == 15
        assert started["questions"]
        assert all(question.get("track_id") == "snowpro-core" for question in started["questions"])
        assert "course_id" not in started["questions"][0]

        first = started["questions"][0]
        stored = conn.execute("SELECT correct_json FROM questions WHERE id = ?", (first["id"],)).fetchone()
        assert stored is not None
        import json

        correct = [int(value) for value in json.loads(stored["correct_json"])]
        graded = quiz_grade(
            QuizGradeRequest(answers=[QuizAnswer(question_id=first["id"], selected=correct)]),
            {"id": 0},
        )
        assert graded["score"] == 1 and graded["total"] == 1

        # A retired task mapping must be classified as stale and ignored for trust.
        conn.execute(
            """
            INSERT INTO question_skill_map(question_id, track_id, domain_id, skill_id, confidence, reviewed)
            VALUES (?, 'snowpro-core', 'retired-domain', 'retired-old-core-skill', 0.99, 1)
            """,
            (first["id"],),
        )
        audit = evidence_audit(conn, "snowpro-core")
        assert audit["stale_mapping_edges"] >= 1

    assert_no_legacy_runtime_tokens()

    assert not (ROOT / "app" / "ingest.py").exists()
    assert not (ROOT / "app" / "routers" / "courses.py").exists()
    assert not (ROOT / "frontend" / "views" / "academy.js").exists()

    print("Certification-native architecture smoke passed")
    print(f"database_backend={DATABASE_BACKEND} database={BRAIN_DB if DATABASE_BACKEND == 'sqlite' else health.get('schema')}")
    print("domains=5 tasks=19 course_video_tables=0")
    print(f"seeded_questions={started['total']} stale_edges={audit['stale_mapping_edges']}")


if __name__ == "__main__":
    try:
        main()
    finally:
        TEMP.cleanup()
