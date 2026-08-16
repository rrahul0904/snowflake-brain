from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from .config import DATABASE_BACKEND
from .database import connect
from .question_versions import ensure_question_version_schema


SCHEMA_VERSION = "20260815_060_question_editorial_maturity_v1"
_ALLOWED_REVIEW_ACTIONS = {"approved", "changes_requested"}
_DEPENDENCY_PATTERNS = (
    r"\bprevious question\b",
    r"\bquestion above\b",
    r"\babove question\b",
    r"\bshown earlier\b",
    r"\bfrom the previous item\b",
    r"\bas described above\b",
)
_ABSOLUTE_TERMS = (" always ", " never ", " only ", " must ", " impossible ")
_SCENARIO_TERMS = ("scenario", "company", "organization", "administrator", "engineer", "architect", "workload", "requirement")
_TERMINOLOGY_CASE = {
    "snowpipe streaming": "Snowpipe Streaming",
    "snowpark": "Snowpark",
    "snowsight": "Snowsight",
    "snowgrid": "Snowgrid",
    "time travel": "Time Travel",
    "failsafe": "Fail-safe",
    "fail safe": "Fail-safe",
}


class EditorialError(ValueError):
    pass


@dataclass(frozen=True)
class Finding:
    dimension: str
    code: str
    severity: str
    message: str
    metadata: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _table_exists(conn: Any, table: str) -> bool:
    if DATABASE_BACKEND == "postgresql":
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=current_schema() AND table_name=?",
            (table,),
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return bool(row and int(row["n"]) > 0)


def ensure_question_editorial_schema() -> None:
    ensure_question_version_schema()
    with connect() as conn:
        existing = conn.execute("SELECT 1 FROM schema_migrations WHERE version=?", (SCHEMA_VERSION,)).fetchone()
        if existing:
            return
        if DATABASE_BACKEND == "postgresql":
            raise RuntimeError("PostgreSQL editorial maturity migration was not applied")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS question_editorial_state (
              question_id TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
              qa_status TEXT NOT NULL DEFAULT 'pending' CHECK(qa_status IN ('pending','passed','failed')),
              qa_score REAL NOT NULL DEFAULT 0 CHECK(qa_score BETWEEN 0 AND 100),
              qa_question_version_id INTEGER REFERENCES question_versions(id) ON DELETE SET NULL,
              last_qa_run_id INTEGER,
              content_review_status TEXT NOT NULL DEFAULT 'pending' CHECK(content_review_status IN ('pending','approved','changes_requested')),
              content_review_question_version_id INTEGER REFERENCES question_versions(id) ON DELETE SET NULL,
              content_reviewer TEXT NOT NULL DEFAULT '',
              content_reviewed_at TEXT,
              sme_review_status TEXT NOT NULL DEFAULT 'pending' CHECK(sme_review_status IN ('pending','approved','changes_requested')),
              sme_review_question_version_id INTEGER REFERENCES question_versions(id) ON DELETE SET NULL,
              sme_reviewer TEXT NOT NULL DEFAULT '',
              sme_reviewed_at TEXT,
              updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS editorial_qa_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              track_id TEXT NOT NULL,
              scope TEXT NOT NULL DEFAULT 'bank',
              started_at TEXT NOT NULL DEFAULT (datetime('now')),
              completed_at TEXT,
              question_count INTEGER NOT NULL DEFAULT 0,
              passed_count INTEGER NOT NULL DEFAULT 0,
              failed_count INTEGER NOT NULL DEFAULT 0,
              blocker_count INTEGER NOT NULL DEFAULT 0,
              warning_count INTEGER NOT NULL DEFAULT 0,
              info_count INTEGER NOT NULL DEFAULT 0,
              metrics_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS editorial_findings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              qa_run_id INTEGER NOT NULL REFERENCES editorial_qa_runs(id) ON DELETE CASCADE,
              question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,
              dimension TEXT NOT NULL,
              check_code TEXT NOT NULL,
              severity TEXT NOT NULL CHECK(severity IN ('blocker','warning','info')),
              message TEXT NOT NULL,
              metadata_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS editorial_review_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
              question_version_id INTEGER NOT NULL REFERENCES question_versions(id) ON DELETE CASCADE,
              stage TEXT NOT NULL CHECK(stage IN ('content','sme')),
              action TEXT NOT NULL CHECK(action IN ('approved','changes_requested')),
              actor TEXT NOT NULL,
              notes TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_editorial_state_qa ON question_editorial_state(qa_status,qa_score);
            CREATE INDEX IF NOT EXISTS idx_editorial_state_content ON question_editorial_state(content_review_status,sme_review_status);
            CREATE INDEX IF NOT EXISTS idx_editorial_findings_question ON editorial_findings(question_id,severity,check_code);
            CREATE INDEX IF NOT EXISTS idx_editorial_review_events_question ON editorial_review_events(question_id,created_at DESC);
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
            (SCHEMA_VERSION, "SQLite question editorial maturity and version-bound approvals"),
        )


