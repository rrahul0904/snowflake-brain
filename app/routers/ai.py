import json
import sqlite3
from typing import Any, AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..database import connect
from ..ingest import fts_query

router = APIRouter()

CONCEPT_GUIDES: list[dict[str, Any]] = [
    {
        "keys": ["micro partition", "micro partitions", "micro-partition", "micro-partitions", "partition pruning", "clustering"],
        "title": "Micro-partitions",
        "answer": [
            "Snowflake stores table data in immutable micro-partitions and keeps metadata about each partition, such as value ranges and row counts.",
            "Query pruning uses this metadata to skip micro-partitions that cannot contain the requested rows.",
            "Clustering can improve pruning when data is naturally disordered for common filter predicates.",
        ],
        "remember": [
            "Users do not manually create micro-partitions.",
            "Good clustering improves pruning; it does not replace warehouse sizing or query design.",
        ],
        "tip": "When an exam question mentions pruning, clustering depth, or metadata ranges, think micro-partitions.",
    },
    {
        "keys": ["time travel", "undrop", "before statement", "at offset", "retention"],
        "title": "Snowflake Time Travel",
        "answer": [
            "Time Travel lets you query, clone, or restore historical data from a table, schema, or database within its configured retention window.",
            "Common exam operations include `SELECT ... AT | BEFORE`, `UNDROP`, and cloning an object at a point in time.",
            "Retention is edition and object dependent; transient and temporary objects have different recovery expectations than permanent objects.",
        ],
        "remember": [
            "Time Travel is for user-accessible historical recovery.",
            "Fail-safe is Snowflake-managed disaster recovery and is not directly queryable by users.",
        ],
        "tip": "Do not confuse Time Travel with Fail-safe: Time Travel is the feature you use in SQL; Fail-safe is handled by Snowflake.",
    },
    {
        "keys": ["fail safe", "failsafe", "disaster recovery"],
        "title": "Fail-safe",
        "answer": [
            "Fail-safe is Snowflake's internal recovery period after Time Travel retention ends.",
            "Users cannot run normal SQL queries against Fail-safe data.",
            "It is mainly for Snowflake-assisted disaster recovery, not routine table restore workflows.",
        ],
        "remember": ["Use Time Travel for self-service recovery.", "Use Fail-safe as the last-resort Snowflake recovery layer."],
        "tip": "If an answer says users can directly query Fail-safe, treat it as suspicious.",
    },
    {
        "keys": ["zero copy", "clone", "cloning"],
        "title": "Zero-copy cloning",
        "answer": [
            "Zero-copy cloning creates a metadata-based copy of a database, schema, or table without duplicating existing micro-partition storage immediately.",
            "The clone is writable and diverges from the source as changes occur.",
            "It is commonly used for development, testing, quick recovery, and point-in-time copies with Time Travel.",
        ],
        "remember": ["Cloning is fast because existing storage is shared.", "New changes after the clone consume additional storage."],
        "tip": "For fast environment copies, zero-copy clone is usually the Snowflake-native answer.",
    },
    {
        "keys": ["warehouse", "auto suspend", "auto resume", "scaling", "multi cluster"],
        "title": "Virtual warehouses",
        "answer": [
            "Virtual warehouses provide compute for queries, loading, and transformations.",
            "Size affects query resources; multi-cluster warehouses primarily help concurrency, not single-query speed.",
            "Auto-suspend and auto-resume are central cost controls because warehouses bill while running.",
        ],
        "remember": ["Scale up for heavy queries.", "Scale out with multi-cluster for concurrent users.", "Suspend idle warehouses to control cost."],
        "tip": "For concurrency problems, look for multi-cluster; for individual slow queries, look first at warehouse size and query design.",
    },
    {
        "keys": ["rbac", "role", "privilege", "grant", "ownership"],
        "title": "RBAC and access control",
        "answer": [
            "Snowflake uses role-based access control: privileges are granted to roles, and roles are granted to users or other roles.",
            "Access is the result of the active role hierarchy and the privileges available to it.",
            "`OWNERSHIP` is powerful because it transfers control over an object.",
        ],
        "remember": ["Grant privileges to roles, not directly to users.", "Use role hierarchy for reusable access patterns."],
        "tip": "Exam answers that bypass roles usually do not match Snowflake's normal access model.",
    },
    {
        "keys": ["stream", "task", "change data", "cdc"],
        "title": "Streams and tasks",
        "answer": [
            "Streams track change data capture records for tables and views.",
            "Tasks schedule SQL or stored procedure work, often consuming streams for incremental pipelines.",
            "Together, streams and tasks are a common Snowflake-native pattern for ELT automation.",
        ],
        "remember": ["Streams record changes.", "Tasks run scheduled work.", "Use both for incremental processing."],
        "tip": "When the question says incremental pipeline inside Snowflake, streams plus tasks is often the answer.",
    },
    {
        "keys": ["snowpipe", "pipe", "continuous load", "auto ingest"],
        "title": "Snowpipe",
        "answer": [
            "Snowpipe loads files from stages continuously or near-continuously into Snowflake tables.",
            "It is serverless from the user's warehouse perspective and is commonly paired with cloud event notifications.",
            "Bulk `COPY INTO` is still appropriate for batch loading and controlled warehouse-based loads.",
        ],
        "remember": ["Snowpipe is for automated file ingestion.", "`COPY INTO` is the basic batch loading command."],
        "tip": "If the question says new staged files should load automatically, think Snowpipe.",
    },
]


