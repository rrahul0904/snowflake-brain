#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.database import connect, run_migrations
from app.intelligence import build_question_skill_map


def _correct_indices(question: dict[str, Any]) -> list[int]:
    options = question.get("options") or []
    by_letter = {str(option.get("letter") or "").strip(): index for index, option in enumerate(options)}
    return sorted({by_letter[letter] for letter in question.get("correct") or [] if letter in by_letter})


def _source_kind(exam_code: str) -> tuple[str, int]:
    return ("source", 0) if str(exam_code).upper() == "COF-C03" else ("legacy", 1)


def import_bank(path: Path, track_id: str = "snowpro-core", replace: bool = False) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    banks = payload.get("banks") or []
    run_migrations()
    counts = {"banks": 0, "tests": 0, "questions": 0, "current_questions": 0, "legacy_questions": 0}

    with connect() as conn:
        if replace:
            source_tests = [
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM practice_tests WHERE track_id = ? AND source_kind IN ('source','legacy')",
                    (track_id,),
                )
            ]
            if source_tests:
                placeholders = ",".join("?" for _ in source_tests)
                conn.execute(f"DELETE FROM questions WHERE test_id IN ({placeholders})", source_tests)
                conn.execute(f"DELETE FROM practice_tests WHERE id IN ({placeholders})", source_tests)

        for bank in banks:
            exam_code = str(bank.get("exam_code") or "").upper()
            source_kind, is_legacy = _source_kind(exam_code)
            counts["banks"] += 1
            for position, test in enumerate(bank.get("tests") or [], start=1):
                raw_test_id = str(test.get("id") or f"exam-{position}")
                test_id = f"imported::{track_id}::{exam_code.lower()}::{bank.get('id')}::{raw_test_id}"
                test_title = str(test.get("title") or f"Practice Exam {position}")
                questions = test.get("questions") or []
                conn.execute(
                    """
                    INSERT INTO practice_tests(
                      id, track_id, title, exam_code, source_kind, source_path,
                      position, question_count, version, is_legacy
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      title=excluded.title,
                      exam_code=excluded.exam_code,
                      source_kind=excluded.source_kind,
                      source_path=excluded.source_path,
                      position=excluded.position,
                      question_count=excluded.question_count,
                      version=excluded.version,
                      is_legacy=excluded.is_legacy
                    """,
                    (
                        test_id,
                        track_id,
                        test_title,
                        exam_code,
                        source_kind,
                        str(bank.get("source") or path),
                        position,
                        len(questions),
                        str(test.get("version") or ""),
                        is_legacy,
                    ),
                )
                counts["tests"] += 1

                for q_position, question in enumerate(questions, start=1):
                    options = [str(item.get("text") or "") for item in question.get("options") or []]
                    correct = _correct_indices(question)
                    raw_question_id = str(question.get("id") or f"q-{q_position}")
                    question_id = f"{test_id}::{raw_question_id}"
                    assessment_type = "multi-select" if len(correct) > 1 else "single-select"
                    conn.execute(
                        """
                        INSERT INTO questions(
                          id, track_id, test_id, test_title, question, options_json,
                          correct_json, explanation, source_path, source_kind,
                          assessment_type, tags, difficulty, multiple, question_position
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'medium', ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                          track_id=excluded.track_id,
                          test_id=excluded.test_id,
                          test_title=excluded.test_title,
                          question=excluded.question,
                          options_json=excluded.options_json,
                          correct_json=excluded.correct_json,
                          explanation=excluded.explanation,
                          source_path=excluded.source_path,
                          source_kind=excluded.source_kind,
                          assessment_type=excluded.assessment_type,
                          multiple=excluded.multiple,
                          question_position=excluded.question_position
                        """,
                        (
                            question_id,
                            track_id,
                            test_id,
                            test_title,
                            str(question.get("question") or ""),
                            json.dumps(options, ensure_ascii=False),
                            json.dumps(correct),
                            str(question.get("explanation") or ""),
                            str(bank.get("source") or path),
                            source_kind,
                            assessment_type,
                            json.dumps([exam_code, bank.get("id"), raw_test_id], ensure_ascii=False),
                            int(len(correct) > 1),
                            q_position,
                        ),
                    )
                    counts["questions"] += 1
                    if is_legacy:
                        counts["legacy_questions"] += 1
                    else:
                        counts["current_questions"] += 1

        mapping = build_question_skill_map(conn, track_id)
        counts["mapped"] = int(mapping.get("mapped") or 0)
        counts["low_confidence"] = int(mapping.get("low_confidence") or 0)

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import normalized Snowflake certification practice exams into V24.")
    parser.add_argument("json_path", type=Path, help="Path to normalized practice-bank JSON")
    parser.add_argument("--track-id", default="snowpro-core")
    parser.add_argument("--replace", action="store_true", help="Replace previously imported current/legacy source tests for this track")
    args = parser.parse_args()
    if not args.json_path.exists():
        raise SystemExit(f"File not found: {args.json_path}")
    result = import_bank(args.json_path, track_id=args.track_id, replace=args.replace)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
