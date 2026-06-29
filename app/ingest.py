import hashlib
import html
import json
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from threading import Lock
from typing import Any

from .config import BRAIN_DB, CONTENT_ROOT
from .database import connect as database_connect
from .database import run_migrations
from .labs import LABS

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov"}
TEXT_DOC_EXTENSIONS = {".md", ".txt", ".csv"}
ENGLISH_SIGNAL_WORDS = {
    "a",
    "about",
    "account",
    "and",
    "are",
    "as",
    "be",
    "can",
    "create",
    "data",
    "database",
    "for",
    "from",
    "if",
    "in",
    "is",
    "it",
    "load",
    "of",
    "on",
    "or",
    "query",
    "role",
    "schema",
    "snowflake",
    "table",
    "that",
    "the",
    "this",
    "to",
    "use",
    "warehouse",
    "when",
    "with",
    "you",
}
NON_ENGLISH_SIGNAL_WORDS = {
    "agora",
    "aqui",
    "assim",
    "avec",
    "bien",
    "como",
    "con",
    "cuando",
    "dados",
    "dans",
    "des",
    "donc",
    "données",
    "chào",
    "chúng",
    "cùng",
    "dịch",
    "được",
    "hãy",
    "hiểu",
    "kiếm",
    "el",
    "elle",
    "então",
    "esta",
    "este",
    "esto",
    "está",
    "être",
    "ici",
    "isso",
    "mais",
    "mas",
    "muito",
    "não",
    "nous",
    "người",
    "này",
    "para",
    "pero",
    "por",
    "porque",
    "que",
    "ser",
    "sobre",
    "tìm",
    "thêm",
    "tiếp",
    "trong",
    "truy",
    "também",
    "temos",
    "todos",
    "uma",
    "uno",
    "vous",
    "você",
    "vamos",
    "vậy",
    "về",
    "vụ",
    "xem",
    # Italian caption signals
    "anche",
    "alla",
    "cercarlo",
    "gratuita",
    "gratuito",
    "hai",
    "modulo",
    "pagina",
    "prova",
    "puoi",
    "registrarti",
    "vai",
    # German caption signals
    "aber",
    "alle",
    "alles",
    "auch",
    "auf",
    "beginnen",
    "bleiben",
    "dann",
    "darauf",
    "daran",
    "das",
    "dass",
    "dem",
    "den",
    "der",
    "deutsche",
    "diese",
    "diesem",
    "diesen",
    "dieser",
    "einen",
    "einem",
    "einer",
    "für",
    "garage",
    "gewöhnen",
    "habe",
    "haben",
    "ich",
    "kurs",
    "kurzen",
    "lassen",
    "lagerhäusern",
    "mich",
    "mir",
    "motoren",
    "müssen",
    "nicht",
    "oder",
    "sie",
    "sich",
    "und",
    "uns",
    "virtuellen",
    "werde",
    "werden",
    "willkommen",
    "zehn",
    "zu",
    "überblick",
}
QUERY_STOPWORDS = {
    "a",
    "about",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "practice",
    "should",
    "snowflake",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
    "work",
}
GENERIC_TEST_TITLES = {
    "check your knowledge",
    "knowledge check",
    "practice test",
    "quiz",
    "test",
    "test your knowledge",
}
CERTIFICATION_TRACKS = [
    (
        "snowpro-core",
        "SnowPro Core",
        "Core Snowflake architecture, virtual warehouses, storage, loading, security, sharing, and account operations.",
    ),
    (
        "associate-platform",
        "SnowPro Associate Platform",
        "Associate platform exam material, platform administration, and practical Snowflake operations.",
    ),
    (
        "advanced-architect",
        "SnowPro Advanced Architect",
        "Advanced architecture, governance, optimization, security, and multi-account design.",
    ),
    (
        "advanced-data-engineer",
        "SnowPro Advanced Data Engineer",
        "Data engineering, pipelines, streams, tasks, Snowpipe, transformation, and reliability patterns.",
    ),
    (
        "snowpark",
        "SnowPro Snowpark",
        "Snowpark development, Python, UDFs, stored procedures, and Snowpark certification preparation.",
    ),
    (
        "cortex-genai",
        "Snowflake Cortex and GenAI",
        "Cortex, LLM functions, AI/ML features, and Snowflake GenAI specialty material.",
    ),
    (
        "cost-optimization",
        "Snowflake Cost Optimization",
        "Warehouses, billing, query tuning, auto-suspend, monitoring, and cost-control courses.",
    ),
    (
        "iceberg",
        "Apache Iceberg",
        "Apache Iceberg and Snowflake open table concepts included in the archive.",
    ),
    (
        "general-snowflake",
        "General Snowflake",
        "General Snowflake courses that do not map cleanly to one certification track.",
    ),
]


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def get_text(self) -> str:
        return " ".join(self.parts)