def _latest_question_version_id(conn: Any, question_id: str) -> int:
    row = conn.execute(
        "SELECT id FROM question_versions WHERE question_id=? ORDER BY id DESC LIMIT 1",
        (question_id,),
    ).fetchone()
    if not row:
        raise EditorialError(f"Question has no immutable version: {question_id}")
    return int(row["id"])


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(str(value or "[]"))
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _tokens(value: str) -> set[str]:
    stop = {"a", "an", "the", "to", "of", "for", "in", "on", "is", "are", "and", "or", "which", "what", "snowflake"}
    return {token for token in _normalize_text(value).split() if token not in stop and len(token) > 2}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _question_domain(conn: Any, question_id: str) -> str:
    # The commercial bank owns blueprint metadata in question_bank_metadata.
    # Prefer that canonical mapping and retain question_skill_map only as a
    # compatibility fallback for older imported material.
    if _table_exists(conn, "question_bank_metadata"):
        row = conn.execute(
            "SELECT domain_id FROM question_bank_metadata WHERE question_id=? LIMIT 1",
            (question_id,),
        ).fetchone()
        if row and row["domain_id"]:
            return str(row["domain_id"])
    if not _table_exists(conn, "question_skill_map"):
        return "unmapped"
    row = conn.execute(
        """
        SELECT domain_id,confidence
          FROM question_skill_map
         WHERE question_id=?
         ORDER BY reviewed DESC,confidence DESC,domain_id
         LIMIT 1
        """,
        (question_id,),
    ).fetchone()
    return str(row["domain_id"] or "unmapped") if row else "unmapped"


def _provenance_state(conn: Any, track_id: str, question_id: str) -> str:
    if not _table_exists(conn, "content_source_links") or not _table_exists(conn, "content_sources"):
        return "not_installed"
    rows = conn.execute(
        """
        SELECT l.editorial_status AS link_status,s.editorial_status AS source_status
          FROM content_source_links l
          JOIN content_sources s ON s.id=l.source_id
         WHERE l.track_id=? AND l.artifact_type='question' AND l.artifact_key=?
        """,
        (track_id, question_id),
    ).fetchall()
    if not rows:
        return "missing"
    if any(str(row["link_status"]) == "verified" and str(row["source_status"]) == "verified" for row in rows):
        return "verified"
    if any(str(row["link_status"]) == "needs_review" or str(row["source_status"]) == "needs_review" for row in rows):
        return "needs_review"
    return "unverified"


