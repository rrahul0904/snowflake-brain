from __future__ import annotations

import copy
import json
from functools import lru_cache
from typing import Any

from .config import CERTIFICATION_CATALOG_CONFIG, STUDY_CONTENT_CORE_CONFIG
from .skill_brain import load_skill_map


@lru_cache(maxsize=1)
def load_certification_catalog() -> dict[str, Any]:
    if not CERTIFICATION_CATALOG_CONFIG.exists():
        return {"version": "missing", "official_certifications": [], "custom_tracks": []}
    return json.loads(CERTIFICATION_CATALOG_CONFIG.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_core_study_content() -> dict[str, Any]:
    if not STUDY_CONTENT_CORE_CONFIG.exists():
        return {"version": "missing", "track_id": "snowpro-core", "skills": {}}
    return json.loads(STUDY_CONTENT_CORE_CONFIG.read_text(encoding="utf-8"))


def _catalog_by_track() -> dict[str, dict[str, Any]]:
    catalog = load_certification_catalog()
    rows = list(catalog.get("official_certifications") or []) + list(catalog.get("custom_tracks") or [])
    return {
        str(row.get("configured_track_id") or row.get("id") or ""): row
        for row in rows
        if row.get("configured_track_id") or row.get("id")
    }


def certification_catalog() -> dict[str, Any]:
    configured = {item.get("id") for item in (load_skill_map().get("certifications") or [])}
    catalog = copy.deepcopy(load_certification_catalog())
    for group in ("official_certifications", "custom_tracks"):
        for row in catalog.get(group) or []:
            track_id = row.get("configured_track_id")
            row["implemented"] = bool(track_id and track_id in configured)
            row["launchable"] = bool(row["implemented"] and row.get("status") == "available")
    return catalog


def configured_skill_map() -> dict[str, Any]:
    """Return the configured curriculum with current catalog metadata overlaid.

    Curriculum/domain/skill content remains versioned in certification_skill_map.json,
    while current public exam names/codes/status are controlled by the catalog.
    """
    skill_map = copy.deepcopy(load_skill_map())
    catalog_by_track = _catalog_by_track()
    for cert in skill_map.get("certifications") or []:
        official = catalog_by_track.get(str(cert.get("id") or ""))
        if not official:
            cert["official"] = False
            cert["catalog_status"] = "custom"
            continue
        cert["title"] = official.get("title") or cert.get("title")
        cert["exam_code"] = official.get("exam_code") or cert.get("exam_code")
        cert["official"] = official.get("category") != "custom"
        cert["catalog_status"] = official.get("status") or "available"
        cert["level"] = official.get("level")
        cert["candidate_experience"] = official.get("candidate_experience")
        cert["official_overview"] = official.get("overview") or []
        cert["official_source_url"] = official.get("source_url")
        cert["simulation"] = official.get("simulation") or {
            "quick_questions": 30,
            "full_questions": 65,
            "seconds_per_question": 120,
        }
    skill_map["catalog_version"] = load_certification_catalog().get("version")
    return skill_map


def _find_skill(track_id: str, skill_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    for cert in configured_skill_map().get("certifications") or []:
        if cert.get("id") != track_id:
            continue
        for domain in cert.get("domains") or []:
            for skill in domain.get("skills") or []:
                if skill.get("id") == skill_id:
                    return cert, domain, skill
    return None, None, None


def _fallback_lesson(cert: dict[str, Any], domain: dict[str, Any], skill: dict[str, Any]) -> dict[str, Any]:
    aliases = list(skill.get("aliases") or [])
    traps = list(skill.get("exam_traps") or [])
    objective = skill.get("objective") or f"Understand and apply {skill.get('title') or skill.get('id')} in Snowflake scenarios."
    terms = aliases[:6]
    trap_explanations = [
        {
            "trap": trap,
            "correction": f"Use the documented behavior and task objective for {skill.get('title')}; reject answers that violate the feature boundary or decision rule.",
        }
        for trap in traps
    ]
    return {
        "generated": True,
        "summary": objective,
        "what_you_need_to_know": [
            objective,
            f"Recognize the Snowflake terms that commonly signal this task: {', '.join(terms)}." if terms else "Recognize the feature boundaries and vocabulary used in scenario questions.",
            "Distinguish what the feature is designed to solve from adjacent Snowflake capabilities.",
            "Choose the option that satisfies the requirement with the least unnecessary privilege, cost, movement, or operational complexity.",
        ],
        "key_concept": f"The exam is testing whether you can apply {skill.get('title')} in context, not simply recognize its name.",
        "decision_rules": [
            {
                "when": f"A scenario explicitly matches the objective for {skill.get('title')}",
                "choose": skill.get("title") or skill.get("id"),
                "why": objective,
            },
            {
                "when": "Two Snowflake features appear plausible",
                "choose": "The feature whose documented responsibility directly matches the requirement",
                "why": "Certification distractors often rely on nearby features that solve a different layer of the problem.",
            },
        ],
        "anti_patterns": traps or ["Choosing a feature because the keyword is familiar without checking the scenario requirement."],
        "trap_explanations": trap_explanations,
        "worked_example": {
            "scenario": f"A certification scenario asks you to choose an approach involving {skill.get('title')}.",
            "reasoning": [
                "Identify the exact requirement and constraint.",
                "Eliminate options that solve a different Snowflake concern.",
                f"Apply the objective: {objective}",
            ],
            "answer": f"Choose the option that correctly applies {skill.get('title')} with the stated constraints.",
        },
        "scenario": {
            "question": f"Which approach best demonstrates correct use of {skill.get('title')}?",
            "options": [
                f"Apply {skill.get('title')} only when its documented responsibility matches the requirement",
                "Choose the most privileged administrative option regardless of the requirement",
                "Move data out of Snowflake even when the requirement can be satisfied in place",
                "Increase compute without first identifying the bottleneck",
            ],
            "correct_index": 0,
            "explanation": f"The correct choice follows the documented objective for this task: {objective}",
        },
        "build_exercise": {
            "title": f"Apply {skill.get('title')}",
            "prompt": f"Write or describe a Snowflake implementation that satisfies this task objective: {objective}",
            "starter_sql": "-- Describe or write the Snowflake implementation here.\n",
            "checks": ["The solution directly addresses the task objective", "The solution avoids the listed exam traps", "The reasoning explains why adjacent alternatives are less appropriate"],
        },
        "sources": [
            {"title": "Snowflake Documentation", "url": "https://docs.snowflake.com/"},
            *([{"title": f"Official {cert.get('title')} certification page", "url": cert.get("official_source_url")}]
              if cert.get("official_source_url") else []),
        ],
    }


def study_lesson(track_id: str, skill_id: str) -> dict[str, Any] | None:
    cert, domain, skill = _find_skill(track_id, skill_id)
    if not cert or not domain or not skill:
        return None
    curated = None
    if track_id == (load_core_study_content().get("track_id") or "snowpro-core"):
        curated = (load_core_study_content().get("skills") or {}).get(skill_id)
    content = copy.deepcopy(curated) if curated else _fallback_lesson(cert, domain, skill)
    return {
        "track_id": track_id,
        "certification": {
            "id": cert.get("id"),
            "title": cert.get("title"),
            "exam_code": cert.get("exam_code"),
            "official": cert.get("official", False),
            "source_url": cert.get("official_source_url"),
        },
        "domain": {
            "id": domain.get("id"),
            "title": domain.get("title"),
            "weight": domain.get("weight", 0),
        },
        "skill": skill,
        "content": content,
        "content_quality": "curated" if curated else "generated_from_curriculum",
        "content_version": load_core_study_content().get("version") if curated else configured_skill_map().get("version"),
    }


def content_coverage() -> dict[str, Any]:
    rows = []
    for cert in configured_skill_map().get("certifications") or []:
        total = 0
        curated = 0
        for domain in cert.get("domains") or []:
            for skill in domain.get("skills") or []:
                total += 1
                if cert.get("id") == "snowpro-core" and skill.get("id") in (load_core_study_content().get("skills") or {}):
                    curated += 1
        rows.append({
            "track_id": cert.get("id"),
            "title": cert.get("title"),
            "tasks": total,
            "curated_tasks": curated,
            "generated_tasks": total - curated,
            "usable_tasks": total,
        })
    return {"tracks": rows, "usable_tasks": sum(row["usable_tasks"] for row in rows), "curated_tasks": sum(row["curated_tasks"] for row in rows)}
