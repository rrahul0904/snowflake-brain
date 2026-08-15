from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, Iterable

from .database import connect
from .question_versions import ensure_question_version_schema


SCHEMA_VERSION = "20260815_020_question_bank_releases_v1"
RELEASE_STATUSES = {"draft", "qa_passed", "sme_approved", "staging", "active", "retired"}
PROMOTION_PATH = {
    "draft": "qa_passed",
    "qa_passed": "sme_approved",
    "sme_approved": "staging",
}
_SCHEMA_LOCK = threading.RLock()
_READY_DATABASES: set[str] = set()


def _database_key(conn) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    if not row:
        return "unknown"
    try:
        return str(row["file"] or row[2] or "memory")
    except (KeyError, TypeError, IndexError):
        return str(row[2] or "memory")


def ensure_question_bank_release_schema() -> None:
    ensure_question_version_schema()
    with _SCHEMA_LOCK:
        with connect() as conn:
            database_key = _database_key(conn)
            if database_key in _READY_DATABASES:
                return
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS question_bank_releases (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  release_key TEXT NOT NULL UNIQUE,
                  track_id TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'draft'
                    CHECK(status IN ('draft','qa_passed','sme_approved','staging','active','retired')),
                  question_count INTEGER NOT NULL DEFAULT 0,
                  source_fingerprint TEXT NOT NULL,
                  notes TEXT NOT NULL DEFAULT '',
                  created_by TEXT NOT NULL DEFAULT 'system',
                  approved_by TEXT,
                  created_at TEXT NOT NULL DEFAULT (datetime('now')),
                  qa_passed_at TEXT,
                  approved_at TEXT,
                  staged_at TEXT,
                  activated_at TEXT,
                  retired_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_question_bank_releases_track_status
                  ON question_bank_releases(track_id,status,created_at DESC);

                CREATE UNIQUE INDEX IF NOT EXISTS uq_question_bank_active_release_per_track
                  ON question_bank_releases(track_id)
                  WHERE status='active';

                CREATE TABLE IF NOT EXISTS question_bank_release_questions (
                  release_id INTEGER NOT NULL REFERENCES question_bank_releases(id) ON DELETE CASCADE,
                  question_id TEXT NOT NULL REFERENCES questions(id),
                  question_version_id INTEGER NOT NULL REFERENCES question_versions(id),
                  PRIMARY KEY(release_id,question_id)
                );

                CREATE INDEX IF NOT EXISTS idx_question_bank_release_questions_version
                  ON question_bank_release_questions(question_version_id);

                CREATE TABLE IF NOT EXISTS question_bank_release_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  release_id INTEGER NOT NULL REFERENCES question_bank_releases(id) ON DELETE CASCADE,
                  action TEXT NOT NULL,
                  actor TEXT NOT NULL DEFAULT 'system',
                  metadata_json TEXT NOT NULL DEFAULT '{}',
                  created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                """
            )
            migrated = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version=? LIMIT 1",
                (SCHEMA_VERSION,),
            ).fetchone()
            if not migrated:
                conn.execute(
                    "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
                    (SCHEMA_VERSION, "Versioned question-bank release, activation, rollback and audit workflow"),
                )
            _READY_DATABASES.add(database_key)


def _event(conn, release_id: int, action: str, actor: str, metadata: dict[str, Any] | None = None) -> None:
    conn.execute(
        "INSERT INTO question_bank_release_events(release_id,action,actor,metadata_json) VALUES (?,?,?,?)",
        (release_id, action, actor or "system", json.dumps(metadata or {}, separators=(",", ":"), sort_keys=True)),
    )


def _snapshot_rows(conn, track_id: str, question_ids: Iterable[str] | None = None) -> list[dict[str, Any]]:
    requested = sorted({str(item).strip() for item in (question_ids or []) if str(item).strip()})
    params: list[Any] = [track_id]
    id_filter = ""
    if requested:
        placeholders = ",".join("?" for _ in requested)
        id_filter = f" AND q.id IN ({placeholders})"
        params.extend(requested)
    rows = [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT q.id AS question_id,
                   (
                     SELECT v.id FROM question_versions v
                     WHERE v.question_id=q.id
                     ORDER BY v.version_number DESC LIMIT 1
                   ) AS question_version_id
              FROM questions q
              JOIN question_bank_metadata m ON m.question_id=q.id
             WHERE q.track_id=?
               AND q.source_kind='private_bank'
               AND m.authoring_status='active'
               {id_filter}
             ORDER BY q.id
            """,
            params,
        )
    ]
    if requested:
        found = {str(row["question_id"]) for row in rows}
        missing = [qid for qid in requested if qid not in found]
        if missing:
            raise ValueError(
                "Release contains questions that are not imported active private-bank records: "
                + ", ".join(missing[:10])
            )
    missing_versions = [str(row["question_id"]) for row in rows if row.get("question_version_id") is None]
    if missing_versions:
        raise ValueError("Question versions are missing for release members: " + ", ".join(missing_versions[:10]))
    return rows


