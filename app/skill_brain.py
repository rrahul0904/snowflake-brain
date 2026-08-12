from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import CERTIFICATION_CURRICULA_SUPPLEMENT_CONFIG, SKILL_MAP_CONFIG


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": "missing", "certifications": []}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_skill_map() -> dict[str, Any]:
    data = copy.deepcopy(_read_json(SKILL_MAP_CONFIG))
    data.setdefault("certifications", [])
    supplement = _read_json(CERTIFICATION_CURRICULA_SUPPLEMENT_CONFIG)
    existing = {cert.get("id") for cert in data["certifications"]}
    for cert in supplement.get("certifications") or []:
        if cert.get("id") not in existing:
            data["certifications"].append(copy.deepcopy(cert))
            existing.add(cert.get("id"))
    data["supplement_version"] = supplement.get("version")
    data["weight_note"] = supplement.get("weight_note")
    return data


def certifications() -> list[dict[str, Any]]:
    return load_skill_map().get("certifications", [])


def certification(track_id: str | None) -> dict[str, Any] | None:
    if not track_id:
        track_id = "snowpro-core"
    for cert in certifications():
        if cert.get("id") == track_id:
            return cert
    return certifications()[0] if certifications() else None


def flatten_skills(track_id: str | None = None) -> list[dict[str, Any]]:
    cert = certification(track_id)
    if not cert:
        return []
    rows: list[dict[str, Any]] = []
    for domain in cert.get("domains", []):
        for skill in domain.get("skills", []):
            row = dict(skill)
            row["domain_id"] = domain.get("id")
            row["domain"] = domain.get("title")
            row["domain_weight"] = domain.get("weight", 0)
            row["certification"] = cert.get("id")
            row["certification_title"] = cert.get("title")
            rows.append(row)
    return rows


def normalize_text(value: str | None) -> str:
    value = value or ""
    return re.sub(r"\s+", " ", value.lower()).strip()


def skill_score(text: str, skill: dict[str, Any]) -> int:
    haystack = normalize_text(text)
    if not haystack:
        return 0
    score = 0
    terms = []
    terms.extend(skill.get("aliases") or [])
    terms.extend(skill.get("question_tags") or [])
    terms.append(skill.get("title") or "")
    for term in terms:
        term_norm = normalize_text(term)
        if not term_norm:
            continue
        if term_norm in haystack:
            score += 4 if len(term_norm) > 8 else 2
        else:
            pieces = [piece for piece in re.split(r"[^a-z0-9_$]+", term_norm) if len(piece) >= 4]
            score += sum(1 for piece in pieces if piece in haystack)
    return score


def infer_skill(text: str, track_id: str | None = None) -> dict[str, Any] | None:
    skills = flatten_skills(track_id)
    scored = [(skill_score(text, skill), skill) for skill in skills]
    scored = [item for item in scored if item[0] > 0]
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    best = dict(scored[0][1])
    best["confidence"] = min(0.95, 0.35 + scored[0][0] / 20)
    return best


def infer_skill_id(text: str, track_id: str | None = None) -> str | None:
    skill = infer_skill(text, track_id)
    return skill.get("id") if skill else None


def matched_skills(text: str, track_id: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    scored = [(skill_score(text, skill), skill) for skill in flatten_skills(track_id)]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: item[0], reverse=True)
    out = []
    for score, skill in scored[:limit]:
        row = dict(skill)
        row["match_score"] = score
        row["confidence"] = min(0.95, 0.35 + score / 20)
        out.append(row)
    return out
