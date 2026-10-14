# Production Incident Runbooks

These procedures apply to the existing Vercel + Neon production architecture. Keep provider secrets in their consoles, preserve audit evidence, and never put question content, credentials, cookies or payment payloads into incident logs. Record the deployment SHA and UTC timestamps for every action.

## Database outage or elevated errors

1. Check `https://snowflakecertificationguide.vercel.app/api/health`, `/api/ready`, and `/api/release`; record status and SHA.
2. Check the Vercel function logs and Neon status/pool metrics. Do not print connection strings.
3. If readiness is failing, stop content or schema changes and keep candidate writes fail-closed. Do not switch production to SQLite.
4. Restore connectivity or the known-good Neon service configuration. If data recovery is needed, follow [`postgres-production-runbook.md`](../postgres-production-runbook.md) and restore to an isolated target first.
5. Confirm health/readiness and candidate-owned state on the recovered service; attach sanitized evidence to the incident record.

## Vercel outage or bad application deployment

1. Capture the failing deployment ID, candidate SHA, request IDs and sanitized logs.
2. Confirm whether the failure affects the current Production deployment or only Preview. Check the public `/api/health`, `/api/ready`, and `/api/release` endpoints.
3. For a bad Production deployment, use Vercel's deployment rollback control to restore the last known-good Production deployment. Do not edit GitHub branch protections or deploy an unreviewed local build.
4. Confirm `/api/release` reports the restored SHA and rerun the smoke checks linked from [`PRODUCTION_RELEASE_CERTIFICATION.md`](../PRODUCTION_RELEASE_CERTIFICATION.md).
5. Fix forward through PR review and the protected release gate.

## Bad question release or suspected bank-integrity failure

1. Stop activation and preserve the release ID, package digest, audit event IDs and alert request IDs. Never copy stems or answer keys into the ticket.
2. Use the audited question-bank release rollback operation to point to the prior eligible immutable release. Require the designated editorial/release operator and record the reason.
3. Verify the active release and counts through the approved count-only inventory report; verify candidate serving with synthetic/test evidence or authorized Preview access.
4. Investigate provenance, source freshness and approval evidence. Do not mark automated QA as human or SME approval.
5. Follow [`question-bank-editorial-runbook.md`](../question-bank-editorial-runbook.md) and preserve historical sittings.

## Suspected question leak or scraper

1. Record the route, timestamp, candidate/account reference (if lawfully available), request IDs and safe response headers. Do not preserve or forward leaked question text.
2. Restrict the affected candidate/session or route using server-side access controls and rate limits; preserve the production release while isolating the exposure.
3. Check access logs and bank-integrity alerts for enumeration patterns, source-map/static exposure, cross-account access and unusual served-history volume.
4. If protected content escaped, treat content as compromised: stop use of the affected release, prepare an approved replacement, notify the content owner, and preserve evidence under the incident policy.
5. Run `python scripts/test_authenticated_bank_isolation.py` and `python scripts/test_hosted_static_exposure.py`; perform protected Preview/Production validation only with authorized access.

## Email delivery outage

1. Check account lifecycle provider status and sanitized delivery/error events. Confirm only status codes/provider message IDs are logged.
2. Verify the webhook configuration in Vercel's environment settings without copying secret values into a terminal or ticket.
3. Keep registration, recovery and email-change actions fail-closed or visibly pending; do not claim delivery based on token generation or an outbox record.
4. Restore the mail provider and send a controlled verification/reset message to an authorized test account. Confirm receipt and action completion.
5. Follow [`account-lifecycle-runbook.md`](../account-lifecycle-runbook.md) and record the provider receipt evidence.

## Stripe outage, replay or stale event

1. Check `BILLING_ENABLED` state and Stripe event delivery in the provider console. Do not expose signing keys or full payment payloads.
2. Treat browser return URLs as informational. Do not manually grant paid access based on a checkout redirect or screenshot.
3. Reconcile only signature-verified, idempotent provider events using the existing billing reconciliation process. Review event age/order before replay.
4. If the event stream is untrusted or stale, disable new checkout as appropriate and keep entitlements fail-closed while investigating.
5. Resume only after signed webhook and entitlement state agree; attach a sanitized event ID and test evidence.

## Google OAuth outage or identity mix-up

1. Disable Google sign-in only through the authorized deployment configuration if the provider transaction cannot be trusted; preserve password sign-in where healthy.
2. Inspect callback host, state, nonce and PKCE transaction binding, session continuity and provider status. Never log authorization codes or tokens.
3. Do not merge identities using email alone. Follow the existing account-linking and identity-continuity rules.
4. Re-enable only after a browser lifecycle rehearsal proves start, callback, session, logout, re-login and stable internal candidate identity.

## Content freshness event

1. Record the official Snowflake source URL, observed change and validation timestamp.
2. Run `python scripts/content_freshness_admin.py --help` to confirm the current supported read/scan commands, then use the documented freshness workflow. Do not infer changes from search snippets.
3. Create an editorial review item for affected lessons/questions. Automation may identify candidate changes but must not rewrite or promote answer content.
4. Update source provenance and review evidence; stage a new immutable release only after required human and SME gates.

## Alert delivery failure

1. Confirm the application emitted the sanitized alert type and request ID; check the configured provider delivery record.
2. Verify alert endpoint configuration in the secret store without reading values into logs or tickets.
3. Use a controlled test alert with the operations owner and confirm receipt in the destination. A local log line is not receipt evidence.
4. Keep an alternate human escalation path active until delivery is restored; document the outage window and affected alert types.

## Backup and restore

Use [`postgres-production-runbook.md`](../postgres-production-runbook.md). Back up through the approved role, verify the checksum, restore into an isolated target, validate schema/readiness/candidate state and governed release counts, then have the recovery owner approve any production cutover. Never restore directly over production as the first test.

## Release evidence

Every incident recovery or release should capture the exact app SHA, deployment ID, active content release ID where authorized, health/readiness/release responses, sanitized checks, operator and timestamp. Do not mark production accepted until the exact-SHA acceptance and rollback gates pass.
