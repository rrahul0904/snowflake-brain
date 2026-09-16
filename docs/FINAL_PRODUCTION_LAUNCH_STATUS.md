# Final Production Launch Status

Last reconciled: 2026-09-16 UTC

Repository: `rrahul0904/snowflake-brain`

Production URL: `https://snowflakecertificationguide.vercel.app`

Current protected `main` SHA: `2fa0d03a71d09259371ce363d50bb337fa797914`

Current Vercel production deployment: `dpl_J9S7zNta2iZSDCAd9WxzjvTtsBiM`

Release identity source of truth: `GET /api/release` plus Vercel production deployment metadata.

## Product scope decision

Video learning is intentionally **not part of the product**. It is not a pending launch feature. The approved product boundary is documented in `docs/PRODUCT_SCOPE.md` and enforced by `scripts/test_product_scope.py` plus the retired-media guard in `scripts/verify_all.sh`.

Billing is intentionally disabled for the current Google-first free-launch posture. Stripe readiness is therefore not a free-launch blocker.

## Current decision

# APPLICATION, RUNTIME, CI AND DEPLOYMENT PATH READY · PRIVATE CERTIFICATION CONTENT RELEASE PENDING

The production application is deployed from the exact protected `main` SHA above, Vercel reports the deployment READY, `/api/health` and `/api/ready` return HTTP 200, PostgreSQL readiness is healthy, and the live release endpoint reports the same Git SHA and production deployment ID.

No unresolved repository PR exists. The required protected-branch launch/security checks on the current main release are green, including production GO, PostgreSQL convergence/restore, browser/mobile accessibility, certification smoke, security assurance, visual parity and Vercel deployment. A fresh repository sweep also found no `TODO`, `FIXME`, `NotImplementedError`, or `placeholder` implementation markers on `main`.

The only core free-launch product blocker is external content/governance evidence: the approved private COF-C03 question corpus is not present in the available private source and has not been imported/activated in production. Genuine independent SME approval cannot be fabricated by automation and remains intentionally fail closed.

## Live verified state

| Area | Live evidence | State |
| --- | --- | --- |
| Protected `main` | SHA `2fa0d03a71d09259371ce363d50bb337fa797914` | PASS |
| Vercel production | READY deployment `dpl_J9S7zNta2iZSDCAd9WxzjvTtsBiM` built from the exact `main` SHA | PASS |
| `/api/release` | production; exact Git SHA and deployment ID match | PASS |
| `/api/health` | HTTP 200; PostgreSQL + structured observability | PASS |
| `/api/ready` | HTTP 200; PostgreSQL pool ready | PASS |
| Vercel runtime errors | no runtime errors observed in the 24-hour production error view during the 2026-09-16 reconciliation | PASS |
| Required repository checks | protected release/security/browser/database/visual/Vercel checks green on the current release | PASS |
| Scheduled official-source check | green on 2026-09-16 | PASS |
| Runtime DB identity | staged least-privilege `snowflake_app_runtime_*` role | PASS |
| Runtime privilege boundary | sensitive question-bank/control writes denied to request-serving runtime | PASS |
| Static/private-file exposure | protected by CI/runtime controls; private corpus not stored in public Git | PASS |
| Video/course/media runtime | excluded from approved scope and guarded from reintroduction | PASS / INTENTIONAL |
| Google OAuth | production start uses the canonical callback with state, nonce and PKCE | PASS |
| Google human round trip | new/returning/link/logout/re-login production evidence recorded in issue #25 | PASS |
| Billing | disabled by design for free launch | PASS / INTENTIONAL |
| Transactional email | not configured; email/password registration/recovery/change-email remain fail closed; Google-first signup remains available | OPTIONAL / NOT FREE-LAUNCH BLOCKER |
| Production SnowPro question rows | latest protected database audit on 2026-09-15 reported 0 | BLOCKER |
| Active production bank release | latest protected database audit on 2026-09-15 reported none | BLOCKER |
| Expected governed bank | 1,200 total: 216 free / 504 practice / 360 mock_reserved / 120 diagnostic | NOT YET DEPLOYED |
| Strict live hostile-subscriber proof | final run requires the real active bank | BLOCKED BY BANK ACTIVATION |
| External alert delivery | structured app observability is ready; downstream paging proof is optional unless explicitly required by launch policy | OPTIONAL OPERATIONS EVIDENCE |

## Repository completeness status

Current repository state is feature-complete for the approved non-video free-launch application scope:

- no open pull requests;
- protected `main` release is deployed exactly to production;
- reverse-engineering completeness and product-scope contracts are enforced in CI;
- certification, practice, mock, readiness, account, Google identity, security, database, visual and observability paths are covered by executable checks;
- independent SME release governance is enforced across the production workflow, question-bank admin CLI and editorial admin CLI;
- no unresolved implementation markers were found in the default-branch code search for `TODO`, `FIXME`, `NotImplementedError`, or `placeholder`.

This does **not** mean the production certification experience has real question content. Application implementation and content release are deliberately separate gates.

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

The controlled workflow `.github/workflows/production-question-bank-release.yml` is already implemented. It downloads the private source ephemerally, verifies the pinned SHA-256, validates/imports the exact immutable payload, creates the release, and automatically advances only to `qa_passed`.

The required promotion path is deliberately separated:

`import_to_qa` → `qa_passed` → genuine independent human `sme_approved` → `staging` → `active` → inventory verification → strict hostile-subscriber acceptance.

The `sme_approved` transition requires a named independent reviewer plus a stable evidence reference and prevents self-approval by the release creator/import operator.

## What is actually still blocked

### Core free-launch blocker

1. Supply the approved private corpus through authenticated private storage using the existing production release secret contract.
2. Run governed `import_to_qa` and automated validation.
3. Obtain genuine independent SME approval for the exact immutable release and retain the stable approval evidence reference.
4. Promote to staging and activate.
5. Prove exact active inventory: 1,200 / 216 / 504 / 360 / 120 with no unexpected or unclassified rows.
6. Run the strict attacker/victim hostile-subscriber production exercise against the active bank.

The available private File Library was searched again during the 2026-09-16 reconciliation. The exact corpus/hash was not found; only implementation/runbook material referencing it was present. Therefore this remains a real source/content dependency, not code debt.

### Optional capabilities that are intentionally deferred

- Transactional email provider: required only if new email/password signup, verification, recovery or change-email are to be enabled. Current Google-first free launch remains fail closed and functional without it.
- External alert delivery: optional unless the launch policy explicitly requires downstream paging proof.
- Stripe/live billing: intentionally deferred and disabled for the free launch. Complete live Stripe provisioning and billing E2E before enabling paid checkout later.

## Deployment decision

The application, infrastructure, security boundaries, CI, production Vercel release, Google-first account path, and controlled private-bank release machinery are **deployment-ready end to end**.

The full SnowPro certification product is **not content-ready for unrestricted launch** until the real approved question bank is supplied, genuinely reviewed by an independent SME, activated, and post-activation isolation/inventory evidence passes.

Do not remove or bypass that final boundary. The correct next action is not another application feature branch; it is delivery of the approved private corpus and genuine reviewer evidence into the already-built release pipeline.
