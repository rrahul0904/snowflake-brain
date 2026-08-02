from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import AUTO_INGEST
from .database import run_migrations
from .routers import ai, courses, data_ai, experience, flashcards, index, intelligence, labs, progress, questions, search, skills, study
from .routers.index import maybe_auto_ingest

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
CAREER_DOCS_DIR = ROOT_DIR / "docs" / "ai-career-curriculum"

app = FastAPI(title="Data + AI Career Lab", version="0.2.0")


@app.on_event("startup")
def startup() -> None:
    run_migrations()
    if AUTO_INGEST:
        maybe_auto_ingest()


app.include_router(index.router, prefix="/api")
app.include_router(courses.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(flashcards.router, prefix="/api")
app.include_router(labs.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(experience.router, prefix="/api")
app.include_router(data_ai.router, prefix="/api")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
if CAREER_DOCS_DIR.exists():
    app.mount("/career-docs", StaticFiles(directory=CAREER_DOCS_DIR, html=True), name="career-docs")


@app.get("/{full_path:path}")
def serve_spa(full_path: str) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
