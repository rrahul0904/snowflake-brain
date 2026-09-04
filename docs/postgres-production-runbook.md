# PostgreSQL Production Runbook

This runbook owns the production persistence boundary for the Snowflake Certification Guide. Vercel is the only production application runtime and managed Neon PostgreSQL is the only production persistence layer. SQLite remains supported strictly for local development and lightweight tests.

## Configuration

Required production setting:

Configure the pooled Neon `DATABASE_URL` only in the Vercel encrypted **Production** environment. Never copy that value into a local `.env`, Docker Compose file, repository file, browser code, log, error response or support ticket.

Recommended settings:

```bash
DATABASE_SCHEMA=public
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=12
DB_POOL_TIMEOUT_SECONDS=10
```

`DATABASE_URL` should come from the deployment secret store. Do not commit production credentials.

## Controlled migrations and runtime verification

PostgreSQL migrations live in:

```text
migrations/postgres/
```

They are applied in lexical order and recorded in `schema_migrations`. An approved deployment job runs `python scripts/migrate_production.py` with `DATABASE_MIGRATION_URL`, a distinct DDL-capable migration credential. The runner takes a PostgreSQL advisory lock, applies pending migrations, verifies the runtime credential can read the expected schema, and exits without printing credentials.

Normal Vercel/FastAPI startup does **not** run migrations, create schemas, auto-import question files or activate a release. It checks the current schema and database connectivity only; a missing/incompatible schema keeps readiness failed.

Readiness is exposed at:

```text
GET /api/ready
```

The readiness probe performs a real database round trip. `/api/health` remains process liveness and should not be used as a dependency-readiness gate.

## Local PostgreSQL stack (development/CI only)

```bash
docker compose up --build
curl http://localhost:8010/api/ready
```

Compose is never a production deployment path. It starts PostgreSQL first, waits for `pg_isready`, then starts the local application. The application itself is considered healthy only after `/api/ready` succeeds.

## SQLite to PostgreSQL migration

Take a filesystem copy/backup of the SQLite source before migration. Use a fresh PostgreSQL database or schema for the first migration rehearsal.

```bash
DATABASE_URL='postgresql://...' \
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite ./data/snowflake_certification.sqlite
```

The migration tool:

- installs the current PostgreSQL migrations first;
- copies only tables that exist in the source;
- preserves durable integer IDs used by candidate/session/release relationships;
- restores immutable question-version IDs after suppressing generated baseline duplicates;
- restores PostgreSQL sequence positions after explicit-ID insertion;
- refuses a non-empty target unless `--allow-nonempty` is supplied intentionally.

After migration, run the full application regression and compare row counts for candidate accounts, questions, attempts, exam sessions, releases, SRS state, and mistake notebook before cutover.

## Backup

Production backup requires PostgreSQL client tools compatible with the server version.

```bash
DATABASE_URL='postgresql://...' bash scripts/backup_postgres.sh
```

The script creates a custom-format `pg_dump`, verifies that `pg_restore --list` can read it, and writes a SHA-256 checksum beside the archive.

Recommended policy:

- automated daily logical backup;
- provider-native point-in-time recovery where available;
- encrypted backup storage outside the application host;
- retention appropriate to business/privacy requirements;
- routine restore rehearsal, not backup creation alone.

## Restore rehearsal

Restore is intentionally guarded because it is destructive to existing objects in the target database.

```bash
CONFIRM_RESTORE=1 \
DATABASE_URL='postgresql://RESTORE_TARGET...' \
bash scripts/restore_postgres.sh ./backups/snowflake-certification-YYYYMMDDTHHMMSSZ.dump
```

Always restore into a non-production target first. Validate `/api/ready`, candidate authentication, question counts, release state, historical exam rendering, and candidate learning state before using a restored database for production recovery.

## Concurrency model

Legacy SQLite code used `BEGIN IMMEDIATE` around scarce entitlement and quota mutations. The PostgreSQL adapter maps that boundary to a transaction-level advisory lock during the migration phase. This preserves correctness while PostgreSQL-native row-level locking is introduced incrementally.

Critical concurrency regressions cover:

- daily question quotas;
- timed-exam entitlement reservations;
- question-bank release activation;
- schema migration serialization.

## Indexes

The production schema includes candidate/question, due-review, exam-session, release-membership, and activity indexes. Important access patterns include:

```text
candidate_id + question_id
candidate_id + due_at
candidate_id + created_at / attempted_at
exam_session_id / session_id
release_id + question_id
track_id + release status
```

Use PostgreSQL query plans and production latency telemetry to tune further indexes; avoid adding speculative indexes without workload evidence.

## Failure handling

If the controlled migration job fails, do not deploy the application. Investigate the error, correct it through a new forward migration, rerun the controlled job, and then deploy. Do not edit an already-applied production migration file in place.

If `/api/ready` fails while `/api/health` succeeds, treat the incident as a dependency/database readiness failure.

## Cutover checklist

Before making PostgreSQL the production source of truth:

1. standard SQLite CI remains green;
2. PostgreSQL Production Smoke is green;
3. the existing regression suite passes against PostgreSQL isolation schemas;
4. SQLite -> PostgreSQL migration rehearsal succeeds on a production-like copy;
5. row-count and relationship checks reconcile;
6. backup archive verifies;
7. restore rehearsal succeeds into a clean target;
8. `/api/ready` reports PostgreSQL healthy;
9. concurrency tests admit exactly the configured entitlement/quota limits;
10. rollback procedure and previous database backup are documented for the deployment window.
