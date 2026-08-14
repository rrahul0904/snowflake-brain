# Google identity and trusted billing

Snowflake Brain keeps candidate identity, membership and billing as separate security boundaries. Google and password login both resolve to the same internal `candidate_id`. Paid access is never granted by browser state, a redirect URL or a reusable license key.

## Google OpenID Connect

Set these only in the deployment environment or secret manager:

```bash
GOOGLE_AUTH_ENABLED=true
GOOGLE_OIDC_CLIENT_ID=...
GOOGLE_OIDC_CLIENT_SECRET=...
GOOGLE_OIDC_REDIRECT_URI=https://YOUR_HOST/api/auth/google/callback
APP_BASE_URL=https://YOUR_HOST
```

For local Docker development the callback is normally:

```text
http://localhost:8010/api/auth/google/callback
```

Create a Google OAuth web application and register the exact callback URI. Production must use HTTPS. The application uses the authorization-code flow with `state`, `nonce` and PKCE S256. The callback verifies the Google ID token and then issues the normal Snowflake Brain HttpOnly session cookie; Google tokens are not used as application sessions.

If a Google identity returns an email already used by a password account, the app does not merge on email alone. It creates a short-lived pending link and requires the existing account password once. The linked Google subject then points at the same candidate ID, membership, progress and mock history.

## Billing authority

Paid plan configuration:

```bash
BILLING_ENABLED=true
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
STRIPE_PRICE_PREMIUM_100=price_...
STRIPE_PRICE_PREMIUM_250=price_...
STRIPE_PRICE_PREMIUM_500=price_...
STRIPE_PRICE_EXAM_PACK=price_...
```

Internal plan mapping is server-controlled:

| Provider price | Internal plan | Product |
| --- | --- | --- |
| `STRIPE_PRICE_PREMIUM_100` | `premium_20` | Premium 100 / $20 month |
| `STRIPE_PRICE_PREMIUM_250` | `premium_40` | Premium 250 / $40 month |
| `STRIPE_PRICE_PREMIUM_500` | `premium_100` | Premium 500 / $100 month |
| `STRIPE_PRICE_EXAM_PACK` | `exam_pack_35` | One-Time Exam Pack / $35 |

The browser sends only an approved internal product choice to `POST /api/billing/checkout`. The backend maps that choice to the configured provider price and creates hosted checkout for the authenticated candidate's billing customer.

Returning to `#/membership?checkout=success` **does not grant Premium**. Subscription or purchase access changes only after `POST /api/billing/webhook` verifies the provider signature, confirms customer ownership, maps the provider price to an internal plan and writes the membership transition.

Webhook processing is idempotent through the unique provider event ID. Membership transitions increment `entitlement_version` only when the actual plan or entitlement expiry changes. The audit log records the old plan, new plan, reason, source and provider event ID.

Recommended Stripe events include:

- `checkout.session.completed` for the one-time Exam Pack
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

Subscription access policy is centralized: `active` and `trialing` grant access; a cancelled subscription remains valid only through its future period end; `past_due` uses the configured grace window; unpaid/expired states fall back to Free (or a previously purchased Exam Pack).

## Development membership overrides

`scripts/set_membership.py` remains a local development CLI. It is not exposed through HTTP and writes `development_override` into the audit trail. Production upgrades must use trusted billing events.

## Security invariants

- No user-entered license key grants Premium.
- No `localStorage`, query parameter, cookie value or request body can set a membership plan.
- Billing customer ownership maps a provider customer to one candidate ID.
- Replayed billing events do not reapply entitlements.
- Google provider subject (`sub`), not email, is the permanent external identity key.
- Password and Google login can coexist on one candidate account.
- Google access/ID tokens are not persisted as Snowflake Brain sessions.
- Provider secrets are never committed to source control or baked into the Docker image.
