from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..database import connect

router = APIRouter()


class StudyGoalCreate(BaseModel):
    track_id: str
    target_exam_date: date
    weekly_hours: int = Field(8, ge=1, le=80)
    daily_question_target: int = Field(30, ge=0, le=300)
    auto_generate: bool = True


class StudyRoadmapCreate(BaseModel):
    track_ids: list[str] = Field(..., min_length=1, max_length=6)
    target_end_date: date
    weekly_hours: int = Field(10, ge=1, le=80)
    daily_question_target: int = Field(40, ge=0, le=300)
    replace_existing: bool = False


class StudyGoalUpdate(BaseModel):
    target_exam_date: date | None = None
    weekly_hours: int | None = Field(default=None, ge=1, le=80)
    daily_question_target: int | None = Field(default=None, ge=0, le=300)
    status: str | None = None


class GeneratePlanRequest(BaseModel):
    days: int | None = Field(default=None, ge=7, le=365)
    replace: bool = True


class PlanItemUpdate(BaseModel):
    completed: bool


@router.get("/study/goals")
def list_goals(status: str | None = "active") -> dict[str, Any]:
    filters = []
    params: list[Any] = []
    if status:
        filters.append("g.status = ?")
        params.append(status)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    with connect() as conn:
        rows = [
            _goal_public(dict(row))
            for row in conn.execute(
                f"""
                SELECT
                  g.*,
                  t.title AS track_title,
                  t.description AS track_description,
                  (SELECT COUNT(*) FROM study_plan_items spi WHERE spi.goal_id = g.id) AS item_count,
                  (SELECT COUNT(*) FROM study_plan_items spi WHERE spi.goal_id = g.id AND spi.completed = 1) AS completed_count,
                  (SELECT COUNT(*) FROM courses c WHERE c.track_id = g.track_id) AS course_count,
                  (SELECT COUNT(*) FROM lessons l JOIN courses c ON c.id = l.course_id WHERE c.track_id = g.track_id) AS lesson_count,
                  (SELECT COUNT(*) FROM questions q JOIN courses c ON c.id = q.course_id WHERE c.track_id = g.track_id) AS question_count
                FROM study_goals g
                JOIN certification_tracks t ON t.id = g.track_id
                {where}
                ORDER BY g.status = 'active' DESC, g.target_exam_date, t.position, t.title
                """,
                params,
            )
        ]
    return {"goals": rows}


