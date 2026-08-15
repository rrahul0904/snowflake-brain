# Production Observability and Incident Runbook

This runbook defines the operational visibility boundary for the Snowflake Certification Guide. The application emits low-cardinality metrics and structured JSON logs without request bodies, query strings, cookies, credentials, candidate email addresses, Stripe secrets, or answer selections.

## Signals

### Correlation IDs

Every HTTP response receives `X-Request-ID`.

- a caller-supplied ID is preserved only when it matches the safe request-ID format;
- malformed IDs are replaced with a generated opaque ID;
- the same ID is attached to structured request and exception events;
- request IDs are safe operational correlation values, not authentication tokens.

Use the request ID first when tracing a user-reported failure.

### Structured logs

The `snowflake.observability` logger writes one-line JSON records to stdout/stderr. Production container/platform logging should collect these streams centrally.

Representative events:

- `application_started`
- `application_stopped`
- `http_request_completed`
- `unhandled_exception`
- `database_migration_failed`
- `operational_alert`
- `question_bank_release_operation`
- `observability_sink_failed`

Optional sanitized error and alert payloads can be forwarded through:

```bash
OBSERVABILITY_ERROR_WEBHOOK_URL=https://telemetry.example/errors
OBSERVABILITY_ALERT_WEBHOOK_URL=https://incident.example/alerts
```

The application treats telemetry delivery as best-effort. A telemetry outage must never break candidate traffic.

## Metrics

Metrics are exposed as low-cardinality JSON at:

```text
GET /api/metrics
Authorization: Bearer <OBSERVABILITY_METRICS_TOKEN>
```

If `OBSERVABILITY_METRICS_TOKEN` is not configured the endpoint returns 404. Incorrect credentials return 401. When `FORCE_HTTPS=true`, metrics must be scraped over HTTPS.

The snapshot contains:

- HTTP request counts and status classes;
- route-template request counts;
- HTTP p50/p95/max latency samples;
- DB operation counts and latency by backend/operation;
- unhandled exception count;
- authentication failures;
- Stripe webhook failures;
- exam start/submit success or failure;
- question-bank release operations;
- readiness failures;
- background/content-operation failures;
- alert counts and rolling failure-window counts.

Never add candidate IDs, email addresses, question IDs, session IDs, payment IDs, or arbitrary user-supplied strings as metric labels.

## Liveness and readiness

`GET /api/health` proves that the application process is alive.

`GET /api/ready` performs a real database round trip. A database dependency failure returns HTTP 503 and emits a `database_unavailable` alert signal.

Infrastructure should:

- use `/api/health` for process liveness;
- use `/api/ready` for traffic readiness;
- remove an instance from traffic when readiness fails;
- alert when readiness repeatedly fails across instances.

## Alert thresholds

Defaults:

```bash
OBSERVABILITY_WINDOW_SECONDS=300
OBSERVABILITY_5XX_ALERT_THRESHOLD=5
OBSERVABILITY_AUTH_FAILURE_ALERT_THRESHOLD=10
OBSERVABILITY_ALERT_COOLDOWN_SECONDS=300
```

The built-in alert signals are intentionally small and operationally meaningful:

1. **API 5xx spike** — threshold of 5 in the rolling five-minute window by default.
2. **Database unavailable** — immediate readiness alert.
3. **Stripe webhook failure** — immediate signal when webhook handling is rejected/fails.
4. **Exam start failure** — operational exam-start failure signal.
5. **Exam submit failure** — operational exam-submission failure signal.
6. **Question-bank release activation failure** — immediate release-operation signal from the admin path.
7. **Abnormal authentication failure rate** — threshold of 10 login failures in five minutes by default.
8. **Background/content job failure** — immediate signal for startup/import/admin background boundaries.

Alerts are cooldown-limited per alert type to prevent storms. Tune thresholds after observing real production traffic rather than increasing label cardinality.

## Incident workflow

### API 5xx spike

1. Confirm `/api/ready` and database status.
2. Use the most recent request IDs from `unhandled_exception` / 5xx request events.
3. Compare route-template latency and DB latency metrics.
4. Check whether the failure correlates with a release, billing event, or deployment.
5. If a new deployment is implicated, roll back using the deployment platform's normal release mechanism.

### Database unavailable

1. Check PostgreSQL provider status and connection limits.
2. Confirm pool pressure through `database_health` / metrics.
3. Keep the affected application instance out of traffic while `/api/ready` fails.
4. Verify connectivity/credentials without printing the database URL.
5. Use the PostgreSQL production runbook for backup/restore or database recovery.

### Stripe webhook failure

1. Inspect the sanitized failure type and request ID.
2. Check Stripe/provider delivery status externally.
3. Do not manually grant entitlements based only on a browser callback.
4. Reprocess through the trusted webhook/provider event path when supported.
5. Confirm membership audit state after recovery.

### Exam start/submit failure

1. Trace the request ID and route-template event.
2. Confirm DB readiness and entitlement-reservation health.
3. For start failures, inspect reservation concurrency/entitlement errors.
4. For submit failures, preserve the existing exam session; do not mutate historical question-version links.
5. Reproduce against the same API contract in staging before applying a fix.

### Question-bank release activation failure

1. Inspect `question_bank_release_events` for the durable audit history.
2. Correlate with the `question_bank_release_operation` structured event.
3. Do not bypass release lifecycle states manually.
4. Correct the release or schema issue and retry through `scripts/question_bank_admin.py`.
5. If candidate content has already changed unexpectedly, use the supported release rollback command.

## Backup and restore signals

The PostgreSQL production foundation already provides:

- `scripts/backup_postgres.sh` — creates and verifies a custom-format logical backup and SHA-256 checksum;
- `scripts/restore_postgres.sh` — guarded restore procedure;
- `PostgreSQL Production Smoke` — performs an automated real backup → fresh-database restore rehearsal.

A production scheduler should treat a non-zero backup command exit as a background operation failure and forward that signal to the incident system. A backup is not considered valid until it can be listed by `pg_restore`; recovery confidence requires periodic restore rehearsals.

## Privacy and redaction rules

Never place these values in structured observability fields or metric labels:

- password/password hash/salt;
- Authorization headers;
- cookies/session tokens;
- OAuth state, nonce, verifier, identity-link tokens;
- Stripe secrets, webhook signatures, customer/payment/subscription IDs;
- candidate email or display name;
- selected answers/correct answers;
- raw request/response bodies;
- query strings containing user input.

When a new operational event is added, log an error *class/type* rather than an exception message whenever that message could contain user/provider data.

## Deployment acceptance checklist

Before production traffic:

1. `OBSERVABILITY_METRICS_TOKEN` is stored in the deployment secret store.
2. Central log collection receives valid JSON records.
3. Error/alert webhook sinks, if used, are TLS endpoints controlled by the deployment team.
4. `/api/health` and `/api/ready` are configured correctly in the platform.
5. The metrics endpoint is not internet-readable without its token.
6. A synthetic request shows the same `X-Request-ID` in response and structured logs.
7. A controlled 5xx test reaches centralized exception reporting without leaking request data.
8. A controlled DB readiness failure reaches the incident signal path.
9. Backup verification succeeds.
10. Restore rehearsal succeeds.
11. `scripts/test_production_observability.py` is green.
12. Standard and PostgreSQL full regression suites are green.