class AskRequest(BaseModel):
    question: str
    context_limit: int = 8
    track_id: str | None = None
    course_id: str | None = None
    lesson_id: str | None = None
    practice_test_id: str | None = None
    question_id: str | None = None
    selected_answer: str | None = None
    correct_answer: str | None = None


@router.post("/ai/ask")
async def ai_ask(payload: AskRequest) -> StreamingResponse:
    return StreamingResponse(_ask_stream(payload), media_type="text/event-stream")


@router.post("/brain/ask")
def brain_ask(payload: AskRequest) -> dict[str, Any]:
    sources = _context(payload.question, payload.context_limit)
    if not sources:
        return {
            "answer": "Local archive answer: I could not find strong course matches for that wording yet. Try the exact Snowflake feature name, SQL command, or object name from the lesson/question.",
            "sources": [],
            "mode": "local_archive",
            "next_steps": ["Search the same term", "Try a shorter Snowflake-specific question", "Open the related lesson or practice question"],
        }
    answer = _local_rag_answer(payload.question, sources)
    return {
        "answer": answer,
        "sources": sources,
        "mode": "local_archive",
        "next_steps": ["Open the strongest source", "Submit the question to see the downloaded explanation", "Mark this question for review if the concept is weak"],
    }


async def _ask_stream(payload: AskRequest) -> AsyncIterator[str]:
    sources = _context(payload.question, payload.context_limit)
    answer = _local_rag_answer(payload.question, sources) if sources else (
        "Local archive answer: I could not find strong course matches for that wording yet. "
        "Try the exact Snowflake feature name, SQL command, or object name from the lesson/question.\n\n"
        "Exam tip: when no clean local evidence is found, search the exact Snowflake object or command before trusting a generated explanation."
    )
    for chunk in _chunk_text(answer, 260):
        yield _sse({"delta": chunk})
    yield _sse({"done": True, "sources": sources, "mode": "local_archive"})


def _context(question: str, limit: int) -> list[dict[str, Any]]:
    query = fts_query(question)
    if not query:
        return []
    max_rows = max(3, min(limit, 12))
    with connect() as conn:
        rows: list[dict[str, Any]] = []
        rows.extend(_search_index_context(conn, query, max_rows))
        rows.extend(_transcript_context(conn, query, max_rows))
        rows.extend(_question_context(conn, query, max_rows))
        rows.extend(_lesson_title_context(conn, query, max_rows))
        if len(rows) < 3:
            rows.extend(_like_context(conn, question, max_rows))
    return _dedupe_sources(rows)[:max_rows]


def _search_index_context(conn, query: str, limit: int) -> list[dict[str, Any]]:
    try:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  title,
                  snippet(search_fts, 1, '', '', '...', 48) AS snippet,
                  type,
                  ref_id,
                  ref_id AS id,
                  course_id,
                  path
                FROM search_fts
                WHERE search_fts MATCH ?
                ORDER BY bm25(search_fts)
                LIMIT ?
                """,
                (query, limit),
            )
        ]
    except sqlite3.OperationalError:
        return []


def _transcript_context(conn, query: str, limit: int) -> list[dict[str, Any]]:
    try:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  l.title || ' transcript' AS title,
                  snippet(chunk_fts, 0, '', '', '...', 52) AS snippet,
                  'transcript' AS type,
                  tc.lesson_id AS ref_id,
                  tc.lesson_id AS id,
                  l.course_id AS course_id,
                  l.video_path AS path
                FROM chunk_fts
                JOIN transcript_chunks tc ON tc.id = chunk_fts.rowid
                JOIN lessons l ON l.id = tc.lesson_id
                WHERE chunk_fts MATCH ?
                ORDER BY bm25(chunk_fts)
                LIMIT ?
                """,
                (query, limit),
            )
        ]
    except sqlite3.OperationalError:
        return []


def _question_context(conn, query: str, limit: int) -> list[dict[str, Any]]:
    try:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  q.question AS title,
                  snippet(question_fts, 0, '', '', '...', 44) || ' ' || snippet(question_fts, 1, '', '', '...', 44) AS snippet,
                  'question' AS type,
                  q.id AS ref_id,
                  q.id AS id,
                  q.course_id AS course_id,
                  q.source_path AS path
                FROM question_fts
                JOIN questions q ON q.rowid = question_fts.rowid
                WHERE question_fts MATCH ?
                ORDER BY bm25(question_fts)
                LIMIT ?
                """,
                (query, limit),
            )
        ]
    except sqlite3.OperationalError:
        return []


def _lesson_title_context(conn, query: str, limit: int) -> list[dict[str, Any]]:
    try:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  l.title AS title,
                  COALESCE(NULLIF(l.excerpt, ''), snippet(lesson_fts, 0, '', '', '...', 36)) AS snippet,
                  'lesson' AS type,
                  l.id AS ref_id,
                  l.id AS id,
                  l.course_id AS course_id,
                  l.video_path AS path
                FROM lesson_fts
                JOIN lessons l ON l.rowid = lesson_fts.rowid
                WHERE lesson_fts MATCH ?
                ORDER BY bm25(lesson_fts)
                LIMIT ?
                """,
                (query, limit),
            )
        ]
    except sqlite3.OperationalError:
        return []


