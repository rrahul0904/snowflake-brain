from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from .config import DATABASE_BACKEND
from .database import connect


SCHEMA_VERSION = "20260815_070_adaptive_readiness_v2"


class AdaptiveReadinessError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace(" ", "T")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _table_exists(conn: Any, table: str) -> bool:
    if DATABASE_BACKEND == "postgresql":
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=current_schema() AND table_name=?",
            (table,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
    return bool(row and int(row["n"]) > 0)


def _columns(conn: Any, table: str) -> set[str]:
    if DATABASE_BACKEND == "postgresql":
        rows = conn.execute(
            "SELECT column_name AS name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=?",
            (table,),
        ).fetchall()
    else:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}


def ensure_adaptive_readiness_schema() -> None:
    with connect() as conn:
        if conn.execute("SELECT 1 FROM schema_migrations WHERE version=?", (SCHEMA_VERSION,)).fetchone():
            return
        if DATABASE_BACKEND == "postgresql":
            raise RuntimeError("PostgreSQL adaptive readiness migration was not applied")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS candidate_readiness_snapshots (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
              track_id TEXT NOT NULL,
              readiness_score REAL NOT NULL CHECK(readiness_score BETWEEN 0 AND 100),
              evidence_confidence TEXT NOT NULL CHECK(evidence_confidence IN ('low','medium','high')),
              readiness_band TEXT NOT NULL,
              mastery_score REAL NOT NULL DEFAULT 0,
              retention_score REAL NOT NULL DEFAULT 0,
              calibration_score REAL NOT NULL DEFAULT 0,
              mock_score REAL NOT NULL DEFAULT 0,
              coverage_score REAL NOT NULL DEFAULT 0,
              pace_score REAL NOT NULL DEFAULT 0,
              unique_questions_seen INTEGER NOT NULL DEFAULT 0,
              recent_mock_count INTEGER NOT NULL DEFAULT 0,
              exam_date TEXT,
              runway_days INTEGER,
              recommended_daily_minutes INTEGER NOT NULL DEFAULT 0,
              evidence_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS candidate_adaptive_recommendations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
              track_id TEXT NOT NULL,
              recommendation_type TEXT NOT NULL,
              domain_id TEXT NOT NULL DEFAULT '',
              skill_id TEXT NOT NULL DEFAULT '',
              priority_score REAL NOT NULL DEFAULT 0,
              reason_code TEXT NOT NULL,
              reason_text TEXT NOT NULL,
              action_json TEXT NOT NULL DEFAULT '{}',
              source_snapshot_id INTEGER REFERENCES candidate_readiness_snapshots(id) ON DELETE CASCADE,
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_readiness_candidate_track
              ON candidate_readiness_snapshots(candidate_id,track_id,created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_adaptive_recommendation_candidate
              ON candidate_adaptive_recommendations(candidate_id,track_id,priority_score DESC,created_at DESC);
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
            (SCHEMA_VERSION, "SQLite evidence-based adaptive readiness intelligence"),
        )


def _active_release_question_ids(conn: Any, track_id: str) -> set[str]:
    """Return only canonical active-release question IDs when a release exists."""
    if _table_exists(conn, "question_bank_releases") and _table_exists(conn, "question_bank_release_questions"):
        release = conn.execute(
            "SELECT id FROM question_bank_releases WHERE track_id=? AND status='active' ORDER BY activated_at DESC,id DESC LIMIT 1",
            (track_id,),
        ).fetchone()
        if release:
            rows = conn.execute(
                "SELECT question_id FROM question_bank_release_questions WHERE release_id=?",
                (int(release["id"]),),
            ).fetchall()
            return {str(row["question_id"]) for row in rows}
    rows = conn.execute("SELECT id FROM questions WHERE track_id=?", (track_id,)).fetchall()
    return {str(row["id"]) for row in rows}


def _question_metadata(conn: Any, track_id: str, eligible: set[str]) -> dict[str, dict[str, str]]:
    rows = conn.execute(
        "SELECT id,difficulty FROM questions WHERE track_id=?",
        (track_id,),
    ).fetchall()
    metadata = {
        str(row["id"]): {
            "difficulty": str(row["difficulty"] or "medium").lower(),
            "domain_id": "unmapped",
            "skill_id": "unmapped",
        }
        for row in rows
        if str(row["id"]) in eligible
    }
    if metadata and _table_exists(conn, "question_bank_metadata"):
        mappings = conn.execute(
            "SELECT question_id,domain_id,task_id FROM question_bank_metadata WHERE authoring_status='active'"
        ).fetchall()
        for row in mappings:
            question_id = str(row["question_id"])
            if question_id in metadata:
                metadata[question_id]["domain_id"] = str(row["domain_id"] or "unmapped")
                metadata[question_id]["skill_id"] = str(row["task_id"] or "unmapped")
        return metadata
    if metadata and _table_exists(conn, "question_skill_map"):
        columns = _columns(conn, "question_skill_map")
        if {"question_id", "skill_id"} <= columns:
            domain_expr = "domain_id" if "domain_id" in columns else "'' AS domain_id"
            mappings = conn.execute(
                f"SELECT question_id,skill_id,{domain_expr} FROM question_skill_map ORDER BY question_id"
            ).fetchall()
            seen: set[str] = set()
            for row in mappings:
                question_id = str(row["question_id"])
                if question_id in metadata and question_id not in seen:
                    seen.add(question_id)
                    metadata[question_id]["skill_id"] = str(row["skill_id"] or "unmapped")
                    metadata[question_id]["domain_id"] = str(row["domain_id"] or "unmapped")
    return metadata


def _attempts(conn: Any, candidate_id: int, eligible: set[str]) -> list[dict[str, Any]]:
    if not eligible:
        return []
    columns = _columns(conn, "question_attempts")
    response = "response_time_ms" if "response_time_ms" in columns else "NULL AS response_time_ms"
    confidence = "confidence" if "confidence" in columns else "NULL AS confidence"
    rows = conn.execute(
        f"SELECT id,question_id,correct,mode,attempted_at,{response},{confidence} FROM question_attempts WHERE candidate_id=? ORDER BY attempted_at,id",
        (candidate_id,),
    ).fetchall()
    return [dict(row) for row in rows if str(row["question_id"]) in eligible]


def _recency(attempted_at: Any, half_life_days: float = 30.0) -> float:
    parsed = _parse_time(attempted_at)
    if not parsed:
        return 0.6
    age_days = max(0.0, (_now() - parsed).total_seconds() / 86400.0)
    return math.exp(-math.log(2.0) * age_days / half_life_days)


def _median_response(attempts: list[dict[str, Any]]) -> float | None:
    values = [
        float(row["response_time_ms"])
        for row in attempts
        if row.get("response_time_ms") not in (None, "", 0) and float(row["response_time_ms"]) > 0
    ]
    return statistics.median(values) if values else None


def _signals(attempt: dict[str, Any], difficulty: str, median_ms: float | None) -> dict[str, Any]:
    correct = bool(int(attempt.get("correct") or 0))
    confidence = int(attempt["confidence"]) if attempt.get("confidence") not in (None, "") else None
    response_ms = float(attempt["response_time_ms"]) if attempt.get("response_time_ms") not in (None, "", 0) else None
    recency = _recency(attempt.get("attempted_at"))
    calibration = 0.72
    if confidence is not None:
        calibration = max(0.0, 1.0 - abs(confidence / 5.0 - (1.0 if correct else 0.0)))
    probable_guess = bool(
        correct
        and confidence is not None
        and confidence <= 2
        and response_ms is not None
        and median_ms is not None
        and response_ms < max(700.0, median_ms * 0.38)
    )
    mastery = 1.0 if correct else 0.0
    if probable_guess:
        mastery *= 0.55
    if not correct and confidence is not None and confidence >= 4:
        mastery = 0.0
    difficulty_factor = {"easy": 0.95, "medium": 1.0, "hard": 1.08}.get(difficulty, 1.0)
    mastery = max(0.0, min(1.0, mastery * recency * difficulty_factor))
    pace = 0.7
    if response_ms and median_ms:
        ratio = median_ms / max(500.0, response_ms)
        pace = max(0.35, min(1.0, 0.72 + 0.22 * math.log2(max(0.25, min(4.0, ratio)))))
    return {
        "mastery": mastery,
        "calibration": calibration,
        "pace": pace,
        "probable_guess": probable_guess,
        "recency": recency,
    }


def _srs(conn: Any, candidate_id: int, eligible: set[str]) -> dict[str, Any]:
    if not _table_exists(conn, "candidate_srs_state"):
        return {"due": 0, "overdue": 0, "total": 0, "retention": 0.5, "due_ids": set()}
    rows = conn.execute(
        "SELECT question_id,due_at,last_correct,repetitions,lapses FROM candidate_srs_state WHERE candidate_id=?",
        (candidate_id,),
    ).fetchall()
    now = _now()
    due = overdue = total = 0
    retained = 0.0
    due_ids: set[str] = set()
    for row in rows:
        question_id = str(row["question_id"])
        if question_id not in eligible:
            continue
        total += 1
        due_at = _parse_time(row["due_at"])
        if due_at and due_at <= now:
            due += 1
            due_ids.add(question_id)
            if (now - due_at).total_seconds() >= 2 * 86400:
                overdue += 1
        base = 0.75 if row["last_correct"] in (1, True) else 0.25
        base += min(0.15, int(row["repetitions"] or 0) * 0.025)
        base -= min(0.25, int(row["lapses"] or 0) * 0.04)
        retained += max(0.0, min(1.0, base))
    retention = retained / total if total else 0.5
    if total:
        retention *= max(0.5, 1.0 - due / total * 0.15 - overdue / total * 0.35)
    return {
        "due": due,
        "overdue": overdue,
        "total": total,
        "retention": max(0.0, min(1.0, retention)),
        "due_ids": due_ids,
    }


def _mocks(conn: Any, candidate_id: int, track_id: str) -> dict[str, Any]:
    if not _table_exists(conn, "exam_sessions"):
        return {"count": 0, "score": 0.5}
    rows = conn.execute(
        "SELECT scaled_score,weighted_accuracy,raw_accuracy FROM exam_sessions WHERE candidate_id=? AND track_id=? AND status='submitted' ORDER BY finished_at DESC,id DESC LIMIT 5",
        (candidate_id, track_id),
    ).fetchall()
    values: list[float] = []
    for row in rows:
        value = row["scaled_score"]
        if value not in (None, ""):
            numeric = float(value)
            values.append(max(0.0, min(1.0, numeric / (1000.0 if numeric > 100 else 100.0))))
            continue
        weighted = row["weighted_accuracy"]
        raw = row["raw_accuracy"]
        chosen = weighted if weighted not in (None, "") else raw
        if chosen not in (None, ""):
            numeric = float(chosen)
            values.append(max(0.0, min(1.0, numeric / 100.0 if numeric > 1 else numeric)))
    return {"count": len(values), "score": sum(values) / len(values) if values else 0.5}


def _preferences(conn: Any, candidate_id: int, track_id: str) -> dict[str, Any]:
    if not _table_exists(conn, "candidate_study_preferences"):
        return {"exam_date": None, "runway_days": None, "daily_minutes": 30, "days_per_week": 5}
    row = conn.execute(
        "SELECT exam_date,daily_minutes,days_per_week FROM candidate_study_preferences WHERE candidate_id=? AND track_id=?",
        (candidate_id, track_id),
    ).fetchone()
    if not row:
        return {"exam_date": None, "runway_days": None, "daily_minutes": 30, "days_per_week": 5}
    exam_date = str(row["exam_date"] or "") or None
    runway = None
    if exam_date:
        try:
            runway = (date.fromisoformat(exam_date) - _now().date()).days
        except Exception:
            runway = None
    return {
        "exam_date": exam_date,
        "runway_days": runway,
        "daily_minutes": max(10, int(row["daily_minutes"] or 30)),
        "days_per_week": max(1, min(7, int(row["days_per_week"] or 5))),
    }


def _skill_scores(attempts: list[dict[str, Any]], metadata: dict[str, dict[str, str]], median_ms: float | None) -> dict[tuple[str, str], dict[str, float]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for attempt in attempts:
        meta = metadata.get(str(attempt["question_id"]), {})
        key = (str(meta.get("domain_id") or "unmapped"), str(meta.get("skill_id") or "unmapped"))
        buckets[key].append(attempt)
    results: dict[tuple[str, str], dict[str, float]] = {}
    for key, rows in buckets.items():
        signals = [_signals(row, metadata.get(str(row["question_id"]), {}).get("difficulty", "medium"), median_ms) for row in rows]
        results[key] = {
            "mastery": sum(float(item["mastery"]) for item in signals) / len(signals),
            "attempts": float(len(rows)),
        }
    return results


def _recommendations(
    *,
    skill_scores: dict[tuple[str, str], dict[str, float]],
    srs: dict[str, Any],
    preferences: dict[str, Any],
    readiness_score: float,
    coverage_score: float,
) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    if int(srs["due"]) > 0:
        recs.append({
            "recommendation_type": "retention",
            "domain_id": "",
            "skill_id": "",
            "priority_score": 98.0 if int(srs["overdue"]) else 90.0,
            "reason_code": "srs_overdue" if int(srs["overdue"]) else "srs_due",
            "reason_text": f"Review {int(srs['due'])} due item(s), including {int(srs['overdue'])} overdue review(s), before adding more new material.",
            "action": {"route": "#/practice?mode=srs"},
        })
    ranked = sorted(skill_scores.items(), key=lambda item: (item[1]["mastery"], -item[1]["attempts"]))
    for (domain_id, skill_id), values in ranked[:3]:
        if values["mastery"] >= 0.78 and coverage_score >= 70:
            continue
        recs.append({
            "recommendation_type": "remediation",
            "domain_id": domain_id,
            "skill_id": skill_id,
            "priority_score": round(88.0 - values["mastery"] * 35.0, 2),
            "reason_code": "weak_skill",
            "reason_text": "Use the written concept, then a focused drill, then a delayed SRS review before the mastery check.",
            "action": {"sequence": ["written_concept", "focused_drill", "delayed_srs", "mastery_check"]},
        })
    runway = preferences.get("runway_days")
    if runway is not None:
        urgency = 95.0 if runway <= 7 else 86.0 if runway <= 21 else 70.0
        recs.append({
            "recommendation_type": "exam_runway",
            "domain_id": "",
            "skill_id": "",
            "priority_score": urgency,
            "reason_code": "exam_date_runway",
            "reason_text": f"With {runway} day(s) to the exam, prioritize the largest readiness gaps, timed mocks, remediation, and due SRS reviews.",
            "action": {"runway_days": runway, "readiness_score": round(readiness_score, 2)},
        })
    if coverage_score < 65:
        recs.append({
            "recommendation_type": "coverage",
            "domain_id": "",
            "skill_id": "",
            "priority_score": 80.0,
            "reason_code": "coverage_gap",
            "reason_text": "Increase active-release coverage before treating recent accuracy as broad exam readiness.",
            "action": {"route": "#/practice?mode=adaptive"},
        })
    return sorted(recs, key=lambda item: (-float(item["priority_score"]), item["recommendation_type"]))


def _readiness_band(score: float, evidence_confidence: str, unique_seen: int) -> str:
    if unique_seen < 5:
        return "insufficient_evidence"
    if evidence_confidence == "low":
        return "building_evidence"
    if score >= 82:
        return "strong"
    if score >= 70:
        return "progressing"
    return "needs_focus"


def _recommended_minutes(base: int, runway: int | None, score: float, coverage: float) -> int:
    minutes = max(15, int(base))
    if score < 65:
        minutes += 15
    if coverage < 50:
        minutes += 10
    if runway is not None and runway <= 21:
        minutes += 15
    if runway is not None and runway <= 7:
        minutes += 15
    return max(15, min(180, minutes))


def build_readiness(candidate_id: int, track_id: str = "snowpro-core", *, persist: bool = True) -> dict[str, Any]:
    ensure_adaptive_readiness_schema()
    with connect() as conn:
        eligible = _active_release_question_ids(conn, track_id)
        metadata = _question_metadata(conn, track_id, eligible)
        attempts = _attempts(conn, candidate_id, eligible)
        median_ms = _median_response(attempts)
        signal_rows = [
            _signals(row, metadata.get(str(row["question_id"]), {}).get("difficulty", "medium"), median_ms)
            for row in attempts
        ]
        unique_seen = len({str(row["question_id"]) for row in attempts})
        coverage = unique_seen / len(eligible) if eligible else 0.0
        mastery = sum(float(item["mastery"]) for item in signal_rows) / len(signal_rows) if signal_rows else 0.5
        calibration = sum(float(item["calibration"]) for item in signal_rows) / len(signal_rows) if signal_rows else 0.5
        pace = sum(float(item["pace"]) for item in signal_rows) / len(signal_rows) if signal_rows else 0.5
        probable_guesses = sum(bool(item["probable_guess"]) for item in signal_rows)
        srs = _srs(conn, candidate_id, eligible)
        mocks = _mocks(conn, candidate_id, track_id)
        prefs = _preferences(conn, candidate_id, track_id)
        skill_scores = _skill_scores(attempts, metadata, median_ms)

        raw = (
            mastery * 0.34
            + float(srs["retention"]) * 0.16
            + calibration * 0.12
            + float(mocks["score"]) * 0.18
            + coverage * 0.14
            + pace * 0.06
        )
        evidence_units = unique_seen + int(mocks["count"]) * 12 + int(srs["total"]) * 2
        if evidence_units >= 45 and coverage >= 0.45:
            evidence_confidence = "high"
            shrink = 0.90
        elif evidence_units >= 16 and coverage >= 0.15:
            evidence_confidence = "medium"
            shrink = 0.76
        else:
            evidence_confidence = "low"
            shrink = 0.45
        # Pull sparse evidence toward a neutral prior so a handful of lucky
        # answers cannot create a false "ready" signal.
        score = (raw * shrink + 0.50 * (1.0 - shrink)) * 100.0
        score = max(0.0, min(100.0, score))
        coverage_score = coverage * 100.0
        band = _readiness_band(score, evidence_confidence, unique_seen)
        minutes = _recommended_minutes(int(prefs["daily_minutes"]), prefs.get("runway_days"), score, coverage_score)
        recommendations = _recommendations(
            skill_scores=skill_scores,
            srs=srs,
            preferences=prefs,
            readiness_score=score,
            coverage_score=coverage_score,
        )
        evidence = {
            "statement": "This is an evidence-based study-readiness indicator, not a probability of passing the SnowPro exam.",
            "active_release_questions": len(eligible),
            "unique_questions_seen": unique_seen,
            "attempt_count": len(attempts),
            "recent_mock_count": int(mocks["count"]),
            "srs_due": int(srs["due"]),
            "srs_overdue": int(srs["overdue"]),
            "srs_total": int(srs["total"]),
            "probable_guess_count": probable_guesses,
            "median_response_time_ms": round(median_ms, 2) if median_ms else None,
        }
        snapshot_id = None
        if persist:
            cursor = conn.execute(
                """
                INSERT INTO candidate_readiness_snapshots(
                  candidate_id,track_id,readiness_score,evidence_confidence,readiness_band,
                  mastery_score,retention_score,calibration_score,mock_score,coverage_score,pace_score,
                  unique_questions_seen,recent_mock_count,exam_date,runway_days,recommended_daily_minutes,evidence_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    candidate_id, track_id, round(score, 4), evidence_confidence, band,
                    round(mastery * 100, 4), round(float(srs["retention"]) * 100, 4),
                    round(calibration * 100, 4), round(float(mocks["score"]) * 100, 4),
                    round(coverage_score, 4), round(pace * 100, 4), unique_seen, int(mocks["count"]),
                    prefs.get("exam_date"), prefs.get("runway_days"), minutes,
                    json.dumps(evidence, separators=(",", ":"), sort_keys=True),
                ),
            )
            snapshot_id = int(cursor.lastrowid)
            for item in recommendations:
                conn.execute(
                    """
                    INSERT INTO candidate_adaptive_recommendations(
                      candidate_id,track_id,recommendation_type,domain_id,skill_id,priority_score,
                      reason_code,reason_text,action_json,source_snapshot_id
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        candidate_id, track_id, item["recommendation_type"], item.get("domain_id", ""),
                        item.get("skill_id", ""), float(item["priority_score"]), item["reason_code"],
                        item["reason_text"], json.dumps(item.get("action", {}), separators=(",", ":"), sort_keys=True),
                        snapshot_id,
                    ),
                )

    return {
        "snapshot_id": snapshot_id,
        "candidate_id": candidate_id,
        "track_id": track_id,
        "readiness_score": round(score, 2),
        "evidence_confidence": evidence_confidence,
        "readiness_band": band,
        "exam_date": prefs.get("exam_date"),
        "runway_days": prefs.get("runway_days"),
        "recommended_daily_minutes": minutes,
        "components": {
            "mastery": round(mastery * 100, 2),
            "retention": round(float(srs["retention"]) * 100, 2),
            "calibration": round(calibration * 100, 2),
            "mock": round(float(mocks["score"]) * 100, 2),
            "coverage": round(coverage_score, 2),
            "pace": round(pace * 100, 2),
        },
        "evidence": evidence,
        "recommendations": recommendations,
    }


def latest_readiness(candidate_id: int, track_id: str = "snowpro-core") -> dict[str, Any] | None:
    ensure_adaptive_readiness_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM candidate_readiness_snapshots WHERE candidate_id=? AND track_id=? ORDER BY id DESC LIMIT 1",
            (candidate_id, track_id),
        ).fetchone()
        if not row:
            return None
        recommendations = conn.execute(
            "SELECT * FROM candidate_adaptive_recommendations WHERE candidate_id=? AND track_id=? AND source_snapshot_id=? ORDER BY priority_score DESC,id",
            (candidate_id, track_id, int(row["id"])),
        ).fetchall()
    result = dict(row)
    result["id"] = int(row["id"])
    result["evidence"] = json.loads(str(row["evidence_json"] or "{}"))
    result["recommendations"] = [
        {
            "id": int(item["id"]),
            "recommendation_type": item["recommendation_type"],
            "domain_id": item["domain_id"],
            "skill_id": item["skill_id"],
            "priority_score": float(item["priority_score"]),
            "reason_code": item["reason_code"],
            "reason_text": item["reason_text"],
            "action": json.loads(str(item["action_json"] or "{}")),
        }
        for item in recommendations
    ]
    return result


def adaptive_question_ids(candidate_id: int, track_id: str = "snowpro-core", *, limit: int = 20) -> list[str]:
    ensure_adaptive_readiness_schema()
    if limit <= 0:
        return []
    with connect() as conn:
        eligible = _active_release_question_ids(conn, track_id)
        metadata = _question_metadata(conn, track_id, eligible)
        attempts = _attempts(conn, candidate_id, eligible)
        median_ms = _median_response(attempts)
        skill_scores = _skill_scores(attempts, metadata, median_ms)
        latest: dict[str, dict[str, Any]] = {}
        for row in attempts:
            latest[str(row["question_id"])] = row
        srs = _srs(conn, candidate_id, eligible)
        due_ids: set[str] = set(srs["due_ids"])
        mistake_ids: set[str] = set()
        if _table_exists(conn, "candidate_mistake_notebook"):
            rows = conn.execute(
                "SELECT question_id FROM candidate_mistake_notebook WHERE candidate_id=? AND status<>'mastered'",
                (candidate_id,),
            ).fetchall()
            mistake_ids = {str(row["question_id"]) for row in rows if str(row["question_id"]) in eligible}

        scored: list[tuple[float, str]] = []
        for question_id in sorted(eligible):
            meta = metadata.get(question_id, {"domain_id": "unmapped", "skill_id": "unmapped", "difficulty": "medium"})
            key = (meta["domain_id"], meta["skill_id"])
            skill_mastery = skill_scores.get(key, {"mastery": 0.5})["mastery"]
            score = (1.0 - float(skill_mastery)) * 60.0
            attempt = latest.get(question_id)
            if not attempt:
                score += 30.0
            else:
                if not bool(int(attempt.get("correct") or 0)):
                    score += 24.0
                age = _parse_time(attempt.get("attempted_at"))
                if age:
                    score += min(15.0, max(0.0, (_now() - age).total_seconds() / 86400.0 * 0.5))
            # Retention debt outranks unseen coverage so a due item cannot be
            # starved indefinitely by a large bank of unseen questions.
            if question_id in due_ids:
                score += 55.0
            if question_id in mistake_ids:
                score += 25.0
            difficulty = meta.get("difficulty", "medium")
            if difficulty == "hard" and skill_mastery < 0.55:
                score -= 8.0
            elif difficulty == "hard" and skill_mastery >= 0.7:
                score += 8.0
            scored.append((score, question_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [question_id for _, question_id in scored[: min(100, int(limit))]]
