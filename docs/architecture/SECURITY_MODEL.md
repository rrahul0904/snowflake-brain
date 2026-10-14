# Security Model

## Principals and trust

Principals are anonymous visitors, authenticated candidates, server-authorized administrators/editors, controlled deployment jobs, and external providers. A browser session identifies a candidate; it does not grant a role, paid entitlement, answer key or release authority.

## Required controls

- Secure, revocable server sessions; candidate ownership on every private read/write; server-side role and entitlement checks.
- HTTPS, secure cookies in production, rate limits, security headers, same-origin mutation checks and CSRF protections.
- Grading and answer disclosure occur server-side. Timed sitting payloads omit answers until grading/review policy allows them.
- Candidate-facing question APIs expose bounded served history and candidate-owned state, never private-bank enumeration.
- Production PostgreSQL is mandatory. Runtime credentials are restricted to application DML; migration credentials stay in controlled jobs. No request-time migrations or bank imports.
- Content packages are validated and hashed; import, staging, approval, activation and rollback are audited. Human/SME gates cannot be inferred from automated QA.
- Logs and telemetry exclude stems, answer keys, explanations, cookies, credentials and provider secrets.
- Account export/deletion and retention behavior are implemented through candidate-owned lifecycle paths.

## Threat coverage

Threats include cross-account IDOR, hostile subscribers, bank scraping, answer leakage, role escalation, stale/replayed payment events, OAuth mix-up/session fixation, CSRF, package tampering, malicious intake, CI artifact leakage, editor self-approval and runtime migration abuse. Existing adversarial, OAuth, billing, bank-isolation, release-governance and PostgreSQL tests cover code behavior. Hosted denial and browser flows still require protected Preview evidence.

## Limits of current evidence

Source and CI checks do not prove the deployed runtime role, deployed OAuth/email/Stripe settings, external alert receipt, or protected Preview behavior. These remain UNKNOWN until observed through authorized hosted tests. See `docs/reconciliation/final-reality.md`.
