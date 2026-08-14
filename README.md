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

The learner-visible catalog is intentionally limited to three paths:

- **SnowPro Core — COF-C03**: available, with the fully authored curriculum and practice experience
- **SnowPro Advanced: Data Engineer — DEA-C02**: Coming Soon; not selectable until its content is genuinely authored
- **SnowPro Advanced: Architect — ARA-C01**: Coming Soon; not selectable until its content is genuinely authored

Performance Optimization remains a legitimate **domain inside SnowPro Core**. It is not exposed as a standalone certification.

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
- `#/membership` — candidate account and Free/Premium access boundary

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
- `app/auth.py` — scrypt password verification, HttpOnly sessions, membership resolution, and entitlement dependencies
- `app/routers/auth.py` — registration, login, logout, and current-session API
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

- `frontend/index-v26.html` — served SPA shell
- `frontend/app-complete.js` — V26 application bootstrap and theme handling
- `frontend/router-complete.js` — V26 hash-route loader
- `frontend/api.js`
- `frontend/components/globe.js` — rotating globe using local world geography
- `frontend/components/feedback.js` — feedback drawer
- `frontend/styles/` — canonical V26 design layers
- `frontend/views/*-v26.js` — curriculum, lessons, mock player, results, progress, and reference views
- `frontend/assets/world-major-land.geojson` — local world geometry used by the globe

## Certification-native database

V26 defaults to:

```text
data/snowflake_certification.sqlite
```

This is deliberately separate from historical local databases so the new product starts on a clean schema boundary.

Runtime tables:

- `candidate_accounts`
- `candidate_sessions`
- `candidate_memberships`
- `membership_events`
- `candidate_task_progress`
- `candidate_bookmarks`
- `candidate_notes`
- `candidate_daily_activity`
- `candidate_daily_question_usage`
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

Legacy anonymous learning rows remain intact for migration compatibility. New authenticated progress, attempts, bookmarks, notes, activity, lab events, and mock sessions are associated with `candidate_id`; mock reads and mutations verify session ownership.

## Candidate accounts and membership

Registration creates a candidate, an active Free membership, and a 30-day session. Passwords use `hashlib.scrypt` with a unique random salt. The browser receives only an opaque `HttpOnly`, `SameSite=Lax`, `Path=/` cookie; SQLite stores only its SHA-256 token hash. Set `AUTH_COOKIE_SECURE=true` behind HTTPS.

Auth routes:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

Every account can read the complete Core curriculum and study materials. Persisted server-side plan limits are:

- Free — 20 practice questions per UTC day and one 20-question timed mock per UTC week; the weekly mock cannot be discarded and must be submitted or expire on its timer
- Premium 100 — $20/month plus applicable taxes, 100 practice/Quick Mock questions per UTC day, and 2 Full Exam starts per UTC month
- Premium 250 — $40/month plus applicable taxes, 250 practice/Quick Mock questions per UTC day, and 4 Full Exam starts per UTC month
- Premium 500 — $100/month plus applicable taxes, 500 practice/Quick Mock questions per UTC day, and unlimited Full Exam starts
- One-Time Exam Pack — $35 plus applicable taxes, lifetime access to a 100-question Practice Mock, and one Full Exam start within 30 days of purchase

Daily allowances reset at 00:00 UTC, weekly allowances Monday at 00:00 UTC, and monthly allowances on the first day at 00:00 UTC. The Exam Pack keeps its lifetime Practice Mock after the separate 30-day Full Exam window ends. All mocks are independent preparation simulations; the product does not sell or administer an official Snowflake certification exam.

No billing provider, checkout, or tax engine is implemented. The UI shows the configured USD prices and states that applicable taxes will be calculated by the future billing provider at checkout; it never pretends a purchase succeeded. For development and test accounts only, use the server-side CLI:

```bash
python scripts/set_membership.py user@example.com premium_20
python scripts/set_membership.py user@example.com premium_40
python scripts/set_membership.py user@example.com premium_100
python scripts/set_membership.py user@example.com exam_pack_35
python scripts/set_membership.py user@example.com free
```

In Docker:

```bash
docker compose exec snowflake-certification-guide python scripts/set_membership.py user@example.com premium_20
```

## Security and deployment boundary

