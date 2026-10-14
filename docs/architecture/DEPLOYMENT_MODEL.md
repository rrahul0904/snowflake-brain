# Deployment Model

## Environments

- Local development supports SQLite compatibility and the existing V26 SPA/FastAPI service.
- CI validates SQLite security and PostgreSQL convergence, restore, browser and security contracts.
- Preview and Production use the existing Vercel project. Production persistence is managed Neon PostgreSQL; Docker and SQLite are not production dependencies.

## Credentials and change path

Request-serving deployments receive only the least-privilege runtime database credential and configured provider credentials. A separately controlled migration job uses the DDL credential. Governed bank imports are explicit deployment/editorial operations; runtime auto-import remains disabled. Values are held only in provider secret stores.

Candidate release procedure: commit to PR #57 lineage; pass required CI; deploy the exact SHA to protected Preview; certify API release identity, database role and denials, private content isolation, browser, accessibility, provider flows and recovery; obtain independent technical and human review; merge through protected main; deploy the exact merged SHA; verify Production endpoints, learner flow and rollback receipt.

## Release identity and rollback

`/api/release` is the runtime identity witness. The SHA must equal the intended commit at Preview and Production. Database backups are restored first into an isolated target and validated before any recovery use. Content rollback uses immutable governed releases; application rollback uses the previous known-good deployment. Preserve sittings and audit history.

## Current state

Production currently serves protected main `9b7dac244b978a67c3ac08449f970b921fcdb80f`. PR #57's candidate Preview is protected and anonymous endpoint access redirects to Vercel authentication; its runtime release identity has not been confirmed. See the reconciliation record for exact deployment IDs and blockers.
