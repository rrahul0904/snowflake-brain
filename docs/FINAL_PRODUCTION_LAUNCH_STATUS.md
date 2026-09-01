# Final Production Launch Status

Last reconciled: 2026-09-01 UTC

Repository: `rrahul0904/snowflake-brain`

Production URL: `https://snowflakecertificationguide.vercel.app`

Production Vercel project: `snowflakecertificationguide` (`prj_2SLKmOpeMM8ogNkXfNYHu7IyjYab`)

PR: #37 — Harden production PostgreSQL runtime boundary

Baseline hardening SHA inspected during this reconciliation: `323df9a839ddd8060493e96184a40434d55c522f`

Production/main SHA currently serving the canonical alias: `c37a9a6c9546fae691d90383672563518a355493`

## Release decision

# PRODUCTION NO-GO

The current production deployment is healthy, but the final hardened commercial launch is not complete. Do not merge or promote PR #37 until the remaining infrastructure and approval gates below are closed.

| Area | Expected | Current | Status | Evidence | Blocker | Required action |
|---|---|---|---|---|---|---|
| Canonical production | `/`, `/api/health`, `/api/ready` healthy | Production responds successfully; readiness reports PostgreSQL `public` schema ready | PASS for current production | Live Vercel checks on 2026-09-01 | This is the pre-PR production SHA | Re-run after final merge and require exact SHA match |
| Production SHA | Exact merged PR #37 SHA on canonical alias | `c37a9a6...` from `main` | BLOCKED | Vercel deployment `dpl_Db4MkL4bNCBPgrKCmhQZQmgbv7aN` | PR #37 not merged | Merge only after all release gates and independent approval |
| Hardened preview | PR #37 head serves successfully | Build is `READY`, but `/api/ready` returns `500 FUNCTION_INVOCATION_FAILED` | BLOCKED | Preview deployment `dpl_9SyMieYwzN7fMG8HhNNr9YWrHGYt` for baseline head `323df9a...` | Hosted `DATABASE_URL` has not yet been rotated to the dedicated least-privilege role | Run `Provision Hosted Runtime Credential`, then force a fresh preview deployment |
| PostgreSQL runtime role | Dedicated `snowflake_app_runtime`, no owner/DDL privileges | Provisioning/reconciliation code exists and CI role-separation tests pass; hosted preview still fails closed | BLOCKED | `scripts/provision_hosted_runtime.py`, `scripts/migrate_production.py`, PostgreSQL Production Smoke | Secret-bearing provisioning workflow has not been executed against hosted env | Supply GitHub secrets, dispatch workflow, redeploy, verify live runtime role |
| CI/security checks | Required PR checks green | Certification Guide Smoke, Security Assurance, V26 Visual Parity, PostgreSQL Production Smoke, Recording Feature Parity, V26 Demo Upgrade, Authenticated Bank Isolation, Adaptive Readiness, Account Lifecycle, Verified Credentials, Production Launch Gate all green on baseline hardening head | PASS | GitHub Actions for `323df9a...` | New commits must re-run the same checks | Keep branch green through final merge |
| PR review | No unresolved blocking threads + independent human approval | Sole P1 runtime-grant thread is resolved; no independent APPROVED review recorded | BLOCKED | PR #37 review thread state | Independent approval required by release rule | Obtain a real human approval; do not manufacture approval |
| Private question bank source | Approved private 1,200-question COF-C03 bank available outside Git/static assets | Private corpus is available outside GitHub and is not committed to the public repo | READY FOR IMPORT | Private bank version `2026-08-14-beta-1200-v2`, track `snowpro-core` | Secure production import/release has not been executed/verified | Use `question_bank_admin.py` through deployment-only DB access; never copy corpus into repo/static build |
| Active production question bank | 1,200 active release questions | Last release evidence in PR reports 0 questions/no active release; not re-verified against managed DB in this session | BLOCKED | PR #37 release blocker + count-only inventory tooling | Managed DB import/release still required | Validate/import private file, create release, promote QA → SME approved → staging, activate, run count-only inventory expecting 1,200 |
| Stripe catalog — test | Four configured plans with exact amounts | All four test-mode products/prices created and verified | PASS | Stripe catalog reconciliation 2026-09-01 | Vercel test/preview secrets not installed yet | Map test price IDs in the intended test environment and run `scripts/verify_stripe_catalog.py` |
| Stripe catalog — live | Four separate live-mode products/prices | All four live-mode products/prices created and verified | PASS | Stripe catalog reconciliation 2026-09-01 | Live account itself cannot charge yet | Complete Stripe account activation before live billing cutover |
| Stripe account readiness | Live charges/payouts enabled, onboarding complete | Charges disabled, payouts disabled, account details not fully submitted | BLOCKED | Stripe account capability/status read | Stripe onboarding/TOS/verification requirements remain | Complete required Stripe Dashboard onboarding and verification |
| Stripe webhook | Production endpoint configured with signing secret stored only in Vercel | No Snowflake Certification Guide webhook endpoint is configured | BLOCKED | Stripe webhook endpoint inventory | No safe secret handoff to Vercel has occurred yet | Create endpoint only when its signing secret can immediately be stored as encrypted `STRIPE_WEBHOOK_SECRET` |
| Stripe Customer Portal | Active portal configuration | No portal configuration exists in test or live mode | BLOCKED | Stripe portal configuration inventory | Dashboard configuration required | Activate/configure Customer Portal, cancellation behavior, payment-method updates, and allowed plan changes |
| Production billing API | `enabled=true`, provider `stripe`, four plans | `/api/billing/config` returns billing disabled | BLOCKED | Live API check 2026-09-01 | Stripe/Vercel billing secrets and price IDs not installed; Stripe account not activated | Configure Vercel secrets only after webhook/account readiness; redeploy; verify config |
| Google authentication | Production OIDC enabled and E2E verified | Provider reports Google enabled | PARTIAL | `/api/auth/providers` | Full browser login/linking lifecycle not executed in this reconciliation | Run dedicated production test candidate E2E |
| Production email | Real delivery provider, no dev outbox | Not verified | BLOCKED | Release checklist | Delivery configuration/evidence absent | Verify webhook delivery mode, action base URL, verification/recovery/change-email flows |
| Observability | Production alerts/metrics configured and redacted | App reports observability ready; live external alert destinations not independently verified | PARTIAL | `/api/ready` | Secret-backed alert destinations not inspected | Verify env names/config and test sanitized failure alerts |
| Hosted hostile-subscriber test | Dedicated attacker/victim accounts pass against real active bank | CI isolation test green; live test blocked until active production inventory and dedicated accounts exist | BLOCKED | Authenticated Bank Isolation CI + hosted release workflow | Real bank and production test credentials unavailable | Run hosted release security workflow after bank activation |
| Final soak | Minimum 20 consecutive health/readiness cycles on exact merged production SHA | Not applicable yet | BLOCKED | Release rule | Exact merged SHA not deployed | Run after merge/promotion; inspect runtime logs for DB/socket/startup-mutation failures |
| Rollback | DB/release/deployment rollback documented and executable | Existing bank release rollback and PostgreSQL backup tooling exist | PARTIAL | `question_bank_admin.py`, backup/release tooling | Final cutover rollback evidence not yet captured | Record exact pre-launch deployment/release IDs and rehearse restore/rollback path |

