#!/usr/bin/env python3
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-question-version-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "question-version.sqlite")

from app.database import connect, run_migrations  # noqa: E402
from app.question_versions import ensure_question_version_schema  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def insert_question(question_id: str, text: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO questions(
              id, track_id, test_title, question, options_json, correct_json,
              explanation, source_path, source_kind, assessment_type,
              tags, difficulty, multiple, question_position
            ) VALUES (?, 'snowpro-core', 'Version Test', ?, '[""A"",""B"",""C""]', '[1]',
                      'Version test explanation with enough content.', 'private://version-test',
                      'private_bank', 'bank_scenario', '[]', 'medium', 0, 1)
            """.replace('[""A"",""B"",""C""]', '["A","B","C"]'),
            (question_id, text),
        )


def main() -> None:
    run_migrations()

    # Existing rows are baselined when the version schema is installed.
    insert_question("version::existing", "Existing question version one before migration.")
    ensure_question_version_schema()
    with connect() as conn:
        existing_versions = conn.execute(
            "SELECT version_number,question FROM question_versions WHERE question_id='version::existing' ORDER BY version_number"
        ).fetchall()
    check(len(existing_versions) == 1 and existing_versions[0]["version_number"] == 1, "existing question is baselined to immutable v1")

    # New rows created after startup receive v1 automatically.
    insert_question("version::new", "New question version one after migration.")
    with connect() as conn:
        created_versions = conn.execute(
            "SELECT version_number,question FROM question_versions WHERE question_id='version::new' ORDER BY version_number"
        ).fetchall()
    check(len(created_versions) == 1 and created_versions[0]["version_number"] == 1, "new question automatically receives v1")

    # An unserved authoring correction creates a new immutable version.
    with connect() as conn:
        conn.execute(
            "UPDATE questions SET question='New question version two before it was ever served.' WHERE id='version::new'"
        )
    with connect() as conn:
        versions = conn.execute(
            "SELECT id,version_number,question FROM question_versions WHERE question_id='version::new' ORDER BY version_number"
        ).fetchall()
    check([row["version_number"] for row in versions] == [1, 2], "content update creates v2")
    v2_id = int(versions[-1]["id"])

    # A timed sitting automatically binds to the exact current version.
    with connect() as conn:
        session_id = int(
            conn.execute(
                "INSERT INTO exam_sessions(track_id,mode,total_questions,status) VALUES ('snowpro-core','exam_full_mock',1,'in_progress')"
            ).lastrowid
        )
        conn.execute(
            """
            INSERT INTO exam_session_questions(
              session_id,question_id,position,options_json,correct_positions_json,flagged
            ) VALUES (?,'version::new',1,'["A","B","C"]','[1]',0)
            """,
            (session_id,),
        )
        linked = conn.execute(
            "SELECT question_version_id FROM exam_session_questions WHERE session_id=? AND question_id='version::new'",
            (session_id,),
        ).fetchone()
    check(int(linked["question_version_id"]) == v2_id, "timed sitting points to the exact served question version")

    # Once served, physical content can no longer be overwritten under the same
    # question ID. Authors must create a new revision/logical release entry.
    blocked = False
    try:
        with connect() as conn:
            conn.execute(
                "UPDATE questions SET question='ILLEGAL version three overwrite.' WHERE id='version::new'"
            )
    except sqlite3.IntegrityError as exc:
        blocked = "served question content is immutable" in str(exc)
    check(blocked, "served question content mutation is rejected by the database")

    with connect() as conn:
        current = conn.execute("SELECT question FROM questions WHERE id='version::new'").fetchone()
        version_count = int(
            conn.execute("SELECT COUNT(*) AS count FROM question_versions WHERE question_id='version::new'").fetchone()["count"]
        )
    check(current["question"] == "New question version two before it was ever served.", "blocked overwrite leaves served content unchanged")
    check(version_count == 2, "blocked overwrite cannot create a phantom version")

    # Even the session->version pointer itself is immutable after assignment.
    relink_blocked = False
    try:
        with connect() as conn:
            conn.execute(
                "UPDATE exam_session_questions SET question_version_id=? WHERE session_id=? AND question_id='version::new'",
                (int(versions[0]["id"]), session_id),
            )
    except sqlite3.IntegrityError as exc:
        relink_blocked = "exam question version link is immutable" in str(exc)
    check(relink_blocked, "historical sitting cannot be relinked to a different question revision")

    print("Immutable question version and historical sitting linkage checks passed.")


if __name__ == "__main__":
    main()
