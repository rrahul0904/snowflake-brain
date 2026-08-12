#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_tmp = tempfile.TemporaryDirectory(prefix="snowflake-guide-smoke-")
os.environ["BRAIN_DB"] = str(Path(_tmp.name) / "guide.sqlite")
os.environ["AUTO_INGEST"] = "false"

from fastapi.testclient import TestClient

from app.database import connect
from app.main import app

REQUIRED_CONTENT_KEYS = {
    "summary",
    "what_you_need_to_know",
    "key_concept",
    "decision_rules",
    "anti_patterns",
    "trap_explanations",
    "worked_example",
    "scenario",
    "build_exercise",
    "sources",
}


def seed_questions() -> None:
    samples = [
        ("q-rbac-1", "rbac-role-hierarchy", "account-security", "Which RBAC design follows least privilege?"),
        ("q-auth-1", "network-policy-authentication", "account-security", "Which control restricts allowed network origins?"),
        ("q-wh-1", "warehouse-cost-control", "virtual-warehouses", "Which warehouse change best addresses concurrency queueing?"),
        ("q-perf-1", "query-performance-history", "virtual-warehouses", "What should you inspect for poor pruning?"),
        ("q-copy-1", "stage-file-format-copy", "data-loading", "Which object stores reusable CSV parsing rules?"),
        ("q-pipe-1", "snowpipe-continuous-load", "data-loading", "Which service continuously loads new cloud files?"),
        ("q-var-1", "variant-flatten-json", "semi-structured-data", "Which table function expands a JSON array?"),
        ("q-tt-1", "time-travel-clone-failsafe", "continuity-governance-sharing", "Which feature queries historical data in retention?"),
        ("q-share-1", "secure-sharing-governance", "continuity-governance-sharing", "How do accounts share live governed data without copies?"),
        ("q-stream-1", "streams-tasks-incremental", "data-pipelines", "Which object exposes changed rows?"),
    ]
    with connect() as conn:
        conn.execute("INSERT INTO certification_tracks(id, title, description, position) VALUES ('snowpro-core','SnowPro Core','',1)")
        conn.execute("INSERT INTO courses(id, track_id, track_title, title) VALUES ('smoke-core','snowpro-core','SnowPro Core','Smoke Certification Questions')")
        for index, (qid, skill_id, domain_id, question) in enumerate(samples):
            conn.execute(
                """
                INSERT INTO questions(id, course_id, course_title, test_id, test_title, question, options_json, correct_json, explanation, source_path, assessment_type, tags, difficulty, question_position)
                VALUES (?, 'smoke-core', 'Smoke Certification Questions', '', 'Certification Bank', ?, ?, '[0]', ?, '', 'multiple_choice', ?, 'medium', ?)
                """,
                (qid, question, json.dumps(["Correct", "Distractor A", "Distractor B", "Distractor C"]), f"Explanation for {skill_id} with sufficient detail.", skill_id.replace("-", " "), index + 1),
            )
            conn.execute(
                """
                INSERT INTO question_skill_map(question_id, track_id, domain_id, skill_id, confidence, evidence_json, reviewed)
                VALUES (?, 'snowpro-core', ?, ?, 0.99, '{"source":"smoke"}', 1)
                """,
                (qid, domain_id, skill_id),
            )


