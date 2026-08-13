import json
from typing import Any


def json_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def question_public(row: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    options = json_list(row.get("options_json") or row.get("options"))
    correct = json_list(row.get("correct_json") or row.get("correct"))
    assessment_type = (row.get("assessment_type") or "").lower()
    multiple = bool(
        row.get("multiple")
        or len(correct) > 1
        or "multiple-select" in assessment_type
        or "multi-select" in assessment_type
        or "multiple-response" in assessment_type
    )
    data = {
        "id": row["id"],
        "track_id": row.get("track_id") or "snowpro-core",
        "test_id": row.get("test_id") or "",
        "test_title": row.get("test_title") or "Practice",
        "question_position": row.get("question_position") or 0,
        "question": row["question"],
        "options": options,
        "multiple": multiple,
        "tags": json_list(row.get("tags")),
        "difficulty": row.get("difficulty") or "medium",
        "source_path": row.get("source_path") or "",
        "source_kind": row.get("source_kind") or "curated",
        "assessment_type": row.get("assessment_type") or "practice",
    }
    if include_answer:
        data["correct"] = [int(item) for item in correct if isinstance(item, int) or str(item).isdigit()]
        data["explanation"] = row.get("explanation") or ""
    return data
