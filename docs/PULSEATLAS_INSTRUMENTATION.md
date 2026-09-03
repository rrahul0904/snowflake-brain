# PulseAtlas portfolio observability

PulseAtlas is an optional downstream observability layer. Snowflake Brain remains authoritative for candidate accounts, progress, attempts, billing, credentials, and the private commercial question bank.

The integration intentionally derives telemetry only from HTTP method, normalized path and successful response status for a very small allowlist:

- `GET /api/health` → health status
- `POST /api/quiz/grade` → practice completion count
- `POST /api/mock/sessions/{id}/submit` → mock completion count

The middleware never reads request bodies or response bodies. Therefore question text, answer choices, selected answers, explanations, credential payloads, candidate notes and private-bank data cannot be included in these events.

Delivery happens on a daemon thread with a short timeout and fails open.

Configuration:

- `PULSEATLAS_ENDPOINT`
- `PULSEATLAS_WRITE_KEY`
- `PULSEATLAS_ENVIRONMENT`
