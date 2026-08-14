from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import QUESTION_BANK_AUTO_IMPORT
from .database import run_migrations
from .identity_billing_schema import ensure_identity_billing_schema
from .question_bank import import_question_bank_directory
from .routers import (
    activity,
    affiliate,
    auth,
    billing,
    certification_practice,
    experience,
    feedback,
    google_auth,
    intelligence,
    labs,
    mock_exam,
    question_bank_runtime,
    questions,
    skills,
)
from .security import SecurityBoundaryMiddleware

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

app = FastAPI(
    title="Snowflake Certification Guide",
    version="0.8.0",
    description="Certification-native SnowPro preparation with private question-bank delivery, tier-aware practice and exams, candidate identity, and trusted paid entitlements.",
)
app.add_middleware(SecurityBoundaryMiddleware)


@app.on_event("startup")
def startup() -> None:
    run_migrations()
    ensure_identity_billing_schema()
    if QUESTION_BANK_AUTO_IMPORT:
        # The source directory is private deployment content, never a frontend
        # asset and never committed to this repository.
        import_question_bank_directory()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "product": "snowflake-certification-guide", "architecture": "certification-native-v26-question-bank-v1"}


app.include_router(skills.router, prefix="/api")
# Candidate-facing question and mock routes are registered before the legacy
# compatibility routers so the private-bank boundary is the authoritative path.
app.include_router(question_bank_runtime.router, prefix="/api")
app.include_router(affiliate.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(certification_practice.router, prefix="/api")
app.include_router(mock_exam.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(experience.router, prefix="/api")
app.include_router(labs.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(activity.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(google_auth.router, prefix="/api")
app.include_router(billing.router, prefix="/api")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/{full_path:path}")
def serve_spa(full_path: str) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index-v26.html")
