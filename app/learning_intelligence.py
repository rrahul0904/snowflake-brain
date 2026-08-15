from __future__ import annotations

import json
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .database import connect
from .serializers import json_list

SCHEMA_VERSION = "20260815_030_candidate_learning_intelligence_v1"
_SCHEMA_LOCK = threading.RLock()
_READY_DATABASES: set[str] = set()


def _database_key(conn: Any) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    if not row:
        return "unknown"
    try:
        return str(row["file"] or row[2] or "memory")
    except (KeyError, TypeError, IndexError):
        return str(row[2] or "memory")


def _ensure_column(conn: Any, table: str, column: str, declaration: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def ensure_learning_intelligence_schema() -> None:
    with _SCHEMA_LOCK:
        with connect() as conn:
            database_key = _database_key(conn)
            if database_key in _READY_DATABASES:
                return
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS candidate_srs_state (
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                  track_id TEXT NOT NULL,
                  domain_id TEXT NOT NULL DEFAULT '',
                  skill_id TEXT NOT NULL DEFAULT '',
                  repetitions INTEGER NOT NULL DEFAULT 0,
                  interval_days INTEGER NOT NULL DEFAULT 0,
                  ease_factor REAL NOT NULL DEFAULT 2.3,
                  lapses INTEGER NOT NULL DEFAULT 0,
                  due_at TEXT NOT NULL DEFAULT (datetime('now')),
                  last_reviewed_at TEXT,
                  last_correct INTEGER,
                  last_confidence INTEGER,
                  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                  PRIMARY KEY(candidate_id, question_id)
                );

                CREATE INDEX IF NOT EXISTS idx_candidate_srs_due
                  ON candidate_srs_state(candidate_id, track_id, due_at);
                CREATE INDEX IF NOT EXISTS idx_candidate_srs_skill
                  ON candidate_srs_state(candidate_id, track_id, skill_id, due_at);

                CREATE TABLE IF NOT EXISTS candidate_mistake_notebook (
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                  track_id TEXT NOT NULL,
                  domain_id TEXT NOT NULL DEFAULT '',
                  skill_id TEXT NOT NULL DEFAULT '',
                  miss_count INTEGER NOT NULL DEFAULT 1,
                  status TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open','reviewing','mastered')),
                  root_cause TEXT NOT NULL DEFAULT '',
                  note TEXT NOT NULL DEFAULT '',
                  first_missed_at TEXT NOT NULL DEFAULT (datetime('now')),
                  last_missed_at TEXT NOT NULL DEFAULT (datetime('now')),
                  last_reviewed_at TEXT,
                  mastered_at TEXT,
                  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                  PRIMARY KEY(candidate_id, question_id)
                );

                CREATE INDEX IF NOT EXISTS idx_candidate_mistakes_status
                  ON candidate_mistake_notebook(candidate_id, track_id, status, last_missed_at DESC);
                CREATE INDEX IF NOT EXISTS idx_candidate_mistakes_skill
                  ON candidate_mistake_notebook(candidate_id, track_id, skill_id, status);

                CREATE TABLE IF NOT EXISTS candidate_study_preferences (
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  track_id TEXT NOT NULL,
                  exam_date TEXT,
                  daily_minutes INTEGER NOT NULL DEFAULT 45,
                  days_per_week INTEGER NOT NULL DEFAULT 6,
                  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                  PRIMARY KEY(candidate_id, track_id)
                );
                """
            )
            _ensure_column(conn, "exam_session_answers", "confidence", "INTEGER")
            _ensure_column(conn, "exam_session_answers", "response_time_ms", "INTEGER")
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version,name) VALUES (?,?)",
                (SCHEMA_VERSION, "Candidate SRS, mistake notebook, study preferences, confidence calibration and remediation"),
            )
            _READY_DATABASES.add(database_key)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sql_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _question_context(conn: Any, question_id: str) -> dict[str, str]:
    row = conn.execute(
        """
        SELECT q.track_id,
               COALESCE(m.domain_id, '') AS metadata_domain_id,
               COALESCE(m.task_id, '') AS metadata_skill_id
        FROM questions q
        LEFT JOIN question_bank_metadata m ON m.question_id=q.id
        WHERE q.id=?
        """,
        (question_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"Unknown question: {question_id}")
    track_id = str(row["track_id"] or "")
    domain_id = str(row["metadata_domain_id"] or "")
    skill_id = str(row["metadata_skill_id"] or "")
    if not skill_id:
        edge = conn.execute(
            """
            SELECT domain_id, skill_id
            FROM question_skill_map
            WHERE question_id=? AND track_id=?
            ORDER BY reviewed DESC, confidence DESC, updated_at DESC
            LIMIT 1
            """,
            (question_id, track_id),
        ).fetchone()
        if edge:
            domain_id = str(edge["domain_id"] or domain_id)
            skill_id = str(edge["skill_id"] or "")
    return {"track_id": track_id, "domain_id": domain_id, "skill_id": skill_id}


def record_learning_review(
    conn: Any,
    candidate_id: int,
    question_id: str,
    *,
    correct: bool,
    confidence: int | None = None,
    mode: str = "practice",
    session_id: int | None = None,
    response_time_ms: int | None = None,
    selected: list[int] | None = None,
) -> dict[str, Any]:
    ensure_learning_intelligence_schema()
    context = _question_context(conn, question_id)
    confidence_value = int(confidence) if confidence is not None else None
    if confidence_value is not None and not 1 <= confidence_value <= 5:
        confidence_value = None
    current = conn.execute(
        "SELECT * FROM candidate_srs_state WHERE candidate_id=? AND question_id=?",
        (candidate_id, question_id),
    ).fetchone()
    repetitions = int(current["repetitions"] or 0) if current else 0
    interval_days = int(current["interval_days"] or 0) if current else 0
    ease = float(current["ease_factor"] or 2.3) if current else 2.3
    lapses = int(current["lapses"] or 0) if current else 0
    now = _utc_now()

    if correct:
        repetitions += 1
        quality = confidence_value if confidence_value is not None else 4
        ease = _clamp(ease + (quality - 3) * 0.08, 1.3, 2.8)
        if repetitions == 1:
            interval_days = 1
        elif repetitions == 2:
            interval_days = 3
        else:
            interval_days = max(interval_days + 1, int(round(max(1, interval_days) * ease)))
        if confidence_value is not None and confidence_value <= 2:
            interval_days = min(interval_days, 1)
        due_at = now + timedelta(days=interval_days)
    else:
        repetitions = 0
        interval_days = 0
        lapses += 1
        ease = _clamp(ease - (0.18 if confidence_value is None else 0.12 + confidence_value * 0.025), 1.3, 2.8)
        due_at = now

    conn.execute(
        """
        INSERT INTO candidate_srs_state(
          candidate_id,question_id,track_id,domain_id,skill_id,repetitions,
          interval_days,ease_factor,lapses,due_at,last_reviewed_at,last_correct,
          last_confidence,updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'),?,?,datetime('now'))
        ON CONFLICT(candidate_id,question_id) DO UPDATE SET
          track_id=excluded.track_id,
          domain_id=excluded.domain_id,
          skill_id=excluded.skill_id,
          repetitions=excluded.repetitions,
          interval_days=excluded.interval_days,
          ease_factor=excluded.ease_factor,
          lapses=excluded.lapses,
          due_at=excluded.due_at,
          last_reviewed_at=datetime('now'),
          last_correct=excluded.last_correct,
          last_confidence=excluded.last_confidence,
          updated_at=datetime('now')
        """,
        (
            candidate_id,
            question_id,
            context["track_id"],
            context["domain_id"],
            context["skill_id"],
            repetitions,
            interval_days,
            round(ease, 3),
            lapses,
            _sql_time(due_at),
            int(correct),
            confidence_value,
        ),
    )

    if not correct:
        conn.execute(
            """
            INSERT INTO candidate_mistake_notebook(
              candidate_id,question_id,track_id,domain_id,skill_id,miss_count,status,
              first_missed_at,last_missed_at,updated_at
            ) VALUES (?,?,?,?,?,1,'open',datetime('now'),datetime('now'),datetime('now'))
            ON CONFLICT(candidate_id,question_id) DO UPDATE SET
              track_id=excluded.track_id,
              domain_id=excluded.domain_id,
              skill_id=excluded.skill_id,
              miss_count=candidate_mistake_notebook.miss_count+1,
              status='open',
              last_missed_at=datetime('now'),
              mastered_at=NULL,
              updated_at=datetime('now')
            """,
            (candidate_id, question_id, context["track_id"], context["domain_id"], context["skill_id"]),
        )
    else:
        mistake = conn.execute(
            "SELECT 1 FROM candidate_mistake_notebook WHERE candidate_id=? AND question_id=?",
            (candidate_id, question_id),
        ).fetchone()
        if mistake:
            next_status = "mastered" if repetitions >= 2 else "reviewing"
            conn.execute(
                """
                UPDATE candidate_mistake_notebook
                SET status=?,last_reviewed_at=datetime('now'),
                    mastered_at=CASE WHEN ?='mastered' THEN datetime('now') ELSE NULL END,
                    updated_at=datetime('now')
                WHERE candidate_id=? AND question_id=?
                """,
                (next_status, next_status, candidate_id, question_id),
            )

    if session_id is not None:
        history = conn.execute(
            """
            SELECT id FROM candidate_question_history
            WHERE candidate_id=? AND question_id=? AND session_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (candidate_id, question_id, session_id),
        ).fetchone()
        if history:
            conn.execute(
                """
                UPDATE candidate_question_history
                SET answered_at=datetime('now'),selected_json=?,correct=?,response_time_ms=?,confidence=?
                WHERE id=?
                """,
                (json.dumps(sorted(set(selected or []))), int(correct), response_time_ms, confidence_value, history["id"]),
            )

    conn.execute(
        """
        INSERT INTO learning_events(event_type,track_id,question_id,skill_id,metadata_json,candidate_id)
        VALUES ('learning_review_recorded',?,?,?,?,?)
        """,
        (
            context["track_id"],
            question_id,
            context["skill_id"] or None,
            json.dumps(
                {
                    "mode": mode,
                    "correct": bool(correct),
                    "confidence": confidence_value,
                    "interval_days": interval_days,
                    "repetitions": repetitions,
                    "lapses": lapses,
                },
                separators=(",", ":"),
            ),
            candidate_id,
        ),
    )
    return {
        **context,
        "question_id": question_id,
        "correct": bool(correct),
        "repetitions": repetitions,
        "interval_days": interval_days,
        "ease_factor": round(ease, 3),
        "lapses": lapses,
        "due_at": _sql_time(due_at),
    }


def _active_release_filter() -> str:
    return """
      AND (
        q.source_kind <> 'private_bank'
        OR EXISTS (
          SELECT 1
          FROM question_bank_releases r
          JOIN question_bank_release_questions rq ON rq.release_id=r.id
          WHERE r.track_id=q.track_id AND r.status='active' AND rq.question_id=q.id
        )
      )
    """


def due_today(conn: Any, candidate_id: int, track_id: str = "snowpro-core", limit: int = 20) -> dict[str, Any]:
    ensure_learning_intelligence_schema()
    safe_limit = max(1, min(int(limit), 100))
    rows = [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT s.question_id,s.domain_id,s.skill_id,s.repetitions,s.interval_days,
                   s.ease_factor,s.lapses,s.due_at,s.last_correct,s.last_confidence,
                   q.question,q.options_json,q.multiple,q.difficulty,q.source_kind
            FROM candidate_srs_state s
            JOIN questions q ON q.id=s.question_id
            LEFT JOIN question_bank_metadata m ON m.question_id=q.id
            WHERE s.candidate_id=? AND s.track_id=?
              AND datetime(s.due_at) <= datetime('now')
              AND COALESCE(m.authoring_status,'active') <> 'retired'
              {_active_release_filter()}
            ORDER BY datetime(s.due_at),s.lapses DESC,s.question_id
            LIMIT ?
            """,
            (candidate_id, track_id, safe_limit),
        )
    ]
    queue = []
    for row in rows:
        queue.append(
            {
                "question_id": row["question_id"],
                "question": row["question"],
                "options": json_list(row["options_json"]),
                "multiple": bool(row["multiple"]),
                "difficulty": row["difficulty"],
                "domain_id": row["domain_id"],
                "skill_id": row["skill_id"],
                "repetitions": int(row["repetitions"] or 0),
                "interval_days": int(row["interval_days"] or 0),
                "lapses": int(row["lapses"] or 0),
                "due_at": row["due_at"],
                "last_confidence": row["last_confidence"],
            }
        )
    total_due = int(
        conn.execute(
            "SELECT COUNT(*) AS count FROM candidate_srs_state WHERE candidate_id=? AND track_id=? AND datetime(due_at)<=datetime('now')",
            (candidate_id, track_id),
        ).fetchone()["count"]
        or 0
    )
    return {"track_id": track_id, "due_count": total_due, "returned": len(queue), "questions": queue}


def mistake_notebook(
    conn: Any,
    candidate_id: int,
    track_id: str = "snowpro-core",
    *,
    status: str = "active",
    limit: int = 50,
) -> dict[str, Any]:
    ensure_learning_intelligence_schema()
    safe_limit = max(1, min(int(limit), 200))
    where_status = "m.status IN ('open','reviewing')" if status == "active" else "m.status=?"
    params: list[Any] = [candidate_id, track_id]
    if status != "active":
        if status not in {"open", "reviewing", "mastered"}:
            status = "open"
        params.append(status)
    params.append(safe_limit)
    rows = [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT m.*,q.question,q.difficulty,s.due_at,s.repetitions,s.lapses
            FROM candidate_mistake_notebook m
            JOIN questions q ON q.id=m.question_id
            LEFT JOIN candidate_srs_state s
              ON s.candidate_id=m.candidate_id AND s.question_id=m.question_id
            WHERE m.candidate_id=? AND m.track_id=? AND {where_status}
            ORDER BY m.miss_count DESC,datetime(m.last_missed_at) DESC
            LIMIT ?
            """,
            params,
        )
    ]
    counts = {
        row["status"]: int(row["count"] or 0)
        for row in conn.execute(
            "SELECT status,COUNT(*) AS count FROM candidate_mistake_notebook WHERE candidate_id=? AND track_id=? GROUP BY status",
            (candidate_id, track_id),
        )
    }
    items = [
        {
            "question_id": row["question_id"],
            "question": row["question"],
            "difficulty": row["difficulty"],
            "domain_id": row["domain_id"],
            "skill_id": row["skill_id"],
            "miss_count": int(row["miss_count"] or 0),
            "status": row["status"],
            "root_cause": row["root_cause"],
            "note": row["note"],
            "first_missed_at": row["first_missed_at"],
            "last_missed_at": row["last_missed_at"],
            "last_reviewed_at": row["last_reviewed_at"],
            "due_at": row["due_at"],
            "repetitions": int(row["repetitions"] or 0),
            "lapses": int(row["lapses"] or 0),
        }
        for row in rows
    ]
    return {
        "track_id": track_id,
        "counts": {"open": counts.get("open", 0), "reviewing": counts.get("reviewing", 0), "mastered": counts.get("mastered", 0)},
        "items": items,
    }


