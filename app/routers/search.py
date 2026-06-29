from typing import Any

from fastapi import APIRouter, Query

from ..database import connect
from ..ingest import fts_query

router = APIRouter()


@router.get("/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(12, ge=1, le=50)) -> dict[str, Any]:
    query = fts_query(q)
    if not query:
        return {"results": []}
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  title,
                  snippet(search_fts, 1, '<mark>', '</mark>', '...', 32) AS snippet,
                  type,
                  ref_id,
                  ref_id AS id,
                  course_id,
                  path,
                  rank AS score
                FROM search_fts
                WHERE search_fts MATCH ?
                ORDER BY bm25(search_fts)
                LIMIT ?
                """,
                (query, limit),
            )
        ]
    return {"results": rows}