def _like_context(conn, question: str, limit: int) -> list[dict[str, Any]]:
    tokens = [token for token in fts_query(question).replace("*", "").split() if len(token) > 2][:4]
    if not tokens:
        return []
    like = [f"%{token}%" for token in tokens]
    rows: list[dict[str, Any]] = []
    for pattern in like:
        rows.extend(
            dict(row)
            for row in conn.execute(
                """
                SELECT title, COALESCE(NULLIF(excerpt, ''), substr(transcript_text, 1, 420)) AS snippet,
                       'lesson' AS type, id AS ref_id, id, course_id, video_path AS path
                FROM lessons
                WHERE title LIKE ? OR transcript_text LIKE ?
                LIMIT ?
                """,
                (pattern, pattern, limit),
            )
        )
        rows.extend(
            dict(row)
            for row in conn.execute(
                """
                SELECT question AS title, COALESCE(NULLIF(explanation, ''), question) AS snippet,
                       'question' AS type, id AS ref_id, id, course_id, source_path AS path
                FROM questions
                WHERE question LIKE ? OR explanation LIKE ?
                LIMIT ?
                """,
                (pattern, pattern, limit),
            )
        )
        if len(rows) >= limit:
            break
    return rows


def _dedupe_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        snippet = _clean_snippet(row.get("snippet", ""))
        key = (str(row.get("type") or ""), str(row.get("ref_id") or row.get("id") or ""), snippet[:80])
        if not snippet or key in seen:
            continue
        seen.add(key)
        item = dict(row)
        item["snippet"] = snippet
        deduped.append(item)
    return deduped


def _local_rag_answer(question: str, sources: list[dict[str, Any]]) -> str:
    guide = _concept_guide(question)
    source_bullets = _source_bullets(sources)
    if guide:
        return "\n".join(
            [
                f"Answer: {guide['title']}",
                "",
                *[f"- {line}" for line in guide["answer"]],
                "",
                "What to remember:",
                *[f"- {line}" for line in guide["remember"]],
                "",
                "Local sources found:",
                *source_bullets,
                "",
                f"Exam tip: {guide['tip']}",
            ]
        )

    learned = _snippet_takeaways(sources)
    if not learned:
        learned = ["The local index found related material, but not enough clean context to form a confident direct explanation."]
    return "\n".join(
        [
            f"Answer from the local course intelligence system: {question}",
            "",
            *[f"- {line}" for line in learned],
            "",
            "Local sources found:",
            *source_bullets,
            "",
            "Exam tip: identify the Snowflake object, command, or behavior named in the question, then eliminate answers that describe a different feature.",
        ]
    )


def _concept_guide(question: str) -> dict[str, Any] | None:
    text = " ".join(str(question or "").lower().split())
    for guide in CONCEPT_GUIDES:
        if any(key in text for key in guide["keys"]):
            return guide
    return None


def _source_bullets(sources: list[dict[str, Any]]) -> list[str]:
    bullets = []
    for source in sources:
        snippet = _clean_snippet(source.get("snippet", ""))
        if not snippet:
            continue
        label = source.get("type", "source")
        title = source.get("title", "Course source")
        bullets.append(f"- {title} ({label}): {snippet}")
        if len(bullets) == 3:
            break
    return bullets or ["- Strongest local source did not include a clean snippet."]


def _snippet_takeaways(sources: list[dict[str, Any]]) -> list[str]:
    takeaways = []
    for source in sources:
        snippet = _clean_snippet(source.get("snippet", ""))
        if not snippet:
            continue
        for sentence in snippet.replace("?", ".").split("."):
            sentence = sentence.strip(" -")
            if 45 <= len(sentence) <= 220 and sentence not in takeaways:
                takeaways.append(sentence)
                break
        if len(takeaways) == 3:
            break
    return takeaways


def _clean_snippet(value: str) -> str:
    text = " ".join(str(value or "").split())
    text = text.replace("<mark>", "").replace("</mark>", "")
    return text[:420]


def _chunk_text(text: str, size: int = 240) -> list[str]:
    if not text:
        return [""]
    chunks = []
    current = ""
    for part in text.split(" "):
        if len(current) + len(part) + 1 > size and current:
            chunks.append(current + " ")
            current = part
        else:
            current = f"{current} {part}".strip()
    if current:
        chunks.append(current)
    return chunks


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"