@router.post("/study/goals")
def create_goal(payload: StudyGoalCreate) -> dict[str, Any]:
    target = payload.target_exam_date.isoformat()
    today = date.today()
    if payload.target_exam_date < today:
        raise HTTPException(status_code=400, detail="Target exam date must be today or later")
    with connect() as conn:
        _require_track(conn, payload.track_id)
        existing = conn.execute(
            """
            SELECT id
            FROM study_goals
            WHERE track_id = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (payload.track_id,),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail="An active study goal already exists for this certification track",
            )
        cursor = conn.execute(
            """
            INSERT INTO study_goals(track_id, target_exam_date, weekly_hours, daily_question_target)
            VALUES (?, ?, ?, ?)
            """,
            (payload.track_id, target, payload.weekly_hours, payload.daily_question_target),
        )
        goal_id = int(cursor.lastrowid)
        generated_count = 0
        if payload.auto_generate:
            generated_count = _generate_plan(
                conn,
                goal_id=goal_id,
                track_id=payload.track_id,
                target_exam_date=target,
                weekly_hours=payload.weekly_hours,
                daily_question_target=payload.daily_question_target,
                days=None,
                replace=True,
                start_date=None,
            )
        goal = _fetch_goal(conn, goal_id)
    return {"goal": _goal_public(goal), "generated_items": generated_count}


@router.post("/study/roadmap")
def create_roadmap(payload: StudyRoadmapCreate) -> dict[str, Any]:
    today = date.today()
    if payload.target_end_date < today:
        raise HTTPException(status_code=400, detail="Roadmap target end date must be today or later")

    total_days = max(1, (payload.target_end_date - today).days + 1)
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    with connect() as conn:
        seen: set[str] = set()
        track_ids = []
        for track_id in payload.track_ids:
            if track_id in seen:
                continue
            _require_track(conn, track_id)
            seen.add(track_id)
            track_ids.append(track_id)

        previous_milestone_days = 0
        for index, track_id in enumerate(track_ids, start=1):
            milestone_days = max(1, round((total_days * index) / len(track_ids)))
            segment_days = max(1, milestone_days - previous_milestone_days)
            segment_start = today + timedelta(days=previous_milestone_days)
            target_exam_date = today + timedelta(days=milestone_days - 1)
            existing = conn.execute(
                """
                SELECT id
                FROM study_goals
                WHERE track_id = ? AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (track_id,),
            ).fetchone()

            if existing and not payload.replace_existing:
                skipped.append(
                    {
                        "track_id": track_id,
                        "goal_id": existing["id"],
                        "reason": "active_goal_exists",
                    }
                )
                continue

            if existing and payload.replace_existing:
                goal_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE study_goals
                    SET target_exam_date = ?,
                        weekly_hours = ?,
                        daily_question_target = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (target_exam_date.isoformat(), payload.weekly_hours, payload.daily_question_target, goal_id),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO study_goals(track_id, target_exam_date, weekly_hours, daily_question_target)
                    VALUES (?, ?, ?, ?)
                    """,
                    (track_id, target_exam_date.isoformat(), payload.weekly_hours, payload.daily_question_target),
                )
                goal_id = int(cursor.lastrowid)

            generated_count = _generate_plan(
                conn,
                goal_id=goal_id,
                track_id=track_id,
                target_exam_date=target_exam_date.isoformat(),
                weekly_hours=payload.weekly_hours,
                daily_question_target=payload.daily_question_target,
                days=segment_days,
                replace=True,
                start_date=segment_start,
            )
            created.append({"goal": _goal_public(_fetch_goal(conn, goal_id)), "generated_items": generated_count})
            previous_milestone_days = milestone_days

    return {"goals": created, "skipped": skipped, "target_end_date": payload.target_end_date.isoformat()}


@router.patch("/study/goals/{goal_id}")
def update_goal(goal_id: int, payload: StudyGoalUpdate) -> dict[str, Any]:
    updates = []
    params: list[Any] = []
    if payload.target_exam_date is not None:
        updates.append("target_exam_date = ?")
        params.append(payload.target_exam_date.isoformat())
    if payload.weekly_hours is not None:
        updates.append("weekly_hours = ?")
        params.append(payload.weekly_hours)
    if payload.daily_question_target is not None:
        updates.append("daily_question_target = ?")
        params.append(payload.daily_question_target)
    if payload.status is not None:
        if payload.status not in {"active", "paused", "complete", "archived"}:
            raise HTTPException(status_code=400, detail="Unsupported goal status")
        updates.append("status = ?")
        params.append(payload.status)
    if not updates:
        raise HTTPException(status_code=400, detail="No goal fields supplied")
    updates.append("updated_at = datetime('now')")
    with connect() as conn:
        if not conn.execute("SELECT id FROM study_goals WHERE id = ?", (goal_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Study goal not found")
        conn.execute(f"UPDATE study_goals SET {', '.join(updates)} WHERE id = ?", [*params, goal_id])
        goal = _fetch_goal(conn, goal_id)
    return {"goal": _goal_public(goal)}


@router.post("/study/goals/{goal_id}/generate-plan")
def generate_plan(goal_id: int, payload: GeneratePlanRequest) -> dict[str, Any]:
    with connect() as conn:
        goal = conn.execute("SELECT * FROM study_goals WHERE id = ?", (goal_id,)).fetchone()
        if not goal:
            raise HTTPException(status_code=404, detail="Study goal not found")
        generated_count = _generate_plan(
            conn,
            goal_id=goal_id,
            track_id=goal["track_id"],
            target_exam_date=goal["target_exam_date"],
            weekly_hours=goal["weekly_hours"] or 8,
            daily_question_target=goal["daily_question_target"] or 30,
            days=payload.days,
            replace=payload.replace,
            start_date=None,
        )
        goal_public = _goal_public(_fetch_goal(conn, goal_id))
    return {"goal": goal_public, "generated_items": generated_count}


@router.get("/study/goals/{goal_id}/plan")
def goal_plan(
    goal_id: int,
    due_from: date | None = None,
    due_to: date | None = None,
    include_completed: bool = True,
) -> dict[str, Any]:
    filters = ["spi.goal_id = ?"]
    params: list[Any] = [goal_id]
    if due_from:
        filters.append("spi.due_date >= ?")
        params.append(due_from.isoformat())
    if due_to:
        filters.append("spi.due_date <= ?")
        params.append(due_to.isoformat())
    if not include_completed:
        filters.append("spi.completed = 0")
    with connect() as conn:
        if not conn.execute("SELECT id FROM study_goals WHERE id = ?", (goal_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Study goal not found")
        rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                  spi.*,
                  c.title AS course_title,
                  l.title AS lesson_title,
                  pt.title AS practice_test_title
                FROM study_plan_items spi
                LEFT JOIN courses c ON c.id = spi.course_id
                LEFT JOIN lessons l ON l.id = spi.lesson_id
                LEFT JOIN practice_tests pt ON pt.id = spi.practice_test_id
                WHERE {' AND '.join(filters)}
                ORDER BY spi.due_date, spi.position, spi.id
                """,
                params,
            )
        ]
    return {"items": rows}


