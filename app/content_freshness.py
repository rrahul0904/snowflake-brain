from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any, Callable, Iterable
from urllib.parse import urljoin, urlsplit

import httpx

from .config import DATABASE_BACKEND
from .database import connect
from .observability import log_event, record_background_failure


SCHEMA_VERSION = "20260815_050_content_freshness_v1"
_ALLOWED_ARTIFACT_TYPES = {"question", "lesson", "skill", "reference"}
_ALLOWED_EDITORIAL = {"unverified", "verified", "needs_review", "blocked", "retired"}
DEFAULT_ALLOWED_HOSTS = {"docs.snowflake.com"}
MAX_SOURCE_BYTES = max(100_000, int(os.getenv("CONTENT_FRESHNESS_MAX_SOURCE_BYTES", "5000000")))
HTTP_TIMEOUT_SECONDS = max(2.0, float(os.getenv("CONTENT_FRESHNESS_HTTP_TIMEOUT_SECONDS", "15")))
USER_AGENT = os.getenv(
    "CONTENT_FRESHNESS_USER_AGENT",
    "SnowflakeCertificationGuideFreshness/1.0 (+content-provenance)",
).strip()


class ContentFreshnessError(ValueError):
    pass


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    body: str
    etag: str = ""
    last_modified: str = ""
    final_url: str = ""
    elapsed_ms: int = 0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    current = value or _utc_now()
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _allowed_hosts() -> set[str]:
    configured = {
        item.strip().lower().rstrip(".")
        for item in os.getenv("CONTENT_FRESHNESS_ALLOWED_HOSTS", "docs.snowflake.com").split(",")
        if item.strip()
    }
    return configured or set(DEFAULT_ALLOWED_HOSTS)


def _validate_source_url(url: str) -> tuple[str, str]:
    value = str(url or "").strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ContentFreshnessError("Official content sources must use an HTTPS URL.")
    host = parsed.hostname.lower().rstrip(".")
    allowed = _allowed_hosts()
    if not any(host == item or host.endswith(f".{item}") for item in allowed):
        raise ContentFreshnessError(f"Source host is not in CONTENT_FRESHNESS_ALLOWED_HOSTS: {host}")
    if parsed.username or parsed.password:
        raise ContentFreshnessError("Source URLs cannot contain embedded credentials.")
    if parsed.port not in (None, 443):
        raise ContentFreshnessError("Source URLs must use the default HTTPS port.")
    return value, host


