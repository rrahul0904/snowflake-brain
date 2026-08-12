#!/usr/bin/env python3
from __future__ import annotations

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

from app.main import app


def main() -> None:
    with TestClient(app) as client:
        skill_map = client.get("/api/skills/map")
        assert skill_map.status_code == 200, skill_map.text
        certifications = skill_map.json().get("certifications") or []
        assert certifications, "Certification map must expose at least one track"
        cert = certifications[0]
        track_id = cert["id"]
        skills = [skill for domain in cert.get("domains", []) for skill in domain.get("skills", [])]
        assert skills, f"{track_id} must expose task statements"
        skill_id = skills[0]["id"]

        before = client.get("/api/skills/task-progress", params={"track_id": track_id})
        assert before.status_code == 200, before.text
        assert before.json()["completed_tasks"] == 0

        completed = client.post(
            "/api/skills/task-progress",
            json={"track_id": track_id, "skill_id": skill_id, "completed": True},
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["completed"] is True

        after = client.get("/api/skills/task-progress", params={"track_id": track_id})
        assert after.status_code == 200, after.text
        assert skill_id in after.json()["completed_skill_ids"]
        assert after.json()["completed_tasks"] == 1

        cleared = client.post(
            "/api/skills/task-progress",
            json={"track_id": track_id, "skill_id": skill_id, "completed": False},
        )
        assert cleared.status_code == 200, cleared.text
        final = client.get("/api/skills/task-progress", params={"track_id": track_id})
        assert final.json()["completed_tasks"] == 0

        invalid = client.post(
            "/api/skills/task-progress",
            json={"track_id": track_id, "skill_id": "missing-skill", "completed": True},
        )
        assert invalid.status_code == 404, invalid.text

    print("Certification guide task progress smoke passed.")


if __name__ == "__main__":
    main()
