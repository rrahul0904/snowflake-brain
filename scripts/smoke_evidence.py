#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.evidence import evidence_audit, review_mapping
from app.skill_brain import flatten_skills


def build_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE courses (
          id TEXT PRIMARY KEY,
          track_id TEXT DEFAULT '',
          title TEXT DEFAULT ''
        );
        CREATE TABLE practice_tests (
          id TEXT PRIMARY KEY,
          track_id TEXT DEFAULT ''
        );
        CREATE TABLE questions (
          id TEXT PRIMARY KEY,
          question TEXT NOT NULL,
          course_id TEXT,
          course_title TEXT DEFAULT '',
          test_id TEXT DEFAULT ''
        );
        CREATE TABLE question_skill_map (
          question_id TEXT NOT NULL,
          track_id TEXT DEFAULT '',
          domain_id TEXT DEFAULT '',
          skill_id TEXT NOT NULL,
          confidence REAL DEFAULT 0.5,
          evidence_json TEXT DEFAULT '{}',
          reviewed INTEGER DEFAULT 0,
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now')),
          PRIMARY KEY(question_id, skill_id)
        );
        CREATE TABLE lessons (
          id TEXT PRIMARY KEY,
          course_id TEXT,
          course_title TEXT DEFAULT '',
          title TEXT NOT NULL
        );
        CREATE TABLE content_skill_map (
          content_type TEXT NOT NULL,
          content_id TEXT NOT NULL,
          track_id TEXT DEFAULT '',
          domain_id TEXT DEFAULT '',
          skill_id TEXT NOT NULL,
          confidence REAL DEFAULT 0.5,
          evidence_json TEXT DEFAULT '{}',
          reviewed INTEGER DEFAULT 0,
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now')),
          PRIMARY KEY(content_type, content_id, skill_id)
        );
        """
    )
    return conn


def main() -> None:
    skills = flatten_skills("snowpro-core")
    if len(skills) < 2:
        raise AssertionError("SnowPro Core must expose at least two configured skills for evidence smoke testing")
    first, second = skills[0], skills[1]

    conn = build_db()
    conn.execute("INSERT INTO courses(id, track_id, title) VALUES ('c1', 'snowpro-core', 'Core Course')")
    conn.execute("INSERT INTO questions(id, question, course_id, course_title) VALUES ('q1', 'Warehouse sizing question', 'c1', 'Core Course')")
    conn.execute("INSERT INTO questions(id, question, course_id, course_title) VALUES ('q2', 'Unmapped question', 'c1', 'Core Course')")
    conn.execute("INSERT INTO lessons(id, course_id, course_title, title) VALUES ('l1', 'c1', 'Core Course', 'Architecture lesson')")
    conn.execute(
        """
        INSERT INTO question_skill_map(question_id, track_id, domain_id, skill_id, confidence, reviewed, evidence_json)
        VALUES ('q1', 'snowpro-core', ?, ?, 0.40, 0, '{"source":"smoke"}')
        """,
        (first.get("domain_id") or "", first["id"]),
    )
    conn.execute(
        """
        INSERT INTO content_skill_map(content_type, content_id, track_id, domain_id, skill_id, confidence, reviewed)
        VALUES ('lesson', 'l1', 'snowpro-core', ?, ?, 0.90, 1)
        """,
        (first.get("domain_id") or "", first["id"]),
    )

    before = evidence_audit(conn, "snowpro-core", confidence_threshold=0.65, limit=10)
    assert before["questions"]["total"] == 2
    assert before["questions"]["mapped"] == 1
    assert before["questions"]["unmapped"] == 1
    assert before["questions"]["low_confidence"] == 1
    assert before["lessons"]["reviewed"] == 1
    assert {item["item_id"] for item in before["question_review_queue"]} == {"q1", "q2"}

    approved = review_mapping(
        conn,
        mapping_type="question",
        item_id="q1",
        skill_id=first["id"],
        decision="approve",
        track_id="snowpro-core",
    )
    assert approved["status"] == "approved"
    row = conn.execute("SELECT reviewed, confidence FROM question_skill_map WHERE question_id = 'q1'").fetchone()
    assert row["reviewed"] == 1
    assert float(row["confidence"]) >= 0.95

    replaced = review_mapping(
        conn,
        mapping_type="question",
        item_id="q1",
        skill_id=first["id"],
        decision="replace",
        replacement_skill_id=second["id"],
        track_id="snowpro-core",
        confidence=1.0,
    )
    assert replaced["status"] == "replaced"
    row = conn.execute("SELECT skill_id, reviewed, confidence FROM question_skill_map WHERE question_id = 'q1'").fetchone()
    assert row["skill_id"] == second["id"]
    assert row["reviewed"] == 1
    assert float(row["confidence"]) == 1.0

    after = evidence_audit(conn, "snowpro-core", confidence_threshold=0.65, limit=10)
    assert after["questions"]["reviewed"] == 1
    assert after["questions"]["high_confidence"] == 1
    assert [item["item_id"] for item in after["question_review_queue"]] == ["q2"]

    print("Evidence audit and review smoke passed.")


if __name__ == "__main__":
    main()