def _fingerprint(rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(f"{row['question_id']}:{row['question_version_id']}" for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_release(
    release_key: str,
    track_id: str,
    *,
    question_ids: Iterable[str] | None = None,
    actor: str = "system",
    notes: str = "",
    initial_status: str = "draft",
) -> dict[str, Any]:
    ensure_question_bank_release_schema()
    release_key = str(release_key or "").strip()
    track_id = str(track_id or "").strip()
    if not release_key or not track_id:
        raise ValueError("release_key and track_id are required")
    if initial_status not in {"draft", "active"}:
        raise ValueError("New releases may only start as draft or the one-time bootstrap active release")

    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM question_bank_releases WHERE release_key=?", (release_key,)).fetchone():
            raise ValueError(f"Question-bank release already exists: {release_key}")
        rows = _snapshot_rows(conn, track_id, question_ids)
        if not rows:
            raise ValueError("Cannot create an empty question-bank release")
        if initial_status == "active" and conn.execute(
            "SELECT 1 FROM question_bank_releases WHERE track_id=? AND status='active'",
            (track_id,),
        ).fetchone():
            raise ValueError(f"Track {track_id} already has an active release")
        fingerprint = _fingerprint(rows)
        cursor = conn.execute(
            """
            INSERT INTO question_bank_releases(
              release_key,track_id,status,question_count,source_fingerprint,notes,created_by,activated_at
            ) VALUES (?,?,?,?,?,?,?,CASE WHEN ?='active' THEN datetime('now') ELSE NULL END)
            """,
            (release_key, track_id, initial_status, len(rows), fingerprint, notes, actor or "system", initial_status),
        )
        release_id = int(cursor.lastrowid)
        conn.executemany(
            "INSERT INTO question_bank_release_questions(release_id,question_id,question_version_id) VALUES (?,?,?)",
            [(release_id, row["question_id"], int(row["question_version_id"])) for row in rows],
        )
        _event(
            conn,
            release_id,
            "bootstrap_active" if initial_status == "active" else "created",
            actor,
            {"question_count": len(rows), "source_fingerprint": fingerprint},
        )
    return get_release(release_key)


def ensure_active_release_baseline(track_id: str) -> dict[str, Any] | None:
    """Preserve pre-release-system production behavior exactly once.

    If release records already exist, no implicit activation occurs. If this is
    the first release-aware startup and active private-bank content already
    exists, it is snapshotted as a bootstrap active release. Later imports are
    therefore invisible until explicitly released.
    """
    ensure_question_bank_release_schema()
    with connect() as conn:
        active = conn.execute(
            "SELECT release_key FROM question_bank_releases WHERE track_id=? AND status='active' LIMIT 1",
            (track_id,),
        ).fetchone()
        if active:
            return get_release(str(active["release_key"]))
        any_release = conn.execute(
            "SELECT 1 FROM question_bank_releases WHERE track_id=? LIMIT 1",
            (track_id,),
        ).fetchone()
        if any_release:
            return None
        rows = _snapshot_rows(conn, track_id)
    if not rows:
        return None
    fingerprint = _fingerprint(rows)
    return create_release(
        f"bootstrap-{fingerprint[:12]}",
        track_id,
        question_ids=[row["question_id"] for row in rows],
        actor="system",
        notes="Automatic one-time baseline of the private bank that was active when release management was introduced.",
        initial_status="active",
    )


def get_release(release_key: str) -> dict[str, Any]:
    ensure_question_bank_release_schema()
    with connect() as conn:
        row = conn.execute("SELECT * FROM question_bank_releases WHERE release_key=?", (release_key,)).fetchone()
        if not row:
            raise ValueError(f"Unknown question-bank release: {release_key}")
        payload = dict(row)
        events = [
            dict(item)
            for item in conn.execute(
                "SELECT action,actor,metadata_json,created_at FROM question_bank_release_events WHERE release_id=? ORDER BY id",
                (row["id"],),
            )
        ]
    for event in events:
        try:
            event["metadata"] = json.loads(event.pop("metadata_json") or "{}")
        except json.JSONDecodeError:
            event["metadata"] = {}
    payload["events"] = events
    return payload


def list_releases(track_id: str) -> list[dict[str, Any]]:
    ensure_question_bank_release_schema()
    with connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM question_bank_releases WHERE track_id=? ORDER BY id DESC",
                (track_id,),
            )
        ]