class _VisibleTextParser(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "nav", "header", "footer"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = re.sub(r"\s+", " ", data).strip()
        if cleaned:
            self.parts.append(cleaned)


def normalize_html(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(str(html or ""))
    parser.close()
    return "\n".join(parser.parts)


def fingerprint_html(html: str) -> tuple[str, int]:
    normalized = normalize_html(html)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest(), len(normalized)


def ensure_content_freshness_schema() -> None:
    with connect() as conn:
        existing = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version=?",
            (SCHEMA_VERSION,),
        ).fetchone()
        if existing:
            return
        if DATABASE_BACKEND == "postgresql":
            raise RuntimeError("PostgreSQL content freshness migration was not applied")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS content_sources (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_key TEXT NOT NULL UNIQUE,
              source_url TEXT NOT NULL,
              source_title TEXT NOT NULL DEFAULT '',
              source_section TEXT NOT NULL DEFAULT '',
              authority_host TEXT NOT NULL,
              document_version TEXT NOT NULL DEFAULT '',
              document_date TEXT NOT NULL DEFAULT '',
              current_fingerprint TEXT NOT NULL DEFAULT '',
              previous_fingerprint TEXT NOT NULL DEFAULT '',
              etag TEXT NOT NULL DEFAULT '',
              last_modified TEXT NOT NULL DEFAULT '',
              last_checked_at TEXT,
              last_changed_at TEXT,
              last_verified_at TEXT,
              verified_by TEXT NOT NULL DEFAULT '',
              confidence INTEGER NOT NULL DEFAULT 0 CHECK(confidence BETWEEN 0 AND 100),
              editorial_status TEXT NOT NULL DEFAULT 'unverified'
                CHECK(editorial_status IN ('unverified','verified','needs_review','blocked','retired')),
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS content_source_snapshots (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_id INTEGER NOT NULL REFERENCES content_sources(id) ON DELETE CASCADE,
              fingerprint TEXT NOT NULL,
              retrieved_at TEXT NOT NULL DEFAULT (datetime('now')),
              http_status INTEGER NOT NULL DEFAULT 200,
              etag TEXT NOT NULL DEFAULT '',
              last_modified TEXT NOT NULL DEFAULT '',
              normalized_length INTEGER NOT NULL DEFAULT 0,
              change_summary TEXT NOT NULL DEFAULT '',
              UNIQUE(source_id,fingerprint)
            );
            CREATE TABLE IF NOT EXISTS content_source_links (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_id INTEGER NOT NULL REFERENCES content_sources(id) ON DELETE CASCADE,
              artifact_type TEXT NOT NULL CHECK(artifact_type IN ('question','lesson','skill','reference')),
              artifact_key TEXT NOT NULL,
              track_id TEXT NOT NULL DEFAULT 'snowpro-core',
              source_section TEXT NOT NULL DEFAULT '',
              assertion_kind TEXT NOT NULL DEFAULT 'supports',
              editorial_status TEXT NOT NULL DEFAULT 'unverified'
                CHECK(editorial_status IN ('unverified','verified','needs_review','blocked','retired')),
              confidence INTEGER NOT NULL DEFAULT 0 CHECK(confidence BETWEEN 0 AND 100),
              last_verified_at TEXT,
              verified_by TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now')),
              UNIQUE(source_id,artifact_type,artifact_key)
            );
            CREATE TABLE IF NOT EXISTS content_review_queue (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_id INTEGER NOT NULL REFERENCES content_sources(id) ON DELETE CASCADE,
              artifact_type TEXT NOT NULL DEFAULT 'source',
              artifact_key TEXT NOT NULL DEFAULT '',
              track_id TEXT NOT NULL DEFAULT 'snowpro-core',
              reason TEXT NOT NULL,
              old_fingerprint TEXT NOT NULL DEFAULT '',
              new_fingerprint TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL DEFAULT 'open'
                CHECK(status IN ('open','acknowledged','resolved','ignored')),
              detected_at TEXT NOT NULL DEFAULT (datetime('now')),
              resolved_at TEXT,
              resolved_by TEXT NOT NULL DEFAULT '',
              resolution_notes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS content_source_checks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_id INTEGER NOT NULL REFERENCES content_sources(id) ON DELETE CASCADE,
              checked_at TEXT NOT NULL DEFAULT (datetime('now')),
              result TEXT NOT NULL CHECK(result IN ('unchanged','changed','initialized','not_modified','error')),
              http_status INTEGER,
              fingerprint TEXT NOT NULL DEFAULT '',
              elapsed_ms INTEGER NOT NULL DEFAULT 0,
              error_type TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS content_freshness_policies (
              track_id TEXT PRIMARY KEY,
              enforcement_enabled INTEGER NOT NULL DEFAULT 0 CHECK(enforcement_enabled IN (0,1)),
              require_all_questions INTEGER NOT NULL DEFAULT 1 CHECK(require_all_questions IN (0,1)),
              max_verification_age_days INTEGER NOT NULL DEFAULT 120 CHECK(max_verification_age_days BETWEEN 1 AND 3650),
              updated_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_by TEXT NOT NULL DEFAULT 'system'
            );
            CREATE INDEX IF NOT EXISTS idx_content_sources_status
              ON content_sources(editorial_status,last_checked_at);
            CREATE INDEX IF NOT EXISTS idx_content_links_artifact
              ON content_source_links(track_id,artifact_type,artifact_key,editorial_status);
            CREATE INDEX IF NOT EXISTS idx_content_review_open
              ON content_review_queue(track_id,status,detected_at);
            CREATE INDEX IF NOT EXISTS idx_content_checks_source
              ON content_source_checks(source_id,checked_at DESC);

            DROP TRIGGER IF EXISTS trg_content_freshness_release_gate;
            CREATE TRIGGER trg_content_freshness_release_gate
            BEFORE UPDATE OF status ON question_bank_releases
            WHEN NEW.status='active'
             AND OLD.status<>'active'
             AND EXISTS(
               SELECT 1 FROM content_freshness_policies p
                WHERE p.track_id=NEW.track_id AND p.enforcement_enabled=1
             )
            BEGIN
              SELECT CASE WHEN EXISTS(
                SELECT 1
                  FROM question_bank_release_questions rqi
                  JOIN content_freshness_policies p ON p.track_id=NEW.track_id
                 WHERE rqi.release_id=NEW.id
                   AND p.enforcement_enabled=1
                   AND (
                     (p.require_all_questions=1 AND NOT EXISTS(
                       SELECT 1
                         FROM content_source_links l
                         JOIN content_sources s ON s.id=l.source_id
                        WHERE l.track_id=NEW.track_id
                          AND l.artifact_type='question'
                          AND l.artifact_key=rqi.question_id
                          AND l.editorial_status='verified'
                          AND s.editorial_status='verified'
                          AND l.last_verified_at IS NOT NULL
                          AND s.last_verified_at IS NOT NULL
                          AND datetime(l.last_verified_at)>=datetime('now','-' || p.max_verification_age_days || ' days')
                          AND datetime(s.last_verified_at)>=datetime('now','-' || p.max_verification_age_days || ' days')
                     ))
                     OR EXISTS(
                       SELECT 1
                         FROM content_source_links l
                         JOIN content_sources s ON s.id=l.source_id
                        WHERE l.track_id=NEW.track_id
                          AND l.artifact_type='question'
                          AND l.artifact_key=rqi.question_id
                          AND (
                            l.editorial_status<>'verified'
                            OR s.editorial_status<>'verified'
                            OR l.last_verified_at IS NULL
                            OR s.last_verified_at IS NULL
                            OR datetime(l.last_verified_at)<datetime('now','-' || p.max_verification_age_days || ' days')
                            OR datetime(s.last_verified_at)<datetime('now','-' || p.max_verification_age_days || ' days')
                          )
                     )
                   )
              ) THEN RAISE(ABORT,'content freshness gate blocked release activation') END;
            END;
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
            (SCHEMA_VERSION, "SQLite official source provenance and content freshness"),
        )


def register_source(
    source_key: str,
    source_url: str,
    *,
    source_title: str = "",
    source_section: str = "",
    document_version: str = "",
    document_date: str = "",
) -> dict[str, Any]:
    ensure_content_freshness_schema()
    key = str(source_key or "").strip()
    if not key or len(key) > 180:
        raise ContentFreshnessError("source_key is required and must be 180 characters or fewer")
    url, host = _validate_source_url(source_url)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO content_sources(
              source_key,source_url,source_title,source_section,authority_host,document_version,document_date
            ) VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(source_key) DO UPDATE SET
              source_url=excluded.source_url,
              source_title=excluded.source_title,
              source_section=excluded.source_section,
              authority_host=excluded.authority_host,
              document_version=excluded.document_version,
              document_date=excluded.document_date,
              updated_at=datetime('now')
            """,
            (key, url, source_title.strip(), source_section.strip(), host, document_version.strip(), document_date.strip()),
        )
    return get_source(key)


def get_source(source_key: str) -> dict[str, Any]:
    ensure_content_freshness_schema()
    with connect() as conn:
        row = conn.execute("SELECT * FROM content_sources WHERE source_key=?", (source_key,)).fetchone()
    if not row:
        raise ContentFreshnessError(f"Unknown source: {source_key}")
    return dict(row)


def link_artifact(
    source_key: str,
    artifact_type: str,
    artifact_key: str,
    *,
    track_id: str = "snowpro-core",
    source_section: str = "",
    assertion_kind: str = "supports",
) -> dict[str, Any]:
    ensure_content_freshness_schema()
    kind = str(artifact_type or "").strip().lower()
    if kind not in _ALLOWED_ARTIFACT_TYPES:
        raise ContentFreshnessError(f"Unsupported artifact_type: {artifact_type}")
    key = str(artifact_key or "").strip()
    if not key:
        raise ContentFreshnessError("artifact_key is required")
    source = get_source(source_key)
    if kind == "question":
        with connect() as conn:
            if not conn.execute("SELECT 1 FROM questions WHERE id=? AND track_id=?", (key, track_id)).fetchone():
                raise ContentFreshnessError(f"Question does not exist in track {track_id}: {key}")
    inherited_status = "verified" if source["editorial_status"] == "verified" else "unverified"
    inherited_at = source.get("last_verified_at") if inherited_status == "verified" else None
    inherited_by = source.get("verified_by") if inherited_status == "verified" else ""
    inherited_confidence = int(source.get("confidence") or 0) if inherited_status == "verified" else 0
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO content_source_links(
              source_id,artifact_type,artifact_key,track_id,source_section,assertion_kind,
              editorial_status,confidence,last_verified_at,verified_by
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source_id,artifact_type,artifact_key) DO UPDATE SET
              track_id=excluded.track_id,
              source_section=excluded.source_section,
              assertion_kind=excluded.assertion_kind,
              updated_at=datetime('now')
            """,
            (
                int(source["id"]), kind, key, track_id, source_section.strip(), assertion_kind.strip() or "supports",
                inherited_status, inherited_confidence, inherited_at, inherited_by,
            ),
        )
        row = conn.execute(
            "SELECT * FROM content_source_links WHERE source_id=? AND artifact_type=? AND artifact_key=?",
            (int(source["id"]), kind, key),
        ).fetchone()
    return dict(row)


def _enqueue_review(
    conn: Any,
    source_id: int,
    *,
    artifact_type: str,
    artifact_key: str,
    track_id: str,
    reason: str,
    old_fingerprint: str,
    new_fingerprint: str,
) -> None:
    duplicate = conn.execute(
        """
        SELECT 1 FROM content_review_queue
        WHERE source_id=? AND artifact_type=? AND artifact_key=? AND reason=?
          AND new_fingerprint=? AND status IN ('open','acknowledged')
        """,
        (source_id, artifact_type, artifact_key, reason, new_fingerprint),
    ).fetchone()
    if duplicate:
        return
    conn.execute(
        """
        INSERT INTO content_review_queue(
          source_id,artifact_type,artifact_key,track_id,reason,old_fingerprint,new_fingerprint
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (source_id, artifact_type, artifact_key, track_id, reason, old_fingerprint, new_fingerprint),
    )


def record_source_content(
    source_key: str,
    html: str,
    *,
    http_status: int = 200,
    etag: str = "",
    last_modified: str = "",
    elapsed_ms: int = 0,
) -> dict[str, Any]:
    ensure_content_freshness_schema()
    source = get_source(source_key)
    fingerprint, normalized_length = fingerprint_html(html)
    old = str(source.get("current_fingerprint") or "")
    initialized = not old
    changed = bool(old and old != fingerprint)
    result = "initialized" if initialized else "changed" if changed else "unchanged"
    change_summary = ""
    if changed:
        change_summary = f"Normalized official-source fingerprint changed; new normalized length={normalized_length}."
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT OR IGNORE INTO content_source_snapshots(
              source_id,fingerprint,http_status,etag,last_modified,normalized_length,change_summary
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (int(source["id"]), fingerprint, int(http_status), etag, last_modified, normalized_length, change_summary),
        )
        if initialized:
            conn.execute(
                """
                UPDATE content_sources
                   SET current_fingerprint=?,etag=?,last_modified=?,last_checked_at=datetime('now'),updated_at=datetime('now')
                 WHERE id=?
                """,
                (fingerprint, etag, last_modified, int(source["id"])),
            )
            _enqueue_review(
                conn,
                int(source["id"]),
                artifact_type="source",
                artifact_key=source_key,
                track_id="snowpro-core",
                reason="initial_verification_required",
                old_fingerprint="",
                new_fingerprint=fingerprint,
            )
        elif changed:
            conn.execute(
                """
                UPDATE content_sources
                   SET previous_fingerprint=current_fingerprint,current_fingerprint=?,etag=?,last_modified=?,
                       last_checked_at=datetime('now'),last_changed_at=datetime('now'),editorial_status='needs_review',
                       confidence=0,updated_at=datetime('now')
                 WHERE id=?
                """,
                (fingerprint, etag, last_modified, int(source["id"])),
            )
            conn.execute(
                """
                UPDATE content_source_links
                   SET editorial_status='needs_review',confidence=0,updated_at=datetime('now')
                 WHERE source_id=? AND editorial_status<>'retired'
                """,
                (int(source["id"]),),
            )
            _enqueue_review(
                conn,
                int(source["id"]),
                artifact_type="source",
                artifact_key=source_key,
                track_id="snowpro-core",
                reason="official_source_changed",
                old_fingerprint=old,
                new_fingerprint=fingerprint,
            )
            links = conn.execute(
                "SELECT artifact_type,artifact_key,track_id FROM content_source_links WHERE source_id=? AND editorial_status='needs_review'",
                (int(source["id"]),),
            ).fetchall()
            for link in links:
                _enqueue_review(
                    conn,
                    int(source["id"]),
                    artifact_type=str(link["artifact_type"]),
                    artifact_key=str(link["artifact_key"]),
                    track_id=str(link["track_id"]),
                    reason="linked_official_source_changed",
                    old_fingerprint=old,
                    new_fingerprint=fingerprint,
                )
        else:
            conn.execute(
                "UPDATE content_sources SET etag=?,last_modified=?,last_checked_at=datetime('now'),updated_at=datetime('now') WHERE id=?",
                (etag, last_modified, int(source["id"])),
            )
        conn.execute(
            """
            INSERT INTO content_source_checks(source_id,result,http_status,fingerprint,elapsed_ms)
            VALUES (?,?,?,?,?)
            """,
            (int(source["id"]), result, int(http_status), fingerprint, int(elapsed_ms)),
        )
    if changed:
        log_event("official_content_source_changed", source_key=source_key)
    return {"source_key": source_key, "result": result, "fingerprint": fingerprint, "normalized_length": normalized_length}


def _record_not_modified(source: dict[str, Any], *, elapsed_ms: int) -> dict[str, Any]:
    with connect() as conn:
        conn.execute("UPDATE content_sources SET last_checked_at=datetime('now'),updated_at=datetime('now') WHERE id=?", (int(source["id"]),))
        conn.execute(
            "INSERT INTO content_source_checks(source_id,result,http_status,fingerprint,elapsed_ms) VALUES (?,'not_modified',304,?,?)",
            (int(source["id"]), str(source.get("current_fingerprint") or ""), int(elapsed_ms)),
        )
    return {"source_key": source["source_key"], "result": "not_modified", "fingerprint": source.get("current_fingerprint") or ""}


def _default_fetcher(source: dict[str, Any]) -> FetchResult:
    url, _ = _validate_source_url(str(source["source_url"]))
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1"}
    if source.get("etag"):
        headers["If-None-Match"] = str(source["etag"])
    if source.get("last_modified"):
        headers["If-Modified-Since"] = str(source["last_modified"])
    started = time.perf_counter()
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=False, headers=headers) as client:
        current = url
        response: httpx.Response | None = None
        for _ in range(4):
            response = client.get(current)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location", "")
                if not location:
                    break
                current = urljoin(current, location)
                _validate_source_url(current)
                continue
            break
    assert response is not None
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if response.status_code == 304:
        return FetchResult(304, "", response.headers.get("etag", ""), response.headers.get("last-modified", ""), current, elapsed_ms)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type and "text/" not in content_type:
        raise ContentFreshnessError(f"Unsupported official source content type: {content_type or 'unknown'}")
    body_bytes = response.content
    if len(body_bytes) > MAX_SOURCE_BYTES:
        raise ContentFreshnessError(f"Official source exceeds configured size limit ({MAX_SOURCE_BYTES} bytes)")
    return FetchResult(
        response.status_code,
        response.text,
        response.headers.get("etag", ""),
        response.headers.get("last-modified", ""),
        current,
        elapsed_ms,
    )


def check_source(source_key: str, *, fetcher: Callable[[dict[str, Any]], FetchResult] | None = None) -> dict[str, Any]:
    ensure_content_freshness_schema()
    source = get_source(source_key)
    fetch = fetcher or _default_fetcher
    try:
        result = fetch(source)
        if result.status_code == 304:
            return _record_not_modified(source, elapsed_ms=result.elapsed_ms)
        return record_source_content(
            source_key,
            result.body,
            http_status=result.status_code,
            etag=result.etag,
            last_modified=result.last_modified,
            elapsed_ms=result.elapsed_ms,
        )
    except Exception as exc:
        with connect() as conn:
            conn.execute(
                "INSERT INTO content_source_checks(source_id,result,elapsed_ms,error_type) VALUES (?,'error',0,?)",
                (int(source["id"]), type(exc).__name__),
            )
            conn.execute("UPDATE content_sources SET last_checked_at=datetime('now'),updated_at=datetime('now') WHERE id=?", (int(source["id"]),))
        record_background_failure("content_freshness_check", exc)
        raise


def check_all_sources(*, fetcher: Callable[[dict[str, Any]], FetchResult] | None = None) -> dict[str, Any]:
    ensure_content_freshness_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT source_key FROM content_sources WHERE editorial_status<>'retired' ORDER BY source_key"
        ).fetchall()
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for row in rows:
        key = str(row["source_key"])
        try:
            results.append(check_source(key, fetcher=fetcher))
        except Exception as exc:
            failures.append({"source_key": key, "error_type": type(exc).__name__})
    return {
        "checked": len(rows),
        "changed": sum(1 for item in results if item.get("result") == "changed"),
        "failed": len(failures),
        "results": results,
        "failures": failures,
    }


def verify_source(
    source_key: str,
    reviewer: str,
    *,
    confidence: int = 100,
    document_version: str = "",
    document_date: str = "",
    notes: str = "",
) -> dict[str, Any]:
    ensure_content_freshness_schema()
    source = get_source(source_key)
    if not source.get("current_fingerprint"):
        raise ContentFreshnessError("Retrieve/fingerprint the official source before editorial verification.")
    reviewer = str(reviewer or "").strip()
    if not reviewer:
        raise ContentFreshnessError("reviewer is required")
    if not 0 <= int(confidence) <= 100:
        raise ContentFreshnessError("confidence must be between 0 and 100")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE content_sources
               SET editorial_status='verified',confidence=?,last_verified_at=datetime('now'),verified_by=?,
                   document_version=CASE WHEN ?<>'' THEN ? ELSE document_version END,
                   document_date=CASE WHEN ?<>'' THEN ? ELSE document_date END,
                   updated_at=datetime('now')
             WHERE id=?
            """,
            (int(confidence), reviewer, document_version, document_version, document_date, document_date, int(source["id"])),
        )
        conn.execute(
            """
            UPDATE content_review_queue
               SET status='resolved',resolved_at=datetime('now'),resolved_by=?,resolution_notes=?
             WHERE source_id=? AND artifact_type='source' AND status IN ('open','acknowledged')
            """,
            (reviewer, notes[:1000], int(source["id"])),
        )
    return get_source(source_key)


def verify_artifact_link(
    source_key: str,
    artifact_type: str,
    artifact_key: str,
    reviewer: str,
    *,
    confidence: int = 100,
    notes: str = "",
) -> dict[str, Any]:
    ensure_content_freshness_schema()
    source = get_source(source_key)
    if source["editorial_status"] != "verified":
        raise ContentFreshnessError("Verify the official source itself before verifying linked certification content.")
    kind = str(artifact_type or "").lower().strip()
    reviewer = str(reviewer or "").strip()
    if kind not in _ALLOWED_ARTIFACT_TYPES or not reviewer:
        raise ContentFreshnessError("A supported artifact_type and reviewer are required.")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id FROM content_source_links WHERE source_id=? AND artifact_type=? AND artifact_key=?",
            (int(source["id"]), kind, artifact_key),
        ).fetchone()
        if not row:
            raise ContentFreshnessError("Source link does not exist.")
        conn.execute(
            """
            UPDATE content_source_links
               SET editorial_status='verified',confidence=?,last_verified_at=datetime('now'),verified_by=?,updated_at=datetime('now')
             WHERE id=?
            """,
            (int(confidence), reviewer, int(row["id"])),
        )
        conn.execute(
            """
            UPDATE content_review_queue
               SET status='resolved',resolved_at=datetime('now'),resolved_by=?,resolution_notes=?
             WHERE source_id=? AND artifact_type=? AND artifact_key=? AND status IN ('open','acknowledged')
            """,
            (reviewer, notes[:1000], int(source["id"]), kind, artifact_key),
        )
        updated = conn.execute("SELECT * FROM content_source_links WHERE id=?", (int(row["id"]),)).fetchone()
    return dict(updated)