def _single_question_findings(conn: Any, row: Any, provenance_state: str) -> list[Finding]:
    question_id = str(row["id"])
    stem = str(row["question"] or "").strip()
    explanation = str(row["explanation"] or "").strip()
    options = [str(item).strip() for item in _json_list(row["options_json"])]
    correct = _json_list(row["correct_json"])
    try:
        correct_indexes = [int(item) for item in correct]
    except Exception:
        correct_indexes = []
    multiple = bool(int(row["multiple"] or 0))
    difficulty = str(row["difficulty"] or "").lower().strip()
    tags = [str(item).lower() for item in _json_list(row["tags"])]
    findings: list[Finding] = []

    def add(dimension: str, code: str, severity: str, message: str, **metadata: Any) -> None:
        findings.append(Finding(dimension, code, severity, message, metadata))

    if len(options) < 3:
        add("structure", "too_few_options", "blocker", "Question must have at least three answer options.", option_count=len(options))
    normalized_options = [_normalize_text(item) for item in options]
    if len(set(normalized_options)) != len(normalized_options):
        add("distractors", "duplicate_options", "blocker", "Question contains duplicate or normalization-equivalent options.")
    if not correct_indexes:
        add("structure", "missing_correct_answer", "blocker", "Question has no valid correct answer index.")
    elif any(index < 0 or index >= len(options) for index in correct_indexes):
        add("structure", "invalid_correct_index", "blocker", "Correct-answer index falls outside the option list.")
    if multiple and len(correct_indexes) < 2:
        add("structure", "multiple_flag_mismatch", "blocker", "Question is marked multiple-answer but has fewer than two correct options.")
    if not multiple and len(correct_indexes) > 1:
        add("structure", "single_flag_mismatch", "blocker", "Question is marked single-answer but has multiple correct options.")
    if len(stem) < 35:
        add("clarity", "stem_too_short", "warning", "Question stem is unusually short and should be checked for missing context.", length=len(stem))
    if stem.count("?") > 1:
        add("clarity", "multiple_questions_in_stem", "warning", "Question stem appears to ask more than one question.")
    if any(re.search(pattern, stem, flags=re.IGNORECASE) for pattern in _DEPENDENCY_PATTERNS):
        add("independence", "cross_question_dependency", "blocker", "Question depends on another item or earlier context.")
    if len(explanation) < 80:
        add("explanation", "explanation_too_short", "warning", "Explanation is too short for a high-quality certification rationale.", length=len(explanation))
    if len(explanation) < 25:
        add("explanation", "explanation_missing_rationale", "blocker", "Explanation is effectively missing.", length=len(explanation))
    if any(_normalize_text(option) in {"all of the above", "none of the above"} for option in options):
        add("distractors", "meta_option", "warning", "Avoid all/none-of-the-above options unless editorially justified.")

    lengths = [len(option) for option in options if option]
    if lengths and min(lengths) > 0 and max(lengths) / max(1, min(lengths)) >= 4.0:
        add("distractors", "option_length_outlier", "warning", "One answer option is much longer than another and may cue the answer.", min_length=min(lengths), max_length=max(lengths))

    padded = f" {_normalize_text(stem)} "
    absolutes = [term.strip() for term in _ABSOLUTE_TERMS if term in padded]
    if absolutes:
        add("ambiguity", "absolute_wording", "warning", "Absolute wording should be checked for unintended ambiguity.", terms=absolutes)

    scenario_tagged = any("scenario" in tag for tag in tags) or any(term in stem.lower() for term in _SCENARIO_TERMS)
    if scenario_tagged and len(stem) < 100:
        add("scenario_realism", "thin_scenario", "warning", "Scenario-style question has limited operational context.", length=len(stem))

    combined = f"{stem}\n{explanation}\n{' '.join(options)}"
    for canonical_lower, canonical in _TERMINOLOGY_CASE.items():
        if canonical_lower in combined.lower() and canonical not in combined:
            add("terminology", "terminology_casing", "info", f"Check Snowflake terminology/casing for {canonical}.", canonical=canonical)

    if difficulty not in {"easy", "medium", "hard"}:
        add("difficulty", "difficulty_missing_or_invalid", "warning", "Difficulty should be normalized to easy, medium, or hard.", difficulty=difficulty)

    if provenance_state == "needs_review":
        add("freshness", "source_needs_review", "blocker", "Linked official source has changed and requires editorial review.")
    elif provenance_state == "unverified":
        add("freshness", "source_unverified", "warning", "Linked official-source provenance has not been verified.")
    elif provenance_state == "missing":
        add("freshness", "source_missing", "warning", "Question has no registered official-source provenance.")

    return findings