@router.patch("/study/plan-items/{item_id}")
def update_plan_item(item_id: int, payload: PlanItemUpdate) -> dict[str, Any]:
    completed = 1 if payload.completed else 0
    completed_at = datetime.utcnow().isoformat(timespec="seconds") if completed else None
    with connect() as conn:
        row = conn.execute("SELECT id FROM study_plan_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Study plan item not found")
        conn.execute(
            """
            UPDATE study_plan_items
            SET completed = ?, completed_at = ?
            WHERE id = ?
            """,
            (completed, completed_at, item_id),
        )
        item = dict(conn.execute("SELECT * FROM study_plan_items WHERE id = ?", (item_id,)).fetchone())
    return {"item": item}


@router.get("/study/today")
def today_plan(track_id: str | None = None, limit: int = Query(40, ge=1, le=200)) -> dict[str, Any]:
    today = date.today().isoformat()
    filters = ["g.status = 'active'", "spi.completed = 0", "spi.due_date <= ?"]
    params: list[Any] = [today]
    if track_id:
        filters.append("g.track_id = ?")
        params.append(track_id)
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                  spi.*,
                  g.track_id,
                  t.title AS track_title,
                  c.title AS course_title,
                  l.title AS lesson_title,
                  pt.title AS practice_test_title
                FROM study_plan_items spi
                JOIN study_goals g ON g.id = spi.goal_id
                JOIN certification_tracks t ON t.id = g.track_id
                LEFT JOIN courses c ON c.id = spi.course_id
                LEFT JOIN lessons l ON l.id = spi.lesson_id
                LEFT JOIN practice_tests pt ON pt.id = spi.practice_test_id
                WHERE {' AND '.join(filters)}
                ORDER BY spi.due_date, spi.position, spi.id
                LIMIT ?
                """,
                [*params, limit],
            )
        ]
        goals = [
            _goal_public(dict(row))
            for row in conn.execute(
                """
                SELECT
                  g.*,
                  t.title AS track_title,
                  t.description AS track_description,
                  (SELECT COUNT(*) FROM study_plan_items spi WHERE spi.goal_id = g.id) AS item_count,
                  (SELECT COUNT(*) FROM study_plan_items spi WHERE spi.goal_id = g.id AND spi.completed = 1) AS completed_count,
                  (SELECT COUNT(*) FROM courses c WHERE c.track_id = g.track_id) AS course_count,
                  (SELECT COUNT(*) FROM lessons l JOIN courses c ON c.id = l.course_id WHERE c.track_id = g.track_id) AS lesson_count,
                  (SELECT COUNT(*) FROM questions q JOIN courses c ON c.id = q.course_id WHERE c.track_id = g.track_id) AS question_count
                FROM study_goals g
                JOIN certification_tracks t ON t.id = g.track_id
                WHERE g.status = 'active'
                ORDER BY g.target_exam_date, t.position
                """
            )
        ]
    return {"date": today, "goals": goals, "items": rows}


@router.get("/study/readiness")
def readiness(track_id: str | None = None) -> dict[str, Any]:
    with connect() as conn:
        if track_id:
            _require_track(conn, track_id)
            return {"tracks": [_readiness_for_track(conn, track_id)]}
        rows = conn.execute("SELECT id FROM certification_tracks ORDER BY position, title").fetchall()
        return {"tracks": [_readiness_for_track(conn, row["id"]) for row in rows]}


@router.get("/study/content-audit")
def content_audit() -> dict[str, Any]:
    with connect() as conn:
        totals = dict(
            conn.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM certification_tracks) AS tracks,
                  (SELECT COUNT(*) FROM courses) AS courses,
                  (SELECT COUNT(*) FROM lessons) AS lessons,
                  (SELECT COUNT(*) FROM practice_tests) AS practice_tests,
                  (SELECT COUNT(*) FROM questions) AS questions,
                  (SELECT COUNT(*) FROM documents) AS documents
                """
            ).fetchone()
        )
        transcript_quality = dict(
            conn.execute(
                """
                SELECT
                  COUNT(*) AS lessons,
                  SUM(CASE WHEN transcript_text LIKE 'English study notes.%' THEN 1 ELSE 0 END) AS generated_notes,
                  SUM(CASE WHEN transcript_text IS NULL OR TRIM(transcript_text) = '' THEN 1 ELSE 0 END) AS empty_transcripts,
                  SUM(CASE WHEN transcript_text NOT LIKE 'English study notes.%'
                            AND transcript_text IS NOT NULL
                            AND TRIM(transcript_text) <> '' THEN 1 ELSE 0 END) AS transcript_like_lessons
                  ,
                  SUM(CASE WHEN duration IS NULL AND duration_s IS NULL THEN 1 ELSE 0 END) AS duration_missing
                FROM lessons
                """
            ).fetchone()
        )
        practice_quality = dict(
            conn.execute(
                """
                SELECT
                  COUNT(*) AS records,
                  SUM(CASE WHEN pt.question_count > 0 THEN 1 ELSE 0 END) AS non_empty,
                  SUM(CASE WHEN pt.question_count = 0 THEN 1 ELSE 0 END) AS empty,
                  SUM(CASE WHEN ptc.classification = 'full_mock_exam' THEN 1 ELSE 0 END) AS full_mock_exam,
                  SUM(CASE WHEN ptc.classification = 'practice_test' THEN 1 ELSE 0 END) AS practice_test,
                  SUM(CASE WHEN ptc.classification = 'section_quiz' THEN 1 ELSE 0 END) AS section_quiz,
                  SUM(CASE WHEN ptc.classification = 'assignment' THEN 1 ELSE 0 END) AS assignment,
                  SUM(CASE WHEN ptc.classification = 'lab' THEN 1 ELSE 0 END) AS lab,
                  SUM(CASE WHEN ptc.classification = 'empty_shell' THEN 1 ELSE 0 END) AS empty_shell
                FROM practice_tests pt
                LEFT JOIN practice_test_classification ptc ON ptc.test_id = pt.id
                """
            ).fetchone()
        )
        tracks = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  t.id AS track_id,
                  t.title AS track_title,
                  (SELECT COUNT(*) FROM courses c WHERE c.track_id = t.id) AS courses,
                  (SELECT COUNT(*) FROM lessons l JOIN courses c ON c.id = l.course_id WHERE c.track_id = t.id) AS lessons,
                  (SELECT COUNT(*) FROM practice_tests pt WHERE pt.track_id = t.id) AS practice_tests,
                  (SELECT COUNT(*) FROM questions q JOIN courses c ON c.id = q.course_id WHERE c.track_id = t.id) AS questions,
                  (SELECT COUNT(*) FROM practice_tests pt WHERE pt.track_id = t.id AND pt.question_count >= 50) AS full_mock_tests,
                  (SELECT COUNT(*) FROM practice_tests pt WHERE pt.track_id = t.id AND pt.question_count > 0 AND pt.question_count < 20) AS micro_quizzes
                FROM certification_tracks t
                ORDER BY t.position, t.title
                """
            )
        ]
        duplicate_prompts = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  representative_question AS question,
                  duplicate_count,
                  status
                FROM question_duplicates
                ORDER BY duplicate_count DESC, question
                LIMIT 20
                """
            )
        ]
        mapping_review = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, title, track_id, track_title, lesson_count, question_count
                FROM courses
                WHERE track_id = ''
                   OR (LOWER(title) LIKE '%data scientist%' AND track_id = 'snowpro-core')
                   OR (LOWER(title) LIKE '%architect%' AND track_id <> 'advanced-architect')
                   OR (LOWER(title) LIKE '%data engineer%' AND track_id <> 'advanced-data-engineer')
                ORDER BY track_title, title
                LIMIT 30
                """
            )
        ]
    return {
        "totals": totals,
        "transcript_quality": transcript_quality,
        "practice_quality": practice_quality,
        "tracks": tracks,
        "duplicate_prompts": duplicate_prompts,
        "mapping_review": mapping_review,
    }


@router.get("/study/practice-classifications")
def practice_classifications(
    classification: str | None = None,
    reviewed: bool | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    filters = []
    params: list[Any] = []
    if classification:
        filters.append("ptc.classification = ?")
        params.append(classification)
    if reviewed is not None:
        filters.append("ptc.reviewed = ?")
        params.append(1 if reviewed else 0)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                  ptc.*,
                  pt.title,
                  pt.original_title,
                  pt.course_id,
                  pt.course_title,
                  pt.track_id,
                  pt.track_title,
                  pt.question_count
                FROM practice_test_classification ptc
                JOIN practice_tests pt ON pt.id = ptc.test_id
                {where}
                ORDER BY ptc.reviewed, ptc.classification, pt.track_title, pt.course_title, pt.position, pt.title
                LIMIT ?
                """,
                [*params, limit],
            )
        ]
    return {"classifications": rows}


