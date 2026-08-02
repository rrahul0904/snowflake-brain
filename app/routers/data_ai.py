from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import connect

router = APIRouter()

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "data_ai_academy.json"
TRACK_ID = "data-ai-academy"


class KnowledgeCheckSubmission(BaseModel):
    selected_index: int


class LabSubmission(BaseModel):
    code: str = ""


@lru_cache(maxsize=1)
def _curriculum() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise RuntimeError("Data + AI curriculum configuration is missing")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _lessons() -> list[dict[str, Any]]:
    return [lesson for module in _curriculum().get("modules", []) for lesson in module.get("lessons", [])]


def _lesson(lesson_id: str) -> dict[str, Any] | None:
    return next((lesson for lesson in _lessons() if lesson.get("id") == lesson_id), None)


def _check(check_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for lesson in _lessons():
        check = lesson.get("knowledge_check") or {}
        if check.get("id") == check_id:
            return lesson, check
    return None


def _lab(lab_id: str) -> dict[str, Any] | None:
    return next((lab for lab in _curriculum().get("labs", []) if lab.get("id") == lab_id), None)


def _event_ids(event_type: str, metadata_key: str) -> set[str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT metadata_json FROM learning_events WHERE track_id = ? AND event_type = ?",
            (TRACK_ID, event_type),
        ).fetchall()
    values: set[str] = set()
    for row in rows:
        try:
            value = json.loads(row["metadata_json"] or "{}").get(metadata_key)
            if value:
                values.add(str(value))
        except (TypeError, json.JSONDecodeError):
            continue
    return values


def _record_event(event_type: str, metadata: dict[str, Any], lesson_id: str | None = None, lab_id: str | None = None) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, lesson_id, lab_id, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, TRACK_ID, lesson_id, lab_id, json.dumps(metadata)),
        )


@router.get("/data-ai/curriculum")
def curriculum() -> dict[str, Any]:
    data = copy.deepcopy(_curriculum())
    completed_lessons = _event_ids("data_ai_lesson_completed", "lesson_id")
    passed_checks = _event_ids("data_ai_check_passed", "check_id")
    passed_labs = _event_ids("data_ai_lab_passed", "lab_id")

    for module in data.get("modules", []):
        for lesson in module.get("lessons", []):
            lesson["completed"] = lesson.get("id") in completed_lessons
            check = lesson.get("knowledge_check") or {}
            check["passed"] = check.get("id") in passed_checks
            check.pop("correct_index", None)
            check.pop("explanation", None)
    for lab in data.get("labs", []):
        lab["completed"] = lab.get("id") in passed_labs
        lab.pop("solution", None)

    total_lessons = len(_lessons())
    total_checks = total_lessons
    total_labs = len(data.get("labs", []))
    total_evidence = total_lessons + total_checks + total_labs
    complete_evidence = len(completed_lessons) + len(passed_checks) + len(passed_labs)
    data["progress"] = {
        "lessons_completed": len(completed_lessons),
        "checks_passed": len(passed_checks),
        "labs_passed": len(passed_labs),
        "total_lessons": total_lessons,
        "total_checks": total_checks,
        "total_labs": total_labs,
        "percent": round((complete_evidence / total_evidence) * 100) if total_evidence else 0,
    }
    return data


@router.post("/data-ai/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: str) -> dict[str, Any]:
    lesson = _lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Data + AI lesson not found")
    _record_event("data_ai_lesson_completed", {"lesson_id": lesson_id}, lesson_id=lesson_id)
    return {"ok": True, "lesson_id": lesson_id, "completed": True}


@router.post("/data-ai/checks/{check_id}/submit")
def submit_check(check_id: str, payload: KnowledgeCheckSubmission) -> dict[str, Any]:
    match = _check(check_id)
    if not match:
        raise HTTPException(status_code=404, detail="Knowledge check not found")
    lesson, check = match
    options = check.get("options") or []
    if payload.selected_index < 0 or payload.selected_index >= len(options):
        raise HTTPException(status_code=400, detail="Selected answer is outside the available options")
    correct_index = int(check.get("correct_index", -1))
    correct = payload.selected_index == correct_index
    if correct:
        _record_event(
            "data_ai_check_passed",
            {"check_id": check_id, "lesson_id": lesson.get("id")},
            lesson_id=str(lesson.get("id")),
        )
    return {
        "correct": correct,
        "correct_index": correct_index,
        "explanation": check.get("explanation") or "Review the lesson and try again.",
    }


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").lower())


@router.post("/data-ai/labs/{lab_id}/submit")
def submit_lab(lab_id: str, payload: LabSubmission) -> dict[str, Any]:
    lab = _lab(lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="Data + AI lab not found")
    submitted = _compact(payload.code)
    results: list[dict[str, Any]] = []
    for test in lab.get("validation_tests", []):
        required = [item for item in test.get("required", []) if item]
        forbidden = [item for item in test.get("forbidden", []) if item]
        missing = [item for item in required if _compact(item) not in submitted]
        forbidden_found = [item for item in forbidden if _compact(item) in submitted]
        passed = not missing and not forbidden_found
        results.append(
            {
                "name": test.get("name") or "Validation",
                "passed": passed,
                "missing": missing,
                "forbidden_found": forbidden_found,
                "message": "Passed" if passed else "Add the missing evidence or remove the unsafe pattern.",
            }
        )
    passed_count = sum(1 for result in results if result["passed"])
    passed = bool(results) and passed_count == len(results)
    if passed:
        _record_event("data_ai_lab_passed", {"lab_id": lab_id}, lab_id=lab_id)
    return {
        "passed": passed,
        "passed_count": passed_count,
        "total": len(results),
        "score_pct": round((passed_count / len(results)) * 100) if results else 0,
        "results": results,
        "solution": lab.get("solution") if not passed else None,
    }