## Stripe catalog created during final-launch implementation

### Test mode

| Internal plan | Price | Stripe product | Stripe price |
|---|---:|---|---|
| `premium_20` / Premium 100 | $20/month | `prod_VB3DNMyhVMALsX` | `price_1UAh71RB8OGmEnBwrmYTR1Bl` |
| `premium_40` / Premium 250 | $40/month | `prod_VB3Do4NXObP1L2` | `price_1UAh76RB8OGmEnBwqxrrUSZD` |
| `premium_100` / Premium 500 | $100/month | `prod_VB3DKepgNdi3nu` | `price_1UAh7CRB8OGmEnBwbzIoly62` |
| `exam_pack_35` / One-Time Exam Pack | $35 once | `prod_VB3D1UFE5zzkNP` | `price_1UAh7HRB8OGmEnBwHAumtGCn` |

### Live mode

| Internal plan | Price | Stripe product | Stripe price |
|---|---:|---|---|
| `premium_20` / Premium 100 | $20/month | `prod_VB3Ehclc0A7sfo` | `price_1UAh7tRB8OGmEnBw4IELJdNO` |
| `premium_40` / Premium 250 | $40/month | `prod_VB3EMJfxgJTb1r` | `price_1UAh7zRB8OGmEnBwnR4LS5n1` |
| `premium_100` / Premium 500 | $100/month | `prod_VB3EBbsPfYvwl5` | `price_1UAh85RB8OGmEnBwLBW2xid9` |
| `exam_pack_35` / One-Time Exam Pack | $35 once | `prod_VB3E8V0honEYpJ` | `price_1UAh8CRB8OGmEnBwyYbQDzyK` |

These IDs are non-secret identifiers. API keys, webhook signing secrets, database credentials, identity verification data, and payout/bank information must never be committed here.

## Exact remaining launch sequence

1. Complete Stripe account activation/verification in Stripe Dashboard.
2. Configure the Stripe Customer Portal.
3. Ensure GitHub Actions has `PRODUCTION_DATABASE_MIGRATION_URL` and `VERCEL_TOKEN` without exposing values.
4. Dispatch `Provision Hosted Runtime Credential` with `snowflake_app_runtime`.
5. Redeploy PR #37 preview and require stable `/api/ready`.
6. Securely make the private 1,200-question JSON available to an approved deployment-only job.
7. Validate/import the bank with `scripts/question_bank_admin.py`.
8. Create a named release from that exact source, promote QA → SME approved → staging, then activate it.
9. Run `scripts/report_production_bank_inventory.py` with `REQUIRE_ACTIVE_BANK=true` and `EXPECTED_ACTIVE_QUESTION_COUNT=1200`.
10. Create Stripe test webhook; immediately store its one-time signing secret in the test/preview secret store; configure test price IDs.
11. Run full Stripe test-mode checkout/webhook/portal lifecycle.
12. Create Stripe live webhook only when its signing secret can immediately be installed as encrypted production configuration.
13. Configure production live price IDs and `BILLING_ENABLED=true`, then redeploy and verify `/api/billing/config`.
14. Verify production email delivery and Google OIDC with dedicated test candidates.
15. Run hosted release security + live hostile-subscriber verification against real active inventory.
16. Obtain independent PR approval.
17. Merge PR #37.
18. Require Vercel production deployment Git SHA to equal the exact merged `main` SHA.
19. Run 20+ production readiness cycles, core E2E acceptance, billing lifecycle, and log inspection.
20. Declare GO only if `artifacts/final-production-release-report.json` contains no blockers.

Until every blocking item above is closed, the correct release decision remains **PRODUCTION NO-GO**.
