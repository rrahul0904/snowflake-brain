from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import run_migrations
from .routers import certification_practice, experience, intelligence, labs, questions, skills

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

app = FastAPI(
    title="Snowflake Certification Guide",
    version="0.4.0",
    description="Certification-native SnowPro preparation: blueprint, written lessons, practice, mastery, and readiness.",
)


@app.on_event("startup")
def startup() -> None:
    run_migrations()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "product": "snowflake-certification-guide", "architecture": "certification-native-v24"}


app.include_router(skills.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(certification_practice.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(experience.router, prefix="/api")
app.include_router(labs.router, prefix="/api")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/{full_path:path}")
def serve_spa(full_path: str) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
