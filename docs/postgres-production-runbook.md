# PostgreSQL Production Runbook

This runbook owns the production persistence boundary for the Snowflake Certification Guide. SQLite remains supported for local development and lightweight tests; production should configure `DATABASE_URL` and use PostgreSQL.

## Configuration

Required production setting:

```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
```

Recommended settings:

```bash
DATABASE_SCHEMA=public
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=12
DB_POOL_TIMEOUT_SECONDS=10
```

`DATABASE_URL` should come from the deployment secret store. Do not commit production credentials.

## Startup and migrations

Application startup calls the database migration boundary before any candidate routes are served. PostgreSQL migrations live in:

```text
migrations/postgres/
```

They are applied in lexical order and recorded in `schema_migrations`. A PostgreSQL advisory transaction lock serializes migration application so concurrent application replicas cannot race the schema bootstrap.

Readiness is exposed at:

```text
GET /api/ready
```

The readiness probe performs a real database round trip. `/api/health` remains process liveness and should not be used as a dependency-readiness gate.

## Local PostgreSQL stack

```bash
docker compose up --build
curl http://localhost:8010/api/ready
```

Compose starts PostgreSQL first, waits for `pg_isready`, then starts the application. The application itself is considered healthy only after `/api/ready` succeeds.

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

If startup migration fails, the application must remain not-ready rather than partially serve candidate traffic. Investigate the migration error, correct it through a new forward migration, and rerun startup. Do not edit an already-applied production migration file in place.

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
