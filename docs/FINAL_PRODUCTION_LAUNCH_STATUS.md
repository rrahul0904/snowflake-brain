# Final Production Launch Status

Last reconciled: 2026-09-16 UTC

Repository: `rrahul0904/snowflake-brain`

Production URL: `https://snowflakecertificationguide.vercel.app`

Audited production baseline at the start of this reconciliation: `2fa0d03a71d09259371ce363d50bb337fa797914`, Vercel deployment `dpl_J9S7zNta2iZSDCAd9WxzjvTtsBiM`.

The live release identity source of truth is `GET /api/release` plus Vercel production deployment metadata. Re-check those after every merge rather than treating the SHA above as a permanent release identifier.

## Product scope decision

Video learning is intentionally **not part of the product**. It is not pending GA work. The approved boundary is documented in `docs/PRODUCT_SCOPE.md` and enforced by `scripts/test_product_scope.py` plus the retired-media guard in `scripts/verify_all.sh`.

Billing is intentionally disabled. Stripe provider evidence is required only if paid billing is enabled later.

Email/password account lifecycle and production alert delivery remain part of the authoritative unrestricted-GA production contract. They may not be relabeled optional merely because the currently deployed runtime safely supports a narrower Google-first posture.

## Current decision

# APPLICATION/RUNTIME/CI/DEPLOYMENT MACHINERY READY · UNRESTRICTED GA STILL HAS EXTERNAL CONTENT/PROVIDER EVIDENCE GATES

The deployed application baseline is healthy: Vercel reports the exact audited deployment READY, `/api/health` and `/api/ready` return HTTP 200, PostgreSQL readiness is healthy, the release endpoint matches the audited Git SHA/deployment ID, and no Vercel production runtime error clusters were observed in the 24-hour view used for this reconciliation.

Application implementation is feature-complete for the approved non-video scope based on the repository's executable completeness, security, browser, database, visual and release checks. A fresh default-branch search also found no `TODO`, `FIXME`, `NotImplementedError`, or `placeholder` implementation markers.

That is not the same as unrestricted production GA. Three external evidence/provider areas still have to be completed truthfully:

1. approved private COF-C03 bank delivery, governed import, genuine independent SME approval, activation, exact inventory proof and hostile-subscriber proof;
2. real transactional account-email lifecycle delivery and public-host verification for registration/verification/recovery/change-email; and
3. real downstream production alert-delivery proof.

The current Google-first runtime is fail closed where transactional email is absent. It is suitable for controlled deployment/rehearsal, but it does not satisfy the authoritative unrestricted-GA smoke contract until the missing provider evidence is completed or the authoritative GA scope itself is explicitly changed and re-approved.

## Live verified state

| Area | Live evidence | State |
| --- | --- | --- |
| Audited protected `main` baseline | SHA `2fa0d03a71d09259371ce363d50bb337fa797914` | PASS |
| Vercel production baseline | READY deployment `dpl_J9S7zNta2iZSDCAd9WxzjvTtsBiM` built from the exact audited SHA | PASS |
| `/api/release` | production; exact audited Git SHA and deployment ID matched | PASS |
| `/api/health` | HTTP 200; PostgreSQL + structured observability | PASS |
| `/api/ready` | HTTP 200; PostgreSQL pool ready | PASS |
| Vercel runtime errors | no production runtime error clusters observed in the 24-hour view during the 2026-09-16 reconciliation | PASS |
| Required repository checks | protected release/security/browser/database/visual/Vercel checks green on the audited release | PASS |
| Scheduled official-source check | green on 2026-09-16 | PASS |
| Required-check trigger alignment | `postgres-production` now runs on every PR, matching the protected-branch requirement | PASS AFTER THIS CHANGE |
| Runtime DB identity | staged least-privilege `snowflake_app_runtime_*` role | PASS |
| Runtime privilege boundary | sensitive question-bank/control writes denied to request-serving runtime | PASS |
| Static/private-file exposure | private corpus excluded from public Git/static artifacts; exposure checks enforced | PASS |
| Video/course/media runtime | excluded from approved scope and guarded from reintroduction | PASS / INTENTIONAL |
| Google OAuth | production start uses canonical callback with state, nonce and PKCE | PASS |
| Google human round trip | new/returning/link/logout/re-login production evidence recorded in issue #25 | PASS |
| Billing | disabled by design | PASS / INTENTIONAL |
| Transactional account email | provider not configured; registration/recovery/change-email remain fail closed | BLOCKER FOR UNRESTRICTED GA |
| Production SnowPro question rows | latest protected database audit on 2026-09-15 reported 0 | BLOCKER |
| Active production bank release | latest protected database audit on 2026-09-15 reported none | BLOCKER |
| Expected governed bank | 1,200 total: 216 free / 504 practice / 360 mock_reserved / 120 diagnostic | NOT YET DEPLOYED |
| Strict live hostile-subscriber proof | final run requires the real active bank | BLOCKED BY BANK ACTIVATION |
| External alert delivery | structured observability is ready, but downstream responder-delivery proof is not recorded | BLOCKER FOR UNRESTRICTED GA |

