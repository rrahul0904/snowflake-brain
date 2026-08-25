from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .account_lifecycle import ensure_account_lifecycle_schema
from .adaptive_readiness import ensure_adaptive_readiness_schema
from .config import DATABASE_BACKEND, OBSERVABILITY_METRICS_TOKEN, QUESTION_BANK_AUTO_IMPORT
from .database import close_database, database_health, run_migrations
from .identity_billing_schema import ensure_identity_billing_schema
from .learning_intelligence import ensure_learning_intelligence_schema
from .observability import (
    ObservabilityMiddleware,
    log_event,
    metrics_snapshot,
    metrics_token_matches,
    record_background_failure,
    record_readiness_failure,
)
from .question_bank import import_question_bank_directory
from .question_bank_releases import ensure_active_release_baseline, ensure_question_bank_release_schema
from .question_versions import ensure_question_version_schema
from .routers import (
    account,
    activity,
    adaptive,
    affiliate,
    auth,
    billing,
    credentials,
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
from .talent_schema import ensure_talent_schema

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

app = FastAPI(
    title="Snowflake Certification Guide",
    version="0.14.0",
    description="Certification-native SnowPro preparation with private question-bank delivery, tier-aware practice and exams, candidate identity, trusted paid entitlements, verified SnowPro credentials, candidate-controlled talent discoverability, learning intelligence, adaptive readiness, PostgreSQL production persistence, production observability, and self-service account lifecycle controls.",
)
app.add_middleware(SecurityBoundaryMiddleware)
# Added after SecurityBoundaryMiddleware so observability is the outer request
# boundary and records authentication/rate-limit denials as well as application
# responses and unhandled exceptions.
app.add_middleware(ObservabilityMiddleware)


@app.on_event("startup")
def startup() -> None:
    try:
        run_migrations()
        ensure_identity_billing_schema()
        ensure_question_version_schema()
        ensure_question_bank_release_schema()
        ensure_learning_intelligence_schema()
        ensure_account_lifecycle_schema()
        ensure_adaptive_readiness_schema()
        ensure_talent_schema()
        # SQLite historically created feedback lazily. Account export/deletion
        # needs that candidate-linked table to exist even for candidates who have
        # never submitted feedback, so bootstrap its lightweight local schema.
        feedback.ensure_feedback_schema()
        if QUESTION_BANK_AUTO_IMPORT:
            # The source directory is private deployment content, never a frontend
            # asset and never committed to this repository. Imports never replace an
            # already active release; they remain admin/staging content until an
            # explicit release activation.
            import_question_bank_directory()
        ensure_active_release_baseline("snowpro-core")
    except Exception as exc:
        record_background_failure("application_startup", exc)
        raise
    log_event("application_started", backend=DATABASE_BACKEND, version=app.version)


@app.on_event("shutdown")
def shutdown() -> None:
    close_database()
    log_event("application_stopped", backend=DATABASE_BACKEND)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Process liveness only; dependency readiness is exposed separately."""
    return {
        "status": "ok",
        "product": "snowflake-certification-guide",
        "architecture": "certification-native-v26",
        "question_bank": "private-v1",
        "database_backend": DATABASE_BACKEND,
        "observability": "structured-v1",
    }


@app.get("/api/ready")
def ready() -> dict:
    """Production readiness probe including the configured database."""
    try:
        database = database_health()
    except Exception as exc:
        record_readiness_failure("database", error_type=type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "dependency": "database", "backend": DATABASE_BACKEND},
        ) from exc
    if database.get("status") != "ok":
        record_readiness_failure("database", error_type="health_check_failed")
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "dependency": "database", "backend": DATABASE_BACKEND},
        )
    return {"status": "ready", "database": database, "observability": "ready"}


@app.get("/api/metrics")
def metrics(request: Request) -> dict:
    """Low-cardinality operational metrics protected by an infrastructure token."""
    if not OBSERVABILITY_METRICS_TOKEN:
        raise HTTPException(status_code=404, detail="Not found")
    if not metrics_token_matches(request.headers.get("authorization"), OBSERVABILITY_METRICS_TOKEN):
        raise HTTPException(status_code=401, detail="Metrics authorization required")
    return metrics_snapshot()


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
app.include_router(adaptive.router, prefix="/api")
app.include_router(experience.router, prefix="/api")
app.include_router(labs.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(activity.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(account.router, prefix="/api")
app.include_router(credentials.router, prefix="/api")
app.include_router(google_auth.router, prefix="/api")
app.include_router(billing.router, prefix="/api")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/{full_path:path}")
def serve_spa(full_path: str) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index-v26.html")
