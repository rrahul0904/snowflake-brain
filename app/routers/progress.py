import json
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter

from ..database import connect
from ..serializers import json_list

router = APIRouter()


@router.get("/progress/summary")
def progress_summary() -> dict[str, Any]:
    with connect() as conn:
        totals = conn.execute(
            "SELECT COUNT(*) AS attempted, COALESCE(SUM(correct), 0) AS correct FROM question_attempts"
        ).fetchone()
        today = conn.execute(
            "SELECT * FROM daily_activity WHERE date = ?",
            (date.today().isoformat(),),
        ).fetchone()
    total_attempted = totals["attempted"] or 0
    total_correct = totals["correct"] or 0
    accuracy = round((total_correct / total_attempted) * 100) if total_attempted else 0
    streak = _streak_days()
    readiness = (total_correct / max(total_attempted, 1)) * 0.6 + min(streak / 30, 1) * 0.2 + min(total_attempted / 300, 1) * 0.2
    return {
        "streak_days": streak,
        "total_attempted": total_attempted,
        "total_correct": total_correct,
        "accuracy_pct": accuracy,
        "today": {
            "answered": today["questions_answered"] if today else 0,
            "correct": today["correct_answers"] if today else 0,
            "minutes": today["minutes_studied"] if today else 0,
        },
        "exam_readiness_pct": round(readiness * 100),
    }


@router.get("/progress/by-topic")
def by_topic() -> dict[str, Any]:
    topic_stats: dict[str, dict[str, int]] = {}
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT q.tags, qa.correct
            FROM question_attempts qa
            JOIN questions q ON q.id = qa.question_id
            """
        ).fetchall()
    for row in rows:
        tags = json_list(row["tags"]) or ["architecture"]
        for tag in tags:
            stats = topic_stats.setdefault(tag, {"attempted": 0, "correct": 0})
            stats["attempted"] += 1
            stats["correct"] += int(row["correct"] or 0)
    topics = [
        {
            "tag": tag,
            "attempted": stats["attempted"],
            "correct": stats["correct"],
            "accuracy": round(stats["correct"] / stats["attempted"] * 100) if stats["attempted"] else 0,
        }
        for tag, stats in sorted(topic_stats.items())
    ]
    return {"topics": topics}


@router.get("/progress/weak-topics")
def weak_topics() -> dict[str, Any]:
    topics = by_topic()["topics"]
    topics = [topic for topic in topics if topic["attempted"]]
    topics.sort(key=lambda item: (item["accuracy"], -item["attempted"]))
    return {"topics": topics[:5]}


@router.get("/progress/heatmap")
def heatmap() -> dict[str, Any]:
    start = date.today() - timedelta(days=89)
    with connect() as conn:
        rows = {
            row["date"]: row
            for row in conn.execute(
                "SELECT * FROM daily_activity WHERE date >= ? ORDER BY date",
                (start.isoformat(),),
            )
        }
    days = []
    for idx in range(90):
        day = start + timedelta(days=idx)
        row = rows.get(day.isoformat())
        days.append(
            {
                "date": day.isoformat(),
                "count": row["questions_answered"] if row else 0,
                "correct": row["correct_answers"] if row else 0,
            }
        )
    return {"days": days}


@router.post("/progress/lesson")
def lesson_progress(payload: dict[str, Any]) -> dict[str, bool]:
    lesson_id = payload.get("lesson_id")
    watched_s = int(payload.get("watched_s") or 0)
    completed = 1 if payload.get("completed") else 0
    if not lesson_id:
        return {"ok": False}
    with connect() as conn:
        lesson = conn.execute(
            """
            SELECT l.course_id, c.track_id
            FROM lessons l
            LEFT JOIN courses c ON c.id = l.course_id
            WHERE l.id = ?
            """,
            (lesson_id,),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO lesson_progress(lesson_id, watched_s, completed)
            VALUES (?, ?, ?)
            ON CONFLICT(lesson_id) DO UPDATE SET
              watched_s = MAX(watched_s, excluded.watched_s),
              completed = MAX(completed, excluded.completed),
              last_watched = datetime('now')
            """,
            (lesson_id, watched_s, completed),
        )
        if completed:
            conn.execute(
                """
                INSERT INTO learning_events(event_type, track_id, course_id, lesson_id, metadata_json)
                VALUES ('lesson_completed', ?, ?, ?, ?)
                """,
                (
                    lesson["track_id"] if lesson else "",
                    lesson["course_id"] if lesson else None,
                    lesson_id,
                    json.dumps({"watched_s": watched_s}),
                ),
            )
    return {"ok": True}


def _streak_days() -> int:
    with connect() as conn:
        rows = {
            row["date"]: row["questions_answered"]
            for row in conn.execute("SELECT date, questions_answered FROM daily_activity ORDER BY date DESC LIMIT 120")
        }
    streak = 0
    cursor = date.today()
    while rows.get(cursor.isoformat(), 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