def review_queue(track_id: str = "snowpro-core", *, status: str = "open") -> list[dict[str, Any]]:
    ensure_content_freshness_schema()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT q.*,s.source_key,s.source_url,s.source_title,s.source_section
              FROM content_review_queue q
              JOIN content_sources s ON s.id=q.source_id
             WHERE q.track_id=? AND q.status=?
             ORDER BY q.detected_at,q.id
            """,
            (track_id, status),
        ).fetchall()
    return [dict(row) for row in rows]


def _active_release_key(conn: Any, track_id: str) -> str | None:
    row = conn.execute(
        "SELECT release_key FROM question_bank_releases WHERE track_id=? AND status='active' ORDER BY activated_at DESC,id DESC LIMIT 1",
        (track_id,),
    ).fetchone()
    return str(row["release_key"]) if row else None


def release_freshness_report(
    release_key: str,
    *,
    require_all_questions: bool = True,
    max_verification_age_days: int = 120,
) -> dict[str, Any]:
    ensure_content_freshness_schema()
    cutoff = _iso(_utc_now() - timedelta(days=max(1, int(max_verification_age_days))))
    with connect() as conn:
        release = conn.execute(
            "SELECT id,release_key,track_id,status FROM question_bank_releases WHERE release_key=?",
            (release_key,),
        ).fetchone()
        if not release:
            raise ContentFreshnessError(f"Unknown release: {release_key}")
        question_rows = conn.execute(
            "SELECT question_id FROM question_bank_release_questions WHERE release_id=? ORDER BY question_id",
            (int(release["id"]),),
        ).fetchall()
        violations: list[dict[str, str]] = []
        verified_count = 0
        for qrow in question_rows:
            question_id = str(qrow["question_id"])
            links = conn.execute(
                """
                SELECT l.editorial_status AS link_status,l.last_verified_at AS link_verified_at,
                       s.editorial_status AS source_status,s.last_verified_at AS source_verified_at,s.source_key
                  FROM content_source_links l
                  JOIN content_sources s ON s.id=l.source_id
                 WHERE l.track_id=? AND l.artifact_type='question' AND l.artifact_key=?
                """,
                (str(release["track_id"]), question_id),
            ).fetchall()
            eligible = [
                link for link in links
                if str(link["link_status"]) == "verified"
                and str(link["source_status"]) == "verified"
                and link["link_verified_at"]
                and link["source_verified_at"]
                and str(link["link_verified_at"]) >= cutoff
                and str(link["source_verified_at"]) >= cutoff
            ]
            if eligible:
                verified_count += 1
                continue
            if require_all_questions or links:
                reason = "missing_provenance" if not links else "stale_or_needs_review"
                violations.append({"question_id": question_id, "reason": reason})
    return {
        "release_key": release_key,
        "track_id": str(release["track_id"]),
        "release_status": str(release["status"]),
        "question_count": len(question_rows),
        "verified_question_count": verified_count,
        "coverage_pct": round((verified_count / len(question_rows) * 100.0) if question_rows else 100.0, 2),
        "gate_pass": not violations,
        "violations": violations,
        "max_verification_age_days": int(max_verification_age_days),
        "require_all_questions": bool(require_all_questions),
    }


def set_freshness_policy(
    track_id: str,
    *,
    enforcement_enabled: bool,
    require_all_questions: bool = True,
    max_verification_age_days: int = 120,
    actor: str = "admin",
    release_key: str | None = None,
) -> dict[str, Any]:
    ensure_content_freshness_schema()
    if enforcement_enabled:
        with connect() as conn:
            target = release_key or _active_release_key(conn, track_id)
        if not target:
            raise ContentFreshnessError("Cannot enable enforcement without an active or explicitly supplied release.")
        report = release_freshness_report(
            target,
            require_all_questions=require_all_questions,
            max_verification_age_days=max_verification_age_days,
        )
        if not report["gate_pass"]:
            raise ContentFreshnessError(
                f"Cannot enable freshness enforcement: {len(report['violations'])} release question(s) are not currently verified."
            )
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO content_freshness_policies(
              track_id,enforcement_enabled,require_all_questions,max_verification_age_days,updated_by
            ) VALUES (?,?,?,?,?)
            ON CONFLICT(track_id) DO UPDATE SET
              enforcement_enabled=excluded.enforcement_enabled,
              require_all_questions=excluded.require_all_questions,
              max_verification_age_days=excluded.max_verification_age_days,
              updated_at=datetime('now'),updated_by=excluded.updated_by
            """,
            (track_id, int(bool(enforcement_enabled)), int(bool(require_all_questions)), int(max_verification_age_days), actor),
        )
        row = conn.execute("SELECT * FROM content_freshness_policies WHERE track_id=?", (track_id,)).fetchone()
    return dict(row)


