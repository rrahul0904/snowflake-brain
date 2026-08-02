# Data + AI Career Lab

A Dockerized local study app for Snowflake certification prep. It indexes your downloaded Udemy course folders, then gives you a single training workspace for videos, captions, practice questions, source-backed search, quizzes, and hands-on Snowflake labs.

## What It Builds

- Local FastAPI app with a SQLite full-text search index.
- Read-only mount of your downloaded course content.
- Ingestion for videos, `.vtt` captions, `.info.json` metadata, Markdown/text resources, and `_practice-tests/practice-tests.json`.
- Browser UI for:
  - Course and lesson library
  - Video/tutorial viewer with transcript notes
  - Local brain search and question answering
  - Random quizzes with grading and explanations
  - Snowflake SQL labs

## Run With Docker

```bash
docker compose up --build
```

Open:

```text
http://localhost:8010
```

The compose file already mounts your course folder:

```text
/Users/297159/Documents/Udemy Project Downloader/downloads
```

as `/content` inside the container.

## Rebuild The Brain

The app auto-indexes on first startup. Use **Rebuild Brain** in the sidebar after adding more videos or practice tests.

You can also call:

```bash
curl -X POST http://localhost:8010/api/index/rebuild
```

## Local Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
CONTENT_ROOT="/Users/297159/Documents/Udemy Project Downloader/downloads" \
BRAIN_DB="./data/snowflake_brain.sqlite" \
uvicorn app.main:app --reload
```

## Notes

This version uses retrieval over your local material rather than fine-tuning a model. That keeps it fast, private, cheap, and immediately useful. The backend is structured so an LLM answer generator or Ollama/OpenAI adapter can be added later on top of the same indexed sources.

## v4 Skill Brain + Lab Runner

This build adds a certification skill map and W3Schools-style Snowflake challenge runner.

Key files:

- `config/certification_skill_map.json`
- `config/snowflake_lab_challenges.json`
- `app/skill_brain.py`
- `app/lab_challenges.py`
- `app/routers/skills.py`
- `frontend/views/labs.js`

New endpoints:

```text
GET /api/skills/map
GET /api/skills/summary?track_id=snowpro-core
GET /api/labs/config
GET /api/labs
POST /api/labs/{lab_id}/submit
```

Labs default to offline validation:

```bash
SNOWFLAKE_LABS_MODE=offline
```

Offline mode checks SQL structure and required Snowflake clauses locally. It does not execute SQL against Snowflake.

## AI Career Curriculum

The repository includes a personalized, evidence-driven curriculum for expanding senior data-engineering leadership into production AI, product-data leadership, forward-deployed architecture and research-engineering literacy. Start with [the curriculum overview](docs/ai-career-curriculum/README.md).
