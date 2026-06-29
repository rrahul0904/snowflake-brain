# Snowflake Brain Review Package

Prepared: 2026-06-29

## Purpose

This package contains the Snowflake Brain source code and planning documents for review.

It intentionally excludes:

- Local SQLite data under `data/`.
- Downloaded paid course content.
- Virtual environments.
- Caches and generated runtime files.

## Main Review Documents

Read in this order:

1. `docs/06_COMPREHENSIVE_REVIEW_AND_REBUILD_PLAN.md`
2. `docs/02_DESIGN_DOCUMENT.md`
3. `docs/03_DATA_MODEL.md`
4. `docs/04_PROJECT_PLAN.md`
5. `docs/05_IMPLEMENTATION_STATUS.md`
6. `docs/01_HIGH_LEVEL_TASKS.md`

## Main Source Areas

- `app/`: FastAPI backend, ingestion, database migrations, routers.
- `frontend/`: Vanilla JavaScript SPA, views, components, styles.
- `Dockerfile`: Container build.
- `docker-compose.yml`: Local app runtime.
- `requirements.txt`: Python dependencies.

## Current Local Runtime

The app runs locally at:

`http://127.0.0.1:8010`

Current live phase:

- Phase 1/2 foundation implemented.
- Study Plan page added.
- Next planned phase: Lessons page rebuild.

## Important Review Notes

The product is not finished. The highest-priority problems are:

1. Lessons must become course-scoped courseware.
2. Practice must become a serious full-test runner.
3. AI tutor must become context-grounded.
4. UI needs one design system.
5. Content quality and duplicate cleanup must be visible and manageable.

## Rebuild Command

From the project root:

```bash
docker compose up -d --build
```

Then open:

```text
http://127.0.0.1:8010/?appv=20260628-phase1#/plan
```
