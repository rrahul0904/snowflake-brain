# Final Production Launch Status

Last reconciled: 2026-09-11 UTC

Repository: `rrahul0904/snowflake-brain`

Production URL: `https://snowflakecertificationguide.vercel.app`

Current production/main SHA: `89c12bc45177ed8987ac9ffdb06f9d07904ad07e`

Current production deployment: `dpl_6PSN8KmKZ3qXXzK6tKq5UzqUBYx8`

## Product scope decision

Video learning is intentionally **not part of the product**. It is not a pending launch feature and must not be counted as incomplete work. The approved product boundary is documented in `docs/PRODUCT_SCOPE.md` and enforced by `scripts/test_product_scope.py` plus the retired-media guard in `scripts/verify_all.sh`.

## Current decision

# APPLICATION BASELINE HEALTHY / FINAL RELEASE EVIDENCE PENDING

The production application is serving the current `main` SHA and is healthy on PostgreSQL. The remaining blockers are release/provider evidence, not a missing video feature and not a known production-runtime outage.

Do not declare unrestricted paid-production GO until the strict release evidence below is complete.

## Current verified state

| Area | State | Status |
| --- | --- | --- |
| Vercel production deployment | Current `main` SHA `89c12bc...` is deployed and READY | PASS |
| `/api/health` | Returns HTTP 200; product reports PostgreSQL and structured observability | PASS |
| `/api/ready` | Returns HTTP 200 with PostgreSQL ready | PASS |
| Recent production runtime | No Vercel runtime errors were observed in the most recent three-day review window | PASS |
| Runtime DDL boundary | Activity and learning-intelligence request paths no longer perform production PostgreSQL schema creation | PASS |
| Hosted liveness/security soak | 20-request health/readiness/security-header evidence passed on current production | PASS |
| Hosted static/private-file exposure | Protected/static exposure probe passed | PASS |
| Reverse-engineering P0/P1 product coverage | Machine-verifiable matrix has no missing/partial/unknown P0/P1 requirement | PASS |
| Video/course/media runtime | Explicitly excluded from scope and guarded from reintroduction | PASS / INTENTIONAL |
| Google provider configuration | Production reports Google enabled | CONFIGURED; real E2E still required |
| Billing | Production `/api/billing/config` reports disabled | DISABLED BY DESIGN until billing gates close |
| Private production question-bank inventory | Exact active release/counts are not independently verified by the latest hosted release job | BLOCKED EVIDENCE |
| Live hostile-subscriber proof | Dedicated production attacker/victim exercise has not been completed on the active bank | BLOCKED EVIDENCE |
| Production email lifecycle | Real mailbox registration/reset/change-email delivery proof is not recorded as complete | BLOCKED EVIDENCE |
| External observability delivery | Application observability is ready; external alert delivery proof is still required | BLOCKED EVIDENCE |
| Repository branch/ruleset protection | Operational GitHub administration item remains outside application code | EXTERNAL GOVERNANCE |

## Hosted Release Security contract

`Hosted Release Security` now has two distinct modes so CI does not confuse protected release evidence with application correctness.

### Continuous mode — ordinary push to `main`

This mode must pass the things that can be verified without protected production release credentials:

- production liveness/readiness soak;
- security headers;
- static/private-file exposure boundaries.

If protected database-audit or attacker/victim credentials are intentionally unavailable, the workflow writes explicit `blocked` evidence and the machine report returns `evidence-pending` instead of falsely reporting an application-code failure.

### Strict release mode — explicit manual dispatch

A release owner must manually dispatch `Hosted Release Security` with `require_active_bank=true` and, for final security certification, `exercise_live_bank=true`.

Strict mode remains fail-closed. It requires:

- an approved production database audit credential;
- an active private-bank release;
- exactly 1,200 active questions;
- exact pool counts of 216 free / 504 practice / 360 mock_reserved / 120 diagnostic;
- dedicated attacker/victim production security-test credentials;
- a passing live hostile-subscriber exercise.

Preferred database secret name: `PRODUCTION_DATABASE_AUDIT_URL`. The workflow retains compatibility fallbacks for the older protected database secret names, but the runtime application credential must remain least-privilege and must not be widened for this check.

## Remaining release work

1. Provide a protected read-only production database audit credential to GitHub Actions.
2. Confirm/import/promote the approved private bank through the governed release path.
3. Complete genuine human content and SME approval for the exact immutable bank release.
4. Run strict hosted release security and verify exact 1,200 total / 216 / 504 / 360 / 120 pool counts.
5. Run the dedicated attacker/victim live hostile-subscriber test.
6. Verify the production account-email lifecycle against a real mailbox.
7. Verify Google sign-in/link/logout/re-login if Google remains enabled for launch.
8. Prove external alert delivery with sanitized synthetic evidence.
9. If paid launch is desired, complete Stripe live-account/provider provisioning and test-mode E2E before enabling billing. Billing may remain disabled for a free launch.
10. Enable GitHub `main` branch/ruleset protection and required release checks.
11. Run the final exact-SHA production acceptance after the release commit is merged/deployed.

## GO rule

For the approved non-video scope, the application engineering baseline can be called feature-complete only when the normal repository verification and production launch gates are green.

Final public release is **GO** only when the applicable external/provider/security evidence is complete for the features being enabled. A free launch may intentionally keep Stripe disabled; an enabled provider may not be represented as verified until its real E2E evidence exists.

No blocker may be closed by fabricating bank counts, human SME approval, provider delivery, security identities, or payment/account status.