@router.get("/study/question-duplicates")
def question_duplicates(status: str | None = "unreviewed", limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    filters = []
    params: list[Any] = []
    if status:
        filters.append("status = ?")
        params.append(status)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT *
                FROM question_duplicates
                {where}
                ORDER BY duplicate_count DESC, representative_question
                LIMIT ?
                """,
                [*params, limit],
            )
        ]
    return {"duplicates": rows}


def _require_track(conn: Any, track_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM certification_tracks WHERE id = ?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Certification track not found")
    return dict(row)


def _fetch_goal(conn: Any, goal_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT
          g.*,
          t.title AS track_title,
          t.description AS track_description,
          (SELECT COUNT(*) FROM study_plan_items spi WHERE spi.goal_id = g.id) AS item_count,
          (SELECT COUNT(*) FROM study_plan_items spi WHERE spi.goal_id = g.id AND spi.completed = 1) AS completed_count,
          (SELECT COUNT(*) FROM courses c WHERE c.track_id = g.track_id) AS course_count,
          (SELECT COUNT(*) FROM lessons l JOIN courses c ON c.id = l.course_id WHERE c.track_id = g.track_id) AS lesson_count,
          (SELECT COUNT(*) FROM questions q JOIN courses c ON c.id = q.course_id WHERE c.track_id = g.track_id) AS question_count
        FROM study_goals g
        JOIN certification_tracks t ON t.id = g.track_id
        WHERE g.id = ?
        """,
        (goal_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Study goal not found")
    return dict(row)


def _goal_public(row: dict[str, Any]) -> dict[str, Any]:
    target = _parse_date(row.get("target_exam_date"))
    today = date.today()
    item_count = row.get("item_count") or 0
    completed_count = row.get("completed_count") or 0
    return {
        **row,
        "days_remaining": (target - today).days if target else None,
        "completion_pct": round((completed_count / item_count) * 100) if item_count else 0,
    }


def _generate_plan(
    conn: Any,
    *,
    goal_id: int,
    track_id: str,
    target_exam_date: str | None,
    weekly_hours: int,
    daily_question_target: int,
    days: int | None,
    replace: bool,
    start_date: date | None,
) -> int:
    target = _parse_date(target_exam_date)
    today = start_date or date.today()
    if days is None:
        if not target:
            raise HTTPException(status_code=400, detail="Goal target exam date is required to generate a plan")
        days = max(1, (target - today).days + 1)
    if days < 1:
        raise HTTPException(status_code=400, detail="Study plan must have at least one day")
    if replace:
        conn.execute("DELETE FROM study_plan_items WHERE goal_id = ?", (goal_id,))

    lessons = conn.execute(
        """
        SELECT l.id, l.course_id, l.title, l.course_title
        FROM lessons l
        JOIN courses c ON c.id = l.course_id
        WHERE c.track_id = ?
        ORDER BY c.title, COALESCE(l.position, l.sort_key), l.title
        """,
        (track_id,),
    ).fetchall()
    practice_tests = conn.execute(
        """
        SELECT id, course_id, title, course_title, question_count
        FROM practice_tests
        WHERE track_id = ? AND question_count > 0
        ORDER BY CASE WHEN question_count >= 50 THEN 0 ELSE 1 END, position, title
        """,
        (track_id,),
    ).fetchall()
    labs = conn.execute("SELECT id, title FROM lab_exercises ORDER BY position, id LIMIT 40").fetchall()

    lesson_quota_days = max(1, int(days * 0.60))
    lessons_per_day = max(1, min(4, math.ceil(len(lessons) / lesson_quota_days))) if lessons else 0
    inserted = 0
    lesson_idx = 0
    test_idx = 0
    lab_idx = 0
    daily_minutes = max(30, round((weekly_hours * 60) / 7))

    for day_idx in range(days):
        due = (today + timedelta(days=day_idx)).isoformat()
        position = 0

        for _ in range(lessons_per_day):
            if lesson_idx >= len(lessons):
                break
            lesson = lessons[lesson_idx]
            inserted += _insert_plan_item(
                conn,
                goal_id,
                due,
                "lesson",
                f"Watch: {lesson['title']}",
                position,
                course_id=lesson["course_id"],
                lesson_id=lesson["id"],
            )
            position += 1
            lesson_idx += 1

        if daily_question_target:
            inserted += _insert_plan_item(
                conn,
                goal_id,
                due,
                "review",
                f"Drill {daily_question_target} questions for {daily_minutes} minutes",
                position,
                question_count=daily_question_target,
            )
            position += 1

        if practice_tests and day_idx >= 7 and day_idx % 7 == 0 and test_idx < len(practice_tests):
            test = practice_tests[test_idx]
            item_type = "mock_exam" if (test["question_count"] or 0) >= 50 else "practice_test"
            inserted += _insert_plan_item(
                conn,
                goal_id,
                due,
                item_type,
                f"Take {test['title']} ({test['question_count']} questions)",
                position,
                course_id=test["course_id"],
                practice_test_id=test["id"],
                question_count=test["question_count"] or 0,
            )
            position += 1
            test_idx += 1

        if labs and day_idx > 0 and day_idx % 10 == 0:
            lab = labs[lab_idx % len(labs)]
            inserted += _insert_plan_item(
                conn,
                goal_id,
                due,
                "lab",
                f"Complete lab: {lab['title']}",
                position,
            )
            position += 1
            lab_idx += 1

        if day_idx >= max(0, days - 10):
            inserted += _insert_plan_item(
                conn,
                goal_id,
                due,
                "flashcards",
                "Final review: missed questions and flashcards",
                position,
            )

    conn.execute("UPDATE study_goals SET updated_at = datetime('now') WHERE id = ?", (goal_id,))
    return inserted


def _insert_plan_item(
    conn: Any,
    goal_id: int,
    due_date: str,
    item_type: str,
    title: str,
    position: int,
    *,
    course_id: str | None = None,
    lesson_id: str | None = None,
    practice_test_id: str | None = None,
    question_count: int = 0,
) -> int:
    conn.execute(
        """
        INSERT INTO study_plan_items(
          goal_id, due_date, item_type, title, course_id, lesson_id,
          practice_test_id, question_count, position
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (goal_id, due_date, item_type, title, course_id, lesson_id, practice_test_id, question_count, position),
    )
    return 1


def _readiness_for_track(conn: Any, track_id: str) -> dict[str, Any]:
    track = _require_track(conn, track_id)
    row = conn.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM lessons l JOIN courses c ON c.id = l.course_id WHERE c.track_id = ?) AS total_lessons,
          (SELECT COUNT(*) FROM lessons l JOIN courses c ON c.id = l.course_id JOIN lesson_progress lp ON lp.lesson_id = l.id WHERE c.track_id = ? AND lp.completed = 1) AS completed_lessons,
          (SELECT COUNT(*) FROM questions q JOIN courses c ON c.id = q.course_id WHERE c.track_id = ?) AS total_questions,
          (SELECT COUNT(DISTINCT qa.question_id) FROM question_attempts qa JOIN questions q ON q.id = qa.question_id JOIN courses c ON c.id = q.course_id WHERE c.track_id = ?) AS attempted_questions,
          (SELECT COUNT(*) FROM question_attempts qa JOIN questions q ON q.id = qa.question_id JOIN courses c ON c.id = q.course_id WHERE c.track_id = ?) AS attempts,
          (SELECT COALESCE(SUM(qa.correct), 0) FROM question_attempts qa JOIN questions q ON q.id = qa.question_id JOIN courses c ON c.id = q.course_id WHERE c.track_id = ?) AS correct_attempts,
          (SELECT COUNT(*) FROM practice_tests pt WHERE pt.track_id = ? AND pt.question_count >= 50) AS full_mock_tests,
          (SELECT COUNT(*) FROM study_plan_items spi JOIN study_goals g ON g.id = spi.goal_id WHERE g.track_id = ? AND spi.completed = 1) AS completed_plan_items,
          (SELECT COUNT(*) FROM study_plan_items spi JOIN study_goals g ON g.id = spi.goal_id WHERE g.track_id = ?) AS total_plan_items
        """,
        (track_id, track_id, track_id, track_id, track_id, track_id, track_id, track_id, track_id),
    ).fetchone()
    total_lessons = row["total_lessons"] or 0
    completed_lessons = row["completed_lessons"] or 0
    total_questions = row["total_questions"] or 0
    attempted_questions = row["attempted_questions"] or 0
    attempts = row["attempts"] or 0
    correct_attempts = row["correct_attempts"] or 0
    total_plan_items = row["total_plan_items"] or 0
    completed_plan_items = row["completed_plan_items"] or 0

    lesson_pct = (completed_lessons / total_lessons) * 100 if total_lessons else 0
    coverage_pct = (attempted_questions / total_questions) * 100 if total_questions else 0
    accuracy_pct = (correct_attempts / attempts) * 100 if attempts else 0
    plan_pct = (completed_plan_items / total_plan_items) * 100 if total_plan_items else 0
    readiness_pct = round((lesson_pct * 0.30) + (coverage_pct * 0.25) + (accuracy_pct * 0.30) + (plan_pct * 0.15))

    return {
        "track_id": track_id,
        "track_title": track["title"],
        "readiness_pct": min(100, readiness_pct),
        "lesson_completion_pct": round(lesson_pct),
        "question_coverage_pct": round(coverage_pct),
        "accuracy_pct": round(accuracy_pct),
        "plan_completion_pct": round(plan_pct),
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "total_questions": total_questions,
        "attempted_questions": attempted_questions,
        "attempts": attempts,
        "correct_attempts": correct_attempts,
        "full_mock_tests": row["full_mock_tests"] or 0,
    }


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