def promote_release(release_key: str, target_status: str, *, actor: str = "system") -> dict[str, Any]:
    ensure_question_bank_release_schema()
    if target_status not in RELEASE_STATUSES - {"active", "retired", "draft"}:
        raise ValueError("Promotion target must be qa_passed, sme_approved, or staging")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM question_bank_releases WHERE release_key=?", (release_key,)).fetchone()
        if not row:
            raise ValueError(f"Unknown question-bank release: {release_key}")
        expected = PROMOTION_PATH.get(str(row["status"]))
        if expected != target_status:
            raise ValueError(f"Invalid release transition: {row['status']} -> {target_status}; expected {expected or 'activation/retirement'}")
        timestamp_column = {
            "qa_passed": "qa_passed_at",
            "sme_approved": "approved_at",
            "staging": "staged_at",
        }[target_status]
        approved_by_sql = ",approved_by=?" if target_status == "sme_approved" else ""
        params: list[Any] = [target_status]
        if target_status == "sme_approved":
            params.append(actor or "system")
        params.append(int(row["id"]))
        conn.execute(
            f"UPDATE question_bank_releases SET status=?,{timestamp_column}=datetime('now'){approved_by_sql} WHERE id=?",
            params,
        )
        _event(conn, int(row["id"]), f"promoted_to_{target_status}", actor)
    return get_release(release_key)


def _assert_release_versions_current(conn, release_id: int) -> None:
    stale = [
        dict(row)
        for row in conn.execute(
            """
            SELECT rq.question_id,rq.question_version_id,
                   (SELECT v.id FROM question_versions v WHERE v.question_id=rq.question_id ORDER BY v.version_number DESC LIMIT 1) AS current_version_id
              FROM question_bank_release_questions rq
             WHERE rq.release_id=?
               AND rq.question_version_id != (
                 SELECT v.id FROM question_versions v WHERE v.question_id=rq.question_id ORDER BY v.version_number DESC LIMIT 1
               )
            """,
            (release_id,),
        )
    ]
    if stale:
        raise ValueError(
            "Release snapshot contains superseded unserved question versions; create a new release snapshot instead: "
            + ", ".join(str(row["question_id"]) for row in stale[:10])
        )


def activate_release(release_key: str, *, actor: str = "system") -> dict[str, Any]:
    ensure_question_bank_release_schema()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        target = conn.execute("SELECT * FROM question_bank_releases WHERE release_key=?", (release_key,)).fetchone()
        if not target:
            raise ValueError(f"Unknown question-bank release: {release_key}")
        if target["status"] != "staging":
            raise ValueError(f"Only a staging release can be activated; {release_key} is {target['status']}")
        _assert_release_versions_current(conn, int(target["id"]))
        previous = conn.execute(
            "SELECT id,release_key FROM question_bank_releases WHERE track_id=? AND status='active' LIMIT 1",
            (target["track_id"],),
        ).fetchone()
        if previous:
            conn.execute(
                "UPDATE question_bank_releases SET status='retired',retired_at=datetime('now') WHERE id=?",
                (previous["id"],),
            )
            _event(conn, int(previous["id"]), "retired_on_activation", actor, {"replacement": release_key})
        conn.execute(
            "UPDATE question_bank_releases SET status='active',activated_at=datetime('now'),retired_at=NULL WHERE id=?",
            (target["id"],),
        )
        _event(
            conn,
            int(target["id"]),
            "activated",
            actor,
            {"replaced_release": str(previous["release_key"]) if previous else None},
        )
    return get_release(release_key)