The application implements the FastAPI portion of the security boundary:

- scrypt candidate authentication and revocable, hashed 30-day sessions
- server-side plan quotas, calendar resets, and candidate ownership checks
- request-scoped mock content with no bulk export route
- conservative in-process auth, mutation, and paid-content rate limits
- reduced limits after repeated authorization failures
- CSP, clickjacking, MIME-sniffing, referrer, permissions, and HTTPS HSTS headers
- a private SQLite bind mount; the database file is never served by FastAPI or copied into static assets

The in-process limiter is a safety net, not a replacement for distributed edge controls. Public deployment must place the service behind an HTTPS CDN/WAF/bot layer with DDoS protection and distributed rate limits. Enable `AUTH_COOKIE_SECURE=true` and `FORCE_HTTPS=true` only when HTTPS/proxy forwarding is correctly configured. Multiple application replicas require the edge layer or a shared rate-limit store; the local limiter is intentionally process-local and stores only short-lived hashes of peer/IP plus User-Agent signals in memory.

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

The V26 production mock contract is configured by `config/exam_simulation.json`:

- Quick Mock — 30 questions, 45 minutes
- Snowflake Brain Full Mock — 100 questions, 120 minutes
- practice threshold — 750 / 1000
- domain weights — 31 / 20 / 18 / 21 / 10

The full sitting is explicitly a configurable Snowflake Brain simulation, not a claim about an exact live-exam format. Each sitting persists its candidate owner, question membership, question order, randomized option mapping, answers, flags, start time, duration, and status. The deadline is derived from `started_at + duration_seconds`; refresh cannot reset it.

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
  "architecture": "certification-native-v26"
}
```

## Docker

Start the V26 application in the background:

```bash
docker compose up --build -d
docker compose ps
```

Open [http://localhost:8010/#/home](http://localhost:8010/#/home).

The container listens on port `8000`; Compose publishes it as host port `8010` by default. The SQLite database is stored at `/data/snowflake_certification.sqlite` and persisted in `./data`. No course/content archive volume is mounted.

Common operations:

```bash
docker compose logs -f snowflake-certification-guide
docker compose down
```

Run the deployed HTTP and mock-exam smoke test after the service becomes healthy:

```bash
BASE_URL=http://localhost:8010 python3 scripts/smoke_docker.py
```

To use a different host port when `8010` is occupied:

```bash
APP_PORT=8020 docker compose up --build -d
```

Inspect recent logs or force a clean image rebuild:

```bash
docker compose logs --tail=200 snowflake-certification-guide
docker compose build --no-cache
```

For an isolated clean-database test, set `BRAIN_DATA_DIR` to an empty host directory. Its default remains `./data`.

The image currently runs as the base image user. A fixed non-root UID can make Linux bind mounts fail when `./data` has a different owner; keep database permissions portable across macOS and Linux, or pre-create a writable data directory before adopting a fixed UID. No secrets are baked into the image, and offline labs require no credentials.

## Verification

Run the complete local gate:

```bash
./scripts/verify_all.sh
```

The V26 gate protects these invariants:

- exactly 5 COF-C03 domains with weights `31/20/18/21/10`
- exactly 19 Core task statements
- 19/19 written Core lessons
- direct certification ownership for questions and practice exams
- exact-set grading for multi-select questions
- current-task-only mapping trust
- no runtime course/video/transcript schema
- no legacy video/archive route surface
- persisted mock membership, answers, flags, deadline, grading, history, and idempotency
- scrypt password storage, hashed/revocable sessions, and active/expired memberships
- Guest, Free, three subscription plans, and one-time Exam Pack HTTP entitlement enforcement
- daily 20/100/250/500 question limits, weekly Free mock, monthly 2/4/unlimited Full Exam starts, and the Exam Pack 30-day window
- cross-candidate mock isolation and non-cancellable Free weekly sittings
- exactly three learner-visible certification paths, with only Core launchable
- no answer leakage from active timed sittings
- current/legacy practice isolation

GitHub Actions execution is separate from local verification. Do not treat a workflow that fails before runner assignment as a code/test failure.

The deployed runtime on `main` is identified by the `certification-native-v26` health marker. Historical V24/V25 runtime files are not part of the active SPA.
