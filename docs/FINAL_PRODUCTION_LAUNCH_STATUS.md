# Final Production Launch Status

Last reconciled: 2026-09-02 UTC

Repository: `rrahul0904/snowflake-brain`

Production URL: `https://snowflakecertificationguide.vercel.app`

PR: #37 — Harden production PostgreSQL runtime boundary

Production/main SHA currently serving the canonical alias: `c37a9a6c9546fae691d90383672563518a355493`

Latest implementation SHA before this evidence refresh: `49b017e5926ac576930555b65ad7375abeb98c8d`

## Release decision

# PRODUCTION NO-GO

The code-side production convergence is substantially complete, including controlled runtime-role provisioning, governed private-bank release automation, secret-safe Stripe webhook/Portal provisioning, hosted billing fail-closed validation, and regression coverage. The release is still blocked by infrastructure credentials/actions that have not been executed, Stripe live-account onboarding, the governed production bank activation, real hosted E2E evidence, and independent PR approval.

## Current state

| Area | Current state | Status | Required next action |
|---|---|---|---|
| Current production | Canonical `/api/health` and `/api/ready` return 200 on PostgreSQL, but production still serves pre-PR `main` SHA `c37a9a6c...` | PASS for old production / BLOCKED for launch | Do not promote until PR #37 gates close; final deployment SHA must equal merged `main` |
| PR #37 | Open, mergeable, not merged | BLOCKED | Independent human `APPROVED` review plus remaining infrastructure gates |
| Repository CI | All 11 required release workflows and the Vercel Preview check are green on `49b017e...` | PASS for that exact head | Require the checks to rerun after any subsequent release-branch commit before merge |
| Hardened Preview | Exact-head Preview was rebuilt Ready after the fail-closed runtime configuration was set. Deployment Protection redirects probes to Vercel SSO before they reach the function, so this is build evidence only | BLOCKED | Run controlled hosted runtime credential provisioning, redeploy, then test an authorized Preview URL until health/readiness are stable |
| Hosted runtime configuration | HTTPS, secure cookies, rate limiting, PostgreSQL pool bounds, public schema, auto-import prohibition, and `BILLING_ENABLED=false` are configured for Preview and Production | PASS for non-secret contract | Preserve these fail-closed values through the final deploy |
| Runtime DB credential | `scripts/provision_hosted_runtime.py` + `Provision Hosted Runtime Credential` already create/rotate `snowflake_app_runtime`, reconcile ACLs, verify the exact role, and write only the generated runtime DSN to Vercel. No release secrets are configured in GitHub Actions | IMPLEMENTED / NOT EXECUTED | Add `PRODUCTION_DATABASE_MIGRATION_URL` and `VERCEL_TOKEN`; dispatch workflow and redeploy |
| Managed PostgreSQL | Active project identified as `snowflake-certification-guide-production` (`round-sunset-09172961`) | IDENTIFIED | Use controlled deployment job for migration/import writes; do not weaken request runtime privileges |
| Private bank source | Approved File Library corpus exists: `snowpro_core_cof_c03_private_bank_1200_beta_v2.json`, version `2026-08-14-beta-1200-v2` | SOURCE READY | Make the exact approved artifact available through authenticated private HTTPS storage for the release job |
| Private bank integrity | SHA-256 `da57f636a57180631448fda79cfdcad2acf8e38ae2f381ea891a8cea91e704c5`; 1,200 questions; pools 216 free / 504 practice / 360 mock_reserved / 120 diagnostic | PASS FOR SOURCE | Preserve hash and exact pool counts through controlled production release |
| Production bank release | Secure workflow exists and enforces ephemeral download, hash verification, validation, import, QA progression, count-only evidence, and exact pool counts | IMPLEMENTED / NOT EXECUTED | `import_to_qa` → genuine SME approval → `promote_sme` → `promote_staging` → `activate` |
| Stripe test catalog | Four active Snowflake test products/prices verified | PASS | Install test secrets/config in Preview and run full test lifecycle after Preview runtime is healthy |
| Stripe live catalog | Four active Snowflake live products/prices verified | PASS | Keep live billing disabled until account + E2E gates close |
| Stripe live account | `charges_enabled=false`, `payouts_enabled=false`; onboarding/TOS/verification incomplete | BLOCKED — HUMAN | Complete Stripe Dashboard onboarding/verification; do not fabricate identity/business data |
| Stripe webhook provisioning | New `scripts/provision_stripe_billing.py` + `Provision Stripe Billing` workflow discovers/validates catalog, creates one dedicated webhook, retains its one-time secret in memory, and directly writes Stripe secrets/config to the correct Vercel target | IMPLEMENTED / NOT EXECUTED | Add `STRIPE_TEST_SECRET_KEY`, `STRIPE_LIVE_SECRET_KEY`, `VERCEL_TOKEN`; dispatch test first. Interactive connector must not create a webhook without safe secret handoff |
| Stripe Customer Portal | New provisioning path creates/validates an app-specific Portal policy and writes `STRIPE_PORTAL_CONFIGURATION_ID` to Vercel. Runtime explicitly passes this ID when opening sessions | IMPLEMENTED / NOT EXECUTED | Dispatch controlled Stripe workflow. Interactive Stripe connector lacks Portal write permission |
| Portal launch policy | Payment-method update enabled; invoice history enabled; cancellation at period end; subscription plan switching disabled at launch | CODE/TEST PASS | Verify behavior in test-mode E2E before paid launch |
| Hosted billing completeness | Vercel startup now fails closed if `BILLING_ENABLED=true` without Stripe API key, webhook secret, app-specific Portal ID, and all four Price IDs | IMPLEMENTED | Keep production `BILLING_ENABLED=false` until every payment gate passes |
| Production billing API | `/api/billing/config` returns disabled; `/api/auth/providers` reports billing disabled | BLOCKED BY DESIGN | Enable only through controlled live provisioning after Stripe reports charges enabled and test E2E is green |
| Google OIDC | Provider reports enabled in production | PARTIAL | Run real candidate Google sign-in/link/logout/re-login E2E |
| Production email | Real delivery provider/lifecycle evidence not independently verified | BLOCKED | Configure/verify production mail webhook and registration/reset/email-change flows |
| Observability | App reports observability ready; real external alert delivery has not been independently proven | PARTIAL | Verify secret-backed destinations using sanitized synthetic alert evidence |
| Hosted hostile-subscriber proof | CI isolation is green on prior exact head; live proof against active production bank is not possible yet | BLOCKED | After bank/runtime convergence, run dedicated attacker/victim hosted security test |
| Final production soak | Not yet applicable to an exact merged SHA | BLOCKED | After merge/deploy, run at least 20 health + 20 readiness requests and inspect runtime logs |

