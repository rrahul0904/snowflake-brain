from pathlib import Path
from typing import Any
import mimetypes

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse

from ..config import CONTENT_ROOT
from ..database import connect
from ..labs import LABS
from ..serializers import lesson_public, question_public

router = APIRouter()


@router.get("/summary")
def summary() -> dict[str, Any]:
    with connect() as conn:
        stats = {
            "tracks": conn.execute("SELECT COUNT(*) AS count FROM certification_tracks").fetchone()["count"],
            "courses": conn.execute("SELECT COUNT(*) AS count FROM courses").fetchone()["count"],
            "practice_tests": conn.execute("SELECT COUNT(*) AS count FROM practice_tests WHERE question_count > 0").fetchone()["count"],
            "lessons": conn.execute("SELECT COUNT(*) AS count FROM lessons").fetchone()["count"],
            "questions": conn.execute("SELECT COUNT(*) AS count FROM questions").fetchone()["count"],
            "documents": conn.execute("SELECT COUNT(*) AS count FROM documents").fetchone()["count"],
            "flashcards": conn.execute("SELECT COUNT(*) AS count FROM flashcards").fetchone()["count"],
            "labs": conn.execute("SELECT COUNT(*) AS count FROM lab_exercises").fetchone()["count"] or len(LABS),
        }
        meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
        courses = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  c.id,
                  c.track_id,
                  c.track_title,
                  c.title,
                  c.slug,
                  c.path,
                  c.source_url,
                  COALESCE(NULLIF(c.lesson_count, 0), (SELECT COUNT(*) FROM lessons l WHERE l.course_id = c.id)) AS lesson_count,
                  COALESCE(NULLIF(c.question_count, 0), (SELECT COUNT(*) FROM questions q WHERE q.course_id = c.id)) AS question_count
                FROM courses c
                ORDER BY question_count DESC, lesson_count DESC, c.title
                LIMIT 12
                """
            )
        ]
    return {"stats": stats, "meta": meta, "courses": courses}


@router.get("/tracks")
def tracks() -> dict[str, Any]:
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  t.id,
                  t.title,
                  t.description,
                  t.position,
                  (SELECT COUNT(*) FROM courses c WHERE c.track_id = t.id) AS course_count,
                  (SELECT COUNT(*) FROM lessons l JOIN courses c ON c.id = l.course_id WHERE c.track_id = t.id) AS lesson_count,
                  (SELECT COUNT(*) FROM questions q JOIN courses c ON c.id = q.course_id WHERE c.track_id = t.id) AS question_count,
                  (SELECT COUNT(*) FROM practice_tests pt WHERE pt.track_id = t.id AND pt.question_count > 0) AS practice_test_count
                FROM certification_tracks t
                ORDER BY t.position, t.title
                """
            )
        ]
    return {"tracks": rows}


@router.get("/tracks/{track_id}/courses")
def track_courses(track_id: str) -> dict[str, Any]:
    return courses(track_id=track_id)


@router.get("/courses")
def courses(track_id: str | None = None, q: str = "") -> dict[str, Any]:
    filters = []
    params: list[Any] = []
    if track_id:
        filters.append("c.track_id = ?")
        params.append(track_id)
    if q:
        filters.append("(c.title LIKE ? OR c.track_title LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])
    where = "WHERE " + " AND ".join(filters) if filters else ""
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                  c.id,
                  c.track_id,
                  c.track_title,
                  c.title,
                  c.slug,
                  c.path,
                  c.source_url,
                  COALESCE(NULLIF(c.lesson_count, 0), (SELECT COUNT(*) FROM lessons l WHERE l.course_id = c.id)) AS lesson_count,
                  COALESCE(NULLIF(c.question_count, 0), (SELECT COUNT(*) FROM questions q WHERE q.course_id = c.id)) AS question_count,
                  (SELECT COUNT(*) FROM documents d WHERE d.course_id = c.id) AS document_count,
                  (SELECT COUNT(*) FROM practice_tests pt WHERE pt.course_id = c.id AND pt.question_count > 0) AS practice_test_count
                FROM courses c
                {where}
                ORDER BY c.track_title, c.title
                """,
                params,
            )
        ]
    return {"courses": rows}


@router.get("/courses/{course_id}")
def course_detail(course_id: str) -> dict[str, Any]:
    with connect() as conn:
        course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        sections = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, title AS section, path, position, lesson_count
                FROM course_sections
                WHERE course_id = ?
                ORDER BY position, title
                """,
                (course_id,),
            )
        ]
        tests = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, title, original_title, position, question_count
                FROM practice_tests
                WHERE course_id = ? AND question_count > 0
                ORDER BY position, title
                """,
                (course_id,),
            )
        ]
    data = dict(course)
    data["sections"] = sections
    data["practice_tests"] = tests
    return data


@router.get("/courses/{course_id}/lessons")
def course_lessons(course_id: str) -> dict[str, Any]:
    return lessons(course_id=course_id, limit=1000, offset=0)


@router.get("/courses/{course_id}/sections")
def course_sections(course_id: str) -> dict[str, Any]:
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, title, path, position, lesson_count
                FROM course_sections
                WHERE course_id = ?
                ORDER BY position, title
                """,
                (course_id,),
            )
        ]
    return {"sections": rows}


