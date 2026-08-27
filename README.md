# Snowflake Certification Guide

Production-oriented SnowPro Core COF-C03 certification preparation built around the current exam blueprint, written task lessons, private question-bank delivery, diagnostic and drill practice, timed mocks, adaptive readiness, persistent candidate accounts, verified SnowPro credential profiles, and production operations.

## Product boundary

The product is **certification-native**. It is not a video course platform and has no active course, academy, video-player, transcript-player, or media-library runtime.

```text
SnowPro Core COF-C03
  -> 5 weighted domains
     -> 19 task statements
        -> written lessons
        -> mapped question evidence
        -> quick reference / glossary
        -> build exercises
  -> diagnostic + drill practice
  -> adaptive 15-question practice
  -> weekly / full timed mocks
  -> persisted attempts, SRS, mistakes, confidence and study plan
  -> evidence-based readiness
  -> candidate-owned verified SnowPro credentials
```

Learner-visible certification catalog:

- **SnowPro Core — COF-C03**: available
- **SnowPro Advanced: Data Engineer — DEA-C02**: Coming Soon
- **SnowPro Advanced: Architect — ARA-C01**: Coming Soon

Only genuinely authored certification content is launchable.

## COF-C03 blueprint

`config/snowpro_core_cof_c03_blueprint.json` is the runtime blueprint contract.

| Domain | Weight |
| --- | ---: |
| Snowflake AI Data Cloud Features and Architecture | 31% |
| Account Management and Data Governance | 20% |
| Data Loading, Unloading, and Connectivity | 18% |
| Performance Optimization, Querying, and Transformation | 21% |
| Data Collaboration | 10% |

All **19 task statements** have written Core lessons in `config/study_content_core.json`.

## Candidate experience

Primary V26 routes:

- `#/home` — product / certification home
- `#/certifications` — certification catalog
- `#/curriculum` — five COF-C03 domains
- `#/domain` — domain task statements
- `#/skill` — full written task lesson
- `#/progress` — progress, due review and readiness evidence
- `#/adaptive` — evidence-driven next-study guidance and 15-question adaptive practice
- `#/practice` — practice, drill and diagnostic modes
- `#/mock` — mock landing and history
- `#/mock/start` — sitting confirmation
- `#/mock/session` — persistent timed exam player
- `#/mock/result` — score, analytics and answer review
- `#/quick-reference` — domain review sheets
- `#/glossary` — certification glossary
- `#/exercises` / `#/labs` — build exercises
- `#/reference` — curated resources
- `#/journal` — certification-focused technical articles
- `#/membership` — Free / Premium / Exam Pack plans
- `#/account` — account, verification, identities and sessions
- `#/credentials` — candidate SnowPro licenses/certifications and talent visibility
- `#/account-action` — email verification, email-change and password-reset actions
- `#/privacy`, `#/about`, `#/changelog` — public information pages

Study content, practice, progress, adaptive readiness, reference material, journal content, labs, credentials and mocks require a candidate account. Public routes are intentionally limited.

## Verified SnowPro credential foundation

Candidates can add the public Credly URL for a SnowPro certification. The server verifies issuer-backed evidence rather than trusting a screenshot or uploaded certificate image.

Automatic verification requires:

- a supported HTTPS Credly badge URL;
- issuer evidence identifying Snowflake;
- a SnowPro credential title;
- a conservative recipient-name match to the candidate profile;
- an active, non-expired credential.

Credential states include `verified`, `expired`, `needs_review`, and `rejected`. Every verification/reverification records an immutable verification event. The same Credly badge cannot be claimed by two candidate accounts.

Talent visibility is **private by default**. Candidates cannot enable recruiter/public discoverability until at least one active SnowPro credential is verified, and visibility is automatically disabled if the last active verified credential expires or otherwise stops qualifying.

The raw credential document upload, manual-review console, recruiter accounts/search, and introduction workflow are later marketplace slices and must not be represented as live today.

See `docs/VERIFIED_TALENT_MARKETPLACE.md`.

## Membership model

Server-side entitlements control question and exam allowances. Browser state cannot grant a paid plan.

| Plan | Price | Practice allowance | Timed exam allowance |
| --- | ---: | --- | --- |
| Free | $0 | 20 questions/day | one 30-question full-content mock/week |
| Premium 100 | $20/month | 100 questions/day | 2 Full Exam starts/month |
| Premium 250 | $40/month | 250 questions/day | 4 Full Exam starts/month |
| Premium 500 | $100/month | 500 questions/day | unlimited Full Exam starts |
| One-Time Exam Pack | $35 | lifetime fixed 100-question Practice Mock | 1 Full Exam start within 30 days |

All mocks are independent preparation simulations, not official Snowflake certification exams.

## Candidate identity and account lifecycle

Email/password registration starts **unverified** and creates the normal candidate session. Account lifecycle includes:

- email verification with hashed, expiring, single-use action tokens
- resend verification
- forgot-password and password reset
- change email
- active-session review and revocation
- password/session revocation controls
- candidate data export, including verified credential/talent-profile facts
- permanent account deletion subject to subscription checks
- visible verified/unverified status in the V26 account experience

Local development uses the account-action outbox. Production uses the configured webhook mailer.

### Google sign-in

Google OpenID Connect is implemented with authorization code flow, `state`, `nonce` and PKCE S256. Google identity resolves to the same internal candidate account; Google tokens are not used as application sessions.

Enable only after a real OAuth web client and the exact callback URI are registered:

