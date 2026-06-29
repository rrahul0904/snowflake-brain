import json
from typing import Any, AsyncIterator

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from ..database import connect
from ..ingest import fts_query

router = APIRouter()

SYSTEM_PROMPT = """You are a concise Snowflake SnowPro Core certification tutor.
You answer ONLY based on the provided context snippets from the user's
course material. If the answer cannot be found in the context, say so.
Keep answers under 200 words. Use bullet points for lists. End with a
one-sentence exam tip starting with "Exam tip:"."""


CONCEPT_GUIDES: list[dict[str, Any]] = [
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
    context_limit: int = 5


@router.post("/ai/ask")
async def ai_ask(payload: AskRequest) -> StreamingResponse:
    return StreamingResponse(_ask_stream(payload), media_type="text/event-stream")


@router.post("/brain/ask")
def brain_ask(payload: AskRequest) -> dict[str, Any]:
    sources = _context(payload.question, payload.context_limit)
    if not sources:
        return {
            "answer": "I could not find strong matches in the local Snowflake brain yet. Try rebuilding the index or asking with Snowflake terms from your course titles.",
            "sources": [],
            "next_steps": ["Rebuild the index", "Try a shorter Snowflake-specific question"],
        }
    answer = _local_rag_answer(payload.question, sources)
    return {
        "answer": answer,
        "sources": sources,
        "next_steps": ["Open the strongest source", "Submit the question to see the downloaded explanation", "Mark this question for review if the concept is weak"],
    }


async def _ask_stream(payload: AskRequest) -> AsyncIterator[str]:
    sources = _context(payload.question, payload.context_limit)
    if not ANTHROPIC_API_KEY:
        yield _sse({"delta": "AI assistant requires ANTHROPIC_API_KEY environment variable."})
        yield _sse({"done": True, "sources": sources})
        return
    context = "\n\n".join(
        f"[{idx + 1}] {source['title']} ({source['type']}): {source['snippet']}"
        for idx, source in enumerate(sources)
    )
    user_text = f"Question: {payload.question}\n\nContext:\n{context or 'No matching context found.'}"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_text}],
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=45) as client:
        async with client.stream("POST", "https://api.anthropic.com/v1/messages", headers=headers, json=body) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line.removeprefix("data:").strip()
                if raw == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if event.get("type") == "content_block_delta":
                    text = event.get("delta", {}).get("text", "")
                    if text:
                        yield _sse({"delta": text})
    yield _sse({"done": True, "sources": sources})


def _context(question: str, limit: int) -> list[dict[str, Any]]:
    query = fts_query(question)
    if not query:
        return []
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                  title,
                  snippet(search_fts, 1, '', '', '...', 42) AS snippet,
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
                (query, max(1, min(limit, 8))),
            )
        ]
    return rows


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
            f"Answer from the local Snowflake brain: {question}",
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


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"