## Repository completeness status

Current repository state is implementation-complete for the approved non-video application scope:

- no unresolved product implementation branch is required to finish the certification application itself;
- reverse-engineering completeness and product-scope contracts are enforced in CI;
- certification, practice, diagnostic, adaptive readiness, mock, account, Google identity, security, PostgreSQL, visual, accessibility and observability paths are covered by executable checks;
- independent SME release governance is enforced across the production workflow, question-bank admin CLI and editorial admin CLI;
- protected `main` requires the launch/security/database/browser/visual/Vercel checks;
- the `postgres-production` workflow trigger now matches that always-required branch-protection context, preventing docs-only PR deadlocks;
- no unresolved implementation markers were found in the default-branch code search for `TODO`, `FIXME`, `NotImplementedError`, or `placeholder`.

This implementation completeness does **not** fabricate production content or provider delivery evidence.

## Private question-bank release contract

Approved corpus expected by the controlled release pipeline:

- filename: `snowpro_core_cof_c03_private_bank_1200_beta_v2.json`
- bank version: `2026-08-14-beta-1200-v2`
- pinned SHA-256: `da57f636a57180631448fda79cfdcad2acf8e38ae2f381ea891a8cea91e704c5`
- total: 1,200
- free: 216
- practice: 504
- mock_reserved: 360
- diagnostic: 120

The corpus must remain outside public Git and public build artifacts.

The controlled workflow `.github/workflows/production-question-bank-release.yml` is implemented. It downloads the source ephemerally, verifies the pinned SHA-256, validates/imports the exact immutable payload, creates the release, and automatically advances only to `qa_passed`.

The required progression is deliberately separated:

`import_to_qa` → `qa_passed` → genuine independent human `sme_approved` → `staging` → `active` → inventory verification → strict hostile-subscriber acceptance.

The `sme_approved` transition requires a named independent reviewer plus a stable evidence reference and prevents self-approval by the release creator/import operator.

The available private File Library was searched again during the 2026-09-16 reconciliation. The exact corpus was not found; only implementation/runbook material referencing it was present. This is a real source/content dependency, not application code debt.

## Remaining unrestricted-GA gates

### 1. Private certification content and governance

1. Supply the approved private corpus through authenticated private storage using the existing production release secret contract.
2. Run governed `import_to_qa` and automated validation.
3. Obtain genuine independent SME approval for the exact immutable release and retain the stable approval evidence reference.
4. Promote to staging and activate.
5. Prove exact active inventory: 1,200 / 216 / 504 / 360 / 120 with no unexpected or unclassified rows.
6. Run the strict attacker/victim hostile-subscriber production exercise against the active bank.

### 2. Transactional account email

The GA product scope includes the email/password lifecycle and the final public-host smoke includes account creation, verification email and password reset. Before unrestricted GA:

1. connect a real transactional email provider using the existing fail-closed provider boundary;
2. enable only the lifecycle capabilities backed by that provider;
3. prove registration verification, resend, password reset and change-email delivery with a real mailbox; and
4. rerun the public-host account lifecycle smoke.

Until that evidence exists, the runtime correctly keeps registration/recovery/change-email disabled rather than issuing undeliverable actions.

### 3. Production alert delivery

Structured application observability/readiness is already healthy, but the authoritative public-launch smoke also requires alert delivery. Before unrestricted GA, connect the intended downstream responder channel and capture real delivery evidence from a controlled production alert exercise.

### Conditional later gate: paid billing

Stripe/live billing is not required while billing remains disabled. If paid launch is enabled later, complete live Stripe provisioning, webhook/Portal/tax configuration and billing E2E before exposing checkout.

## Deployment decision

The application code, infrastructure architecture, security boundaries, CI, Vercel deployment mechanism, Google identity path and governed private-bank release machinery are **deployable end to end**.

The currently deployed Google-first service is healthy and fail closed. However, **unrestricted GA is not yet fully unblocked** because the approved private bank/SME evidence, real transactional account-email delivery, and real downstream alert-delivery proof are external inputs that are still absent.

Do not remove or bypass those gates to make the status look green. The next work is provider/content activation through the already-built production paths, not another replacement application architecture.
