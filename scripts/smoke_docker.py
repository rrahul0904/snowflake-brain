#!/usr/bin/env python3
"""Exercise the deployed V26 application over HTTP without duplicating app logic."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
import uuid
import http.cookiejar
import subprocess
from pathlib import Path
from typing import Any


BASE_URL = os.getenv("BASE_URL", "http://localhost:8010").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))


def check(value: Any, message: str) -> None:
    if not value:
        raise AssertionError(message)


def request(path: str, method: str = "GET", payload: dict[str, Any] | None = None, extra_headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    headers.update(extra_headers or {})
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def request_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None, extra_headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
    status, body = request(path, method, payload, extra_headers)
    return status, json.loads(body)


def verify_persisted_state(state_path: Path) -> None:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    headers = {"Cookie": f"snowflake_candidate_session={state['session_token']}"}
    me_status, me = request_json("/api/auth/me", extra_headers=headers)
    check(me_status == 200 and me["authenticated"] and me["membership"]["tier"] == "premium", "session and membership persisted after restart")
    status, result = request_json(f"/api/mock/sessions/{state['session_id']}/result", extra_headers=headers)
    check(status == 200, f"persisted result unavailable: HTTP {status}")
    review = next(item for item in result["reviews"] if item["question_id"] == state["question_id"])
    check(review["selected"] == [0], "persisted answer changed after restart")
    check(review["flagged"] is True, "persisted flag changed after restart")
    print(
        "Docker persistence smoke: PASS "
        f"(session_id={state['session_id']}, question_id={state['question_id']})"
    )


def run_smoke(state_path: Path | None) -> None:
    status, health = request_json("/api/health")
    check(status == 200, f"health HTTP {status}")
    check(
        health
        == {
            "status": "ok",
            "product": "snowflake-certification-guide",
            "architecture": "certification-native-v26",
        },
        f"unexpected health response: {health}",
    )

    status, html = request("/")
    shell = html.decode()
    check(status == 200 and "app-complete.js" in shell, "V26 SPA shell")
    for stylesheet in (
        "tokens.css",
        "utilities.css",
        "shell.css",
        "home.css",
        "study.css",
        "practice.css",
        "mock.css",
        "content.css",
        "exam.css",
        "membership.css",
        "responsive.css",
        "accessibility.css",
    ):
        check(f"/static/styles/{stylesheet}" in shell, f"canonical stylesheet {stylesheet}")

    status, world = request_json("/static/assets/world-major-land.geojson")
    check(status == 200, "world geography HTTP response")
    check(world.get("geometry", {}).get("type") == "MultiPolygon", "real world geography payload")

    status, activity = request_json("/api/activity/globe")
    check(status == 200 and isinstance(activity.get("locations"), list), "globe activity API")
    check(activity.get("mode") in {"fallback", "live"}, "globe activity mode")
    if activity["mode"] == "fallback":
        check(activity["locations"] == [], "fallback must not fabricate learner cities")

    status, skill_map = request_json("/api/skills/map")
    check(status == 200, "certification API")
    certification = next(item for item in skill_map["certifications"] if item["id"] == "snowpro-core")
    domains = certification["domains"]
    check(len(domains) == 5, "five COF-C03 domains")
    check([int(item["weight"]) for item in domains] == [31, 20, 18, 21, 10], "domain weights")
    check(sum(len(item["skills"]) for item in domains) == 19, "nineteen task statements")
    status, catalog = request_json("/api/skills/catalog")
    focused = [(row["id"], row["exam_code"], row["launchable"]) for row in catalog["official_certifications"]]
    check(focused == [("snowpro-core", "COF-C03", True), ("advanced-data-engineer", "DEA-C02", False), ("advanced-architect", "ARA-C01", False)], f"focused certification catalog: {focused}")

    status, config = request_json("/api/mock/config?track_id=snowpro-core")
    check(status == 200, "mock config")
    check(config["quick_mock"]["question_count"] == 30, "Quick Mock question count")
    check(config["quick_mock"]["time_limit_minutes"] == 45, "Quick Mock duration")
    check(config["full_mock"]["question_count"] == 100, "Full Mock question count")
    check(config["full_mock"]["time_limit_minutes"] == 120, "Full Mock duration")
    check(config["pass_scaled_score"] == 750, "practice threshold")

    guest_status, guest = request_json("/api/mock/sessions", "POST", {"track_id": "snowpro-core", "mode": "quick-mock"})
    check(guest_status == 401, f"guest mock gate: {guest}")
    suffix = uuid.uuid4().hex
    email = f"docker-smoke-{suffix}@example.com"
    password = f"docker-smoke-{suffix}"
    status, signup = request_json(
        "/api/auth/register",
        "POST",
        {"display_name": "Docker Smoke Candidate", "email": email, "password": password},
    )
    check(status == 201 and signup["membership"]["tier"] == "free", f"free candidate signup: {signup}")
    check(signup["membership"]["usage"]["daily_questions"]["limit"] == 20, "Free daily question allowance")
    check(signup["membership"]["usage"]["weekly_mocks"]["limit"] == 1, "Free weekly mock allowance")
    free_status, _ = request_json(
        "/api/mock/sessions", "POST", {"track_id": "snowpro-core", "mode": "quick-mock"}
    )
    check(free_status == 403, "Free plan must not start Premium mocks")
    override = subprocess.run(
        ["docker", "compose", "exec", "-T", "snowflake-certification-guide", "python", "scripts/set_membership.py", email, "premium_20"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    check(override.returncode == 0, f"development membership CLI: {override.stderr or override.stdout}")
    status, upgraded = request_json("/api/auth/me")
    check(status == 200 and upgraded["membership"]["plan_code"] == "premium_20", f"Premium CLI activation: {upgraded}")

    status, session = request_json(
        "/api/mock/sessions", "POST", {"track_id": "snowpro-core", "mode": "quick-mock"}
    )
    check(status == 200, f"create Quick Mock: {session}")
    check(len(session["questions"]) == 30, "Quick Mock must contain exactly 30 questions")
    first = session["questions"][0]
    check("correct" not in first and "explanation" not in first, "pre-submit answer leakage")

    result_status, _ = request_json(f"/api/mock/sessions/{session['session_id']}/result")
    check(result_status == 409, "result must remain hidden before submission")

    status, _ = request_json(
        f"/api/mock/sessions/{session['session_id']}/answers/{first['id']}", "PUT", {"selected": [0]}
    )
    check(status == 200, "answer autosave")
    status, _ = request_json(
        f"/api/mock/sessions/{session['session_id']}/questions/{first['id']}/flag", "PUT", {"flagged": True}
    )
    check(status == 200, "question flag")

    status, resumed = request_json(f"/api/mock/sessions/{session['session_id']}")
    check(status == 200, "session reload")
    resumed_question = next(item for item in resumed["questions"] if item["id"] == first["id"])
    check(resumed_question["selected"] == [0], "answer persisted on reload")
    check(resumed_question["flagged"] is True, "flag persisted on reload")

    status, result = request_json(
        f"/api/mock/sessions/{session['session_id']}/submit", "POST", {"reason": "learner"}
    )
    check(status == 200, f"mock submit: {result}")
    check(len(result["reviews"]) == 30, "submitted review count")
    check("correct" in result["reviews"][0] and "explanation" in result["reviews"][0], "post-submit grading reveal")

    if state_path:
        state_path.write_text(
            json.dumps(
                {
                    "session_id": session["session_id"],
                    "question_id": first["id"],
                    "email": email,
                    "password": password,
                    "session_token": next(cookie.value for cookie in COOKIE_JAR if cookie.name == "snowflake_candidate_session"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    status, feedback = request_json(
        "/api/feedback",
        "POST",
        {
            "title": "Docker V26 smoke",
            "category": "other",
            "description": "Container-hosted end-to-end verification",
            "route": "#/home",
            "track_id": "snowpro-core",
        },
    )
    check(status == 200 and feedback.get("ok") is True, "feedback submission")

    print(
        "Docker V26 HTTP smoke: PASS "
        f"(candidate_id={signup['candidate']['id']}, tier=premium, session_id={session['session_id']}, feedback_id={feedback['feedback_id']}, "
        f"activity_mode={activity['mode']}, activity_locations={len(activity['locations'])})"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-file", type=Path, help="record submitted sitting state for restart verification")
    parser.add_argument("--verify-state", type=Path, help="verify a previously recorded sitting after restart")
    args = parser.parse_args()
    if args.verify_state:
        verify_persisted_state(args.verify_state)
    else:
        run_smoke(args.state_file)


if __name__ == "__main__":
    main()
