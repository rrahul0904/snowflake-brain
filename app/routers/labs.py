from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import connect
from ..lab_challenges import lab_by_id, lab_catalog, load_lab_config, validate_sql
from ..labs import LABS as LEGACY_LABS

router = APIRouter()


class LabSubmit(BaseModel):
    sql: str = ""


@router.get("/labs/config")
def labs_config() -> dict[str, Any]:
    config = load_lab_config()
    return {"version": config.get("version"), "mode": config.get("mode"), "lab_count": len(config.get("labs") or [])}


@router.get("/labs")
def labs(certification: str | None = None, track_id: str | None = None) -> dict[str, Any]:
    selected_certification = certification or track_id
    config_labs = lab_catalog()
    if selected_certification:
        config_labs = [lab for lab in config_labs if str(lab.get("certification") or "") == str(selected_certification)]
    completed = set()
    with connect() as conn:
        try:
            completed = {
                str(row["lab_id"])
                for row in conn.execute(
                    """
                    SELECT lab_id FROM learning_events
                    WHERE event_type = 'lab_passed' AND lab_id IS NOT NULL
                    """
                )
            }
        except Exception:
            completed = set()
    if config_labs:
        for lab in config_labs:
            lab["completed"] = str(lab.get("id")) in completed
        return {"mode": load_lab_config().get("mode"), "labs": config_labs}

    # Legacy DB/static fallback.
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM lab_exercises ORDER BY position, id")]
        completed_db = {
            str(row["exercise_id"])
            for row in conn.execute("SELECT DISTINCT exercise_id FROM lab_submissions WHERE passed = 1")
        }
    if rows:
        return {"mode": "legacy", "labs": [_legacy_lab(row, str(row["id"]) in completed_db) for row in rows]}
    return {"mode": "legacy", "labs": LEGACY_LABS}


@router.get("/labs/{lab_id}")
def lab_detail(lab_id: str) -> dict[str, Any]:
    configured = lab_by_id(lab_id)
    if configured:
        configured["mode"] = load_lab_config().get("mode", "offline")
        configured["solution_locked"] = True
        return configured

    if lab_id.isdigit():
        with connect() as conn:
            row = conn.execute("SELECT * FROM lab_exercises WHERE id = ?", (int(lab_id),)).fetchone()
            if row:
                return _legacy_lab(dict(row), False)
    for lab in LEGACY_LABS:
        if str(lab.get("id")) == str(lab_id):
            return lab
    raise HTTPException(status_code=404, detail="Lab not found")


@router.post("/labs/{lab_id}/submit")
def submit_lab(lab_id: str, payload: LabSubmit) -> dict[str, Any]:
    sql = payload.sql or ""
    configured = lab_by_id(lab_id)
    if configured:
        result = validate_sql(configured, sql)
        with connect() as conn:
            # Store local challenge events without forcing a new schema migration.
            conn.execute(
                """
                INSERT INTO learning_events(event_type, track_id, lab_id, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    "lab_passed" if result["passed"] else "lab_attempted",
                    configured.get("certification") or "snowpro-core",
                    configured.get("id"),
                    json.dumps({
                        "lab_id": configured.get("id"),
                        "skill_id": configured.get("skill_id"),
                        "score_pct": result.get("score_pct"),
                        "passed_count": result.get("passed_count"),
                        "total": result.get("total"),
                    }),
                ),
            )
        return {"lab": configured, **result, "hint": None if result["passed"] else _next_hint(configured, result)}

    # Legacy integer lab validation fallback.
    if not lab_id.isdigit():
        raise HTTPException(status_code=404, detail="Lab not found")
    with connect() as conn:
        row = conn.execute("SELECT * FROM lab_exercises WHERE id = ?", (int(lab_id),)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Lab not found")
        lab = dict(row)
        expected = json.loads(lab.get("expected_output") or "{}")
        keywords = expected.get("keywords") or []
        normalized = " ".join(sql.upper().split())
        missing = [keyword for keyword in keywords if keyword.upper() not in normalized]
        passed = not missing
        feedback = "Correct. Your SQL includes the required Snowflake clauses." if passed else "Missing required clause(s): " + ", ".join(missing)
        conn.execute(
            """
            INSERT INTO lab_submissions(exercise_id, submitted_sql, passed, feedback)
            VALUES (?, ?, ?, ?)
            """,
            (int(lab_id), sql, 1 if passed else 0, feedback),
        )
    return {"passed": passed, "feedback": feedback, "hint": None if passed else lab.get("hint"), "results": []}


def _next_hint(lab: dict[str, Any], result: dict[str, Any]) -> str | None:
    hints = lab.get("hints") or []
    failed = [item for item in result.get("results") or [] if not item.get("passed")]
    if failed:
        return failed[0].get("message") if failed[0].get("message") != "Needs work" else (hints[0] if hints else None)
    return hints[0] if hints else None


def _legacy_lab(row: dict[str, Any], completed: bool) -> dict[str, Any]:
    row["tags"] = json.loads(row.get("tags") or "[]")
    row["completed"] = completed
    row.setdefault("id", str(row.get("id")))
    return row
