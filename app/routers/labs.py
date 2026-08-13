from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import connect
from ..lab_challenges import lab_by_id, lab_catalog, load_lab_config, validate_sql

router = APIRouter()


class LabSubmit(BaseModel):
    sql: str = ""


@router.get("/labs/config")
def labs_config() -> dict[str, Any]:
    config = load_lab_config()
    return {
        "version": config.get("version"),
        "mode": config.get("mode"),
        "lab_count": len(config.get("labs") or []),
    }


@router.get("/labs")
def labs(certification: str | None = None, track_id: str | None = None) -> dict[str, Any]:
    selected = certification or track_id
    rows = lab_catalog()
    if selected:
        rows = [lab for lab in rows if str(lab.get("certification") or "") == str(selected)]
    completed = set()
    with connect() as conn:
        completed = {
            str(row["lab_id"])
            for row in conn.execute(
                """
                SELECT lab_id FROM learning_events
                WHERE event_type = 'lab_passed' AND lab_id IS NOT NULL
                """
            )
        }
    for lab in rows:
        lab["completed"] = str(lab.get("id")) in completed
    return {"mode": load_lab_config().get("mode", "offline"), "labs": rows}


@router.get("/labs/{lab_id}")
def lab_detail(lab_id: str) -> dict[str, Any]:
    configured = lab_by_id(lab_id)
    if not configured:
        raise HTTPException(status_code=404, detail="Lab not found")
    configured["mode"] = load_lab_config().get("mode", "offline")
    configured["solution_locked"] = True
    return configured


@router.post("/labs/{lab_id}/submit")
def submit_lab(lab_id: str, payload: LabSubmit) -> dict[str, Any]:
    configured = lab_by_id(lab_id)
    if not configured:
        raise HTTPException(status_code=404, detail="Lab not found")
    result = validate_sql(configured, payload.sql or "")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, lab_id, skill_id, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "lab_passed" if result["passed"] else "lab_attempted",
                configured.get("certification") or "snowpro-core",
                str(configured.get("id")),
                configured.get("skill_id"),
                json.dumps(
                    {
                        "lab_id": configured.get("id"),
                        "skill_id": configured.get("skill_id"),
                        "score_pct": result.get("score_pct"),
                        "passed_count": result.get("passed_count"),
                        "total": result.get("total"),
                    }
                ),
            ),
        )
    return {
        "lab": configured,
        **result,
        "hint": None if result["passed"] else _next_hint(configured, result),
    }


def _next_hint(lab: dict[str, Any], result: dict[str, Any]) -> str | None:
    hints = lab.get("hints") or []
    failed = [item for item in result.get("results") or [] if not item.get("passed")]
    if failed:
        message = failed[0].get("message")
        if message and message != "Needs work":
            return message
    return hints[0] if hints else None
