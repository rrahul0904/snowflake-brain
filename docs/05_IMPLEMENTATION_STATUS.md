# Snowflake Brain Rebuild - Implementation Status

Last updated: 2026-06-29

## Phase 1 / 2 Foundation

Status: implemented for the backend foundation.

Completed:

- Added `study_goals` and `study_plan_items` migrations.
- Added indexes for common track, lesson, test, question, and study-plan queries.
- Added study APIs under `/api/study`.
- Added active goal listing, goal creation, goal update, plan generation, today's task queue, readiness scoring, and content audit endpoints.
- Added a multi-certification roadmap endpoint that can schedule several certification goals sequentially across a target date range.
- Added frontend API bindings for study goals, roadmap creation, today's plan, readiness, and content audit.
- Added a visible `Study Plan` navigation entry and page.
- Connected dashboard mission items to the real study-plan queue when active tasks exist.

Verified:

- Python backend compiles.
- Browser JavaScript modules pass syntax checks with the bundled Node runtime.
- Docker image rebuilds and starts.
- Live container responds on `http://127.0.0.1:8010`.
- Live study endpoints return real indexed data.

Current live local state:

- Active goal: SnowPro Core.
- Target exam date: 2026-10-06.
- Generated plan items: 156.
- Indexed content audit:
  - 9 tracks.
  - 24 courses.
  - 1,305 lessons.
  - 279 practice test records.
  - 3,386 questions.
  - 24 documents.
  - 1,007 lessons use generated English notes instead of transcript-like text.

## Next Phase

Phase 3 should rebuild Lessons around strict course scope:

- Track selector.
- Course selector scoped to track.
- Section list.
- Ordered lesson playlist.
- Video player.
- English transcript or generated English notes.
- Related practice tests and questions.
- Lesson-context assistant panel.

Stop condition:

- Do not proceed with practice-page redesign until Lessons no longer mixes unrelated courses by default.
