# Snowflake Certification Guide — Production Readiness Gate

A production release is permitted only when every **blocking** row below is green on the same integrated `main` candidate. This checklist is the human-readable contract; `.github/workflows/production-launch-gate.yml` is the automated enforcement.

## 1. Platform and persistence — blocking

- [ ] PostgreSQL migrations apply from an empty database.
- [ ] SQLite remains green for local/test compatibility.
- [ ] Full certification regression passes on PostgreSQL.
- [ ] Concurrent entitlement and schema-bootstrap tests pass.
- [ ] `/api/health` liveness and `/api/ready` database readiness are healthy.
- [ ] Logical PostgreSQL backup completes and restores into a clean database.
- [ ] Restored database passes the required sanity query.

## 2. Candidate identity and privacy — blocking

- [ ] Registration starts email/password candidates unverified.
- [ ] Verification and password-reset links are hashed, single-use and expiring.
- [ ] Password reset/change revokes candidate sessions.
- [ ] Google-only identity unlink cannot lock the candidate out.
- [ ] Candidate export omits credentials, action/session tokens and provider payment identifiers.
- [ ] Active recurring billing blocks account deletion.
- [ ] Privacy deletion purges candidate-owned attempts, exams, SRS, notebook and preference state and leaves only a non-identifying receipt.

## 3. Certification content integrity — blocking

- [ ] Candidate question routes expose no private bank inventory or correct answers before grading.
- [ ] Timed mocks are server-managed and preserve immutable question-version linkage.
- [ ] Release activation/rollback and historical sitting immutability tests pass.
- [ ] Official-source freshness change detection never auto-rewrites question text/answers/explanations.
- [ ] When enabled, freshness policy blocks stale/needs-review release activation.
- [ ] When enabled, editorial policy blocks release transitions without current QA + human content + human SME approval for the exact immutable version.
- [ ] Private question-bank content remains outside tracked/static frontend paths.

## 4. Candidate learning and adaptive intelligence — blocking

- [ ] SRS, mistake notebook, confidence calibration, study plan and mock remediation pass candidate-isolation tests.
- [ ] Adaptive readiness passes on SQLite and PostgreSQL.
- [ ] Adaptive score explicitly states it is not a pass-probability forecast.
- [ ] Sparse evidence cannot produce a high-confidence readiness claim.
- [ ] Probable guesses, confidence, response time, retention debt, coverage and exam runway affect the model.
- [ ] Adaptive question selection stays inside the active release and flows through normal tier/quota/served-history delivery.

## 5. Security and operational reliability — blocking

- [ ] Structured logs redact secrets and do not log request bodies/query strings.
- [ ] Request IDs, HTTP/DB latency metrics, alert thresholds and readiness signals pass observability regression.
- [ ] Candidate/private APIs reject unauthenticated requests.
- [ ] Metrics are unavailable without the infrastructure token.
- [ ] Production profile requires HTTPS, secure cookies, rate limiting, PostgreSQL and webhook account-email delivery.
- [ ] Private bank mount is read-only.
- [ ] Concurrent readiness load completes with zero failures and stays within CI p95 budgets.

## 6. Browser, mobile, accessibility and SEO — blocking

- [ ] Chromium desktop smoke passes.
- [ ] Firefox desktop smoke passes.
- [ ] Chromium mobile viewport smoke passes.
- [ ] Authenticated Adaptive Readiness route renders without client/console errors.
- [ ] Pages have a main landmark, H1 and accessible names for links/buttons; no duplicate IDs or images without alt text in the exercised routes.
- [ ] Public shell has title, meta description, responsive viewport and skip-to-content accessibility baseline.
- [ ] Existing V26 visual-parity workflow is green.

## 7. Deployment rehearsal — blocking

- [ ] `docker compose --env-file deploy/production.env.example config --quiet` succeeds.
- [ ] Production image builds from `Dockerfile`.
- [ ] Production-only account lifecycle configuration is passed into the container.
- [ ] No `.env`, key, PEM, private bank or secret file is tracked.
- [ ] No display/programmatic ad SDK/network is present.

## 8. Editorial operations — ongoing after launch

The editorial framework can be production-ready while the bank itself remains an ongoing content operation. Automated QA **does not impersonate human SME review**. Each content release batch should continue through:

`Draft → automated QA → human content review → human SME approval → staging → active`

Domain bank-health and source-freshness reports determine which batch receives editorial attention next.

## Release decision

The automated launch workflow writes `artifacts/production-readiness-report.json`. A release is **GO** only when the workflow is green and the report contains:

```json
{"status":"pass","blocking_items":0}
```

Any failed workflow step or nonzero blocker count is **NO-GO**.