def _pair_duplicate_findings(rows: list[Any]) -> dict[str, list[Finding]]:
    findings: dict[str, list[Finding]] = defaultdict(list)
    token_sets = {str(row["id"]): _tokens(str(row["question"] or "")) for row in rows}
    ordered = [str(row["id"]) for row in rows]
    for index, left_id in enumerate(ordered):
        for right_id in ordered[index + 1 :]:
            score = _jaccard(token_sets[left_id], token_sets[right_id])
            if score < 0.82:
                continue
            severity = "blocker" if score >= 0.92 else "warning"
            code = "near_duplicate_blocker" if severity == "blocker" else "near_duplicate_warning"
            for question_id, other in ((left_id, right_id), (right_id, left_id)):
                findings[question_id].append(
                    Finding(
                        "duplicates",
                        code,
                        severity,
                        "Question stem is highly similar to another active item.",
                        {"other_question_id": other, "jaccard": round(score, 4)},
                    )
                )
    return findings


def _distribution_findings(rows: list[Any], domains: dict[str, str]) -> dict[str, list[Finding]]:
    results: dict[str, list[Finding]] = defaultdict(list)
    by_domain: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        by_domain[domains[str(row["id"])]].append(row)

    for domain_id, domain_rows in by_domain.items():
        if len(domain_rows) >= 8:
            answer_positions: list[int] = []
            for row in domain_rows:
                correct = _json_list(row["correct_json"])
                if correct:
                    try:
                        answer_positions.append(int(correct[0]))
                    except Exception:
                        pass
            counts = Counter(answer_positions)
            if answer_positions:
                most_position, most_count = counts.most_common(1)[0]
                share = most_count / len(answer_positions)
                if share > 0.55:
                    for row in domain_rows:
                        results[str(row["id"])].append(
                            Finding(
                                "answer_distribution",
                                "answer_position_skew",
                                "warning",
                                "Domain answer positions are overly concentrated and should be rebalanced editorially.",
                                {"domain_id": domain_id, "position": most_position, "share": round(share, 4)},
                            )
                        )
                    break

        if len(domain_rows) >= 12:
            difficulties = Counter(str(row["difficulty"] or "").lower().strip() for row in domain_rows)
            if difficulties and max(difficulties.values()) / len(domain_rows) > 0.80:
                dominant, count = difficulties.most_common(1)[0]
                for row in domain_rows:
                    results[str(row["id"])].append(
                        Finding(
                            "difficulty",
                            "difficulty_distribution_skew",
                            "warning",
                            "Domain difficulty mix is heavily concentrated in one tier.",
                            {"domain_id": domain_id, "difficulty": dominant, "share": round(count / len(domain_rows), 4)},
                        )
                    )
                break
    return results


def _score(findings: Iterable[Finding]) -> float:
    score = 100.0
    for finding in findings:
        score -= {"blocker": 35.0, "warning": 8.0, "info": 1.5}.get(finding.severity, 0.0)
    return max(0.0, round(score, 2))


