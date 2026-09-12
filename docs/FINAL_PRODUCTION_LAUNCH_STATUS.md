# Final Production Launch Status

Last reconciled: 2026-09-12 UTC

Repository: `rrahul0904/snowflake-brain`

Production URL: `https://snowflakecertificationguide.vercel.app`

Release identity source of truth: `GET /api/release` plus the Vercel production deployment metadata. The last fully-audited production baseline before PR #46 was `c27e7ef88c6ce29836be6bc8f4b1f0de75590195`.

## Product scope decision

Video learning is intentionally **not part of the product**. It is not a pending launch feature. The approved product boundary is documented in `docs/PRODUCT_SCOPE.md` and enforced by `scripts/test_product_scope.py` plus the retired-media guard in `scripts/verify_all.sh`.

## Current decision

# APPLICATION/RUNTIME BASELINE HEALTHY · CONTENT RELEASE AND EXTERNAL PROVIDER EVIDENCE PENDING

The production application is healthy on managed PostgreSQL and the request-serving database role is least privilege. Google OAuth is configured. Paid billing remains disabled by design for the current free-launch posture.

Two live production dependencies are confirmed incomplete rather than merely undocumented:

1. the approved private COF-C03 question bank has **not been imported/activated** in the production database; and
2. production account email is still configured as the development outbox rather than a real transactional provider.

PR #46 makes the second condition fail closed: hosted production no longer creates new email/password registrations or recovery/change-email actions that cannot actually be delivered. Existing password login remains available, and new candidates can use the configured Google OAuth path.

Do not declare the full certification experience production-complete until the private bank is governed through QA, genuine SME approval, staging, activation, exact count verification, and live isolation testing.

## Live verified state

| Area | Live evidence | State |
| --- | --- | --- |
| Vercel deployment | Exact audited `main` release was READY | PASS |
| `/api/health` | HTTP 200; PostgreSQL + structured observability | PASS |
| `/api/ready` | HTTP 200; PostgreSQL pool ready | PASS |
| Runtime DB identity | Active `snowflake_app_runtime_*` role observed in Neon | PASS |
| Runtime privilege boundary | no superuser/createdb/createrole/replication/bypass-RLS; public schema CREATE denied; sensitive bank/control tables SELECT-only | PASS |
| Hosted security soak | 20-request / 41-probe run, security headers present, zero findings | PASS |
| Static/private-file exposure | zero findings; source maps unavailable; protected-looking paths do not expose files | PASS |
| Repository governance | protected PR merge requirements and required checks demonstrated on PR #45 | PASS |
| Video/course/media runtime | excluded from scope and guarded from reintroduction | PASS / INTENTIONAL |
| Google OAuth configuration | provider enabled; production start redirects to Google with production callback, state, nonce, PKCE, secure state cookie | CONFIGURED |
| Google human round trip | new/returning/link/logout/re-login not independently exercised with a real Google identity in this audit | EVIDENCE PENDING |
| Billing | `/api/billing/config` reports disabled | DISABLED BY DESIGN |
| Production question rows | `snowpro-core` question count = **0** | BLOCKER |
| Active production bank release | none | BLOCKER |
| Expected governed bank | 1,200 total: 216 free / 504 practice / 360 mock_reserved / 120 diagnostic | NOT YET DEPLOYED |
| Account email delivery | development outbox; 2 queued verification messages observed | BLOCKER FOR EMAIL SIGNUP/RECOVERY |
| Existing candidate state | 3 accounts: 1 verified, 2 unverified at audit time | OBSERVED |
| Strict live hostile-subscriber proof | cannot be final-certified until active bank exists | BLOCKER AFTER BANK ACTIVATION |
| External alert delivery | structured app observability exists; real downstream delivery proof not yet recorded | EVIDENCE PENDING |

## Production question-bank release contract

The private corpus is deliberately not stored in the public repository. The controlled workflow `.github/workflows/production-question-bank-release.yml` requires the approved private source, verifies its pinned SHA-256, validates and imports it, creates an exact-source release, and promotes only to `qa_passed` during import.

The final promotion path remains deliberately separated:

`qa_passed` → genuine human `sme_approved` → `staging` → `active`

No code change, CI credential, or operator shortcut may fabricate SME approval. After activation, strict inventory must prove exactly:

- 1,200 active questions;
- 216 `free`;
- 504 `practice`;
- 360 `mock_reserved`;
- 120 `diagnostic`.

## Account delivery contract

Local/CI may use `ACCOUNT_EMAIL_DELIVERY_MODE=outbox` for deterministic lifecycle tests. A hosted Vercel runtime may not treat that outbox as a mail provider.

With PR #46:

- existing password login remains functional;
- Google sign-in remains available when Google is configured;
- new email/password registration is disabled when real transactional delivery is unavailable;
- password reset, verification resend, and change-email requests fail closed instead of creating undeliverable action links;
- the frontend follows the server capability contract and hides dead email actions;
- the standalone account page uses the canonical `DELETE /api/auth/sessions/{id}` revocation route.

A real webhook/provider can re-enable the email lifecycle without another product fork by setting the production email delivery configuration and proving real mailbox delivery.

## Strict release security contract

Ordinary `main` pushes continuously verify hosted liveness/readiness, security headers, and static/private-file exposure without requiring privileged production evidence credentials.

Final release certification is a separate strict action and remains fail closed. It must include:

- count-only production-bank inventory using a protected audit credential;
- the active 1,200-question release with exact pool counts;
- dedicated attacker/victim security-test identities;
- a passing live hostile-subscriber exercise against the real active bank.

Missing strict evidence may be reported as `evidence-pending` during ordinary continuous checks, but an observed runtime/static regression is always a hard failure.

## Remaining blockers that cannot be truthfully closed by repository code alone

1. Supply the approved private bank through authenticated private storage, run `import_to_qa`, complete genuine independent SME approval, promote to staging, and activate it.
2. Run strict production inventory and the dedicated attacker/victim live-bank security exercise after activation.
3. Connect/configure a real transactional email provider and prove registration verification, resend, reset, and change-email delivery to a real mailbox if email/password signup is to be enabled. Until then the product safely operates Google-first for new users.
4. Exercise the real Google OAuth human round trip for new account, returning login, existing-account link, logout and re-login.
5. Prove external operational alert delivery if external alerting is part of launch operations.
6. If a paid launch is desired later, finish live Stripe provisioning and billing E2E before enabling billing. Stripe is not a blocker for the intentionally free launch posture.

## GO rule

For the approved non-video scope, application code is release-ready only when the protected repository verification and production launch gates are green.

The **full certification website is not production-complete while the private bank is absent**, because practice, diagnostic, mock and adaptive question workflows cannot provide their intended production content with zero active questions.

No blocker may be closed by fabricating question content, bank counts, human SME approval, email delivery, security identities, OAuth completion, or payment/account status.
