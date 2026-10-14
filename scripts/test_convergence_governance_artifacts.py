from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/reverse-engineering/capability-ledger.yaml"
ARCHITECTURE = ROOT / "docs/architecture"

REQUIRED_CAPABILITIES = {
    "exam-guide", "domain-task-workbench", "concept-check", "exam-sim", "build-coach",
    "question-studio", "custom-quizzes", "question-explorer", "diagnostic", "targeted-drill",
    "missed-only-repair", "readiness-exam", "quick-mock", "full-mock", "question-navigator",
    "flagging", "mock-replay", "socratic-coach", "daily-session", "blitz-recall", "streaks",
    "architecture-builder", "practice-hub", "mistake-notebook", "add-to-review", "due-today",
    "spaced-repetition", "confidence-calibration", "readiness-explanations", "study-plan", "labs",
    "content-correction", "editorial-ingestion", "public-discovery-seo", "quick-reference", "glossary",
    "freshness-metadata",
}
REQUIRED_FIELDS = {
    "donor", "evidence", "classification", "learner_problem", "behavior_contract", "current_authority",
    "implementation_state", "gap", "decision", "acceptance_tests", "security_notes", "clean_room_notes",
}
ARCHITECTURE_FILES = {
    "C4_CONTEXT.md", "C4_CONTAINER.md", "COMPONENTS.md", "DATA_MODEL.md", "SECURITY_MODEL.md",
    "QUESTION_SUPPLY_CHAIN.md", "LEARNING_INTELLIGENCE.md", "DEPLOYMENT_MODEL.md", "adr/0001-preserve-v26-and-vercel-neon.md",
}


def main() -> None:
    text = LEDGER.read_text(encoding="utf-8")
    entries = re.split(r"(?m)^  - capability_id: ", text)[1:]
    seen: set[str] = set()
    for entry in entries:
        capability_id = entry.splitlines()[0].strip()
        seen.add(capability_id)
        missing = sorted(field for field in REQUIRED_FIELDS if not re.search(rf"(?m)^    {field}:", entry))
        if missing:
            raise SystemExit(f"{capability_id}: missing ledger fields {', '.join(missing)}")
        decision = re.search(r"(?m)^    decision: ([A-Z_]+)$", entry)
        if not decision or decision.group(1) not in {"MATCH", "IMPROVE", "NEW", "OMIT"}:
            raise SystemExit(f"{capability_id}: invalid decision")
        classification = re.search(r"(?m)^    classification: ([A-Z_]+)$", entry)
        if not classification or classification.group(1) not in {"OBSERVED", "INFERRED", "HYPOTHESIS", "UNKNOWN", "VERIFIED"}:
            raise SystemExit(f"{capability_id}: invalid evidence classification")
    missing_capabilities = sorted(REQUIRED_CAPABILITIES - seen)
    if missing_capabilities:
        raise SystemExit(f"Missing required capabilities: {', '.join(missing_capabilities)}")
    if "status: REA_UNAVAILABLE" not in text:
        raise SystemExit("Ledger must preserve an explicit REA_UNAVAILABLE status when the provider is not available")
    if "NON_VIDEO_GA_WITH_VIDEO_BACKLOG" not in (ROOT / "docs/reconciliation/final-reality.md").read_text(encoding="utf-8"):
        raise SystemExit("Reality record must contain the explicit video boundary")
    acceptance = (ROOT / "docs/reconciliation/FINAL_PRODUCTION_ACCEPTANCE.md").read_text(encoding="utf-8")
    verdicts = re.findall(r"(?m)^\*\*Verdict: (PRODUCTION GO|PRODUCTION NO-GO)\*\*$", acceptance)
    if len(verdicts) != 1:
        raise SystemExit("Final production acceptance must contain exactly one verdict")
    if verdicts[0] != "PRODUCTION NO-GO":
        raise SystemExit("Production GO requires verified exact-SHA acceptance evidence")
    missing_architecture = sorted(path for path in ARCHITECTURE_FILES if not (ARCHITECTURE / path).is_file())
    if missing_architecture:
        raise SystemExit(f"Missing architecture artifacts: {', '.join(missing_architecture)}")
    print(f"Convergence governance artifacts: PASS ({len(seen)} capability contracts)")


if __name__ == "__main__":
    main()