@router.get("/courses/{course_id}/practice-tests")
def course_practice_tests(course_id: str) -> dict[str, Any]:
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT *
                FROM practice_tests
                WHERE course_id = ? AND question_count > 0
                ORDER BY position, title
                """,
                (course_id,),
            )
        ]
    return {"tests": rows}


@router.get("/lessons")
def lessons(
    track_id: str | None = None,
    course_id: str | None = None,
    q: str = "",
    limit: int = Query(40, ge=1, le=3000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    filters = []
    params: list[Any] = []
    if course_id:
        filters.append("course_id = ?")
        params.append(course_id)
    if track_id:
        filters.append("course_id IN (SELECT id FROM courses WHERE track_id = ?)")
        params.append(track_id)
    if q:
        filters.append("(title LIKE ? OR transcript_text LIKE ? OR course_title LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    where = "WHERE " + " AND ".join(filters) if filters else ""
    with connect() as conn:
        rows = [
            lesson_public(dict(row))
            for row in conn.execute(
                f"""
                SELECT *
                FROM lessons
                {where}
                ORDER BY course_title, COALESCE(position, sort_key), title
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
        ]
    return {"lessons": rows}


@router.get("/lessons/{lesson_id}")
def lesson_detail(lesson_id: str) -> dict[str, Any]:
    with connect() as conn:
        lesson = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        questions = [
            question_public(dict(row), include_answer=True)
            for row in conn.execute(
                """
                SELECT * FROM questions
                WHERE course_id = ?
                ORDER BY RANDOM()
                LIMIT 6
                """,
                (lesson["course_id"],),
            )
        ]
        notes = [
            dict(row)
            for row in conn.execute(
                "SELECT id, body, created_at FROM notes WHERE lesson_id = ? ORDER BY created_at DESC",
                (lesson_id,),
            )
        ]
    data = lesson_public(dict(lesson))
    data["transcript_text"] = lesson["transcript_text"] or ""
    data["related_questions"] = questions
    data["notes"] = notes
    return data


@router.get("/lessons/{lesson_id}/transcript")
def lesson_transcript(lesson_id: str) -> dict[str, Any]:
    with connect() as conn:
        chunks = [
            dict(row)
            for row in conn.execute(
                """
                SELECT chunk_idx, text, start_s, end_s
                FROM transcript_chunks
                WHERE lesson_id = ?
                ORDER BY chunk_idx
                """,
                (lesson_id,),
            )
        ]
    return {"lesson_id": lesson_id, "chunks": chunks}


@router.get("/lessons/{lesson_id}/vtt")
def lesson_vtt(lesson_id: str) -> PlainTextResponse:
    with connect() as conn:
        row = conn.execute("SELECT transcript_path, vtt_path FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    rel = row["vtt_path"] or row["transcript_path"]
    if not rel:
        raise HTTPException(status_code=404, detail="No caption file for this lesson")
    target = _safe_content_path(rel)
    try:
        text = target.read_text(errors="ignore")
    except OSError:
        raise HTTPException(status_code=404, detail="Caption file not found") from None
    return PlainTextResponse(text, media_type="text/vtt; charset=utf-8")


@router.post("/lessons/{lesson_id}/notes")
def lesson_note(lesson_id: str, payload: dict[str, str]) -> dict[str, Any]:
    body = (payload.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Note body is required")
    with connect() as conn:
        if not conn.execute("SELECT id FROM lessons WHERE id = ?", (lesson_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Lesson not found")
        cursor = conn.execute("INSERT INTO notes(lesson_id, body) VALUES (?, ?)", (lesson_id, body))
    return {"ok": True, "id": cursor.lastrowid}


@router.get("/documents/{document_id}")
def document_detail(document_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    data = dict(row)
    data["body"] = (data.get("body") or "")[:10000]
    return data


@router.get("/media")
def media(request: Request, path: str):
    """Serve local lesson videos with byte-range support.

    Browser video controls need HTTP 206 responses for seeking/scrubbing.
    Some ASGI/FileResponse combinations stream the file but do not provide
    reliable range behavior for local MP4/MOV assets, so we implement the
    Range header explicitly here.
    """
    target = _safe_content_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Media not found")

    file_size = target.stat().st_size
    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    range_header = request.headers.get("range")

    if not range_header:
        response = FileResponse(target, media_type=media_type)
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Content-Length"] = str(file_size)
        return response

    try:
        units, byte_range = range_header.strip().split("=", 1)
        if units.lower() != "bytes":
            raise ValueError("Unsupported range unit")
        start_s, end_s = (byte_range.split("-", 1) + [""])[:2]

        if start_s == "":
            # suffix range: bytes=-500 means the final 500 bytes
            suffix_len = int(end_s)
            start = max(file_size - suffix_len, 0)
            end = file_size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else file_size - 1

        if start < 0 or end < start or start >= file_size:
            return StreamingResponse(
                iter(()),
                status_code=416,
                headers={
                    "Content-Range": f"bytes */{file_size}",
                    "Accept-Ranges": "bytes",
                },
                media_type=media_type,
            )
        end = min(end, file_size - 1)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Range header")

    chunk_size = 1024 * 1024
    content_length = end - start + 1

    def iter_file():
        with target.open("rb") as handle:
            handle.seek(start)
            remaining = content_length
            while remaining > 0:
                data = handle.read(min(chunk_size, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        iter_file(),
        status_code=206,
        media_type=media_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        },
    )


def _safe_content_path(path: str) -> Path:
    root = CONTENT_ROOT.resolve()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise HTTPException(status_code=404, detail="Media not found")
    return target