def main() -> None:
    with TestClient(app) as client:
        catalog_response = client.get("/api/skills/catalog")
        assert catalog_response.status_code == 200, catalog_response.text
        catalog = catalog_response.json()
        by_id = {item["id"]: item for item in catalog.get("official_certifications", [])}
        assert by_id["snowpro-core"]["exam_code"] == "COF-C03"
        assert by_id["snowpark"]["exam_code"] == "SPS-C01"
        assert by_id["cortex-genai"]["exam_code"] == "GES-C01"
        assert by_id["advanced-data-engineer"]["exam_code"] == "DEA-C02"
        assert any(item.get("category") == "custom" for item in catalog.get("custom_tracks", []))

        skill_map = client.get("/api/skills/map")
        assert skill_map.status_code == 200, skill_map.text
        certifications = skill_map.json().get("certifications") or []
        assert certifications, "Certification map must expose at least one track"
        mapped = {cert["id"]: cert for cert in certifications}
        assert mapped["snowpark"]["exam_code"] == "SPS-C01"
        assert mapped["cortex-genai"]["exam_code"] == "GES-C01"
        assert mapped["advanced-data-engineer"]["exam_code"] == "DEA-C02"

        coverage = client.get("/api/skills/content-coverage")
        assert coverage.status_code == 200, coverage.text
        coverage_body = coverage.json()
        core_coverage = next(row for row in coverage_body["tracks"] if row["track_id"] == "snowpro-core")
        assert core_coverage["tasks"] == 10
        assert core_coverage["curated_tasks"] == 10
        assert all(row["usable_tasks"] == row["tasks"] for row in coverage_body["tracks"])

        for cert in certifications:
            for domain in cert.get("domains", []):
                for skill in domain.get("skills", []):
                    lesson = client.get(f"/api/skills/{skill['id']}/lesson", params={"track_id": cert["id"]})
                    assert lesson.status_code == 200, (cert["id"], skill["id"], lesson.text)
                    body = lesson.json()
                    assert REQUIRED_CONTENT_KEYS.issubset(body["content"]), (cert["id"], skill["id"], body["content"].keys())
                    assert body["content"]["what_you_need_to_know"]
                    assert body["content"]["sources"]
                    if cert["id"] == "snowpro-core":
                        assert body["content_quality"] == "curated"

        cert = mapped["snowpro-core"]
        track_id = cert["id"]
        skills = [skill for domain in cert.get("domains", []) for skill in domain.get("skills", [])]
        skill_id = skills[0]["id"]

        before = client.get("/api/skills/task-progress", params={"track_id": track_id})
        assert before.status_code == 200 and before.json()["completed_tasks"] == 0
        completed = client.post("/api/skills/task-progress", json={"track_id": track_id, "skill_id": skill_id, "completed": True})
        assert completed.status_code == 200 and completed.json()["completed"] is True
        after = client.get("/api/skills/task-progress", params={"track_id": track_id})
        assert skill_id in after.json()["completed_skill_ids"]

        seed_questions()

        targeted = client.post("/api/certification-quiz/start", json={"track_id": track_id, "mode": "drill", "skill_id": "warehouse-cost-control", "count": 1})
        assert targeted.status_code == 200, targeted.text
        assert targeted.json()["selection_strategy"] == "skill_targeted"
        assert targeted.json()["total"] == 1
        assert "warehouse-cost-control" in targeted.json()["skill_ids"]
        assert targeted.json()["mapping_provenance"].get("human_reviewed") == 1

        diagnostic = client.post("/api/certification-quiz/start", json={"track_id": track_id, "mode": "diagnostic", "count": 10})
        assert diagnostic.status_code == 200, diagnostic.text
        assert diagnostic.json()["selection_strategy"] == "domain_balanced"
        assert len(diagnostic.json()["domain_counts"]) >= 5

        mock = client.post("/api/certification-quiz/start", json={"track_id": track_id, "mode": "full-mock", "count": 10})
        assert mock.status_code == 200, mock.text
        assert mock.json()["selection_strategy"] == "blueprint_weighted"
        assert mock.json()["total"] == 10

        mock_record = client.post("/api/certification-mock/record", json={"track_id": track_id, "mode": "full-mock", "score": 8, "total": 10, "elapsed_seconds": 600, "selection_strategy": "blueprint_weighted"})
        assert mock_record.status_code == 200, mock_record.text
        assert mock_record.json()["score_pct"] == 80

        readiness = client.get("/api/intelligence/readiness", params={"track_id": track_id})
        assert readiness.status_code == 200, readiness.text
        readiness_body = readiness.json()
        assert readiness_body["mock_exam_attempts"] == 1
        assert readiness_body["best_mock_score"] == 80
        assert "readiness_confidence" in readiness_body
        assert "readiness_confidence_status" in readiness_body

        mastery = client.get("/api/intelligence/skill-mastery", params={"track_id": track_id})
        assert mastery.status_code == 200, mastery.text
        mastery_body = mastery.json()
        assert mastery_body["mapping_stats"].get("human_reviewed") == 10
        first = next(item for item in mastery_body["skills"] if item["skill_id"] == skill_id)
        assert first["task_completed"] is True
        assert "task_content_available" in first["evidence"]
        assert "lesson_count" not in first
        assert "completed_lessons" not in first

        invalid = client.post("/api/skills/task-progress", json={"track_id": track_id, "skill_id": "missing-skill", "completed": True})
        assert invalid.status_code == 404, invalid.text

    print("Complete Snowflake certification product smoke passed.")


if __name__ == "__main__":
    main()
