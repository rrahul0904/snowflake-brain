#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    backend_path = ROOT / "app/routers/question_explorer.py"
    frontend_path = ROOT / "frontend/views/question-explorer-v26.js"
    require(backend_path.is_file(), "question explorer backend missing")
    require(frontend_path.is_file(), "question explorer frontend missing")
    ast.parse(backend_path.read_text(encoding="utf-8"))

    backend = text("app/routers/question_explorer.py")
    frontend = text("frontend/views/question-explorer-v26.js")
    main_py = text("app/main.py")
    router = text("frontend/router-complete.js")
    api = text("frontend/api.js")
    sidebar = text("frontend/components/study-shell.js")

    require("candidate_question_history" in backend, "explorer must be limited to candidate-served history")
    require("candidate_was_served_question" in backend, "coach/report must enforce served-question ownership")
    require('"answer_revealed": False' in backend, "coach answer-leak guard missing")
    require("correct_json" not in backend and "explanation" not in backend.split("@router.get("/question-explorer/{question_id}/coach")")[0], "history endpoint must not expose answer material")
    require("ensure_feedback_schema" in backend and "Question review:" in backend, "content correction workflow missing")
    require("question_explorer.router" in main_py, "question explorer router is not mounted")

    for token in ("Question Explorer", "Ask Snowflake Coach", "Start custom session", "Flag content", "Private note"):
        require(token.lower() in frontend.lower(), f"LeetQuiz experience missing: {token}")
    require("getQuestionExplorerHistory" in api and "getQuestionCoach" in api and "reportQuestionIssue" in api, "client API incomplete")
    require('"#/question-explorer":"question-explorer-v26.js"' in router, "question explorer route missing")
    require("Question Explorer" in sidebar, "question explorer navigation missing")

    require("snowpro_core_cof_c03_private_bank_1200_beta_v2.json" not in frontend, "private artifact leaked to frontend")
    require("bank_pool" not in frontend and "source_refs" not in frontend, "private pool/provenance metadata leaked to frontend")
    print("LEETQUIZ DONOR SLICE: PASS")


if __name__ == "__main__":
    main()