def rollback_release(release_key: str, *, actor: str = "system") -> dict[str, Any]:
    """Atomically restore a previously retired release snapshot."""
    ensure_question_bank_release_schema()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        target = conn.execute("SELECT * FROM question_bank_releases WHERE release_key=?", (release_key,)).fetchone()
        if not target:
            raise ValueError(f"Unknown question-bank release: {release_key}")
        if target["status"] != "retired":
            raise ValueError(f"Rollback target must be retired; {release_key} is {target['status']}")
        _assert_release_versions_current(conn, int(target["id"]))
        current = conn.execute(
            "SELECT id,release_key FROM question_bank_releases WHERE track_id=? AND status='active' LIMIT 1",
            (target["track_id"],),
        ).fetchone()
        if current:
            conn.execute(
                "UPDATE question_bank_releases SET status='retired',retired_at=datetime('now') WHERE id=?",
                (current["id"],),
            )
            _event(conn, int(current["id"]), "retired_on_rollback", actor, {"rollback_to": release_key})
        conn.execute(
            "UPDATE question_bank_releases SET status='active',activated_at=datetime('now'),retired_at=NULL WHERE id=?",
            (target["id"],),
        )
        _event(
            conn,
            int(target["id"]),
            "rollback_activated",
            actor,
            {"replaced_release": str(current["release_key"]) if current else None},
        )
    return get_release(release_key)


def retire_release(release_key: str, *, actor: str = "system") -> dict[str, Any]:
    ensure_question_bank_release_schema()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM question_bank_releases WHERE release_key=?", (release_key,)).fetchone()
        if not row:
            raise ValueError(f"Unknown question-bank release: {release_key}")
        if row["status"] == "active":
            raise ValueError("Do not retire the active release without a replacement; activate a staging release instead")
        if row["status"] == "retired":
            return get_release(release_key)
        conn.execute(
            "UPDATE question_bank_releases SET status='retired',retired_at=datetime('now') WHERE id=?",
            (row["id"],),
        )
        _event(conn, int(row["id"]), "retired", actor)
    return get_release(release_key)


def compare_releases(left_key: str, right_key: str) -> dict[str, Any]:
    ensure_question_bank_release_schema()
    with connect() as conn:
        left = conn.execute("SELECT id,track_id FROM question_bank_releases WHERE release_key=?", (left_key,)).fetchone()
        right = conn.execute("SELECT id,track_id FROM question_bank_releases WHERE release_key=?", (right_key,)).fetchone()
        if not left or not right:
            raise ValueError("Both release keys must exist")
        if left["track_id"] != right["track_id"]:
            raise ValueError("Question-bank releases from different tracks cannot be compared")
        left_rows = {
            str(row["question_id"]): int(row["question_version_id"])
            for row in conn.execute(
                "SELECT question_id,question_version_id FROM question_bank_release_questions WHERE release_id=?",
                (left["id"],),
            )
        }
        right_rows = {
            str(row["question_id"]): int(row["question_version_id"])
            for row in conn.execute(
                "SELECT question_id,question_version_id FROM question_bank_release_questions WHERE release_id=?",
                (right["id"],),
            )
        }
    left_ids = set(left_rows)
    right_ids = set(right_rows)
    return {
        "left": left_key,
        "right": right_key,
        "added": sorted(right_ids - left_ids),
        "removed": sorted(left_ids - right_ids),
        "changed": sorted(qid for qid in left_ids & right_ids if left_rows[qid] != right_rows[qid]),
        "unchanged_count": sum(1 for qid in left_ids & right_ids if left_rows[qid] == right_rows[qid]),
    }


def active_release_question_ids(track_id: str) -> set[str]:
    ensure_active_release_baseline(track_id)
    with connect() as conn:
        active = conn.execute(
            "SELECT id FROM question_bank_releases WHERE track_id=? AND status='active' LIMIT 1",
            (track_id,),
        ).fetchone()
        if not active:
            return set()
        return {
            str(row["question_id"])
            for row in conn.execute(
                "SELECT question_id FROM question_bank_release_questions WHERE release_id=?",
                (active["id"],),
            )
        }


def filter_rows_to_active_release(rows: list[dict[str, Any]], track_id: str) -> list[dict[str, Any]]:
    """Hide managed private-bank rows that are not in the active release.

    Canonical/curated fallback rows remain available for development and staged
    authoring exactly as before. Only commercial managed-bank rows are governed
    by the release snapshot.
    """
    allowed = active_release_question_ids(track_id)
    return [
        row
        for row in rows
        if not row.get("bank_pool") or str(row.get("id") or "") in allowed
    ]
