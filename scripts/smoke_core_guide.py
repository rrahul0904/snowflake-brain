from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = ROOT / "config" / "snowpro_core_cof_c03_blueprint.json"
CONTENT = ROOT / "config" / "study_content_core.json"

EXPECTED_WEIGHTS = [31, 20, 18, 21, 10]
EXPECTED_CODES = [
    "1.1", "1.2", "1.3", "1.4", "1.5", "1.6",
    "2.1", "2.2", "2.3",
    "3.1", "3.2", "3.3",
    "4.1", "4.2", "4.3", "4.4",
    "5.1", "5.2", "5.3",
]
REQUIRED_FIELDS = {
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
FORBIDDEN_LEARNER_TERMS = ("video", "transcript", "course archive", "watch related lessons")


def fail(message: str) -> None:
    raise SystemExit(f"COF-C03 guide smoke failed: {message}")


def load(path: Path) -> dict:
    if not path.exists():
        fail(f"missing {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    blueprint = load(BLUEPRINT)
    content = load(CONTENT)

    if blueprint.get("track_id") != "snowpro-core" or blueprint.get("exam_code") != "COF-C03":
        fail("blueprint must identify snowpro-core / COF-C03")
    if content.get("track_id") != "snowpro-core" or content.get("exam_code") != "COF-C03":
        fail("study content must identify snowpro-core / COF-C03")

    domains = blueprint.get("domains") or []
    weights = [int(domain.get("weight") or 0) for domain in domains]
    if len(domains) != 5:
        fail(f"expected 5 COF-C03 domains, found {len(domains)}")
    if weights != EXPECTED_WEIGHTS or sum(weights) != 100:
        fail(f"expected weights {EXPECTED_WEIGHTS}, found {weights}")

    tasks = [skill for domain in domains for skill in (domain.get("skills") or [])]
    task_ids = [str(skill.get("id") or "") for skill in tasks]
    task_codes = [str(skill.get("task_code") or "") for skill in tasks]
    if len(tasks) != 19 or len(set(task_ids)) != 19:
        fail(f"expected 19 unique tasks, found {len(tasks)} / {len(set(task_ids))} unique")
    if task_codes != EXPECTED_CODES:
        fail(f"task codes differ from canonical sequence: {task_codes}")

    lessons = content.get("skills") or {}
    missing = sorted(set(task_ids) - set(lessons))
    stale = sorted(set(lessons) - set(task_ids))
    if missing:
        fail(f"missing curated lessons: {missing}")
    if stale:
        fail(f"stale/non-blueprint lessons remain: {stale}")

    for task in tasks:
        skill_id = task["id"]
        lesson = lessons[skill_id]
        absent = sorted(REQUIRED_FIELDS - set(lesson))
        if absent:
            fail(f"{skill_id} missing fields: {absent}")
        if len(lesson.get("what_you_need_to_know") or []) < 5:
            fail(f"{skill_id} needs at least 5 knowledge bullets")
        if len(lesson.get("decision_rules") or []) < 3:
            fail(f"{skill_id} needs at least 3 decision rules")
        if len(lesson.get("anti_patterns") or []) < 2:
            fail(f"{skill_id} needs at least 2 anti-patterns")
        if len(lesson.get("trap_explanations") or []) < 2:
            fail(f"{skill_id} needs at least 2 trap explanations")

        worked = lesson.get("worked_example") or {}
        if not worked.get("scenario") or len(worked.get("reasoning") or []) < 2 or not worked.get("answer"):
            fail(f"{skill_id} has an incomplete worked example")

        scenario = lesson.get("scenario") or {}
        options = scenario.get("options") or []
        correct = scenario.get("correct_index")
        if not scenario.get("question") or len(options) < 4 or not isinstance(correct, int) or not 0 <= correct < len(options):
            fail(f"{skill_id} has an invalid practice scenario")
        if not scenario.get("explanation"):
            fail(f"{skill_id} practice scenario lacks explanation")

        exercise = lesson.get("build_exercise") or {}
        if not exercise.get("title") or not exercise.get("prompt") or len(exercise.get("checks") or []) < 2:
            fail(f"{skill_id} has an incomplete build exercise")

        sources = lesson.get("sources") or []
        if not sources:
            fail(f"{skill_id} has no Snowflake source")
        for source in sources:
            url = str(source.get("url") or "")
            if not (url.startswith("https://docs.snowflake.com/") or url.startswith("https://learn.snowflake.com/")):
                fail(f"{skill_id} has non-Snowflake source: {url}")

        serialized = json.dumps(lesson, ensure_ascii=False).lower()
        for forbidden in FORBIDDEN_LEARNER_TERMS:
            if forbidden in serialized:
                fail(f"{skill_id} reintroduced forbidden learner concept: {forbidden}")

    # Import after file-level validation so the app-level overlay is tested too.
    from app.skill_brain import load_skill_map

    skill_map = load_skill_map()
    core = next((cert for cert in skill_map.get("certifications", []) if cert.get("id") == "snowpro-core"), None)
    if not core:
        fail("snowpro-core disappeared from configured skill map")
    app_domains = core.get("domains") or []
    app_ids = [skill.get("id") for domain in app_domains for skill in (domain.get("skills") or [])]
    if [int(domain.get("weight") or 0) for domain in app_domains] != EXPECTED_WEIGHTS:
        fail("application skill-map overlay is not using canonical COF-C03 weights")
    if app_ids != task_ids:
        fail("application skill-map overlay is not using canonical 19-task COF-C03 IDs")

    print(
        "COF-C03 full guide smoke passed: "
        f"5 domains, {len(tasks)} curated tasks, weights={weights}, content={content.get('version')}."
    )


if __name__ == "__main__":
    main()