## Stripe catalog

### Test mode

| Internal plan | Amount | Stripe product | Stripe price |
|---|---:|---|---|
| `premium_20` | $20/month | `prod_VB3DNMyhVMALsX` | `price_1UAh71RB8OGmEnBwrmYTR1Bl` |
| `premium_40` | $40/month | `prod_VB3Do4NXObP1L2` | `price_1UAh76RB8OGmEnBwqxrrUSZD` |
| `premium_100` | $100/month | `prod_VB3DKepgNdi3nu` | `price_1UAh7CRB8OGmEnBwbzIoly62` |
| `exam_pack_35` | $35 once | `prod_VB3D1UFE5zzkNP` | `price_1UAh7HRB8OGmEnBwHAumtGCn` |

### Live mode

| Internal plan | Amount | Stripe product | Stripe price |
|---|---:|---|---|
| `premium_20` | $20/month | `prod_VB3Ehclc0A7sfo` | `price_1UAh7tRB8OGmEnBw4IELJdNO` |
| `premium_40` | $40/month | `prod_VB3EMJfxgJTb1r` | `price_1UAh7zRB8OGmEnBwnR4LS5n1` |
| `premium_100` | $100/month | `prod_VB3EBbsPfYvwl5` | `price_1UAh85RB8OGmEnBwLBW2xid9` |
| `exam_pack_35` | $35 once | `prod_VB3E8V0honEYpJ` | `price_1UAh8CRB8OGmEnBwyYbQDzyK` |

These IDs are non-secret. API keys, signing secrets, database credentials, payment data, identity verification information, and payout/bank information must never be committed.

## Exact remaining launch sequence

1. Complete Stripe live account onboarding/TOS/verification until live charges and payouts are enabled.
2. Ensure GitHub Actions has `PRODUCTION_DATABASE_MIGRATION_URL` and `VERCEL_TOKEN`; dispatch `Provision Hosted Runtime Credential` for `snowflake_app_runtime`.
3. Redeploy the latest PR head and prove authorized Preview `/api/health` + `/api/ready` stability without runtime DDL or bank mutation.
4. Place the approved private bank behind authenticated private HTTPS storage and set the release-job source secrets.
5. Run `Production Question Bank Release` with `import_to_qa`; complete genuine SME approval; promote to staging and activate.
6. Require active count 1,200 and exact 216/504/360/120 pool counts with zero unclassified questions.
7. Add `STRIPE_TEST_SECRET_KEY`, `STRIPE_LIVE_SECRET_KEY`, and `VERCEL_TOKEN` to the approved GitHub secret store.
8. Dispatch `Provision Stripe Billing` in test mode against an approved Preview webhook URL and Preview membership return URL; then redeploy Preview.
9. Run Premium 100/250/500 + Exam Pack test checkout, signed webhook, idempotency/replay, cancellation/past-due/recovery, and app-specific Portal E2E.
10. After live account activation and all release gates, dispatch live Stripe provisioning against `https://snowflakecertificationguide.vercel.app/api/billing/webhook` and `https://snowflakecertificationguide.vercel.app/#/membership`, initially with billing disabled.
11. Verify live webhook/Portal/catalog; only then run controlled live provisioning with `enable_billing=true`, redeploy, and require `/api/billing/config` to expose all four plans.
12. Verify Google OIDC, real account email delivery, observability alerts, and dedicated hosted hostile-subscriber evidence.
13. Obtain independent PR approval.
14. Require all exact-final-head GitHub checks green and no unresolved P0/P1 issue.
15. Merge PR #37 into `main`; require Vercel Production Git SHA to equal the exact merge/main SHA.
16. Run final canonical production acceptance and 20+ health/readiness soak; inspect runtime logs.
17. Declare **PRODUCTION GO** only if the machine-readable release report contains no blockers.

Until every blocking item above is closed, the release remains **PRODUCTION NO-GO**.
