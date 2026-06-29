# Snowflake Brain - Implementation Status

Last updated: 2026-06-29

## Current Guardrail Phase

Status: in progress.

Scope:

- Add baseline inventory.
- Add API contracts.
- Add migration safety marker.
- Add verification scripts.
- Prevent package leaks.
- Prevent source-boundary and question-count regressions.

## Phase Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 0A - Baseline Inventory And Regression Lock | partial | Scripts added; baseline generated after script run. |
| Phase 0B - API Contract Freeze | partial | Current API contracts documented; Pydantic response models not yet added. |
| Phase 0C - Migration And Seeding Safety | partial | `schema_migrations` marker added; full migration runner not yet split into numbered files. |
| Phase 1 - Simplify Visible Product Scope | partial | Visible nav reduced earlier; route registry and route smoke test still pending. |
| Phase 2A - Content Trust Tables | partial | Tables/seeders exist; dedicated `/api/content-audit/*` route family pending. |
| Phase 2B - Manual Review Overrides | not started | Override endpoints pending. |
| Phase 2C - Exam Session Tables | partial | Initial session endpoints exist; abandon/resume/report/misses pending. |
| Phase 3 - Lessons Course Player | not started | Do not start until guardrails pass. |
| Phase 4 - Practice Runner | not started | Do not start until guardrails pass. |
| Phase 5 - Local Tutor | not started | Do not start until Practice/Lessons contracts are stable. |
| Phase 6 - Real Progress/Readiness | not started | Requires learning-event coverage. |
| Phase 7 - Review Cockpit | not started | Requires readiness and audit APIs. |
| Phase 8 - UI Consolidation | not started | Last step only. |
| Phase 10 - Verification Gate | partial | `scripts/verify_all.sh` added; route screenshot checklist pending. |

## Latest Verification

Last run: 2026-06-29.

Command: `scripts/verify_all.sh`

Result: passed.

Checks passed:

- Backend compile.
- Database migration rerun.
- API smoke tests.
- Source boundary check.
- Question count regression check.
- Frontend syntax checks.
- Clean package leak check.

Generated clean package:

- `dist/snowflake-brain-source-2026-06-29.zip`

## Stop Conditions

Pause immediately if:

- Total question count drops unexpectedly.
- A practice test loses questions.
- Tests merge by title.
- Lessons leak across courses/tracks.
- Package contains SQLite DB, `.venv`, `.git`, old `static/`, or paid content.
- Tutor requires external API key for local mode.
- Migrations cannot be rerun.
