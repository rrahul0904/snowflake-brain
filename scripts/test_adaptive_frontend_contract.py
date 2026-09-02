#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"Missing {label}: {needle}")


def main() -> None:
    api = read("frontend/api.js")
    router = read("frontend/router-complete.js")
    nav = read("frontend/components/nav.js")
    view = read("frontend/views/adaptive-v26.js")
    runtime = read("app/routers/question_bank_runtime.py")
    selector = read("app/question_bank_selection.py")
    backend_router = read("app/routers/adaptive.py")
    main_py = read("app/main.py")

    for export in ("getAdaptiveReadiness", "getAdaptiveRecommendations"):
        require(api, f"export const {export}", f"adaptive API export {export}")
    if "getAdaptiveQuestionIds" in api or "/adaptive/question-ids" in api:
        raise AssertionError("Candidate frontend must not expose raw adaptive question-ID inventory")
    if '"/question-ids"' in backend_router or "def question_ids" in backend_router:
        raise AssertionError("Candidate adaptive router must not expose raw active-release question IDs")

    require(router, '"#/adaptive":"adaptive-v26.js"', "adaptive SPA route")
    require(nav, 'href="#/adaptive?track_id=', "adaptive signed-in navigation")
    require(nav, 'Adaptive Readiness', "adaptive navigation label")
    require(view, "not a probability", "readiness disclaimer")
    require(view, 'mode: "adaptive"', "adaptive practice launch")
    require(view, "confidence", "confidence capture")
    require(view, "response_time_ms", "response-time capture")
    require(backend_router, 'prefix="/intelligence/adaptive"', "authenticated adaptive API router")
    require(main_py, "app.include_router(adaptive.router, prefix=\"/api\")", "adaptive router mount")

    # Adaptive priorities remain server-side. The candidate starts a normal
    # adaptive practice session; the canonical selector then applies active
    # release, entitlement, quota and served-history boundaries before wording is
    # returned.
    require(runtime, "adaptive_question_ids", "server-side adaptive priority lookup")
    require(runtime, "preferred_question_ids=preferred", "adaptive priorities passed to canonical selector")
    require(selector, "filter_rows_to_active_release", "active release boundary")
    require(selector, "filter_rows_for_entitlement", "tier entitlement boundary")
    require(selector, "reserve_daily_questions", "daily quota boundary")
    require(selector, 'strategy = "adaptive_readiness_entitlement_aware"', "adaptive selection strategy")

    print("Adaptive frontend/delivery contract: PASS (no raw ID inventory; entitled server-side adaptive delivery)")


if __name__ == "__main__":
    main()
