from __future__ import annotations

from typing import Any

from .config import DATABASE_BACKEND
from .database import connect
from .question_editorial import EditorialError, ensure_question_editorial_schema, release_editorial_report


SCHEMA_VERSION = "20260815_061_question_editorial_gate_v1"


def ensure_question_editorial_policy_schema() -> None:
    ensure_question_editorial_schema()
    with connect() as conn:
        existing = conn.execute("SELECT 1 FROM schema_migrations WHERE version=?", (SCHEMA_VERSION,)).fetchone()
        if existing:
            return
        if DATABASE_BACKEND == "postgresql":
            raise RuntimeError("PostgreSQL question editorial gate migration was not applied")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS question_editorial_policies (
              track_id TEXT PRIMARY KEY,
              enforcement_enabled INTEGER NOT NULL DEFAULT 0 CHECK(enforcement_enabled IN (0,1)),
              minimum_qa_score REAL NOT NULL DEFAULT 70 CHECK(minimum_qa_score BETWEEN 0 AND 100),
              require_content_review INTEGER NOT NULL DEFAULT 1 CHECK(require_content_review IN (0,1)),
              require_sme_review INTEGER NOT NULL DEFAULT 1 CHECK(require_sme_review IN (0,1)),
              updated_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_by TEXT NOT NULL DEFAULT 'system'
            );

            DROP TRIGGER IF EXISTS trg_question_editorial_release_gate;
            CREATE TRIGGER trg_question_editorial_release_gate
            BEFORE UPDATE OF status ON question_bank_releases
            WHEN NEW.status IN ('qa_passed','sme_approved','staging','active')
             AND NEW.status<>OLD.status
             AND EXISTS(
               SELECT 1 FROM question_editorial_policies p
                WHERE p.track_id=NEW.track_id AND p.enforcement_enabled=1
             )
            BEGIN
              SELECT CASE WHEN EXISTS(
                SELECT 1
                  FROM question_bank_release_questions item
                  JOIN question_editorial_policies p ON p.track_id=NEW.track_id
                  LEFT JOIN question_editorial_state state ON state.question_id=item.question_id
                 WHERE item.release_id=NEW.id
                   AND p.enforcement_enabled=1
                   AND (
                     state.question_id IS NULL
                     OR state.qa_status<>'passed'
                     OR COALESCE(state.qa_score,0)<p.minimum_qa_score
                     OR COALESCE(state.qa_question_version_id,0)<>COALESCE(item.question_version_id,0)
                     OR (
                       NEW.status IN ('sme_approved','staging','active')
                       AND p.require_content_review=1
                       AND (
                         state.content_review_status<>'approved'
                         OR COALESCE(state.content_review_question_version_id,0)<>COALESCE(item.question_version_id,0)
                       )
                     )
                     OR (
                       NEW.status IN ('sme_approved','staging','active')
                       AND p.require_sme_review=1
                       AND (
                         state.sme_review_status<>'approved'
                         OR COALESCE(state.sme_review_question_version_id,0)<>COALESCE(item.question_version_id,0)
                       )
                     )
                   )
              ) THEN RAISE(ABORT,'question editorial gate blocked release transition') END;
            END;
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
            (SCHEMA_VERSION, "SQLite optional version-bound question editorial release gate"),
        )


def set_editorial_policy(
    track_id: str,
    *,
    enforcement_enabled: bool,
    minimum_qa_score: float = 70.0,
    require_content_review: bool = True,
    require_sme_review: bool = True,
    actor: str = "admin",
    release_key: str | None = None,
) -> dict[str, Any]:
    ensure_question_editorial_policy_schema()
    score = float(minimum_qa_score)
    if not 0 <= score <= 100:
        raise EditorialError("minimum_qa_score must be between 0 and 100")
    if enforcement_enabled:
        with connect() as conn:
            if release_key:
                target = release_key
            else:
                row = conn.execute(
                    "SELECT release_key FROM question_bank_releases WHERE track_id=? AND status='active' ORDER BY activated_at DESC,id DESC LIMIT 1",
                    (track_id,),
                ).fetchone()
                target = str(row["release_key"]) if row else None
        if not target:
            raise EditorialError("Cannot enable editorial enforcement without an active or explicitly supplied release")
        report = release_editorial_report(target)
        if report["qa_pct"] < 100.0:
            raise EditorialError("Cannot enable editorial enforcement until every release item has current QA")
        if require_content_review and report["content_approved_pct"] < 100.0:
            raise EditorialError("Cannot enable editorial enforcement until every release item has current content approval")
        if require_sme_review and report["sme_approved_pct"] < 100.0:
            raise EditorialError("Cannot enable editorial enforcement until every release item has current SME approval")
        with connect() as conn:
            low_score = conn.execute(
                """
                SELECT COUNT(*) AS n
                  FROM question_bank_release_questions item
                  JOIN question_bank_releases rel ON rel.id=item.release_id
                  LEFT JOIN question_editorial_state state ON state.question_id=item.question_id
                 WHERE rel.release_key=? AND COALESCE(state.qa_score,0)<?
                """,
                (target, score),
            ).fetchone()
        if low_score and int(low_score["n"]) > 0:
            raise EditorialError("Cannot enable editorial enforcement: one or more release items are below the configured QA score")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO question_editorial_policies(
              track_id,enforcement_enabled,minimum_qa_score,require_content_review,require_sme_review,updated_by
            ) VALUES (?,?,?,?,?,?)
            ON CONFLICT(track_id) DO UPDATE SET
              enforcement_enabled=excluded.enforcement_enabled,
              minimum_qa_score=excluded.minimum_qa_score,
              require_content_review=excluded.require_content_review,
              require_sme_review=excluded.require_sme_review,
              updated_at=datetime('now'),updated_by=excluded.updated_by
            """,
            (
                track_id,
                int(bool(enforcement_enabled)),
                score,
                int(bool(require_content_review)),
                int(bool(require_sme_review)),
                actor,
            ),
        )
        row = conn.execute("SELECT * FROM question_editorial_policies WHERE track_id=?", (track_id,)).fetchone()
    return dict(row)