def update_mistake(
    conn: Any,
    candidate_id: int,
    question_id: str,
    *,
    note: str | None = None,
    root_cause: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    ensure_learning_intelligence_schema()
    row = conn.execute(
        "SELECT * FROM candidate_mistake_notebook WHERE candidate_id=? AND question_id=?",
        (candidate_id, question_id),
    ).fetchone()
    if not row:
        raise ValueError("Mistake record not found")
    next_status = str(status or row["status"])
    if next_status not in {"open", "reviewing", "mastered"}:
        raise ValueError("Mistake status must be open, reviewing, or mastered")
    next_note = str(row["note"] if note is None else note).strip()[:4000]
    next_root = str(row["root_cause"] if root_cause is None else root_cause).strip()[:500]
    conn.execute(
        """
        UPDATE candidate_mistake_notebook
        SET note=?,root_cause=?,status=?,
            mastered_at=CASE WHEN ?='mastered' THEN COALESCE(mastered_at,datetime('now')) ELSE NULL END,
            updated_at=datetime('now')
        WHERE candidate_id=? AND question_id=?
        """,
        (next_note, next_root, next_status, next_status, candidate_id, question_id),
    )
    return {"question_id": question_id, "note": next_note, "root_cause": next_root, "status": next_status}


def confidence_calibration(conn: Any, candidate_id: int, track_id: str = "snowpro-core") -> dict[str, Any]:
    ensure_learning_intelligence_schema()
    samples: list[tuple[int, int, str]] = []
    for row in conn.execute(
        """
        SELECT confidence,correct,mode
        FROM candidate_question_history
        WHERE candidate_id=? AND confidence IS NOT NULL AND correct IS NOT NULL
          AND question_id IN (SELECT id FROM questions WHERE track_id=?)
        """,
        (candidate_id, track_id),
    ):
        samples.append((int(row["confidence"]), int(row["correct"]), str(row["mode"] or "practice")))
    for row in conn.execute(
        """
        SELECT a.confidence,a.correct,s.mode
        FROM exam_session_answers a
        JOIN exam_sessions s ON s.id=a.session_id
        WHERE s.candidate_id=? AND s.track_id=? AND s.status='finished'
          AND a.confidence IS NOT NULL
        """,
        (candidate_id, track_id),
    ):
        samples.append((int(row["confidence"]), int(row["correct"]), str(row["mode"] or "mock")))

    buckets = {level: {"confidence": level, "attempts": 0, "correct": 0} for level in range(1, 6)}
    overconfident = 0
    underconfident = 0
    for confidence, correct, _mode in samples:
        if confidence not in buckets:
            continue
        buckets[confidence]["attempts"] += 1
        buckets[confidence]["correct"] += int(correct)
        overconfident += int(confidence >= 4 and not correct)
        underconfident += int(confidence <= 2 and bool(correct))
    per_level = []
    weighted_gap = 0.0
    usable = 0
    for level in range(1, 6):
        item = buckets[level]
        attempts = item["attempts"]
        accuracy = round(item["correct"] / attempts * 100, 1) if attempts else 0.0
        expected = level * 20
        gap = round(expected - accuracy, 1) if attempts else 0.0
        if attempts:
            weighted_gap += abs(gap) * attempts
            usable += attempts
        per_level.append({**item, "accuracy_pct": accuracy, "expected_pct": expected, "calibration_gap": gap})
    calibration_score = max(0, round(100 - weighted_gap / usable, 1)) if usable else 0
    if usable < 5:
        status = "insufficient_data"
    elif calibration_score >= 85:
        status = "well_calibrated"
    elif overconfident > underconfident:
        status = "overconfident"
    elif underconfident > overconfident:
        status = "underconfident"
    else:
        status = "mixed"
    return {
        "track_id": track_id,
        "sample_size": usable,
        "calibration_score": calibration_score,
        "status": status,
        "overconfident_misses": overconfident,
        "underconfident_correct": underconfident,
        "per_level": per_level,
    }


def set_study_preferences(
    conn: Any,
    candidate_id: int,
    track_id: str,
    *,
    exam_date: str | None,
    daily_minutes: int,
    days_per_week: int,
) -> dict[str, Any]:
    ensure_learning_intelligence_schema()
    normalized_exam_date = None
    if exam_date:
        try:
            normalized_exam_date = date.fromisoformat(str(exam_date)).isoformat()
        except ValueError as exc:
            raise ValueError("exam_date must be YYYY-MM-DD") from exc
    minutes = max(15, min(int(daily_minutes), 240))
    days = max(1, min(int(days_per_week), 7))
    conn.execute(
        """
        INSERT INTO candidate_study_preferences(candidate_id,track_id,exam_date,daily_minutes,days_per_week,updated_at)
        VALUES (?,?,?,?,?,datetime('now'))
        ON CONFLICT(candidate_id,track_id) DO UPDATE SET
          exam_date=excluded.exam_date,daily_minutes=excluded.daily_minutes,
          days_per_week=excluded.days_per_week,updated_at=datetime('now')
        """,
        (candidate_id, track_id, normalized_exam_date, minutes, days),
    )
    return {"track_id": track_id, "exam_date": normalized_exam_date, "daily_minutes": minutes, "days_per_week": days}


def study_plan(conn: Any, candidate_id: int, track_id: str = "snowpro-core") -> dict[str, Any]:
    ensure_learning_intelligence_schema()
    from .intelligence import readiness_model, skill_mastery

    pref = conn.execute(
        "SELECT * FROM candidate_study_preferences WHERE candidate_id=? AND track_id=?",
        (candidate_id, track_id),
    ).fetchone()
    preferences = {
        "exam_date": pref["exam_date"] if pref else None,
        "daily_minutes": int(pref["daily_minutes"] or 45) if pref else 45,
        "days_per_week": int(pref["days_per_week"] or 6) if pref else 6,
    }
    mastery = skill_mastery(conn, track_id, candidate_id=candidate_id)
    readiness = readiness_model(conn, track_id, mastery=mastery, candidate_id=candidate_id)
    due_rows = conn.execute(
        "SELECT skill_id,COUNT(*) AS count FROM candidate_srs_state WHERE candidate_id=? AND track_id=? AND datetime(due_at)<=datetime('now') GROUP BY skill_id",
        (candidate_id, track_id),
    ).fetchall()
    due_by_skill = {str(row["skill_id"] or ""): int(row["count"] or 0) for row in due_rows}
    mistake_rows = conn.execute(
        "SELECT skill_id,SUM(miss_count) AS misses,COUNT(*) AS questions FROM candidate_mistake_notebook WHERE candidate_id=? AND track_id=? AND status IN ('open','reviewing') GROUP BY skill_id",
        (candidate_id, track_id),
    ).fetchall()
    mistakes_by_skill = {str(row["skill_id"] or ""): {"misses": int(row["misses"] or 0), "questions": int(row["questions"] or 0)} for row in mistake_rows}

    priority = []
    for item in mastery.get("skills") or []:
        skill_id = str(item.get("skill_id") or "")
        mastery_level = int(item.get("mastery_level") or 1)
        accuracy = int(item.get("accuracy_pct") or 0)
        attempts = int(item.get("attempts") or 0)
        misses = int((mistakes_by_skill.get(skill_id) or {}).get("misses") or 0)
        due = int(due_by_skill.get(skill_id) or 0)
        gap_score = (7 - mastery_level) * 12 + max(0, 80 - accuracy) * 0.45 + misses * 5 + due * 3 + (8 if attempts == 0 else 0)
        priority.append(
            {
                "skill_id": skill_id,
                "skill": item.get("skill") or skill_id,
                "domain_id": item.get("domain_id") or "",
                "mastery_level": mastery_level,
                "accuracy_pct": accuracy,
                "attempts": attempts,
                "open_misses": misses,
                "due_count": due,
                "priority_score": round(gap_score, 1),
                "lesson_url": f"#/skill?track_id={track_id}&skill_id={skill_id}",
                "drill_url": f"#/practice?track_id={track_id}&mode=drill&skill_id={skill_id}",
            }
        )
    priority.sort(key=lambda item: (-item["priority_score"], item["skill_id"]))
    top = priority[:5]
    daily_minutes = preferences["daily_minutes"]
    review_minutes = min(15, max(5, round(daily_minutes * 0.25)))
    lesson_minutes = min(20, max(10, round(daily_minutes * 0.35)))
    drill_minutes = max(10, daily_minutes - review_minutes - lesson_minutes)
    today = date.today()
    days = []
    for offset in range(7):
        target = top[offset % len(top)] if top else None
        active_day = offset < preferences["days_per_week"]
        sessions = []
        if active_day:
            sessions.append({"type": "srs", "minutes": review_minutes, "title": "Due Today", "href": f"#/practice?track_id={track_id}&mode=srs"})
            if target:
                sessions.append({"type": "lesson", "minutes": lesson_minutes, "title": f"Review {target['skill']}", "skill_id": target["skill_id"], "href": target["lesson_url"]})
                sessions.append({"type": "drill", "minutes": drill_minutes, "title": f"Drill {target['skill']}", "skill_id": target["skill_id"], "href": target["drill_url"]})
            else:
                sessions.append({"type": "foundation", "minutes": daily_minutes - review_minutes, "title": "Complete the next blueprint task", "href": f"#/curriculum?track_id={track_id}"})
        else:
            sessions.append({"type": "rest", "minutes": 0, "title": "Recovery / catch-up day", "href": f"#/progress?track_id={track_id}"})
        days.append({"date": (today + timedelta(days=offset)).isoformat(), "active": active_day, "sessions": sessions, "total_minutes": sum(int(item["minutes"]) for item in sessions)})

    days_until_exam = None
    if preferences["exam_date"]:
        days_until_exam = (date.fromisoformat(preferences["exam_date"]) - today).days
    return {
        "track_id": track_id,
        "preferences": preferences,
        "days_until_exam": days_until_exam,
        "readiness_score": readiness.get("readiness_score", 0),
        "readiness_status": readiness.get("status", "insufficient_data"),
        "due_today": sum(due_by_skill.values()),
        "open_mistakes": sum(item["questions"] for item in mistakes_by_skill.values()),
        "priority_skills": top,
        "days": days,
        "generated_at": _sql_time(_utc_now()),
        "strategy_version": "candidate-learning-v1",
    }


def mock_remediation(conn: Any, candidate_id: int, session_id: int) -> dict[str, Any]:
    ensure_learning_intelligence_schema()
    session = conn.execute(
        "SELECT * FROM exam_sessions WHERE id=? AND candidate_id=?",
        (session_id, candidate_id),
    ).fetchone()
    if not session:
        raise ValueError("Mock session not found")
    if session["status"] != "finished":
        raise ValueError("Mock remediation is available after submission")
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT sq.question_id,sq.position,COALESCE(a.correct,0) AS correct,
                   COALESCE(a.selected_json,'[]') AS selected_json,
                   q.question,q.explanation,
                   COALESCE(m.domain_id,'') AS domain_id,
                   COALESCE(m.task_id,'') AS metadata_skill_id
            FROM exam_session_questions sq
            JOIN questions q ON q.id=sq.question_id
            LEFT JOIN exam_session_answers a ON a.session_id=sq.session_id AND a.question_id=sq.question_id
            LEFT JOIN question_bank_metadata m ON m.question_id=sq.question_id
            WHERE sq.session_id=?
            ORDER BY sq.position
            """,
            (session_id,),
        )
    ]
    skill_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "misses": 0, "questions": []})
    mistakes = []
    for row in rows:
        context = _question_context(conn, row["question_id"])
        skill_id = str(row["metadata_skill_id"] or context["skill_id"] or "unmapped")
        item = skill_stats[skill_id]
        item["total"] += 1
        if not int(row["correct"] or 0):
            item["misses"] += 1
            item["questions"].append(row["question_id"])
            mistakes.append(
                {
                    "question_id": row["question_id"],
                    "position": int(row["position"]),
                    "question": row["question"],
                    "explanation": row["explanation"],
                    "selected": json_list(row["selected_json"]),
                    "domain_id": context["domain_id"],
                    "skill_id": skill_id,
                }
            )
    prioritized = []
    for skill_id, item in skill_stats.items():
        if not item["misses"]:
            continue
        accuracy = round((item["total"] - item["misses"]) / item["total"] * 100, 1) if item["total"] else 0
        prioritized.append(
            {
                "skill_id": skill_id,
                "misses": item["misses"],
                "total": item["total"],
                "accuracy_pct": accuracy,
                "question_ids": item["questions"],
                "lesson_url": f"#/skill?track_id={session['track_id']}&skill_id={skill_id}",
                "drill_url": f"#/practice?track_id={session['track_id']}&mode=drill&skill_id={skill_id}",
            }
        )
    prioritized.sort(key=lambda item: (-item["misses"], item["accuracy_pct"], item["skill_id"]))
    return {
        "session_id": session_id,
        "track_id": session["track_id"],
        "scaled_score": int(session["scaled_score"] or 0),
        "mistake_count": len(mistakes),
        "priority_tasks": prioritized,
        "mistakes": mistakes,
        "actions": [
            {"type": "srs", "title": "Review failed questions while they are due", "href": f"#/practice?track_id={session['track_id']}&mode=srs"},
            {"type": "mistakes", "title": "Write the rule you missed in the Mistake Notebook", "href": f"#/progress?track_id={session['track_id']}#mistakes"},
        ] + [
            {"type": "drill", "title": f"Drill {item['skill_id']}", "href": item["drill_url"]}
            for item in prioritized[:3]
        ],
    }
