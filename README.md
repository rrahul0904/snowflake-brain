# Snowflake Certification Guide

A local-first Snowflake certification preparation product built around the exam blueprint, written task lessons, source practice questions, diagnostic assessment, adaptive drill, timed mock exams, hands-on exercises, mastery, and readiness.

## Product model

The application is **certification-native**. It is not a course player and does not ingest video archives, captions, transcripts, or course folders.

```text
Certification
  -> Exam blueprint
     -> Weighted domains
        -> Task statements
           -> Written lessons
           -> Mapped practice questions
           -> Build exercises
  -> Diagnostic
  -> Adaptive drill
  -> Timed mock exams
  -> Attempts / task completion
  -> Mastery / readiness
```

The current fully authored track is **SnowPro Core COF-C03**.

### COF-C03 blueprint

The runtime blueprint is `config/snowpro_core_cof_c03_blueprint.json` and is authoritative for SnowPro Core.

| Domain | Weight |
| --- | ---: |
| Snowflake AI Data Cloud Features and Architecture | 31% |
| Account Management and Data Governance | 20% |
| Data Loading, Unloading, and Connectivity | 18% |
| Performance Optimization, Querying, and Transformation | 21% |
| Data Collaboration | 10% |

The five domains contain 19 task statements (`1.1` through `5.3`). Fully written Core lessons live in `config/study_content_core.json`.

## User experience

Primary routes:

- `#/home` — certification overview
- `#/curriculum` — weighted domains and task statements
- `#/domain` — one domain and its tasks
- `#/skill` — full written task lesson
- `#/mock` — mock landing, sitting selection, source exams, and history
- `#/mock/start` — quick/full sitting confirmation
- `#/mock/session` — persistent timed exam player
- `#/mock/result` — score, domain/task analytics, and answer review
- `#/practice` — diagnostic and adaptive drill
- `#/progress` — mastery and readiness
- `#/quick-reference` — final-review reference
- `#/glossary` — certification glossary
- `#/exercises` / `#/labs` — hands-on build exercises
- `#/journal` — certification-focused technical articles

There are no course, video, transcript, archive, academy, or media-player routes or active UI assets.

## Architecture

### Backend

- Python 3.13
- FastAPI
- Pydantic
- SQLite in WAL mode

The runtime is intentionally small:

- `app/main.py` — application entry point and router registration
- `app/database.py` — certification-native schema
- `app/skill_brain.py` — blueprint/task resolution
- `app/certification_content.py` — written lesson/catalog content
- `app/intelligence.py` — task mapping, mastery, mistakes, diagnostics, readiness
- `app/evidence.py` — question-to-task mapping trust/review
- `app/lab_challenges.py` — configured hands-on exercises
- `app/mock_exam.py` — persisted sitting selection, timing, grading, analytics, and history
- `app/routers/skills.py`
- `app/routers/questions.py`
- `app/routers/certification_practice.py`
- `app/routers/intelligence.py`
- `app/routers/experience.py`
- `app/routers/labs.py`
- `app/routers/mock_exam.py`

### Frontend

The UI is a vanilla JavaScript SPA using hash routes and native ES modules.

Core files:

- `frontend/app.js`
- `frontend/router.js`
- `frontend/api.js`
- `frontend/views/guide.js`
- `frontend/views/quiz.js`
- `frontend/views/mock.js`
- `frontend/views/labs.js`
- `frontend/views/journal.js`

## Certification-native database

V24 defaults to:

```text
data/snowflake_certification.sqlite
```

This is deliberately separate from historical local databases so the new product starts on a clean schema boundary.

Runtime tables:

- `certification_tracks`
- `certification_task_progress`
- `practice_tests`
- `questions`
- `question_skill_map`
- `question_attempts`
- `exam_sessions`
- `exam_session_questions`
- `exam_session_answers`
- `bookmarks`
- `notes`
- `daily_activity`
- `learning_events`

Questions own `track_id` directly. Practice tests own `track_id` directly. There is no `courses` table and no fake course required to run an exam.

## Question provenance

`questions.source_kind` makes source quality explicit:

- `source` — imported current certification practice material
- `curated` — manually authored/maintained question material
- `canonical` — deterministic supplemental questions derived from written task lessons
- `legacy` — older exam-version material, isolated from current readiness by default

Default COF-C03 diagnostic, drill, mock, mastery, and readiness flows exclude `legacy` questions. When current source questions are available, selection favors them before supplemental canonical questions.

## Question-to-task mapping

Current resolution precedence is:

1. human-reviewed persisted mapping
2. persisted mapping with confidence >= 0.70
3. heuristic fallback against the current task blueprint

Mappings whose task IDs are no longer present in the current blueprint are treated as stale and ignored. Evidence audit reports the stale edge count instead of allowing old task IDs to inflate mapping trust.

## Exam engine

The V25 production mock contract is configured by `config/exam_simulation.json`:

- Quick Mock — 30 questions, 45 minutes
- Snowflake Brain Full Mock — 100 questions, 120 minutes
- practice threshold — 750 / 1000
- domain weights — 31 / 20 / 18 / 21 / 10

The full sitting is explicitly a configurable Snowflake Brain simulation, not a claim about an exact live-exam format. Each sitting persists its question membership, question order, randomized option mapping, answers, flags, start time, duration, and status. The deadline is derived from `started_at + duration_seconds`; refresh cannot reset it.

Primary API routes:

- `GET /api/mock/config`
- `POST /api/mock/sessions`
- `GET /api/mock/sessions/{session_id}`
- `PUT /api/mock/sessions/{session_id}/answers/{question_id}`
- `PUT /api/mock/sessions/{session_id}/questions/{question_id}/flag`
- `POST /api/mock/sessions/{session_id}/submit`
- `GET /api/mock/sessions/{session_id}/result`
- `GET /api/mock/history`

Correct options and explanations are excluded from every pre-submit session payload. The backend grades exact set equality for multi-select questions. Submission is idempotent.

### Readiness score

The product reports raw accuracy separately from its transparent practice estimate:

```text
domain accuracy = correct in domain / questions in domain
weighted readiness % = Σ(domain accuracy × COF-C03 domain weight)
practice readiness score = round(weighted readiness % × 10)
```

This 0–1000 practice score is not presented as Snowflake's confidential production scoring formula.

## Run locally

One-command setup and start:

```bash
./scripts/setup.sh
./scripts/dev.sh
```

Open:

```text
http://127.0.0.1:8000
```

Health check:

```text
GET /api/health
```

Expected architecture marker:

```json
{
  "status": "ok",
  "product": "snowflake-certification-guide",
  "architecture": "certification-native-v24"
}
```

## Docker

```bash
docker compose up --build
```

The compose stack persists only the certification database under `./data`. No course/content archive volume is mounted.

## Verification

Run the complete local gate:

```bash
./scripts/verify_all.sh
```

The V25 gate protects these invariants:

- exactly 5 COF-C03 domains with weights `31/20/18/21/10`
- exactly 19 Core task statements
- 19/19 written Core lessons
- direct certification ownership for questions and practice exams
- exact-set grading for multi-select questions
- current-task-only mapping trust
- no runtime course/video/transcript schema
- no legacy video/archive route surface
- persisted mock membership, answers, flags, deadline, grading, history, and idempotency
- no answer leakage from active timed sittings
- current/legacy practice isolation

GitHub Actions execution is separate from local verification. Do not treat a workflow that fails before runner assignment as a code/test failure.

## Branching

Production mock work is developed from `main` on:

```text
agent/v25-production-mock-exam
```

The pull request base is `main`; this is not a stacked branch.
