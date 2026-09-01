# Stripe Production Setup — Snowflake Certification Guide

This runbook covers the existing Stripe Checkout + Billing + Customer Portal + signed-webhook implementation for `snowflakecertificationguide`.

Production URL: `https://snowflakecertificationguide.vercel.app`

Webhook URL: `https://snowflakecertificationguide.vercel.app/api/billing/webhook`

## Security rules

- Never commit `STRIPE_SECRET_KEY`.
- Never commit `STRIPE_WEBHOOK_SECRET`.
- Never copy database credentials, card/payment data, identity-verification data, payout details, or bank information into GitHub artifacts/docs.
- Browser checkout success is not an entitlement authority. Only verified Stripe webhook processing may change paid entitlements.
- Test and live products/prices/webhook secrets must remain separate.
- Create a webhook endpoint only when its one-time signing secret can immediately be stored in the correct encrypted deployment secret store.

## Account readiness

As of 2026-09-01, the connected live Stripe account is **not ready to accept production charges**. Charges and payouts are disabled and Stripe account onboarding/verification remains incomplete.

Complete the outstanding Stripe Dashboard onboarding requirements before setting `BILLING_ENABLED=true` in production.

Operational checklist:

- [ ] Stripe live account onboarding complete
- [ ] Terms of Service accepted in Stripe
- [ ] Identity/business verification complete
- [ ] Charges enabled
- [ ] Payouts enabled
- [ ] Business/support website configured
- [ ] Support email configured
- [ ] Statement descriptor reviewed
- [ ] Customer receipts reviewed
- [ ] Refund/cancellation policy linked from the product
- [ ] Customer Portal configured
- [ ] Revenue Recovery / Smart Retries reviewed
- [ ] Fraud/Radar settings reviewed
- [ ] Tax obligation decision recorded; use Stripe Tax threshold monitoring until registrations/collection requirements are confirmed

## Existing internal plans

| Internal plan | Product name | Amount | Billing | Entitlement summary |
|---|---|---:|---|---|
| `premium_20` | Premium 100 | $20 | Monthly | 100 questions/day, 2 full exams/month |
| `premium_40` | Premium 250 | $40 | Monthly | 250 questions/day, 4 full exams/month |
| `premium_100` | Premium 500 | $100 | Monthly | 500 questions/day, highest configured full-exam allowance |
| `exam_pack_35` | One-Time Exam Pack | $35 | One-time | Lifetime practice mock + one full exam within configured 30-day window |

## Stripe objects created

### Test mode

| Plan | Product ID | Price ID |
|---|---|---|
| `premium_20` | `prod_VB3DNMyhVMALsX` | `price_1UAh71RB8OGmEnBwrmYTR1Bl` |
| `premium_40` | `prod_VB3Do4NXObP1L2` | `price_1UAh76RB8OGmEnBwqxrrUSZD` |
| `premium_100` | `prod_VB3DKepgNdi3nu` | `price_1UAh7CRB8OGmEnBwbzIoly62` |
| `exam_pack_35` | `prod_VB3D1UFE5zzkNP` | `price_1UAh7HRB8OGmEnBwHAumtGCn` |

### Live mode

| Plan | Product ID | Price ID |
|---|---|---|
| `premium_20` | `prod_VB3Ehclc0A7sfo` | `price_1UAh7tRB8OGmEnBw4IELJdNO` |
| `premium_40` | `prod_VB3EMJfxgJTb1r` | `price_1UAh7zRB8OGmEnBwnR4LS5n1` |
| `premium_100` | `prod_VB3EBbsPfYvwl5` | `price_1UAh85RB8OGmEnBwLBW2xid9` |
| `exam_pack_35` | `prod_VB3E8V0honEYpJ` | `price_1UAh8CRB8OGmEnBwyYbQDzyK` |

These IDs are safe identifiers; they are not secret keys.

## Application environment mapping

The existing code expects these environment variable names.

### Test/preview mapping

```text
BILLING_ENABLED=true
APP_BASE_URL=<approved preview/test HTTPS origin>
STRIPE_SECRET_KEY=<encrypted test key>
STRIPE_WEBHOOK_SECRET=<encrypted test webhook signing secret>
STRIPE_PRICE_PREMIUM_100=price_1UAh71RB8OGmEnBwrmYTR1Bl
STRIPE_PRICE_PREMIUM_250=price_1UAh76RB8OGmEnBwqxrrUSZD
STRIPE_PRICE_PREMIUM_500=price_1UAh7CRB8OGmEnBwbzIoly62
STRIPE_PRICE_EXAM_PACK=price_1UAh7HRB8OGmEnBwHAumtGCn
```

### Production/live mapping

Do not install this until the Stripe account is activated, the live webhook exists, and its signing secret can be stored safely.