def run_qa(track_id: str = "snowpro-core", *, active_only: bool = True, scope: str = "bank") -> dict[str, Any]:
    ensure_question_editorial_schema()
    with connect() as conn:
        where = "WHERE q.track_id=?"
        params: list[Any] = [track_id]
        if active_only:
            where += " AND EXISTS (SELECT 1 FROM question_bank_metadata meta WHERE meta.question_id=q.id AND meta.authoring_status='active')"
        rows = conn.execute(f"SELECT q.* FROM questions q {where} ORDER BY q.id", tuple(params)).fetchall()
        if not rows:
            raise EditorialError(f"No questions found for track {track_id}")
        domains = {str(row["id"]): _question_domain(conn, str(row["id"])) for row in rows}
        provenance = {str(row["id"]): _provenance_state(conn, track_id, str(row["id"])) for row in rows}
        version_ids = {str(row["id"]): _latest_question_version_id(conn, str(row["id"])) for row in rows}

        run_cursor = conn.execute(
            "INSERT INTO editorial_qa_runs(track_id,scope,question_count) VALUES (?,?,?)",
            (track_id, scope, len(rows)),
        )
        run_id = int(run_cursor.lastrowid)

        all_findings: dict[str, list[Finding]] = {
            str(row["id"]): _single_question_findings(conn, row, provenance[str(row["id"])])
            for row in rows
        }
        duplicate_findings = _pair_duplicate_findings(rows)
        distribution_findings = _distribution_findings(rows, domains)
        for question_id in all_findings:
            all_findings[question_id].extend(duplicate_findings.get(question_id, []))
            all_findings[question_id].extend(distribution_findings.get(question_id, []))

        passed = failed = blockers = warnings = infos = 0
        score_values: list[float] = []
        for row in rows:
            question_id = str(row["id"])
            findings = all_findings[question_id]
            score = _score(findings)
            has_blocker = any(item.severity == "blocker" for item in findings)
            qa_status = "failed" if has_blocker or score < 70.0 else "passed"
            passed += int(qa_status == "passed")
            failed += int(qa_status == "failed")
            blockers += sum(item.severity == "blocker" for item in findings)
            warnings += sum(item.severity == "warning" for item in findings)
            infos += sum(item.severity == "info" for item in findings)
            score_values.append(score)

            conn.execute(
                """
                INSERT INTO question_editorial_state(
                  question_id,qa_status,qa_score,qa_question_version_id,last_qa_run_id
                ) VALUES (?,?,?,?,?)
                ON CONFLICT(question_id) DO UPDATE SET
                  qa_status=excluded.qa_status,
                  qa_score=excluded.qa_score,
                  qa_question_version_id=excluded.qa_question_version_id,
                  last_qa_run_id=excluded.last_qa_run_id,
                  content_review_status=CASE
                    WHEN question_editorial_state.content_review_question_version_id=excluded.qa_question_version_id
                    THEN question_editorial_state.content_review_status ELSE 'pending' END,
                  content_review_question_version_id=CASE
                    WHEN question_editorial_state.content_review_question_version_id=excluded.qa_question_version_id
                    THEN question_editorial_state.content_review_question_version_id ELSE NULL END,
                  content_reviewer=CASE
                    WHEN question_editorial_state.content_review_question_version_id=excluded.qa_question_version_id
                    THEN question_editorial_state.content_reviewer ELSE '' END,
                  content_reviewed_at=CASE
                    WHEN question_editorial_state.content_review_question_version_id=excluded.qa_question_version_id
                    THEN question_editorial_state.content_reviewed_at ELSE NULL END,
                  sme_review_status=CASE
                    WHEN question_editorial_state.sme_review_question_version_id=excluded.qa_question_version_id
                    THEN question_editorial_state.sme_review_status ELSE 'pending' END,
                  sme_review_question_version_id=CASE
                    WHEN question_editorial_state.sme_review_question_version_id=excluded.qa_question_version_id
                    THEN question_editorial_state.sme_review_question_version_id ELSE NULL END,
                  sme_reviewer=CASE
                    WHEN question_editorial_state.sme_review_question_version_id=excluded.qa_question_version_id
                    THEN question_editorial_state.sme_reviewer ELSE '' END,
                  sme_reviewed_at=CASE
                    WHEN question_editorial_state.sme_review_question_version_id=excluded.qa_question_version_id
                    THEN question_editorial_state.sme_reviewed_at ELSE NULL END,
                  updated_at=datetime('now')
                """,
                (question_id, qa_status, score, version_ids[question_id], run_id),
            )
            for finding in findings:
                conn.execute(
                    """
                    INSERT INTO editorial_findings(
                      qa_run_id,question_id,dimension,check_code,severity,message,metadata_json
                    ) VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        run_id,
                        question_id,
                        finding.dimension,
                        finding.code,
                        finding.severity,
                        finding.message,
                        json.dumps(finding.metadata, separators=(",", ":"), sort_keys=True),
                    ),
                )

        domain_metrics: dict[str, dict[str, Any]] = {}
        for domain_id in sorted(set(domains.values())):
            ids = [question_id for question_id, value in domains.items() if value == domain_id]
            domain_scores = [
                _score(all_findings[question_id]) for question_id in ids
            ]
            domain_metrics[domain_id] = {
                "questions": len(ids),
                "avg_qa_score": round(sum(domain_scores) / len(domain_scores), 2) if domain_scores else 0,
                "qa_passed": sum(not any(f.severity == "blocker" for f in all_findings[qid]) and _score(all_findings[qid]) >= 70 for qid in ids),
                "provenance_verified": sum(provenance[qid] == "verified" for qid in ids),
            }

        metrics = {
            "average_qa_score": round(sum(score_values) / len(score_values), 2) if score_values else 0.0,
            "domain_metrics": domain_metrics,
        }
        conn.execute(
            """
            UPDATE editorial_qa_runs
               SET completed_at=datetime('now'),passed_count=?,failed_count=?,blocker_count=?,warning_count=?,info_count=?,metrics_json=?
             WHERE id=?
            """,
            (passed, failed, blockers, warnings, infos, json.dumps(metrics, separators=(",", ":"), sort_keys=True), run_id),
        )

    return {
        "run_id": run_id,
        "track_id": track_id,
        "scope": scope,
        "questions": len(rows),
        "passed": passed,
        "failed": failed,
        "blockers": blockers,
        "warnings": warnings,
        "info": infos,
        **metrics,
    }


def review_question(
    question_id: str,
    stage: str,
    action: str,
    actor: str,
    *,
    notes: str = "",
) -> dict[str, Any]:
    ensure_question_editorial_schema()
    stage = str(stage or "").strip().lower()
    action = str(action or "").strip().lower()
    actor = str(actor or "").strip()
    if stage not in {"content", "sme"}:
        raise EditorialError("stage must be content or sme")
    if action not in _ALLOWED_REVIEW_ACTIONS:
        raise EditorialError("action must be approved or changes_requested")
    if not actor:
        raise EditorialError("A human reviewer/SME actor is required; automation cannot self-approve editorial stages.")

    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        version_id = _latest_question_version_id(conn, question_id)
        state = conn.execute("SELECT * FROM question_editorial_state WHERE question_id=?", (question_id,)).fetchone()
        if not state or int(state["qa_question_version_id"] or 0) != version_id:
            raise EditorialError("Run automated QA on the current immutable question version before human review.")
        if str(state["qa_status"]) != "passed":
            raise EditorialError("Question cannot be approved while automated QA is failing.")
        if stage == "sme":
            if str(state["content_review_status"]) != "approved" or int(state["content_review_question_version_id"] or 0) != version_id:
                raise EditorialError("Content review of the current version must be approved before SME approval.")

        conn.execute(
            "INSERT INTO editorial_review_events(question_id,question_version_id,stage,action,actor,notes) VALUES (?,?,?,?,?,?)",
            (question_id, version_id, stage, action, actor, notes[:2000]),
        )
        if stage == "content":
            conn.execute(
                """
                UPDATE question_editorial_state
                   SET content_review_status=?,content_review_question_version_id=?,content_reviewer=?,content_reviewed_at=datetime('now'),
                       sme_review_status=CASE WHEN ?='approved' THEN sme_review_status ELSE 'pending' END,
                       sme_review_question_version_id=CASE WHEN ?='approved' THEN sme_review_question_version_id ELSE NULL END,
                       sme_reviewer=CASE WHEN ?='approved' THEN sme_reviewer ELSE '' END,
                       sme_reviewed_at=CASE WHEN ?='approved' THEN sme_reviewed_at ELSE NULL END,
                       updated_at=datetime('now')
                 WHERE question_id=?
                """,
                (action, version_id, actor, action, action, action, action, question_id),
            )
        else:
            conn.execute(
                """
                UPDATE question_editorial_state
                   SET sme_review_status=?,sme_review_question_version_id=?,sme_reviewer=?,sme_reviewed_at=datetime('now'),updated_at=datetime('now')
                 WHERE question_id=?
                """,
                (action, version_id, actor, question_id),
            )
        updated = conn.execute("SELECT * FROM question_editorial_state WHERE question_id=?", (question_id,)).fetchone()
    return _state_public(updated)


def _state_public(row: Any) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "question_id": row["question_id"],
        "qa_status": row["qa_status"],
        "qa_score": float(row["qa_score"] or 0),
        "qa_question_version_id": row["qa_question_version_id"],
        "content_review_status": row["content_review_status"],
        "content_review_question_version_id": row["content_review_question_version_id"],
        "content_reviewer": row["content_reviewer"],
        "content_reviewed_at": row["content_reviewed_at"],
        "sme_review_status": row["sme_review_status"],
        "sme_review_question_version_id": row["sme_review_question_version_id"],
        "sme_reviewer": row["sme_reviewer"],
        "sme_reviewed_at": row["sme_reviewed_at"],
        "updated_at": row["updated_at"],
    }


def question_status(question_id: str) -> dict[str, Any]:
    ensure_question_editorial_schema()
    with connect() as conn:
        current_version = _latest_question_version_id(conn, question_id)
        row = conn.execute("SELECT * FROM question_editorial_state WHERE question_id=?", (question_id,)).fetchone()
        findings = conn.execute(
            """
            SELECT dimension,check_code,severity,message,metadata_json,created_at
              FROM editorial_findings
             WHERE question_id=? AND qa_run_id=(SELECT last_qa_run_id FROM question_editorial_state WHERE question_id=?)
             ORDER BY CASE severity WHEN 'blocker' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END,id
            """,
            (question_id, question_id),
        ).fetchall()
    state = _state_public(row)
    state["current_question_version_id"] = current_version
    state["qa_current"] = bool(row and int(row["qa_question_version_id"] or 0) == current_version)
    state["content_review_current"] = bool(row and int(row["content_review_question_version_id"] or 0) == current_version and str(row["content_review_status"]) == "approved")
    state["sme_review_current"] = bool(row and int(row["sme_review_question_version_id"] or 0) == current_version and str(row["sme_review_status"]) == "approved")
    state["findings"] = [
        {
            "dimension": item["dimension"],
            "check_code": item["check_code"],
            "severity": item["severity"],
            "message": item["message"],
            "metadata": json.loads(item["metadata_json"] or "{}"),
            "created_at": item["created_at"],
        }
        for item in findings
    ]
    return state


def release_editorial_report(release_key: str) -> dict[str, Any]:
    ensure_question_editorial_schema()
    with connect() as conn:
        release = conn.execute("SELECT id,track_id,status FROM question_bank_releases WHERE release_key=?", (release_key,)).fetchone()
        if not release:
            raise EditorialError(f"Unknown question-bank release: {release_key}")
        items = conn.execute(
            "SELECT question_id,question_version_id FROM question_bank_release_questions WHERE release_id=? ORDER BY question_id",
            (int(release["id"]),),
        ).fetchall()
        violations: list[dict[str, Any]] = []
        passed = content = sme = 0
        for item in items:
            question_id = str(item["question_id"])
            version_id = int(item["question_version_id"] or 0)
            state = conn.execute("SELECT * FROM question_editorial_state WHERE question_id=?", (question_id,)).fetchone()
            qa_ok = bool(state and str(state["qa_status"]) == "passed" and int(state["qa_question_version_id"] or 0) == version_id)
            content_ok = bool(state and str(state["content_review_status"]) == "approved" and int(state["content_review_question_version_id"] or 0) == version_id)
            sme_ok = bool(state and str(state["sme_review_status"]) == "approved" and int(state["sme_review_question_version_id"] or 0) == version_id)
            passed += int(qa_ok)
            content += int(content_ok)
            sme += int(sme_ok)
            if not qa_ok:
                violations.append({"question_id": question_id, "stage": "qa", "reason": "current release version not QA-passed"})
            elif not content_ok:
                violations.append({"question_id": question_id, "stage": "content_review", "reason": "current release version lacks human content approval"})
            elif not sme_ok:
                violations.append({"question_id": question_id, "stage": "sme_review", "reason": "current release version lacks explicit SME approval"})
    total = len(items)
    return {
        "release_key": release_key,
        "track_id": str(release["track_id"]),
        "release_status": str(release["status"]),
        "question_count": total,
        "qa_current": passed,
        "content_approved_current": content,
        "sme_approved_current": sme,
        "qa_pct": round(passed / total * 100, 2) if total else 100.0,
        "content_approved_pct": round(content / total * 100, 2) if total else 100.0,
        "sme_approved_pct": round(sme / total * 100, 2) if total else 100.0,
        "gate_pass": not violations,
        "violations": violations,
    }


def bank_health(track_id: str = "snowpro-core") -> dict[str, Any]:
    ensure_question_editorial_schema()
    with connect() as conn:
        questions = conn.execute(
            """
            SELECT q.id,q.difficulty,q.correct_json
              FROM questions q
              JOIN question_bank_metadata meta ON meta.question_id=q.id
             WHERE q.track_id=? AND meta.authoring_status='active'
             ORDER BY q.id
            """,
            (track_id,),
        ).fetchall()
        domains = {str(row["id"]): _question_domain(conn, str(row["id"])) for row in questions}
        states = {
            str(row["question_id"]): row
            for row in conn.execute(
                "SELECT * FROM question_editorial_state WHERE question_id IN (SELECT id FROM questions WHERE track_id=?)",
                (track_id,),
            ).fetchall()
        }
        provenance_installed = _table_exists(conn, "content_source_links") and _table_exists(conn, "content_sources")
        domain_rows: dict[str, list[Any]] = defaultdict(list)
        for row in questions:
            domain_rows[domains[str(row["id"])]].append(row)

        domain_health: dict[str, Any] = {}
        for domain_id, rows in sorted(domain_rows.items()):
            ids = [str(row["id"]) for row in rows]
            qa = content = sme = 0
            quality: list[float] = []
            provenance_verified = 0
            for question_id in ids:
                state = states.get(question_id)
                if state:
                    current = _latest_question_version_id(conn, question_id)
                    qa_ok = str(state["qa_status"]) == "passed" and int(state["qa_question_version_id"] or 0) == current
                    content_ok = str(state["content_review_status"]) == "approved" and int(state["content_review_question_version_id"] or 0) == current
                    sme_ok = str(state["sme_review_status"]) == "approved" and int(state["sme_review_question_version_id"] or 0) == current
                    qa += int(qa_ok)
                    content += int(content_ok)
                    sme += int(sme_ok)
                    if int(state["qa_question_version_id"] or 0) == current:
                        quality.append(float(state["qa_score"] or 0))
                if provenance_installed and _provenance_state(conn, track_id, question_id) == "verified":
                    provenance_verified += 1
            difficulty = Counter(str(row["difficulty"] or "unknown").lower() for row in rows)
            answer_positions = Counter()
            for row in rows:
                correct = _json_list(row["correct_json"])
                if correct:
                    try:
                        answer_positions[int(correct[0])] += 1
                    except Exception:
                        pass
            total = len(rows)
            domain_health[domain_id] = {
                "questions": total,
                "qa_pass_pct": round(qa / total * 100, 2) if total else 100.0,
                "content_approved_pct": round(content / total * 100, 2) if total else 100.0,
                "sme_approved_pct": round(sme / total * 100, 2) if total else 100.0,
                "avg_qa_score": round(sum(quality) / len(quality), 2) if quality else 0.0,
                "provenance_verified_pct": (round(provenance_verified / total * 100, 2) if provenance_installed and total else None),
                "difficulty_distribution": dict(sorted(difficulty.items())),
                "first_correct_position_distribution": {str(key): value for key, value in sorted(answer_positions.items())},
            }

        findings = conn.execute(
            """
            SELECT severity,COUNT(*) AS n
              FROM editorial_findings f
              JOIN editorial_qa_runs r ON r.id=f.qa_run_id
             WHERE r.track_id=? AND r.id=(SELECT MAX(id) FROM editorial_qa_runs WHERE track_id=?)
             GROUP BY severity
            """,
            (track_id, track_id),
        ).fetchall()
    finding_counts = {str(row["severity"]): int(row["n"]) for row in findings}
    return {
        "track_id": track_id,
        "questions": len(questions),
        "domains": domain_health,
        "latest_findings": {
            "blocker": finding_counts.get("blocker", 0),
            "warning": finding_counts.get("warning", 0),
            "info": finding_counts.get("info", 0),
        },
        "provenance_available": provenance_installed,
    }
