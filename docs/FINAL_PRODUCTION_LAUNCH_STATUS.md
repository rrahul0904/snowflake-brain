# Final Production Launch Status

Last reconciled: 2026-09-01 UTC

Repository: `rrahul0904/snowflake-brain`

Production URL: `https://snowflakecertificationguide.vercel.app`

Production Vercel project: `snowflakecertificationguide` (`prj_2SLKmOpeMM8ogNkXfNYHu7IyjYab`)

PR: #37 — Harden production PostgreSQL runtime boundary

Current hardening SHA verified during this reconciliation: `8d0fd9a3f649e5ddcf5a6fc5005db5d277968fd3`

Production/main SHA currently serving the canonical alias: `c37a9a6c9546fae691d90383672563518a355493`

## Release decision

# PRODUCTION NO-GO

Repository CI is fully green on the exact current hardening head, and the existing production deployment is healthy. The final hardened commercial launch is still blocked by secret-bearing infrastructure activation, the governed production bank release, Stripe account activation/configuration, live end-to-end evidence, and independent PR approval. Do not merge or promote PR #37 until those gates are genuinely closed.

| Area | Expected | Current | Status | Evidence | Blocker | Required action |
|---|---|---|---|---|---|---|
| Canonical production | `/api/health` and `/api/ready` healthy | Both return `200`; readiness reports PostgreSQL/public schema ready | PASS for current production | Live checks 2026-09-01 | This is still the pre-PR production SHA | Re-run after final merge and require exact SHA match |
| Production SHA | Exact merged PR #37 SHA on canonical alias | `c37a9a6c...` from `main` | BLOCKED | Vercel deployment `dpl_Db4MkL4bNCBPgrKCmhQZQmgbv7aN` | PR #37 not merged | Merge only after every release gate and independent approval |
| Hardened preview | Exact PR head serves successfully | Deployment `dpl_7PW5GGAp85CPB93BYdzTFV9LSGU4` is build `READY`, but `/api/health` fails with `500 FUNCTION_INVOCATION_FAILED` during application startup | BLOCKED | Exact preview SHA `8d0fd9a...`; Vercel runtime logs show startup RuntimeError/fail-closed behavior | Hosted `DATABASE_URL` has not been converged to the dedicated least-privilege runtime role | Run `Provision Hosted Runtime Credential`, redeploy exact head, then verify health/readiness soak |
| PostgreSQL runtime role | Dedicated `snowflake_app_runtime`, no owner/DDL privileges | Provisioning/reconciliation code and role-separation tests pass; hosted Preview still fails closed | BLOCKED | `scripts/provision_hosted_runtime.py`, `scripts/migrate_production.py`, green PostgreSQL Production Smoke | Secret-bearing provisioning workflow has not been executed against hosted env | Ensure `PRODUCTION_DATABASE_MIGRATION_URL` + `VERCEL_TOKEN`, dispatch provisioning workflow, redeploy |
| Managed PostgreSQL project | Active production Neon project resolved | `snowflake-certification-guide-production` / `round-sunset-09172961`, main branch `br-raspy-credit-afssvp59` | IDENTIFIED | Neon project metadata | Final release inventory must still be produced by the controlled release job | Use deployment-only release workflow for write/import operations |
| CI/security checks | All required exact-head checks green | Certification Guide Smoke, Security Assurance, V26 Visual Parity, PostgreSQL Production Smoke, Recording Feature Parity, V26 Demo Upgrade, Authenticated Bank Isolation, Adaptive Readiness, Account Lifecycle, Verified Credentials, and Production Launch Gate all succeeded | PASS | GitHub Actions for `8d0fd9a...` | Any subsequent branch commit retriggers checks | Keep exact final head green before merge |
| PR review | No blocking thread + independent approval | Existing P1 thread resolved; only automated COMMENTED review exists; no independent `APPROVED` review | BLOCKED | PR #37 review state | Independent approval required by release rule | Obtain legitimate human approval; do not self-approve |
| Private question bank source | Approved private 1,200-question COF-C03 artifact available outside Git/static assets | File Library contains `snowpro_core_cof_c03_private_bank_1200_beta_v2.json`; manifest confirms SHA-256 and 1,200 questions | READY, NOT DEPLOYABLE YET | Private bank + coverage manifest | GitHub Actions requires an approved private HTTPS source; File Library is not directly consumable by the release workflow | Place the approved file in private authenticated HTTPS storage and set release-job source secrets |
| Private bank integrity | Exact reviewed version/count/pools | Version `2026-08-14-beta-1200-v2`; 1,200 total; free 216, practice 504, mock_reserved 360, diagnostic 120 | PASS FOR SOURCE | Coverage manifest | Production import/release not executed | Preserve pinned hash and exact pool counts through activation |
| Active production question bank | Active immutable 1,200-question release | Last release evidence reports no active production release; not promoted/activated in this convergence session | BLOCKED | PR #37 operational blocker + count-only inventory workflow | Controlled import and governance progression still required | `import_to_qa` → human/SME approval → `promote_sme` → `promote_staging` → `activate`, then inventory gate |
| Stripe catalog — test | Four intended plans only | Four Snowflake test-mode products remain active with expected mapped Price IDs | PASS | Stripe product inventory 2026-09-01 | App test/Preview secret configuration and webhook E2E remain | Configure signing secret + test price mappings only in the intended test environment |
| Stripe catalog — live | Four separate live plans | Four Snowflake live-mode products remain active with expected mapped Price IDs | PASS | Stripe product inventory 2026-09-01 | Live account cannot charge yet | Complete Stripe account activation before live billing cutover |
| Stripe account readiness | Live charges/payouts enabled, onboarding complete | `charges_enabled=false`, `payouts_enabled=false`; account onboarding/TOS/verification still incomplete | BLOCKED | Stripe live account read 2026-09-01 | Human Stripe onboarding is required | Complete Stripe Dashboard requirements; do not fabricate verification data |
| Stripe webhook — test | Dedicated Snowflake test endpoint + signing secret in test secret store | No Snowflake Certification Guide webhook exists; existing test endpoints belong to other applications | BLOCKED | Stripe webhook inventory | No safe signing-secret handoff to Vercel is available through connected tools | Create only when secret can immediately be stored as encrypted `STRIPE_WEBHOOK_SECRET` |
| Stripe webhook — live | Dedicated Snowflake live endpoint + production signing secret | No live webhook endpoints configured | BLOCKED | Stripe live webhook inventory | Same secret-handoff requirement plus live account activation | Create during controlled live cutover and immediately install encrypted signing secret |
| Stripe Customer Portal | Active safe portal configuration | No active Portal configuration exists in either test or live mode | BLOCKED | Stripe portal configuration inventory | Current connected Stripe API surface exposes read-only portal configuration | Configure in Stripe Dashboard or another authorized write path, then verify app portal session |
| Production billing API | `enabled=true`, provider `stripe`, four plans after all payment gates | `/api/billing/config` returns `enabled=false`; `/api/auth/providers` shows billing disabled | BLOCKED BY DESIGN | Live API check 2026-09-01 | Webhook/Portal/account/live-secret gates incomplete | Keep `BILLING_ENABLED=false` until all test/live prerequisites are satisfied |
| Google authentication | Production OIDC enabled and E2E verified | Provider reports Google enabled | PARTIAL | `/api/auth/providers` | Full browser candidate lifecycle has not been executed in this reconciliation | Run dedicated production Google sign-in/link/logout/re-login E2E |
| Production email | Real delivery provider, no development outbox | Not independently verified | BLOCKED | Release checklist | Real delivery configuration/evidence absent | Verify production webhook mailer and registration/reset/email-change lifecycle |
| Observability | Production alerts/metrics connected and redacted | Application readiness reports observability ready; external alert destinations not independently verified | PARTIAL | `/api/ready` | Secret-backed destinations unavailable to this session | Verify actual production alert destinations and sanitized synthetic alert delivery |
| Hosted hostile-subscriber test | Dedicated attacker/victim accounts pass against real active bank | CI isolation is green; live hosted proof remains blocked | BLOCKED | Green Authenticated Bank Isolation CI | Active production bank and dedicated live test credentials required | Run hosted release security after bank activation/runtime convergence |
| Final soak | 20+ health/readiness cycles on exact merged production SHA | Not applicable yet | BLOCKED | Release rule | Exact merged SHA not deployed | Run after merge/promotion and inspect runtime logs |
| Rollback | Deployment/database/bank/billing rollback documented | Existing release rollback, backup tooling, and billing-disable switch exist | PARTIAL | Repository runbooks | Final cutover IDs/evidence not yet captured | Record exact pre-cutover deployment/release identifiers before production promotion |

