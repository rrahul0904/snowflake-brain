# V26 Production Architecture

## Product boundary

Snowflake Certification Guide is a certification-preparation application centered on SnowPro Core COF-C03. The active runtime does not ingest, index, stream or track video courses, captions, transcripts, course folders or lesson media.

```text
Certification
  -> Blueprint
     -> Weighted domain
        -> Task statement
           -> Written lesson
           -> Question evidence
           -> Build exercise
  -> Practice / diagnostic / adaptive session
  -> Timed mock
  -> Candidate evidence
     -> SRS / mistakes / confidence / remediation
     -> domain and task readiness
```

## Runtime shell

`app/main.py` owns the FastAPI application, production middleware, startup migrations/schema convergence, readiness endpoints and router registration. `frontend/index-v26.html` is the only active SPA shell and loads `frontend/app-complete.js` plus `frontend/router-complete.js`.

Public SPA routes are limited to home, membership, about, changelog, privacy and secure account-action links. Certification study routes require a candidate session.

## Configuration and authored content

- `config/snowpro_core_cof_c03_blueprint.json` — canonical 5-domain / 19-task COF-C03 blueprint
- `config/study_content_core.json` — written lessons for all Core task statements
- `config/certification_catalog.json` — learner-visible certification catalog
- `config/certification_skill_map.json` — certification metadata / mapping support
- `config/snowflake_lab_challenges.json` — build exercises
- `config/exam_simulation.json` — preparation mock configuration

Commercial question wording is not stored in tracked frontend/config assets. Production bank content is mounted read-only through `PRIVATE_QUESTION_BANK_DIR`.

## Backend boundaries

### Persistence

`app/database.py` abstracts local SQLite and production PostgreSQL. Production uses PostgreSQL pooling and migrations under `migrations/postgres/`. CI verifies schema convergence, concurrent bootstrap, logical backup and clean restore.

### Candidate identity

- `app/auth.py` — scrypt credentials, hashed/revocable candidate sessions, candidate dependencies
- `app/routers/auth.py` — registration, login, logout, current candidate and session controls
- `app/account_lifecycle.py` / `app/routers/account.py` — verification, recovery, email/password changes, export and deletion
- `app/google_oidc.py` / `app/routers/google_auth.py` — Google OpenID Connect with state, nonce and PKCE

Email/password registration begins unverified. Verification/recovery tokens are hashed, expiring and single-use. Google and email/password methods resolve to the same internal candidate ID.

### Membership and billing

- `app/billing/` — provider mapping, trusted entitlement transitions and Stripe webhook authority
- `app/routers/billing.py` — public billing config, authenticated checkout/portal, provider webhook
- candidate membership state remains server-side; browser state cannot grant Premium

Stripe is configuration-driven and disabled until real deployment secrets and price IDs are installed.

### Certification content and question delivery

- `app/skill_brain.py` — certification/domain/task resolution
- `app/certification_content.py` — authored lesson/catalog helpers
- `app/question_bank.py` — private-bank import boundary
- `app/question_bank_releases.py` — active release snapshots and rollback
- `app/question_versions.py` — immutable question-version linkage
- `app/routers/question_bank_runtime.py` — authorized candidate question/session delivery
- `app/routers/question_bank_candidate_state.py` — candidate-specific question state

Correct answers and explanations are not exposed in active timed sitting payloads before grading.

### Learning intelligence

- `app/learning_intelligence.py` — SRS, mistake notebook, confidence, study plan and remediation persistence
- `app/adaptive_readiness.py` — evidence-based readiness, calibration, coverage, retention, runway and recommendation logic
- `app/routers/intelligence.py` — candidate learning APIs
- `app/routers/adaptive.py` — adaptive readiness and practice APIs

Adaptive selection remains inside the active question-bank release and normal tier/quota/history boundaries.

### Exercises, experience and supporting APIs

- `app/routers/skills.py` — curriculum/skill map
- `app/routers/experience.py` — candidate experience state
- `app/routers/labs.py` — build exercises
- `app/routers/activity.py` — candidate/public activity signals
- `app/routers/feedback.py` — feedback
- `app/routers/affiliate.py` — optional editorial affiliate resources; no display-ad network

### Observability and security

- `app/observability.py` — structured events, request IDs, latency/error metrics and alert sinks
- `app/security.py` — HTTPS enforcement, rate limiting, authentication boundary, security headers and same-origin mutation checks
- `/api/health` — process liveness
- `/api/ready` — database readiness
- `/api/metrics` — infrastructure-token-protected operational metrics

Production requires HTTPS, secure cookies, PostgreSQL, account-email webhook delivery and a read-only private-bank mount.

## Frontend architecture

`frontend/router-complete.js` maps V26 routes to ES-module views. Primary modules include:

- `home-v26.js`
- `certifications.js`
- `curriculum-v26.js`
- `lesson-v26.js`
- `progress-v26.js`
- `adaptive-v26.js`
- `practice-v26.js`
- `mock-landing.js`
- `mock-start-v26.js`
- `exam-session-v26.js`
- `exam-result-v26.js`
- `lookup-v26.js`
- `exercises-v26.js`
- `reference.js`
- `journal-v26.js`
- `membership-v26.js`
- `account-v26.js`
- `account-action-v26.js`
- `info-v26.js`

The style stack is layered under `frontend/styles/`, with final recording/account/membership polish loaded last where intentional overrides are required.

## Question and release governance

The private-bank lifecycle is:

```text
Draft
  -> automated QA
  -> human content review
  -> human SME approval
  -> staging
  -> active immutable release
```

Official-source freshness detects Snowflake documentation changes but never rewrites question wording or answers automatically. Historical exam sittings preserve the question versions used when the sitting began.

## Deployment model

### Local development

- SQLite-compatible local runtime is supported
- `./scripts/setup.sh`
- `./scripts/dev.sh`
- default URL `http://127.0.0.1:8000/#/home`

### Docker / production rehearsal

`docker-compose.yml` runs PostgreSQL 17 plus the application and mounts the private bank read-only. Default host URL is `http://localhost:8010/#/home`.

`deploy/production.env.example` documents the secure production contract; real secrets and provider credentials must live in the deployment secret store.

## Verification architecture

`./scripts/verify_all.sh` covers certification, auth, verification, Google identity, billing, tier transitions, question-bank isolation, releases, mocks, learning intelligence, observability, no-ad policy, retired-media guards and all frontend JavaScript syntax.

`./scripts/run_production_release_gates.sh` adds account lifecycle, source freshness, editorial maturity, adaptive readiness and the production launch gate.

`.github/workflows/production-launch-gate.yml` runs on pull requests and pushes to `main` and blocks on:

1. SQLite security/convergence + production image/Compose validation
2. PostgreSQL full regression + logical backup/restore
3. Chromium desktop, Firefox desktop and Chromium mobile browser/accessibility rehearsal
4. zero-blocker Production GO decision

The canonical release boundary is the exact `main` SHA that passes those jobs.