STATUS_LOCK = Lock()
INDEX_STATUS: dict[str, Any] = {
    "running": False,
    "message": "Not started",
    "courses_seen": 0,
    "lessons_indexed": 0,
    "questions_indexed": 0,
    "documents_indexed": 0,
    "chunks_indexed": 0,
    "started_at": None,
    "finished_at": None,
    "error": None,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_root() -> Path:
    return CONTENT_ROOT


def db_path() -> Path:
    return BRAIN_DB


@contextmanager
def connect() -> Any:
    with database_connect() as conn:
        yield conn


def init_db() -> None:
    run_migrations()
    with connect() as conn:
        seed_certification_tracks(conn)
        insert_labs_into_search(conn)
        seed_lab_exercises(conn)


def set_status(**kwargs: Any) -> None:
    with STATUS_LOCK:
        INDEX_STATUS.update(kwargs)


def get_status() -> dict[str, Any]:
    with STATUS_LOCK:
        return dict(INDEX_STATUS)


def rebuild_index() -> dict[str, Any]:
    root = content_root()
    set_status(
        running=True,
        message="Scanning source content",
        courses_seen=0,
        lessons_indexed=0,
        questions_indexed=0,
        documents_indexed=0,
        chunks_indexed=0,
        started_at=now_iso(),
        finished_at=None,
        error=None,
    )
    try:
        stats = _rebuild_index(root)
        set_status(running=False, message="Index ready", finished_at=now_iso(), **stats)
        return stats
    except Exception as exc:
        set_status(running=False, message="Index failed", finished_at=now_iso(), error=str(exc))
        raise


def _rebuild_index(root: Path) -> dict[str, Any]:
    init_db()
    stats = {
        "source_courses_seen": 0,
        "courses_seen": 0,
        "lessons_indexed": 0,
        "duplicate_courses_skipped": 0,
        "duplicate_lessons_skipped": 0,
        "questions_indexed": 0,
        "duplicate_questions_skipped": 0,
        "documents_indexed": 0,
        "duplicate_documents_skipped": 0,
        "chunks_indexed": 0,
    }
    with connect() as conn:
        conn.commit()
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.executescript(
            """
            DELETE FROM search_fts;
            DELETE FROM transcript_chunks;
            DELETE FROM documents;
            DELETE FROM questions;
            DELETE FROM practice_tests;
            DELETE FROM lessons;
            DELETE FROM course_sections;
            DELETE FROM courses;
            DELETE FROM meta WHERE key IN ('last_indexed_at', 'content_root');
            """
        )
        seed_certification_tracks(conn)
        insert_labs_into_search(conn)

        if not root.exists():
            conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('content_root', ?)", (str(root),))
            return stats

        course_candidates, skipped_courses = select_course_candidates(root)
        stats["source_courses_seen"] = len(course_candidates) + len(skipped_courses)
        stats["duplicate_courses_skipped"] = len(skipped_courses)
        seen_lesson_keys: set[str] = set()
        seen_question_keys: set[str] = set()
        seen_document_keys: set[str] = set()

        for candidate in course_candidates:
            course_dir = candidate["course_dir"]
            course_meta = candidate["course_meta"]
            course_id = stable_id(course_dir.relative_to(root).as_posix())
            title = candidate["title"]
            track_id = candidate["track_id"]
            track_title = candidate["track_title"]
            source_url = candidate["source_url"]
            rel_course = candidate["rel_course"]

            conn.execute(
                """
                INSERT OR REPLACE INTO courses(id, track_id, track_title, title, slug, path, source_url, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (course_id, track_id, track_title, title, course_dir.name, rel_course, source_url, now_iso()),
            )

            stats["courses_seen"] += 1
            set_status(courses_seen=stats["courses_seen"], message=f"Indexing {title}")

            lessons, chunks, skipped_lessons = index_lessons(conn, root, course_dir, course_id, title, seen_lesson_keys)
            questions, skipped_questions = index_questions(conn, root, course_dir, course_id, title, track_id, track_title, course_meta, seen_question_keys)
            docs, skipped_docs = index_documents(conn, root, course_dir, course_id, title, seen_document_keys)

            stats["lessons_indexed"] += lessons
            stats["duplicate_lessons_skipped"] += skipped_lessons
            stats["chunks_indexed"] += chunks
            stats["questions_indexed"] += questions
            stats["duplicate_questions_skipped"] += skipped_questions
            stats["documents_indexed"] += docs
            stats["duplicate_documents_skipped"] += skipped_docs
            set_status(
                lessons_indexed=stats["lessons_indexed"],
                questions_indexed=stats["questions_indexed"],
                documents_indexed=stats["documents_indexed"],
                chunks_indexed=stats["chunks_indexed"],
            )

        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('last_indexed_at', ?)", (now_iso(),))
        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('content_root', ?)", (str(root),))
        seed_lab_exercises(conn)
        refresh_course_counts(conn)
        rebuild_fts_tables(conn)

    return stats


def insert_labs_into_search(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM search_fts WHERE type = 'lab'")
    for lab in LABS:
        body = " ".join(
            [
                lab["domain"],
                lab["level"],
                lab["setup"],
                " ".join(lab["objectives"]),
                " ".join(lab["steps"]),
                " ".join(lab["validation"]),
                lab["sql"],
            ]
        )
        conn.execute(
            "INSERT INTO search_fts(title, body, type, ref_id, course_id, path) VALUES (?, ?, 'lab', ?, '', ?)",
            (lab["title"], body, lab["id"], lab["id"]),
        )


def seed_certification_tracks(conn: sqlite3.Connection) -> None:
    for position, (track_id, title, description) in enumerate(CERTIFICATION_TRACKS, start=1):
        conn.execute(
            """
            INSERT OR REPLACE INTO certification_tracks(id, title, description, position)
            VALUES (?, ?, ?, ?)
            """,
            (track_id, title, description, position),
        )


def select_course_candidates(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    for course_dir in sorted([p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")]):
        course_meta = read_course_meta(course_dir)
        title = course_meta.get("title") or nice_title(course_dir.name)
        if not is_relevant_course(course_dir, title):
            continue
        track_id, track_title = infer_certification_track(title, course_dir.name)
        source_url = clean_text(str(course_meta.get("course_url") or ""))
        rel_course = safe_rel(course_dir, root)
        candidates.append(
            {
                "course_dir": course_dir,
                "course_meta": course_meta,
                "title": title,
                "track_id": track_id,
                "track_title": track_title,
                "source_url": source_url,
                "rel_course": rel_course,
                "dedupe_key": course_identity_key(track_id, title, source_url),
                "score": course_quality_score(course_dir, course_meta, rel_course),
            }
        )

    best_by_key: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        current = best_by_key.get(candidate["dedupe_key"])
        if current is None or candidate["score"] > current["score"]:
            best_by_key[candidate["dedupe_key"]] = candidate

    selected_paths = {candidate["rel_course"] for candidate in best_by_key.values()}
    selected = sorted(best_by_key.values(), key=lambda item: item["rel_course"])
    skipped = sorted(
        [candidate for candidate in candidates if candidate["rel_course"] not in selected_paths],
        key=lambda item: item["rel_course"],
    )
    return selected, skipped


def course_quality_score(course_dir: Path, course_meta: dict[str, Any], rel_course: str) -> tuple[int, int, int, int, int, int]:
    question_count = sum(len(test.get("assessments") or []) for test in course_meta.get("practice_tests") or [])
    video_count = sum(
        1
        for path in course_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS and "_practice-tests" not in path.parts
    )
    transcript_count = sum(1 for path in course_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".vtt", ".srt"})
    document_count = sum(1 for path in course_dir.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_DOC_EXTENSIONS)
    return (question_count + video_count, question_count, video_count, transcript_count, document_count, -len(rel_course))


def course_identity_key(track_id: str, title: str, source_url: str) -> str:
    url = canonical_course_url(source_url)
    if url:
        return f"{track_id}:url:{url}"
    return f"{track_id}:title:{dedupe_text(title)}"


def canonical_course_url(source_url: str) -> str:
    url = clean_text(str(source_url or "")).lower().split("?", 1)[0].rstrip("/")
    return url


def infer_certification_track(title: str, slug: str = "") -> tuple[str, str]:
    text = f"{title} {slug}".lower()
    if "cost optimization" in text or "optimization" in text:
        return "cost-optimization", "Snowflake Cost Optimization"
    if "iceberg" in text:
        return "iceberg", "Apache Iceberg"
    if "snowpark" in text:
        return "snowpark", "SnowPro Snowpark"
    if "cortex" in text or "gen ai" in text or "genai" in text or "llm" in text:
        return "cortex-genai", "Snowflake Cortex and GenAI"
    if "advanced architect" in text or "ara-c01" in text or "architect" in text:
        return "advanced-architect", "SnowPro Advanced Architect"
    if "data engineer" in text or "dea-c" in text:
        return "advanced-data-engineer", "SnowPro Advanced Data Engineer"
    if "associate platform" in text or "sol-c01" in text or "platform" in text:
        return "associate-platform", "SnowPro Associate Platform"
    if "core" in text or "cof-c" in text or "snowpro" in text:
        return "snowpro-core", "SnowPro Core"
    return "general-snowflake", "General Snowflake"


def refresh_course_counts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE courses
        SET
          section_count = (SELECT COUNT(*) FROM course_sections cs WHERE cs.course_id = courses.id),
          lesson_count = (SELECT COUNT(*) FROM lessons l WHERE l.course_id = courses.id),
          question_count = (SELECT COUNT(*) FROM questions q WHERE q.course_id = courses.id)
        """
    )
    conn.execute(
        """
        UPDATE course_sections
        SET lesson_count = (SELECT COUNT(*) FROM lessons l WHERE l.section_id = course_sections.id)
        """
    )


LAB_EXERCISES = [
    ("Create a Basic Warehouse", "Write a CREATE WAREHOUSE statement for TRAINING_WH, X-Small size, auto-suspend after 60 seconds.", "CREATE WAREHOUSE TRAINING_WH ", '{"keywords":["CREATE WAREHOUSE","WAREHOUSE_SIZE","AUTO_SUSPEND"]}', "Warehouse names are case-insensitive.", '["warehouse"]', "easy"),
    ("Alter Warehouse Size", "Resize TRAINING_WH to Small.", "ALTER WAREHOUSE TRAINING_WH ", '{"keywords":["ALTER WAREHOUSE","SET WAREHOUSE_SIZE"]}', None, '["warehouse"]', "easy"),
    ("Suspend and Resume", "Write statements to suspend then resume TRAINING_WH.", "", '{"keywords":["SUSPEND","RESUME"]}', None, '["warehouse"]', "easy"),
    ("Multi-cluster Warehouse", "Create a multi-cluster warehouse with min 2 and max 5 clusters.", "CREATE WAREHOUSE ", '{"keywords":["MIN_CLUSTER_COUNT","MAX_CLUSTER_COUNT"]}', "Requires Enterprise edition.", '["warehouse"]', "medium"),
    ("Create Database and Schema", "Create database TRAINING_DB and schema TRAINING_DB.PUBLIC.", "", '{"keywords":["CREATE DATABASE","CREATE SCHEMA"]}', None, '["architecture"]', "easy"),
    ("Create a Stage", "Create an internal named stage MY_STAGE.", "CREATE STAGE ", '{"keywords":["CREATE STAGE"]}', None, '["snowpipe"]', "easy"),
    ("COPY INTO Table", "Load data from @MY_STAGE into TABLE_NAME using COPY INTO.", "COPY INTO ", '{"keywords":["COPY INTO","FROM @"]}', None, '["snowpipe"]', "medium"),
    ("Create File Format", "Define a CSV file format with header skip=1.", "CREATE FILE FORMAT ", '{"keywords":["CREATE FILE FORMAT","TYPE = CSV","SKIP_HEADER"]}', None, '["snowpipe"]', "easy"),
    ("Create Role and User", "Create role ANALYST and user ALICE. Grant ANALYST to ALICE.", "", '{"keywords":["CREATE ROLE","CREATE USER","GRANT ROLE"]}', None, '["rbac"]', "easy"),
    ("Grant Privileges", "Grant SELECT on all tables in TRAINING_DB.PUBLIC to ANALYST.", "GRANT SELECT ON ALL TABLES IN SCHEMA ", '{"keywords":["GRANT SELECT","ON ALL TABLES"]}', None, '["rbac"]', "medium"),
    ("Object Ownership", "Transfer ownership of MY_TABLE to ADMIN.", "GRANT OWNERSHIP ON TABLE ", '{"keywords":["GRANT OWNERSHIP"]}', None, '["rbac"]', "medium"),
    ("Row Access Policy", "Create a row access policy that restricts rows by current_role().", "CREATE ROW ACCESS POLICY ", '{"keywords":["CREATE ROW ACCESS POLICY","CURRENT_ROLE"]}', None, '["masking policies"]', "hard"),
    ("Query Historical Data AT", "Query MY_TABLE as it was one hour ago using AT OFFSET.", "SELECT * FROM MY_TABLE ", '{"keywords":["AT (OFFSET"]}', None, '["time travel"]', "easy"),
    ("UNDROP Table", "Restore a dropped table named OLD_TABLE.", "UNDROP TABLE ", '{"keywords":["UNDROP TABLE"]}', None, '["time travel"]', "easy"),
    ("Clone with Time Travel", "Clone MY_TABLE as of timestamp 2024-01-01 00:00:00.", "CREATE TABLE MY_TABLE_CLONE CLONE MY_TABLE ", '{"keywords":["CLONE","AT (TIMESTAMP"]}', None, '["time travel"]', "medium"),
    ("Create a Stream", "Create MY_STREAM on table MY_TABLE.", "CREATE STREAM ", '{"keywords":["CREATE STREAM","ON TABLE"]}', None, '["streams tasks"]', "easy"),
    ("Consume a Stream", "Insert from MY_STREAM into TARGET_TABLE.", "INSERT INTO TARGET_TABLE SELECT ", '{"keywords":["FROM MY_STREAM"]}', None, '["streams tasks"]', "medium"),
    ("Create a Task", "Create MY_TASK that runs every 5 minutes.", "CREATE TASK MY_TASK ", '{"keywords":["CREATE TASK","SCHEDULE","MINUTE"]}', None, '["streams tasks"]', "medium"),
    ("Task with Condition", "Create a task that runs only when MY_STREAM has data.", "CREATE TASK ", '{"keywords":["WHEN SYSTEM$STREAM_HAS_DATA"]}', None, '["streams tasks"]', "hard"),
    ("Task Tree DAG", "Create a child task that depends on PARENT_TASK.", "CREATE TASK CHILD_TASK ", '{"keywords":["AFTER PARENT_TASK"]}', None, '["streams tasks"]', "hard"),
    ("Create Dynamic Table", "Create SALES_AGG with target lag and warehouse.", "CREATE DYNAMIC TABLE SALES_AGG ", '{"keywords":["CREATE DYNAMIC TABLE","TARGET_LAG","WAREHOUSE"]}', None, '["dynamic tables"]', "medium"),
    ("Refresh Dynamic Table", "Manually refresh a dynamic table.", "ALTER DYNAMIC TABLE ", '{"keywords":["REFRESH"]}', None, '["dynamic tables"]', "easy"),
    ("Create Snowpipe", "Create a pipe that auto-ingests from @MY_STAGE into MY_TABLE.", "CREATE PIPE MY_PIPE AS ", '{"keywords":["CREATE PIPE","COPY INTO","AUTO_INGEST"]}', None, '["snowpipe"]', "medium"),
    ("Pause and Resume Pipe", "Pause MY_PIPE.", "ALTER PIPE MY_PIPE ", '{"keywords":["SET PIPE_EXECUTION_PAUSED = TRUE"]}', None, '["snowpipe"]', "easy"),
    ("Cluster a Table", "Add clustering on columns C1 and C2 to MY_TABLE.", "ALTER TABLE MY_TABLE CLUSTER BY ", '{"keywords":["CLUSTER BY"]}', None, '["architecture"]', "medium"),
    ("Recluster Table", "Manually trigger reclustering.", "ALTER TABLE MY_TABLE RECLUSTER ", '{"keywords":["RECLUSTER"]}', None, '["architecture"]', "medium"),
    ("Create Masking Policy", "Create SSN_MASK that checks current_role and returns masked text.", "CREATE MASKING POLICY SSN_MASK AS (VAL STRING) ", '{"keywords":["CREATE MASKING POLICY","CURRENT_ROLE","RETURN"]}', None, '["masking policies"]', "hard"),
    ("Apply Masking Policy", "Apply SSN_MASK to SSN in EMPLOYEES.", "ALTER TABLE EMPLOYEES MODIFY COLUMN SSN ", '{"keywords":["SET MASKING POLICY"]}', None, '["masking policies"]', "medium"),
    ("Snowpark Python UDF", "Create a Python UDF that returns the square of a number.", "CREATE FUNCTION SQUARE(N FLOAT) RETURNS FLOAT ", '{"keywords":["CREATE FUNCTION","LANGUAGE PYTHON","RETURNS"]}', None, '["snowpark"]', "hard"),
    ("Call a UDF", "Call SQUARE(5) in a SELECT statement.", "SELECT SQUARE(5);", '{"keywords":["SELECT","SQUARE"]}', None, '["snowpark"]', "easy"),
    ("Cortex SENTIMENT", "Use SNOWFLAKE.CORTEX.SENTIMENT to score text.", "SELECT SNOWFLAKE.CORTEX.SENTIMENT(", '{"keywords":["SNOWFLAKE.CORTEX.SENTIMENT"]}', None, '["cortex"]', "medium"),
    ("Cortex COMPLETE", "Call CORTEX.COMPLETE with llama to summarize text.", "SELECT SNOWFLAKE.CORTEX.COMPLETE(", '{"keywords":["SNOWFLAKE.CORTEX.COMPLETE","LLAMA"]}', None, '["cortex"]', "medium"),
    ("Information Schema", "Query INFORMATION_SCHEMA.TABLES to list tables.", "SELECT * FROM INFORMATION_SCHEMA.TABLES ", '{"keywords":["INFORMATION_SCHEMA.TABLES"]}', None, '["architecture"]', "easy"),
    ("Account Usage", "Find top 5 expensive queries from ACCOUNT_USAGE.QUERY_HISTORY.", "SELECT ", '{"keywords":["ACCOUNT_USAGE.QUERY_HISTORY","ORDER BY","LIMIT 5"]}', None, '["architecture"]', "medium"),
    ("Search Optimization Service", "Enable search optimization on MY_TABLE.", "ALTER TABLE MY_TABLE ADD SEARCH OPTIMIZATION;", '{"keywords":["ADD SEARCH OPTIMIZATION"]}', None, '["architecture"]', "medium"),
    ("Materialized View", "Create materialized view MV_SALES from MY_TABLE.", "CREATE MATERIALIZED VIEW MV_SALES AS ", '{"keywords":["CREATE MATERIALIZED VIEW"]}', None, '["architecture"]', "medium"),
    ("External Table", "Create an external table over files in @MY_STAGE.", "CREATE EXTERNAL TABLE EXT_ORDERS ", '{"keywords":["CREATE EXTERNAL TABLE","LOCATION = @"]}', None, '["architecture"]', "hard"),
    ("Outbound Data Share", "Create a share and grant access to MY_TABLE.", "CREATE SHARE MY_SHARE;", '{"keywords":["CREATE SHARE","GRANT USAGE ON DATABASE","GRANT SELECT ON TABLE"]}', None, '["architecture"]', "hard"),
    ("Resource Monitor", "Create a resource monitor that triggers at 90 percent of 1000 credits.", "CREATE RESOURCE MONITOR RM1 WITH CREDIT_QUOTA = 1000 ", '{"keywords":["RESOURCE MONITOR","TRIGGERS AT 90 PERCENT"]}', None, '["architecture"]', "hard"),
    ("Transaction Control", "Write a transaction that inserts a row and commits.", "BEGIN;", '{"keywords":["BEGIN","COMMIT"]}', None, '["architecture"]', "easy"),
]


def seed_lab_exercises(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS count FROM lab_exercises").fetchone()["count"]
    if existing:
        return
    for position, (title, description, starter_sql, expected, hint, tags, difficulty) in enumerate(LAB_EXERCISES, start=1):
        conn.execute(
            """
            INSERT INTO lab_exercises(
              title, description, starter_sql, solution_sql, expected_output, hint, tags, difficulty, position
            ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?)
            """,
            (title, description, starter_sql, expected, hint, tags, difficulty, position),
        )


def rebuild_fts_tables(conn: sqlite3.Connection) -> None:
    for table in ("question_fts", "lesson_fts", "chunk_fts"):
        try:
            conn.execute(f"INSERT INTO {table}({table}) VALUES('rebuild')")
        except sqlite3.DatabaseError:
            continue


def index_lessons(
    conn: sqlite3.Connection,
    root: Path,
    course_dir: Path,
    course_id: str,
    course_title: str,
    seen_lesson_keys: set[str] | None = None,
) -> tuple[int, int, int]:
    count = 0
    chunk_count = 0
    skipped = 0
    section_positions: dict[str, int] = {}
    videos = [
        video
        for video in sorted(course_dir.rglob("*"))
        if video.is_file() and video.suffix.lower() in VIDEO_EXTENSIONS and "_practice-tests" not in video.parts
    ]
    for course_position, video in enumerate(videos, start=1):
        transcript = find_transcript(video)
        info_file = find_info(video)
        info = read_json(info_file) if info_file else {}
        title = clean_lesson_title(str(info.get("title") or video.stem))
        raw_chunks = parse_vtt_chunks(transcript) if transcript else []
        raw_transcript_text = clean_text(" ".join(chunk["text"] for chunk in raw_chunks)) if raw_chunks else parse_vtt(transcript)
        transcript_text, chunks, transcript_is_english = english_transcript_payload(
            course_title,
            title,
            info,
            raw_chunks,
            raw_transcript_text,
        )
        lesson_key = lesson_identity_key(title, transcript_text)
        if seen_lesson_keys is not None and lesson_key:
            if lesson_key in seen_lesson_keys:
                skipped += 1
                continue
            seen_lesson_keys.add(lesson_key)
        excerpt = make_excerpt(transcript_text, 420)
        sort_key = lesson_sort_key(video.name)
        lesson_id = stable_id(safe_rel(video, root))
        video_rel = safe_rel(video, root)
        transcript_rel = safe_rel(transcript, root) if transcript and transcript_is_english else None
        info_rel = safe_rel(info_file, root) if info_file else None
        duration = coerce_float(info.get("duration"))
        section_path = "." if video.parent == course_dir else video.parent.relative_to(course_dir).as_posix()
        section = clean_lesson_title(video.parent.name) if video.parent != course_dir else "Course"
        if section_path not in section_positions:
            section_positions[section_path] = len(section_positions) + 1
            section_id = stable_id(f"{course_id}:{section_path}")
            conn.execute(
                """
                INSERT OR REPLACE INTO course_sections(id, course_id, title, path, position, lesson_count)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (section_id, course_id, section, section_path, section_positions[section_path]),
            )
        section_id = stable_id(f"{course_id}:{section_path}")

        conn.execute(
            """
            INSERT OR REPLACE INTO lessons(
              id, course_id, section_id, course_title, title, sort_key, video_path, transcript_path,
              info_path, duration, transcript_text, excerpt, section, vtt_path, duration_s, position
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson_id,
                course_id,
                section_id,
                course_title,
                title,
                sort_key,
                video_rel,
                transcript_rel,
                info_rel,
                duration,
                transcript_text,
                excerpt,
                section,
                transcript_rel,
                int(duration) if duration is not None else None,
                course_position,
            ),
        )
        for idx, chunk in enumerate(chunks):
            conn.execute(
                """
                INSERT INTO transcript_chunks(lesson_id, chunk_idx, text, start_s, end_s)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    lesson_id,
                    int(chunk.get("chunk_idx") if chunk.get("chunk_idx") is not None else idx),
                    chunk["text"],
                    chunk.get("start_s"),
                    chunk.get("end_s"),
                ),
            )
            chunk_count += 1
        searchable = transcript_text or build_english_lesson_notes(course_title, title, info)
        conn.execute(
            """
            INSERT INTO search_fts(title, body, type, ref_id, course_id, path)
            VALUES (?, ?, 'lesson', ?, ?, ?)
            """,
            (title, searchable, lesson_id, course_id, video_rel),
        )
        count += 1
    return count, chunk_count, skipped


def index_questions(
    conn: sqlite3.Connection,
    root: Path,
    course_dir: Path,
    course_id: str,
    course_title: str,
    track_id: str,
    track_title: str,
    course_meta: dict[str, Any],
    seen_question_keys: set[str] | None = None,
) -> tuple[int, int]:
    tests = course_meta.get("practice_tests") or []
    practice_file = course_dir / "_practice-tests" / "practice-tests.json"
    raw_titles = [clean_text(str(test.get("title") or "")) for test in tests]
    title_counts = Counter(raw_titles)
    count = 0
    skipped = 0
    for test_position, test in enumerate(tests, start=1):
        raw_test_title = clean_text(str(test.get("title") or ""))
        test_title = practice_test_display_title(raw_test_title, test_position, title_counts[raw_test_title])
        test_id = stable_id(f"{safe_rel(practice_file, root)}:{test.get('id') or test_position}:{raw_test_title}")
        source_path = safe_rel(practice_file, root) if practice_file.exists() else safe_rel(course_dir, root)
        test_count = 0
        for question_position, assessment in enumerate(test.get("assessments") or [], start=1):
            prompt = assessment.get("prompt") or {}
            question = clean_html_text(prompt.get("question") or assessment.get("question_plain") or "")
            if not question:
                continue
            if not is_english_index_text(question):
                continue
            options = [clean_html_text(item) for item in prompt.get("answers") or []]
            options = [item for item in options if item]
            if options and not is_english_index_text(" ".join(options)):
                continue
            correct = normalize_correct(assessment.get("correct_response"), options)
            explanation = clean_html_text(prompt.get("explanation") or "")
            if explanation and not is_english_index_text(explanation):
                explanation = ""
            if not explanation:
                feedbacks = [clean_html_text(item) for item in prompt.get("feedbacks") or []]
                explanation = " ".join(item for item in feedbacks if item and is_english_index_text(item))
            assessment_type = str(assessment.get("assessment_type") or "")
            tags = auto_tag(question, explanation)
            multiple = (
                len(correct) > 1
                or "multiple-select" in assessment_type.lower()
                or "multi-select" in assessment_type.lower()
                or "multiple-response" in assessment_type.lower()
            )
            question_key = question_identity_key(question, options, correct)
            if seen_question_keys is not None:
                if question_key in seen_question_keys:
                    skipped += 1
                    continue
                seen_question_keys.add(question_key)
            question_id = stable_id(f"{safe_rel(practice_file, root)}:{test_id}:{assessment.get('id') or question_position}:{question[:40]}")

            conn.execute(
                """
                INSERT OR REPLACE INTO questions(
                  id, course_id, course_title, test_title, question, options_json, correct_json,
                  explanation, source_path, assessment_type, tags, difficulty, multiple,
                  test_id, test_position, question_position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    course_id,
                    course_title,
                    test_title,
                    question,
                    json.dumps(options),
                    json.dumps(correct),
                    explanation,
                    source_path,
                    assessment_type,
                    json.dumps(tags),
                    infer_difficulty(question, explanation, options),
                    1 if multiple else 0,
                    test_id,
                    test_position,
                    question_position,
                ),
            )
            body = " ".join([question, " ".join(options), explanation])
            conn.execute(
                """
                INSERT INTO search_fts(title, body, type, ref_id, course_id, path)
                VALUES (?, ?, 'question', ?, ?, ?)
                """,
                (test_title, body, question_id, course_id, source_path),
            )
            count += 1
            test_count += 1
        conn.execute(
            """
            INSERT OR REPLACE INTO practice_tests(
              id, course_id, course_title, track_id, track_title, title,
              original_title, position, question_count, source_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_id,
                course_id,
                course_title,
                track_id,
                track_title,
                test_title,
                raw_test_title,
                test_position,
                test_count,
                source_path,
            ),
        )
    return count, skipped


def practice_test_display_title(raw_title: str, position: int, duplicate_count: int) -> str:
    title = clean_text(raw_title)
    lowered = title.lower()
    if not title or lowered in GENERIC_TEST_TITLES:
        return f"Practice Test {position}"
    if duplicate_count > 1:
        return f"Practice Test {position}: {title}"
    return title


def index_documents(
    conn: sqlite3.Connection,
    root: Path,
    course_dir: Path,
    course_id: str,
    course_title: str,
    seen_document_keys: set[str] | None = None,
) -> tuple[int, int]:
    count = 0
    skipped = 0
    for doc in sorted(course_dir.rglob("*")):
        if not doc.is_file() or doc.suffix.lower() not in TEXT_DOC_EXTENSIONS:
            continue
        if doc.name == ".download-archive.txt":
            continue
        if "_practice-tests" in doc.parts and doc.suffix.lower() in {".json", ".html"}:
            continue
        try:
            body = doc.read_text(errors="ignore")
        except OSError:
            continue
        if len(body.strip()) < 40:
            continue
        title = clean_lesson_title(doc.stem)
        body = ensure_english_document_body(body, course_title, title)
        document_key = document_identity_key(title, body)
        if seen_document_keys is not None:
            if document_key in seen_document_keys:
                skipped += 1
                continue
            seen_document_keys.add(document_key)
        doc_id = stable_id(safe_rel(doc, root))
        rel = safe_rel(doc, root)
        excerpt = make_excerpt(clean_text(body), 420)
        conn.execute(
            """
            INSERT OR REPLACE INTO documents(id, course_id, course_title, title, path, body, excerpt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, course_id, course_title, title, rel, body, excerpt),
        )
        conn.execute(
            """
            INSERT INTO search_fts(title, body, type, ref_id, course_id, path)
            VALUES (?, ?, 'document', ?, ?, ?)
            """,
            (title, body, doc_id, course_id, rel),
        )
        count += 1
    return count, skipped


def read_course_meta(course_dir: Path) -> dict[str, Any]:
    practice_file = course_dir / "_practice-tests" / "practice-tests.json"
    data = read_json(practice_file) if practice_file.exists() else {}
    if not data:
        first_info = next(iter(sorted(course_dir.glob("**/000 - *.info.json"))), None)
        data = read_json(first_info) if first_info else {}
    title = clean_text(str(data.get("course_title") or data.get("title") or nice_title(course_dir.name)))
    data["title"] = title
    return data


def is_relevant_course(course_dir: Path, title: str) -> bool:
    haystack = f"{course_dir.name} {title}".lower()
    return any(term in haystack for term in ("snowflake", "snowpro", "snowpark", "iceberg"))


def find_transcript(video: Path) -> Path | None:
    stem = video.stem
    candidates = [
        video.with_name(f"{stem}.en.vtt"),
        video.with_name(f"{stem}.vtt"),
        video.with_name(f"{stem}.en.srt"),
        video.with_name(f"{stem}.srt"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = sorted(video.parent.glob(f"{stem}*.vtt")) + sorted(video.parent.glob(f"{stem}*.srt"))
    return matches[0] if matches else None


def find_info(video: Path) -> Path | None:
    candidate = video.with_name(f"{video.stem}.info.json")
    return candidate if candidate.exists() else None


def parse_vtt(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return ""
    parts: list[str] = []
    previous = ""
    for raw in lines:
        line = raw.strip()
        if not line or line == "WEBVTT" or "-->" in line:
            continue
        if line.isdigit() or line.startswith("NOTE") or line.startswith("STYLE"):
            continue
        line = re.sub(r"<[^>]+>", " ", line)
        line = html.unescape(line)
        line = clean_text(line)
        if not line or line == previous:
            continue
        parts.append(line)
        previous = line
    return clean_text(" ".join(parts))


def parse_vtt_chunks(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return []
    chunks: list[dict[str, Any]] = []
    cue_text: list[str] = []
    start_s: float | None = None
    end_s: float | None = None

    def flush() -> None:
        nonlocal cue_text, start_s, end_s
        text = clean_text(" ".join(cue_text))
        if text:
            chunks.append(
                {
                    "chunk_idx": len(chunks),
                    "text": text,
                    "start_s": start_s,
                    "end_s": end_s,
                }
            )
        cue_text = []
        start_s = None
        end_s = None

    for raw in lines:
        line = raw.strip()
        if not line or line == "WEBVTT":
            flush()
            continue
        if line.isdigit() or line.startswith("NOTE") or line.startswith("STYLE"):
            continue
        if "-->" in line:
            flush()
            left, right = [part.strip() for part in line.split("-->", 1)]
            start_s = vtt_time_to_seconds(left)
            end_s = vtt_time_to_seconds(right.split()[0])
            continue
        line = re.sub(r"<[^>]+>", " ", line)
        cue_text.append(clean_text(html.unescape(line)))
    flush()
    return chunks


def vtt_time_to_seconds(value: str) -> float | None:
    match = re.match(r"(?:(\d+):)?(\d{2}):(\d{2})(?:[.,](\d{1,3}))?", value)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int((match.group(4) or "0").ljust(3, "0")[:3])
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def english_transcript_payload(
    course_title: str,
    lesson_title: str,
    info: dict[str, Any],
    raw_chunks: list[dict[str, Any]],
    raw_text: str,
) -> tuple[str, list[dict[str, Any]], bool]:
    notes = build_english_lesson_notes(course_title, lesson_title, info)
    if not raw_text:
        return notes, [{"chunk_idx": 0, "text": notes, "start_s": None, "end_s": None}], False

    english_chunks = [
        {
            **chunk,
            "text": clean_text(chunk["text"]),
        }
        for chunk in raw_chunks
        if is_english_caption_chunk(chunk.get("text", ""))
    ]
    english_text = clean_text(" ".join(chunk["text"] for chunk in english_chunks))
    retained_ratio = len(english_chunks) / max(1, len(raw_chunks))
    raw_is_english = is_likely_english(raw_text) and not has_non_english_signal(raw_text)

    if english_text and raw_is_english and retained_ratio >= 0.92:
        return english_text, english_chunks, True

    if english_text and is_likely_english(english_text) and retained_ratio >= 0.75:
        # Keep the English-safe captions, but do not expose the raw VTT file.
        return english_text, english_chunks, False

    return notes, [{"chunk_idx": 0, "text": notes, "start_s": None, "end_s": None}], False


def has_non_english_signal(text: str) -> bool:
    if has_non_latin_script(text):
        return True
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", clean_text(text).lower())
    return any(word in NON_ENGLISH_SIGNAL_WORDS for word in words)


def has_non_latin_script(text: str) -> bool:
    return any(
        "\u0370" <= char <= "\u03ff"  # Greek
        or "\u0400" <= char <= "\u04ff"  # Cyrillic
        or "\u0590" <= char <= "\u05ff"  # Hebrew
        or "\u0600" <= char <= "\u06ff"  # Arabic
        or "\u0900" <= char <= "\u097f"  # Devanagari
        or "\u0e00" <= char <= "\u0e7f"  # Thai
        or "\u3040" <= char <= "\u30ff"  # Japanese hiragana/katakana
        or "\u3400" <= char <= "\u9fff"  # CJK ideographs
        or "\uac00" <= char <= "\ud7af"  # Hangul
        for char in text
    )


def is_english_index_text(text: str) -> bool:
    cleaned = clean_text(text)
    if not cleaned:
        return False
    return is_likely_english(cleaned) and not has_non_english_signal(cleaned)


def is_english_caption_chunk(text: str) -> bool:
    cleaned = clean_text(text)
    if not cleaned:
        return False
    if has_non_english_signal(cleaned):
        return False
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", cleaned.lower())
    if not words:
        return False
    accented_letters = sum(1 for char in cleaned if char.isalpha() and ord(char) > 127)
    alpha_letters = sum(1 for char in cleaned if char.isalpha())
    if alpha_letters and accented_letters / alpha_letters > 0.08:
        return False
    if len(words) < 16:
        ascii_letters = sum(1 for char in cleaned if char.isalpha() and ord(char) < 128)
        return ascii_letters / max(1, alpha_letters) >= 0.92
    return is_likely_english(cleaned)


def auto_tag(question_text: str, explanation: str = "") -> list[str]:
    text = f"{question_text} {explanation}".lower()
    rules = [
        ("warehouse", ("warehouse",)),
        ("rbac", ("role", "grant", "privilege")),
        ("snowpipe", ("snowpipe", "copy into")),
        ("streams tasks", ("stream", "task")),
        ("time travel", ("time travel", "undrop", "fail-safe", "failsafe")),
        ("dynamic tables", ("dynamic table",)),
        ("cortex", ("cortex", "llm")),
        ("snowpark", ("snowpark",)),
        ("masking policies", ("masking", "row access")),
    ]
    tags = [tag for tag, keywords in rules if any(keyword in text for keyword in keywords)]
    return tags or ["architecture"]


def infer_difficulty(question: str, explanation: str, options: list[str]) -> str:
    text = f"{question} {explanation}".lower()
    hard_terms = ("row access", "masking", "snowpark", "external table", "resource monitor", "task tree", "cortex")
    easy_terms = ("default", "which", "create role", "create warehouse", "undrop")
    if len(options) > 4 or any(term in text for term in hard_terms):
        return "hard"
    if len(question) < 160 and any(term in text for term in easy_terms):
        return "easy"
    return "medium"


def is_likely_english(text: str) -> bool:
    text = clean_text(text)
    if not text:
        return False
    if has_non_latin_script(text):
        return False
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", text.lower())
    if len(words) < 16:
        return True
    sample = words[:600]
    english_hits = sum(1 for word in sample if word in ENGLISH_SIGNAL_WORDS)
    non_english_hits = sum(1 for word in sample if word in NON_ENGLISH_SIGNAL_WORDS)
    ascii_chars = sum(1 for char in text[:4000] if ord(char) < 128)
    ascii_ratio = ascii_chars / max(1, len(text[:4000]))

    if non_english_hits >= 8 and non_english_hits > english_hits:
        return False
    if ascii_ratio < 0.94 and non_english_hits >= 4:
        return False
    return english_hits >= max(4, non_english_hits)


def build_english_lesson_notes(course_title: str, lesson_title: str, info: dict[str, Any]) -> str:
    description = clean_html_text(info.get("description") or "")
    description_line = f" Source description: {description}" if description and is_english_index_text(description) else ""
    return clean_text(
        f"""
        English study notes. Course: {course_title}. Lesson topic: {lesson_title}.{description_line}
        Certification focus: understand the Snowflake concept, object, command, or design pattern named in this lesson.
        Review checklist: define the topic in plain English; identify where it appears in Snowflake architecture or administration;
        know the common SQL commands or UI actions; compare it with nearby features; and practice with matching quiz questions or labs.
        """
    )


def ensure_english_document_body(body: str, course_title: str, title: str) -> str:
    cleaned = clean_text(body)
    if is_english_index_text(cleaned):
        return body
    return build_english_lesson_notes(course_title, title, {})


def clean_html_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    parser = TextExtractor()
    try:
        parser.feed(text)
        parsed = parser.get_text()
    except Exception:
        parsed = re.sub(r"<[^>]+>", " ", text)
    return clean_text(html.unescape(parsed or text))


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip()
    return value


def dedupe_text(value: str) -> str:
    value = html.unescape(str(value or "")).lower()
    value = re.sub(r"[^a-z0-9_]+", " ", value)
    return clean_text(value)


def question_identity_key(question: str, options: list[str], correct: list[int]) -> str:
    payload = {
        "question": dedupe_text(question),
        "options": [dedupe_text(option) for option in options],
        "correct": sorted(set(int(item) for item in correct)),
    }
    return stable_id(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def lesson_identity_key(title: str, transcript_text: str) -> str:
    normalized_transcript = dedupe_text(transcript_text)
    if len(normalized_transcript) < 160:
        return ""
    return stable_id(f"{dedupe_text(title)}:{normalized_transcript[:3000]}")


def document_identity_key(title: str, body: str) -> str:
    normalized_body = dedupe_text(body)
    return stable_id(f"{dedupe_text(title)}:{normalized_body[:5000]}")


def clean_lesson_title(value: str) -> str:
    value = re.sub(r"^\d+\s*[-_.]\s*", "", value)
    value = value.replace("_", " ").replace("-", " ")
    return clean_text(value).title()


def nice_title(value: str) -> str:
    value = re.sub(r"-[0-9a-f]{8}$", "", value)
    return clean_lesson_title(value)


def lesson_sort_key(filename: str) -> int:
    match = re.match(r"^(\d+)", filename)
    return int(match.group(1)) if match else 999999


def normalize_correct(raw: Any, options: list[str]) -> list[int]:
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else [raw]
    indexes: list[int] = []
    for item in values:
        if isinstance(item, int):
            idx = item
        else:
            token = str(item).strip().lower()
            if re.fullmatch(r"[a-z]", token):
                idx = ord(token) - ord("a")
            elif token.isdigit():
                idx = int(token)
            else:
                idx = next((i for i, option in enumerate(options) if option.lower() == token), -1)
        if 0 <= idx < len(options) and idx not in indexes:
            indexes.append(idx)
    return indexes


def read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        with path.open(errors="ignore") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


def safe_rel(path: Path | None, root: Path) -> str:
    if not path:
        return ""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def make_excerpt(text: str, limit: int = 360) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "..."


def coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def index_is_empty() -> bool:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM courses").fetchone()
    return int(row["count"]) == 0


def fts_query(text: str) -> str:
    tokens = [
        token
        for token in re.findall(r"[A-Za-z0-9_]+", text.lower())
        if token not in QUERY_STOPWORDS and len(token) > 1
    ]
    if not tokens:
        return ""
    return " ".join(f"{token}*" for token in tokens[:10])