def provenance_status(track_id: str = "snowpro-core") -> dict[str, Any]:
    ensure_content_freshness_schema()
    with connect() as conn:
        source_counts = {
            str(row["editorial_status"]): int(row["n"])
            for row in conn.execute("SELECT editorial_status,COUNT(*) AS n FROM content_sources GROUP BY editorial_status").fetchall()
        }
        link_counts = {
            str(row["editorial_status"]): int(row["n"])
            for row in conn.execute(
                "SELECT editorial_status,COUNT(*) AS n FROM content_source_links WHERE track_id=? GROUP BY editorial_status",
                (track_id,),
            ).fetchall()
        }
        open_reviews = int(
            conn.execute("SELECT COUNT(*) AS n FROM content_review_queue WHERE track_id=? AND status IN ('open','acknowledged')", (track_id,)).fetchone()["n"]
        )
        active_release = _active_release_key(conn, track_id)
        policy = conn.execute("SELECT * FROM content_freshness_policies WHERE track_id=?", (track_id,)).fetchone()
    release_report = None
    if active_release:
        release_report = release_freshness_report(
            active_release,
            require_all_questions=bool(policy["require_all_questions"]) if policy else True,
            max_verification_age_days=int(policy["max_verification_age_days"]) if policy else 120,
        )
    return {
        "track_id": track_id,
        "sources": source_counts,
        "links": link_counts,
        "open_reviews": open_reviews,
        "policy": dict(policy) if policy else None,
        "active_release": release_report,
    }
