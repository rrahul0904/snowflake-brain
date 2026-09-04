# Public Launch Cutover

This document separates **application engineering readiness** from the external configuration required to put the Snowflake Certification Guide on the public internet for real candidates and paid transactions.

The codebase can be green while these deployment/provider steps are still intentionally unset. Do not treat placeholder configuration as a completed production cutover.

## 1. Domain, HTTPS and edge protection

Before public traffic:

- use the existing Vercel production hostname: `https://snowflakecertificationguide.vercel.app/`
- keep TLS, routing and edge protection on the existing Vercel project
- preserve the original HTTPS scheme/host correctly to FastAPI
- enable `FORCE_HTTPS=true`
- enable `AUTH_COOKIE_SECURE=true`
- keep `SECURITY_RATE_LIMIT_ENABLED=true`
- configure edge DDoS/bot/distributed rate limiting appropriate to the host
- set `APP_BASE_URL=https://snowflakecertificationguide.vercel.app`

Run `/api/health` and `/api/ready` through the real public HTTPS path after cutover.

## 2. Production PostgreSQL

- provision/use the intended managed Neon PostgreSQL project
- create a least-privilege runtime role and a separate migration role
- configure the pooled `DATABASE_URL` only in Vercel's encrypted Production environment
- run `python scripts/migrate_production.py` from an approved deployment job using `DATABASE_MIGRATION_URL`; Vercel startup must only verify schema compatibility
- configure provider-native backups/PITR in addition to application logical-backup procedures
- perform and retain evidence of at least one restore rehearsal for the production backup policy

SQLite is supported for local/test compatibility, not as the public production datastore.

## 3. Account email delivery

Production verification/recovery cannot rely on the local outbox.

Configure:

```text
ACCOUNT_EMAIL_DELIVERY_MODE=webhook
ACCOUNT_EMAIL_WEBHOOK_URL=...
ACCOUNT_EMAIL_WEBHOOK_TOKEN=...
ACCOUNT_EMAIL_ACTION_BASE_URL=https://snowflakecertificationguide.vercel.app
```

Then test with a real mailbox:

- registration verification
- resend verification
- password reset
- change email
- expired token
- reused token
- link opened while signed out

Do not log action tokens or mailer credentials.

## 4. Google sign-in (only if enabled)

Create a Google OAuth web application and register the exact production callback:

```text
https://snowflakecertificationguide.vercel.app/api/auth/google/callback
```

Configure:

```text
GOOGLE_AUTH_ENABLED=true
GOOGLE_OIDC_CLIENT_ID=...
GOOGLE_OIDC_CLIENT_SECRET=...
GOOGLE_OIDC_REDIRECT_URI=https://snowflakecertificationguide.vercel.app/api/auth/google/callback
```

Live cutover test:

- new Google candidate
- existing password account linking flow
- returning Google sign-in
- Google + password continuity to the same candidate ID
- logout/session revocation

Never commit the client secret.

## 5. Stripe billing (only if paid checkout is enabled)

Before setting `BILLING_ENABLED=true`:

- create the four intended products/prices in the production Stripe account
- configure the exact price IDs
- create the production webhook endpoint at `/api/billing/webhook`
- configure the webhook signing secret
- configure the Stripe Billing Portal for only the intended subscription products/prices
- verify tax handling for the business/entity and target customer locations
- publish/review the applicable Terms, privacy disclosures, cancellation/refund policy and customer-support contact before accepting real money

Configure:

```text
BILLING_ENABLED=true
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
STRIPE_PRICE_PREMIUM_100=price_...
STRIPE_PRICE_PREMIUM_250=price_...
STRIPE_PRICE_PREMIUM_500=price_...
STRIPE_PRICE_EXAM_PACK=price_...
```

Live-mode cutover test using the provider's supported test/production validation process:

- subscription checkout
- webhook activation
- upgrade/downgrade through portal
- cancellation through portal
- past-due/grace behavior
- duplicate webhook replay
- out-of-order webhook protection
- one-time Exam Pack purchase and expiry window
- account deletion blocked while recurring subscription is active

A browser return URL must never grant Premium by itself.

## 6. Monitoring and incident routing

Configure real values for:

- `OBSERVABILITY_METRICS_TOKEN`
- error webhook destination
- alert webhook destination
- log collection/retention
- uptime monitoring against `/api/health` and `/api/ready`

Exercise at least one non-production alert to prove the destination is reachable.

## 7. Private question-bank activation

- place the approved private artifact in an approved administrative import context
- import/stage it through the controlled PostgreSQL import process
- validate checksum/version metadata
- run automated QA
- complete the required human content/SME review for the release batch
- activate the intended immutable release explicitly
- verify candidate APIs do not expose bulk inventory or answers before grading

The 1,200-question manifest is a beta corpus manifest; automated QA is not a substitute for independent human SME review.

## 8. Commercial/legal/support readiness

Before unrestricted paid public launch, have the responsible business/legal owner review and publish the policies appropriate to the operating entity and customer geography, including at minimum:

- Terms of Use / Terms of Service
- privacy notice
- cancellation/refund policy
- customer support/contact method
- pricing/tax disclosures
- independent-study / non-affiliation disclaimer where appropriate

The application must not imply that its mock exam or readiness score is an official Snowflake exam, confidential scoring formula or guaranteed pass prediction.

## 9. Repository and release governance

- protect `main` with a GitHub branch protection rule or repository ruleset
- require pull requests for production changes
- require `Production Launch Gate`
- require `Certification Guide Smoke`
- restrict direct force pushes/deletions as appropriate
- create a release tag/immutable release marker for the exact green `main` SHA

The connected automation environment may not have permission to configure GitHub branch protection. Treat this as a GitHub repository-administration task, not an application code task.

## 10. Final production smoke

After the real deployment is live, test through the public hostname—not localhost:

- home/public pages on `https://snowflakecertificationguide.vercel.app/`
- create account
- verification email
- login/logout
- Google sign-in if enabled
- curriculum/lesson
- practice answer/grade
- diagnostic
- adaptive readiness + adaptive session
- weekly mock
- full mock for an authorized account
- progress/SRS/mistake notebook
- membership/account/security
- password reset
- export
- session revocation
- Stripe checkout/portal if enabled
- mobile viewport
- Firefox and Chromium
- `/api/health`
- `/api/ready`
- protected metrics behavior
- alert delivery

## GO / NO-GO

Public launch is **GO** only when:

1. the exact deployed application commit has a green Production Launch Gate,
2. the production host/provider configuration above is complete for every feature being enabled,
3. an approved question-bank release is active,
4. required business/legal/support policies are published for paid use,
5. the real public-host smoke test passes.

If Google or Stripe is intentionally disabled, their provider-specific cutover tests are not blockers for a free/email-only launch; the UI must continue to show those capabilities as unavailable rather than pretending they work.
