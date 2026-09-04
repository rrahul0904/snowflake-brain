# Production environment contract

Values are never included in this document. Vercel scopes values by Preview and
Production; request-serving deployments must not receive the migration URL.

| Classification | Variables / contract |
| --- | --- |
| Required | `DATABASE_URL` (runtime-role Neon URL), `APP_BASE_URL`, `AUTH_COOKIE_SECURE=true`, `FORCE_HTTPS=true`, `SECURITY_RATE_LIMIT_ENABLED=true`, `DATABASE_SCHEMA` |
| Required when billing enabled | `BILLING_ENABLED=true`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PORTAL_CONFIGURATION_ID`, `STRIPE_PRICE_PREMIUM_100`, `STRIPE_PRICE_PREMIUM_250`, `STRIPE_PRICE_PREMIUM_500`, `STRIPE_PRICE_EXAM_PACK` |
| External gate | Google OAuth client settings and callback registration; verified email delivery webhook; observability alert endpoint; Stripe live-account approval; private-bank source and SME approval |
| Optional | `OBSERVABILITY_METRICS_TOKEN`, alert/error webhook URLs, `ADMIN_REPORTING_TIMEZONE` (defaults to UTC) |
| Disabled until launch | `QUESTION_BANK_AUTO_IMPORT=false`, `ALLOW_MEMBERSHIP_DEV_OVERRIDE=false`; keep `BILLING_ENABLED=false` until live Stripe gates close |

`DATABASE_MIGRATION_URL` belongs only to the controlled migration job. It must
not be present in any Vercel request-serving runtime.
