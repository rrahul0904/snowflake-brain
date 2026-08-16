# Account Lifecycle, Recovery, Export and Deletion Runbook

This runbook owns candidate account recovery and privacy controls for the Snowflake Certification Guide.

## Browser entry points

Public recovery request:

```text
/static/recover-account.html
```

Secure emailed actions:

```text
/static/account-action.html
```

Signed-in self-service management:

```text
/static/account-management.html
```

The existing in-app Account area continues to own the normal candidate navigation/session experience. The standalone management surface is intentionally small and uses the same authenticated APIs so recovery/privacy controls remain usable even if the main SPA is being repaired.

## Email delivery

Account action tokens are random, single-use and time-limited. `account_action_tokens` stores only a SHA-256 token hash. A new token for the same candidate/purpose invalidates earlier unused tokens.

Supported delivery modes:

```bash
ACCOUNT_EMAIL_DELIVERY_MODE=webhook
ACCOUNT_EMAIL_WEBHOOK_URL=https://mailer.example/account-action
ACCOUNT_EMAIL_WEBHOOK_TOKEN=<deployment-secret>
ACCOUNT_EMAIL_ACTION_BASE_URL=https://guide.example/static/account-action.html
ACCOUNT_EMAIL_VERIFY_HOURS=24
ACCOUNT_PASSWORD_RESET_MINUTES=30
ACCOUNT_CHANGE_EMAIL_HOURS=2
```

`ACCOUNT_EMAIL_DELIVERY_MODE=outbox` exists for development/CI only. It stores the generated action URL in `development_account_outbox` so automated tests can exercise the complete lifecycle without sending email. Do **not** use development outbox mode in production because an action URL necessarily contains the bearer token.

`ACCOUNT_EMAIL_DELIVERY_MODE=disabled` is useful only for isolated development where recovery delivery is intentionally unavailable.

The webhook receives only:

```json
{
  "recipient": "candidate@example.com",
  "purpose": "verify_email | password_reset | change_email",
  "action_url": "https://guide.example/static/account-action.html/#/account-action?..."
}
```

The mailer should send the action URL as a transactional account-security email. It must not place the token in logs/analytics.

## Email verification

New accounts created through the public registration API are marked unverified and receive a verification action. Existing pre-migration accounts remain verified for backward compatibility.

Candidates can resend verification while authenticated. Resending invalidates the previous unused verification token.

Verification links are single-use and expire after the configured verification window.

## Password recovery

`POST /api/auth/password-reset/request` always returns the same accepted response for known and unknown addresses. This prevents account enumeration.

A successful reset:

- creates a new scrypt password hash/salt;
- enables password sign-in if the account was previously external-identity-only;
- records `password_changed_at`;
- consumes the reset token;
- revokes every candidate session.

The candidate must sign in again after reset.

## Password changes

Password-enabled accounts must supply the current password before changing it. External-identity-only accounts may add a password from an authenticated, verified account session.

Every successful password change revokes all sessions, including the browser that made the change.

## Email changes

A requested email change does not modify the account immediately. A confirmation token is sent to the **new** address. The account email changes only after that token is confirmed.

Confirmation:

- verifies the new address;
- changes the candidate account email;
- consumes the token;
- revokes all sessions.

The candidate must sign in again using the new address.

## Linked Google identities

Linked identities are visible in account status/management. Candidates may unlink an external identity when another sign-in method remains.

The application blocks unlinking the only external identity when password sign-in is disabled. The candidate must add a password first, preventing accidental account lockout.

Provider subjects and provider-side credentials are never included in the portable candidate export.

## Sessions

Existing APIs remain authoritative:

```text
GET  /api/auth/sessions
POST /api/auth/sessions/revoke
POST /api/auth/sessions/revoke-all
```

Password reset, password change and confirmed email change additionally revoke all sessions automatically.

## Portable data export

Authenticated candidates can download:

```text
GET /api/account/export
```

The JSON export includes:

- profile and verification state;
- membership history;
- exam history;
- practice attempts;
- task progress/mastery evidence;
- SRS state;
- mistake notebook;
- study preferences;
- bookmarks and notes;
- linked identity metadata;
- session timestamps (never session tokens);
- account lifecycle audit events;
- privacy-safe billing status summary.

The export excludes:

- password hashes/salts;
- raw account-action tokens or token hashes;
- session tokens;
- OAuth state/nonces/verifiers;
- provider customer/subscription/payment/event identifiers;
- Stripe secrets or webhook material.

The response is `private, no-store` and offered as `snowflake-certification-account-export.json`.

## Subscription-aware deletion

Permanent deletion requires:

1. an authenticated candidate;
2. literal confirmation text `DELETE`;
3. the current password when password sign-in is enabled;
4. no active recurring paid subscription.

Recurring subscription statuses that block deletion:

```text
active
trialing
past_due
unpaid
incomplete
```

The candidate must cancel the recurring subscription and wait until the paid/active period has ended before deleting the account. A completed/canceled subscription does not block deletion. One-time Exam Pack ownership does not prevent a candidate from exercising account deletion.

## Deletion semantics

Deletion is intended to remove candidate-owned application data, not merely detach the candidate ID.

Before deleting the candidate row, the application explicitly removes historical rows whose older foreign-key contract used `ON DELETE SET NULL`, including candidate practice attempts, exam sessions, learning events and feedback. Candidate-owned tables with cascade relationships are removed by foreign-key cascade.

The deletion path removes/invalidates candidate-owned:

- profile;
- sessions;
- identities;
- memberships and membership audit;
- billing-customer/subscription/purchase rows linked to the candidate;
- practice attempts;
- exam sessions and their session answers/questions;
- daily usage/activity;
- Exam Pack sets;
- bookmarks and notes;
- task progress;
- SRS state;
- mistake notebook;
- study preferences and learning sync state;
- account-action tokens/outbox/audit events;
- feedback/learning events explicitly linked to the candidate.

A random `account_deletion_receipts.receipt_id` remains with a generic reason and timestamp. The receipt stores **no candidate ID, email, display name, provider ID, or other direct account identifier**.

## Account lifecycle audit

`account_audit_events` records lifecycle actions such as verification, password changes, email changes, identity unlinking and export generation. It intentionally stores small operational metadata rather than credentials or action tokens. These rows are candidate-owned and are deleted when the account is deleted.

## Operational response

For suspected account takeover:

1. revoke all sessions;
2. change/reset the password;
3. verify the account email and linked identities;
4. inspect recent account lifecycle audit events;
5. rotate/remove an unexpected linked identity only after another sign-in method is confirmed.

For delivery failures:

1. confirm the configured webhook endpoint is healthy;
2. inspect sanitized `background_job_failure` / account-email delivery observability signals;
3. do not retrieve or copy bearer tokens from production logs;
4. request a new verification/reset/change-email action after delivery is restored, which invalidates the older unused token.

## Production acceptance checklist

1. `ACCOUNT_EMAIL_DELIVERY_MODE=webhook` in production.
2. Webhook URL and token are held in the deployment secret store.
3. `ACCOUNT_EMAIL_ACTION_BASE_URL` points to `/static/account-action.html` on the canonical HTTPS application origin.
4. Known/unknown password-reset requests are indistinguishable to callers.
5. Verification/reset/change-email tokens are single-use and expiration is enforced.
6. Password reset/change and confirmed email change revoke all sessions.
7. Google-only candidates cannot unlink their last sign-in method.
8. Export contains all documented candidate-learning categories and no credential/provider identifiers.
9. Active recurring subscriptions block deletion.
10. A deletion rehearsal proves candidate-owned attempts/exams/SRS/notebook/preferences/sessions are removed.
11. The deletion receipt contains no candidate identifier.
12. `Account Lifecycle Smoke` passes on both SQLite and PostgreSQL.
13. Standard Certification Guide Smoke, V26 Visual Parity and PostgreSQL Production Smoke remain green.