```bash
GOOGLE_AUTH_ENABLED=true
GOOGLE_OIDC_CLIENT_ID=...
GOOGLE_OIDC_CLIENT_SECRET=...
GOOGLE_OIDC_REDIRECT_URI=https://YOUR_HOST/api/auth/google/callback
APP_BASE_URL=https://YOUR_HOST
```

See `docs/GOOGLE_AUTH_AND_BILLING.md`.

## Billing authority

Stripe hosted Checkout / Billing Portal integration is implemented but disabled until real deployment credentials are installed.

```bash
BILLING_ENABLED=true
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
STRIPE_PRICE_PREMIUM_100=price_...
STRIPE_PRICE_PREMIUM_250=price_...
STRIPE_PRICE_PREMIUM_500=price_...
STRIPE_PRICE_EXAM_PACK=price_...
```

Paid access changes only from verified server-to-server billing events. Returning from a checkout URL never grants Premium. Webhooks are signature-verified, idempotent and protected against stale/out-of-order subscription events.

## Question bank and editorial governance

Commercial question content is **private deployment content** and must never be committed into the public/static application.

The current private-bank manifest documents a 1,200-question COF-C03 beta corpus with exact five-domain / 19-task coverage. Runtime release governance provides:

- immutable question versions
- active release snapshots
- release activation / rollback
- historical sitting immutability
- source freshness monitoring
- automated editorial QA
- human content-review and SME-approval gates for governed releases

Automated QA does not impersonate a human Snowflake SME. Human review remains an editorial operation per release batch.

See:

- `docs/COF_C03_PRIVATE_BANK_1200_MANIFEST.md`
- `docs/PRIVATE_QUESTION_BANK_DEPLOYMENT.md`
- `docs/question-bank-editorial-maturity.md`
- `docs/content-freshness-pipeline.md`

## Adaptive learning intelligence

Candidate learning intelligence includes:

- spaced repetition / Due Today
- mistake notebook
- confidence 1–5
- study plan
- mock remediation
- evidence-based Adaptive Readiness
- coverage and recency decay
- calibration / probable-guess handling
- exam runway and daily-study recommendations

Adaptive Readiness explicitly is **not a pass-probability forecast** and sparse evidence cannot produce a high-confidence readiness claim.

## Architecture

### Backend

- Python 3.13
- FastAPI + Pydantic
- SQLite for local/test compatibility
- Vercel for the sole production application runtime
- managed Neon PostgreSQL for the sole production datastore
- connection pooling and migrations
- structured logs, request IDs, latency/error metrics and alert webhooks
- `/api/health` liveness
- `/api/ready` database readiness
- protected `/api/metrics`

Production persistence and backup/restore are exercised in CI against PostgreSQL 17.

### Frontend

- vanilla JavaScript SPA
- hash routing through `frontend/router-complete.js`
- native ES modules
- V26 responsive design system
- Chromium desktop, Firefox desktop and Chromium mobile launch rehearsal
- accessibility baseline and visual-parity capture

See `docs/ARCHITECTURE.md` for the current runtime map.

## Run locally

```bash
./scripts/setup.sh
./scripts/dev.sh
```

Open:

```text
http://127.0.0.1:8000/#/home
```

Health:

```text
http://127.0.0.1:8000/api/health
```

The expected marker includes:

```json
{
  "status": "ok",
  "product": "snowflake-certification-guide",
  "architecture": "certification-native-v26"
}
```

`scripts/dev.sh` loads a gitignored local `.env` when present. Never commit provider secrets.

## Docker (development / CI only)

```bash
docker compose up --build -d
docker compose ps
```

Open:

```text
http://localhost:8010/#/home
```

Compose runs a local PostgreSQL rehearsal stack plus the application. It is **DEVELOPMENT / CI ONLY — NOT PRODUCTION** and must never receive production credentials. Production does not mount question-bank files: an approved administrative job imports the private artifact into PostgreSQL, and the Vercel runtime serves only the active release.

## Production configuration

`deploy/production.env.example` is a **contract**, not deployable credentials. Configure production secrets only in the existing Vercel project's encrypted Production environment. The canonical production URL is `https://snowflakecertificationguide.vercel.app/`.

A public production cutover requires real values for the chosen deployment features, including:

- Vercel HTTPS domain / edge runtime
- managed Neon PostgreSQL with a pooled runtime URL
- metrics and alert destinations
- account-email webhook
- Google OAuth client if Google is enabled
- Stripe keys, webhook and price IDs if billing is enabled
- private approved question-bank release imported into PostgreSQL

See `docs/public-launch-cutover.md` and `docs/production-readiness-checklist.md`.

## Verification

Run the complete local regression bundle:

```bash
./scripts/verify_all.sh
```

Run the verified credential lifecycle smoke directly:

```bash
python scripts/smoke_verified_credentials.py
```

Run the production release bundle:

```bash
./scripts/run_production_release_gates.sh
```

The Production Launch Gate runs on pull requests and every push to `main`. It blocks on:

- SQLite security/convergence
- PostgreSQL full regression
- PostgreSQL logical backup + clean restore
- development/CI Compose validation
- development/CI image build
- Chromium desktop
- Firefox desktop
- Chromium mobile
- accessibility / client-error checks
- final machine-readable Production GO decision

A release is GO only when the integrated `main` gate reports zero blocking jobs.

## Release governance

Use pull requests for production changes and require the Production Launch Gate before release. The repository-level branch/ruleset protection is operational governance and should be enabled on `main` in GitHub settings.

The application source, private question content, provider credentials and production infrastructure are intentionally separate security boundaries.
