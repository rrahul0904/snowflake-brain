import threading
from typing import Any

from fastapi import APIRouter, BackgroundTasks

from ..config import CONTENT_ROOT
from ..database import connect
from ..ingest import get_status, index_is_empty, rebuild_index

router = APIRouter()


def maybe_auto_ingest() -> None:
    if index_is_empty():
        thread = threading.Thread(target=rebuild_index, daemon=True)
        thread.start()


@router.get("/index/status")
def index_status() -> dict[str, Any]:
    status = get_status()
    if not status.get("running"):
        with connect() as conn:
            courses = conn.execute("SELECT COUNT(*) AS count FROM courses").fetchone()["count"]
            lessons = conn.execute("SELECT COUNT(*) AS count FROM lessons").fetchone()["count"]
            questions = conn.execute("SELECT COUNT(*) AS count FROM questions").fetchone()["count"]
            chunks = conn.execute("SELECT COUNT(*) AS count FROM transcript_chunks").fetchone()["count"]
            documents = conn.execute("SELECT COUNT(*) AS count FROM documents").fetchone()["count"]
            meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
        if courses:
            status.update(
                {
                    "message": "Index ready",
                    "courses_seen": courses,
                    "courses_indexed": courses,
                    "lessons_indexed": lessons,
                    "questions_indexed": questions,
                    "chunks_indexed": chunks,
                    "documents_indexed": documents,
                    "last_built": meta.get("last_indexed_at"),
                }
            )
    status["content_root"] = str(CONTENT_ROOT)
    return status


@router.post("/index/rebuild")
def rebuild(background_tasks: BackgroundTasks) -> dict[str, Any]:
    status = get_status()
    if status.get("running"):
        return {"started": False, "status": status}
    background_tasks.add_task(rebuild_index)
    return {"started": True}
