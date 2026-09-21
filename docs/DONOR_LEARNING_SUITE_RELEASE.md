# Donor Learning Suite — Hosted Release Boundary

This document records the final hosted cutover contract for the combined LeetQuiz, Claude Certification Guide, Clouding Academy, and AcademyOS AI integration.

## Repository certification

The combined integration branch is `feat/donor-learning-suite-integration`.

Current certified integration head:

- Git SHA: `dfaed09fc19ea1dbf60bd35d92bcdf98a88a95f8`
- GitHub PR: #57
- Production Launch Gate: passed
- PostgreSQL Production Smoke: passed
- Security Assurance: passed
- Authenticated Bank Isolation: passed
- V26 Visual Parity: passed
- Certification Guide Smoke: passed
- Adaptive Readiness Smoke: passed
- Verified Credentials Smoke: passed
- Account Lifecycle Smoke: passed
- Reverse Engineering Completeness: passed
- Vercel build/deployment state: READY

These checks certify the code, migrations, security contracts, browser integration, and isolated PostgreSQL convergence. They do **not** prove that the shared managed PostgreSQL database has already received a new migration.

## Required hosted database cutover

The donor suite adds PostgreSQL migration:

`20260918_001_question_feedback`

The Vercel request-serving role is intentionally unable to run migrations. A fresh hosted runtime therefore fails closed until the controlled migration and privilege reconciliation completes.

Use the existing GitHub Actions workflow:

**Provision Hosted Runtime Credential**

Workflow file:

`.github/workflows/provision-hosted-runtime.yml`

Run it against the exact release branch/head being promoted, with:

- `PRODUCTION_DATABASE_MIGRATION_URL` available as the deployment-only migration credential
- `VERCEL_TOKEN` available
- runtime role base `snowflake_app_runtime`

The workflow executes `scripts/provision_hosted_runtime.py`, which:

1. creates a fresh staged least-privilege PostgreSQL runtime role;
2. runs all pending PostgreSQL migrations through the deployment-only credential;
3. reconciles runtime grants;
4. executes `assert_production_schema_ready()` using the staged runtime role;
5. updates Vercel `DATABASE_URL` for future Preview and Production deployments without printing credentials.

Do not add `DATABASE_MIGRATION_URL` to Vercel request-serving environments and do not weaken the application startup schema gate.

## Evidence already observed before cutover

Vercel preview deployment:

- deployment: `dpl_ApQZNQ7qpVZhjDHtWkV1RgdSLNrC`
- branch: `feat/donor-learning-suite-integration`
- SHA: `dfaed09fc19ea1dbf60bd35d92bcdf98a88a95f8`
- build state: `READY`

A runtime request on this exact preview returned HTTP 500 because application startup correctly detected the missing production migration:

`Production database/runtime role is not ready; run the controlled migration/privilege job before deploying the application (details: 20260918_001_question_feedback).`

This is a deployment-state blocker, not a repository-code failure.

## Post-migration acceptance

After the controlled workflow succeeds, create or redeploy an exact-SHA preview from the same release head. Do not certify the hosted donor suite until all of the following are true on that deployment:

- `/api/health` returns HTTP 200;
- `/api/ready` returns HTTP 200 and reports PostgreSQL ready;
- `/api/release` returns the exact expected Git SHA and `source_dirty=false`;
- there are no startup/schema runtime error clusters for the exact deployment;
- public `/discover` and `#/exam-guide` remain reachable;
- authenticated `#/question-studio`, `#/daily-session`, and `#/practice-hub` mount successfully;
- candidate question corrections can be submitted only for served questions;
- Founder Operations can read/triage the correction queue;
- the request-serving PostgreSQL role remains unable to perform schema DDL.

Only after those checks should the integration branch be considered hosted-certified for merge/promotion.

## Separate unrestricted-GA gates

This migration/cutover does not replace the existing unrestricted-GA dependencies:

- approved private 1,200-question SnowPro Core bank;
- genuine independent SME approval and activation;
- real transactional email delivery evidence;
- downstream production alert delivery evidence.

Those external evidence gates remain separate from donor-suite code completion.