```text
BILLING_ENABLED=true
APP_BASE_URL=https://snowflakecertificationguide.vercel.app
STRIPE_SECRET_KEY=<encrypted live key>
STRIPE_WEBHOOK_SECRET=<encrypted live webhook signing secret>
STRIPE_PRICE_PREMIUM_100=price_1UAh7tRB8OGmEnBw4IELJdNO
STRIPE_PRICE_PREMIUM_250=price_1UAh7zRB8OGmEnBwnR4LS5n1
STRIPE_PRICE_PREMIUM_500=price_1UAh85RB8OGmEnBwLBW2xid9
STRIPE_PRICE_EXAM_PACK=price_1UAh8CRB8OGmEnBwyYbQDzyK
```

## Webhook configuration

Create a dedicated Snowflake Certification Guide endpoint. Do not reuse webhook signing secrets from other applications.

Endpoint:

```text
https://snowflakecertificationguide.vercel.app/api/billing/webhook
```

Events required by the current backend:

```text
checkout.session.completed
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
invoice.paid
invoice.payment_failed
```

The backend already verifies Stripe signatures, applies a five-minute timestamp tolerance, records event payload hashes, treats a processed event ID idempotently, rejects replay of an event ID with a different payload, rejects unknown subscription price mappings, and derives entitlements server-side.

### Safe webhook cutover

1. Confirm the deployment secret store is ready.
2. Create the Stripe webhook endpoint.
3. Copy the one-time signing secret directly to encrypted `STRIPE_WEBHOOK_SECRET`.
4. Do not paste the signing secret into GitHub, documentation, issue comments, logs, or chat transcripts.
5. Redeploy the intended environment so the server receives the new secret.
6. Send/trigger test events and require HTTP 2xx.
7. Confirm duplicate delivery is idempotent.
8. Confirm invalid/expired signatures are rejected.

## Customer Portal

A Customer Portal configuration was not present during the 2026-09-01 reconciliation. Configure it before paid launch.

Recommended launch behavior:

- allow payment-method updates;
- allow subscription cancellation;
- prefer cancel-at-period-end for standard cancellation;
- allow appropriate upgrades/downgrades only among the three subscription prices;
- do not expose the one-time Exam Pack as a subscription switch target;
- send the customer back to `https://snowflakecertificationguide.vercel.app/#/membership`.

The application already creates portal sessions for candidates who have an active Stripe subscription.

## Catalog verification

Run the repository verifier after installing environment variables:

```bash
EXPECTED_STRIPE_LIVEMODE=false python scripts/verify_stripe_catalog.py
```

for test mode, or:

```bash
EXPECTED_STRIPE_LIVEMODE=true python scripts/verify_stripe_catalog.py
```

for live mode.

It writes only non-secret verification evidence to:

`artifacts/stripe-catalog-verification.json`

The verifier checks:

- all four configured price IDs exist;
- amounts match the application catalog;
- currency is USD;
- recurring vs one-time mode is correct;
- test/live mode matches the intended environment;
- Stripe product metadata maps to `snowflake-brain` and the expected internal plan.

## Test-mode acceptance gate

Do not enable production billing until all are proven using dedicated test candidates:

- [ ] Premium 100 checkout completes
- [ ] `customer.subscription.created/updated` grants `premium_20`
- [ ] Premium 250 grants `premium_40`
- [ ] Premium 500 grants `premium_100`
- [ ] Exam Pack checkout records exactly one paid purchase
- [ ] Duplicate Exam Pack webhook does not duplicate the purchase
- [ ] Customer Portal opens for active subscription
- [ ] Cancel-at-period-end retains access until period end
- [ ] Subscription deletion removes subscription entitlement at the correct time
- [ ] `invoice.payment_failed` produces past-due behavior with configured grace period
- [ ] `invoice.paid` recovers entitlement
- [ ] Invalid signature is rejected
- [ ] Expired signature is rejected
- [ ] Replayed event ID with a different payload is rejected
- [ ] Unknown Stripe Price ID cannot grant paid access
- [ ] Browser success URL alone cannot grant paid access

## Live cutover gate

Only after test-mode acceptance, Stripe account activation, production DB/runtime hardening, and the private bank release are green:

1. Create and install the dedicated live webhook secret.
2. Install the four live Price IDs.
3. Set `APP_BASE_URL=https://snowflakecertificationguide.vercel.app`.
4. Set `BILLING_ENABLED=true`.
5. Redeploy the exact release candidate.
6. Require `/api/billing/config` to report Stripe enabled with all four plans.
7. Execute one controlled real payment only under the approved release test procedure.
8. Confirm webhook → database → entitlement → paid feature → Customer Portal.
9. Refund/cancel the controlled transaction if the test procedure calls for it.
10. Record only safe Stripe object IDs; never payment-method data.

Until these gates pass, billing must remain fail-closed.
