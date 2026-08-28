#!/usr/bin/env python3
"""Low-impact authenticated black-box verification for a hosted deployment.

Requires two dedicated test accounts supplied through secrets. The default run
performs ownership, entitlement-tampering, cache, retired-route, CSRF, and
session-revocation checks without consuming question inventory. Set
EXERCISE_LIVE_BANK=true only for the final production release proof; that mode
consumes one legitimate drill question from the victim test account and records
no question wording or IDs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "live-hostile-subscriber.json"
BASE = os.environ.get("SECURITY_BASE_URL", "https://snowflakecertificationguide.vercel.app").rstrip("/")
ATTACKER_EMAIL = os.environ.get("SECURITY_TEST_ATTACKER_EMAIL", "").strip()
ATTACKER_PASSWORD = os.environ.get("SECURITY_TEST_ATTACKER_PASSWORD", "")
VICTIM_EMAIL = os.environ.get("SECURITY_TEST_VICTIM_EMAIL", "").strip()
VICTIM_PASSWORD = os.environ.get("SECURITY_TEST_VICTIM_PASSWORD", "")
EXERCISE_LIVE_BANK = os.environ.get("EXERCISE_LIVE_BANK", "false").strip().lower() in {"1", "true", "yes", "on"}

FORBIDDEN_KEYS = {
    "correct",
    "correct_json",
    "correct_options",
    "correct_positions_json",
    "answer_key",
    "solution",
    "explanation",
    "rationale",
    "correct_rationale",
    "distractor_rationales",
    "distractor_rationales_json",
    "expected_answer",
    "grading",
    "score_key",
    "editorial_answer",
    "sme_notes",
    "review_notes",
}
FORBIDDEN_FRAGMENTS = (
    "correct_answer",
    "correct_option",
    "answer_key",
    "solution",
    "explanation",
    "rationale",
    "expected_answer",
    "grading",
    "score_key",
    "editorial_answer",
    "sme_note",
    "review_note",
)


def private_no_store(response: httpx.Response) -> bool:
    value = response.headers.get("cache-control", "").lower()
    return "private" in value and "no-store" in value


def has_answer_material(value: object) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_KEYS or any(fragment in lowered for fragment in FORBIDDEN_FRAGMENTS):
                return True
            if has_answer_material(child):
                return True
    elif isinstance(value, list):
        return any(has_answer_material(item) for item in value)
    return False


def login(client: httpx.Client, email: str, password: str) -> bool:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return response.status_code == 200


def plan_code(me: dict) -> str:
    candidate = me.get("candidate") or {}
    membership = me.get("membership") or {}
    return str(candidate.get("plan_code") or membership.get("plan_code") or membership.get("code") or "").lower()


def first_skill_id(payload: dict) -> str:
    for certification in payload.get("certifications") or []:
        for domain in certification.get("domains") or []:
            skills = domain.get("skills") or []
            if skills:
                return str(skills[0].get("id") or "")
    return ""


def main() -> None:
    required = (ATTACKER_EMAIL, ATTACKER_PASSWORD, VICTIM_EMAIL, VICTIM_PASSWORD)
    if not all(required):
        raise SystemExit("Dedicated attacker/victim production test credentials are required")

    findings: list[str] = []
    checks: dict[str, object] = {}
    timeout = httpx.Timeout(20.0)

    with (
        httpx.Client(base_url=BASE, follow_redirects=False, timeout=timeout) as attacker,
        httpx.Client(base_url=BASE, follow_redirects=False, timeout=timeout) as victim,
        httpx.Client(base_url=BASE, follow_redirects=False, timeout=timeout) as secondary,
    ):
        if not login(attacker, ATTACKER_EMAIL, ATTACKER_PASSWORD):
            findings.append("attacker_login_failed")
        if not login(victim, VICTIM_EMAIL, VICTIM_PASSWORD):
            findings.append("victim_login_failed")
        if findings:
            write_result(findings, checks)
            return

        attacker_me = attacker.get("/api/auth/me")
        victim_me = victim.get("/api/auth/me")
        if attacker_me.status_code != 200 or not attacker_me.json().get("authenticated"):
            findings.append("attacker_session_not_authenticated")
        if victim_me.status_code != 200 or not victim_me.json().get("authenticated"):
            findings.append("victim_session_not_authenticated")
        checks["attacker_plan"] = plan_code(attacker_me.json()) if attacker_me.status_code == 200 else "unknown"
        checks["victim_plan"] = plan_code(victim_me.json()) if victim_me.status_code == 200 else "unknown"

        skill_map = attacker.get("/api/skills/map")
        checks["candidate_cache_private_no_store"] = skill_map.status_code == 200 and private_no_store(skill_map)
        if not checks["candidate_cache_private_no_store"]:
            findings.append("candidate_response_cache_policy_failed")
        skill_id = first_skill_id(skill_map.json()) if skill_map.status_code == 200 else ""
        if not skill_id:
            findings.append("skill_map_unavailable")
        else:
            resources = attacker.get(f"/api/skills/{skill_id}/resources", params={"track_id": "snowpro-core", "limit": 50})
            safe_resources = (
                resources.status_code == 200
                and resources.json().get("questions") == []
                and resources.json().get("mapping_strategy") == "candidate_delivery_only"
                and not has_answer_material(resources.json())
            )
            checks["skill_resource_inventory_closed"] = safe_resources
            if not safe_resources:
                findings.append("skill_resource_inventory_or_answer_leak")

        retired_checks = {
            "adaptive_question_ids": attacker.get("/api/intelligence/adaptive/question-ids?limit=100").status_code,
            "evidence_audit": attacker.get("/api/intelligence/evidence-audit").status_code,
            "evidence_review": attacker.post("/api/intelligence/evidence-review", json={"question_id": "probe", "skill_id": skill_id or "probe", "reviewed": True}).status_code,
            "evidence_reindex": attacker.post("/api/intelligence/reindex-skill-map").status_code,
        }
        checks["retired_candidate_admin_routes"] = retired_checks
        if any(status != 404 for status in retired_checks.values()):
            findings.append("retired_candidate_admin_route_reachable")

        cross_site = attacker.post(
            "/api/account/change-email/request",
            headers={"Origin": "https://attacker.invalid", "Sec-Fetch-Site": "cross-site"},
            json={"new_email": "blocked-change@example.invalid"},
        )
        checks["cross_site_mutation_status"] = cross_site.status_code
        if cross_site.status_code != 403:
            findings.append("cross_site_mutation_not_blocked")

        if checks.get("attacker_plan") not in {"free", "free_v1", ""}:
            findings.append("attacker_test_account_must_be_free")
        else:
            overflow = attacker.post(
                "/api/certification-quiz/start",
                json={"track_id": "snowpro-core", "mode": "drill", "count": 21, "plan_code": "premium_500", "is_premium": True},
            )
            checks["forged_practice_entitlement_status"] = overflow.status_code
            if overflow.status_code != 403:
                findings.append("forged_practice_entitlement_not_denied")
            oversized = attacker.post(
                "/api/certification-quiz/start",
                json={"track_id": "snowpro-core", "mode": "drill", "count": 501},
            )
            checks["oversized_practice_status"] = oversized.status_code
            if oversized.status_code != 422:
                findings.append("oversized_practice_count_not_rejected")
            forged_mock = attacker.post(
                "/api/mock/sessions",
                json={"track_id": "snowpro-core", "mode": "full-mock", "plan_code": "premium_500", "is_premium": True, "membership": {"tier": "premium"}},
            )
            checks["forged_full_mock_status"] = forged_mock.status_code
            if forged_mock.status_code != 403:
                findings.append("forged_full_mock_entitlement_not_denied")

        before_sessions = victim.get("/api/auth/sessions")
        before_ids = {int(row["id"]) for row in (before_sessions.json().get("sessions") or [])} if before_sessions.status_code == 200 else set()
        if not login(secondary, VICTIM_EMAIL, VICTIM_PASSWORD):
            findings.append("victim_secondary_login_failed")
        else:
            after_sessions = victim.get("/api/auth/sessions")
            after_rows = after_sessions.json().get("sessions") or [] if after_sessions.status_code == 200 else []
            new_ids = [int(row["id"]) for row in after_rows if int(row["id"]) not in before_ids]
            if not new_ids:
                findings.append("victim_secondary_session_not_resolved")
            else:
                secondary_id = new_ids[0]
                denied = attacker.delete(f"/api/auth/sessions/{secondary_id}")
                checks["cross_candidate_session_revoke_status"] = denied.status_code
                if denied.status_code != 404:
                    findings.append("cross_candidate_session_revoke_succeeded")
                if secondary.get("/api/skills/map").status_code != 200:
                    findings.append("denied_attack_changed_victim_session")
                cleanup = victim.delete(f"/api/auth/sessions/{secondary_id}")
                if cleanup.status_code != 200 or secondary.get("/api/skills/map").status_code != 401:
                    findings.append("owner_session_revocation_failed")

        if EXERCISE_LIVE_BANK:
            one = victim.post(
                "/api/certification-quiz/start",
                json={"track_id": "snowpro-core", "mode": "drill", "count": 1},
            )
            checks["live_bank_delivery_status"] = one.status_code
            if one.status_code != 200 or len(one.json().get("questions") or []) != 1:
                findings.append("live_bank_one_question_delivery_failed")
            else:
                questions = one.json().get("questions") or []
                if has_answer_material(questions):
                    findings.append("live_pre_submit_answer_material")
                question_id = str(questions[0].get("id") or "")
                guessed = attacker.get(f"/api/questions/{question_id}")
                grade = attacker.post("/api/quiz/grade", json={"answers": [{"question_id": question_id, "selected": [0]}]})
                attempt = attacker.post(
                    f"/api/questions/{question_id}/attempt",
                    json={"selected": [0], "mode": "drill", "confidence": 5, "response_time_ms": 500},
                )
                checks["cross_candidate_question_status"] = guessed.status_code
                checks["cross_candidate_grade_status"] = grade.status_code
                checks["cross_candidate_attempt_status"] = attempt.status_code
                if guessed.status_code != 404 or grade.status_code != 404 or attempt.status_code != 404:
                    findings.append("live_question_id_oracle_or_cross_candidate_access")
                if has_answer_material(safe_json(guessed)) or has_answer_material(safe_json(grade)):
                    findings.append("live_denial_answer_metadata_leak")
        else:
            checks["live_bank_exercise"] = "not_requested"

    write_result(findings, checks)


def safe_json(response: httpx.Response) -> object:
    try:
        return response.json()
    except Exception:
        return {}


def write_result(findings: list[str], checks: dict[str, object]) -> None:
    payload = {
        "status": "pass" if not findings else "fail",
        "base_url": BASE,
        "live_bank_exercised": EXERCISE_LIVE_BANK,
        "checks": checks,
        "finding_count": len(findings),
        "findings": sorted(set(findings)),
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if findings:
        raise SystemExit("Live hostile-subscriber verification failed")


if __name__ == "__main__":
    main()
