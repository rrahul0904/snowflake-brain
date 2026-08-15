from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import QUESTION_BANK_AUTO_IMPORT
from .database import run_migrations
from .identity_billing_schema import ensure_identity_billing_schema
from .question_bank import import_question_bank_directory
from .question_bank_releases import ensure_active_release_baseline, ensure_question_bank_release_schema
from .question_versions import ensure_question_version_schema
from .routers import (
    activity,
    affiliate,
    auth,
    billing,
    experience,
    feedback,
    google_auth,
    intelligence,
    labs,
    question_bank_candidate_state,
    question_bank_runtime,
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
    ensure_question_version_schema()
    ensure_question_bank_release_schema()
    if QUESTION_BANK_AUTO_IMPORT:
        # The source directory is private deployment content, never a frontend
        # asset and never committed to this repository. Imports never replace an
        # already active release; they remain admin/staging content until an
        # explicit release activation.
        import_question_bank_directory()
    ensure_active_release_baseline("snowpro-core")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "product": "snowflake-certification-guide",
        "architecture": "certification-native-v26",
        "question_bank": "private-v1",
    }


app.include_router(skills.router, prefix="/api")
# Candidate question/practice/mock ownership is intentionally singular. The
# legacy questions, certification_practice and mock_exam routers remain as
# implementation modules for shared helpers where needed, but are not mounted
# into the public application. This prevents registration-order security from
# becoming part of the candidate boundary.
app.include_router(question_bank_runtime.router, prefix="/api")
app.include_router(question_bank_candidate_state.router, prefix="/api")
app.include_router(affiliate.router, prefix="/api")
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