## Verified Stripe catalog

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

1. Complete Stripe account activation/TOS/verification in Stripe Dashboard.
2. Configure safe Stripe Customer Portal behavior.
3. Ensure GitHub Actions has `PRODUCTION_DATABASE_MIGRATION_URL` and `VERCEL_TOKEN` without exposing values.
4. Dispatch `Provision Hosted Runtime Credential` using `snowflake_app_runtime`.
5. Redeploy the exact PR #37 head and require stable `/api/health` + `/api/ready`.
6. Put the already-approved private 1,200-question file behind authenticated private HTTPS storage and configure the release-job source secrets.
7. Run `Production Question Bank Release` with `import_to_qa`.
8. Complete genuine human/SME content approval, then `promote_sme`, `promote_staging`, and `activate`.
9. Require count-only inventory: total 1,200 and exact 216/504/360/120 pool counts with no unclassified items.
10. Create/configure Stripe test webhook only when its signing secret can immediately enter the encrypted test/Preview secret store.
11. Configure test Price IDs and run subscription + Exam Pack test-mode checkout/webhook/Portal E2E.
12. After Stripe live account activation, create live webhook and immediately install its signing secret in encrypted production configuration.
13. Configure live Price IDs and enable `BILLING_ENABLED=true` only after the payment gates pass; redeploy and verify `/api/billing/config`.
14. Verify Google OIDC and production email delivery using dedicated candidate accounts.
15. Run hosted release security + live hostile-subscriber verification against the real active bank.
16. Obtain independent PR approval.
17. Reconcile exact final-head CI after any infrastructure-supporting documentation/code commits.
18. Merge PR #37 only when all required gates are green.
19. Require Vercel production Git SHA to equal the exact merged `main` SHA.
20. Run 20+ production health/readiness cycles, core E2E acceptance, billing lifecycle verification, and runtime-log inspection.
21. Declare GO only when `artifacts/final-production-release-report.json` contains no blockers.

Until every blocking item above is closed, the correct release decision remains **PRODUCTION NO-GO**.
