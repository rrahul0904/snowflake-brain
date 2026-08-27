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

    for export in ("getAdaptiveReadiness", "getAdaptiveRecommendations", "getAdaptiveQuestionIds"):
        require(api, f"export const {export}", f"adaptive API export {export}")
    require(router, '"#/adaptive":"adaptive-v26.js"', "adaptive SPA route")
    # Adaptive remains a first-class signed-in capability but the recording-parity
    # header intentionally keeps only Curriculum, Practice, Reference and Journal.
    # Require an explicit account-menu entry instead of coupling the capability to
    # one particular primary-navigation layout.
    require(nav, 'href="#/adaptive?track_id=', "adaptive signed-in navigation")
    require(nav, 'Adaptive Readiness', "adaptive navigation label")
    require(view, "not a probability", "readiness disclaimer")
    require(view, 'mode: "adaptive"', "adaptive practice launch")
    require(view, "confidence", "confidence capture")
    require(view, "response_time_ms", "response-time capture")
    require(backend_router, 'prefix="/intelligence/adaptive"', "authenticated adaptive API router")
    require(main_py, "app.include_router(adaptive.router, prefix=\"/api\")", "adaptive router mount")
    require(runtime, "adaptive_question_ids", "adaptive priority lookup")
    require(runtime, "preferred_question_ids=preferred", "adaptive priorities passed to canonical selector")
    require(selector, "filter_rows_to_active_release", "active release boundary")
    require(selector, "filter_rows_for_entitlement", "tier entitlement boundary")
    require(selector, "reserve_daily_questions", "daily quota boundary")
    require(selector, 'strategy = "adaptive_readiness_entitlement_aware"', "adaptive selection strategy")

    forbidden = ("correct_json", "correct_options", "explanation")
    question_ids_handler = backend_router.split("def question_ids", 1)[1]
    for token in forbidden:
        if token in question_ids_handler:
            raise AssertionError(f"Adaptive question-ID endpoint leaks answer-oriented field: {token}")

    print("Adaptive frontend/delivery contract: PASS (route, signed-in navigation, evidence, active-release + entitlement-aware delivery)")


if __name__ == "__main__":
    main()
