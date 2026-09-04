# Predeployment certification

The canonical no-deploy gate is:

```bash
bash scripts/release_predeploy_certify.sh
```

It validates the additive migration, control-plane authorization contract,
subscription reconciliation dry run, source syntax, required release documents
and any supplied dedicated browser-matrix evidence, then writes
`artifacts/predeployment-certification.json`. It never invokes Vercel, Stripe,
or private-bank activation.

The reporting timezone is UTC. Admin metrics return zero for empty data and
`NOT_CONNECTED` for provider-cost data that has not been supplied. Retention:
operational snapshots are aggregate-only; audit rows exclude secrets and should
be retained for 365 days, while raw replay/auth telemetry follows the existing
candidate privacy and deletion policy.

Before `FINAL_RELEASE`, require the existing SQLite/PostgreSQL, browser-matrix,
security, question-bank, billing, and production launch workflows to be green
for the exact release SHA. Missing or failing browser evidence leaves this
certificate `BLOCKED`; the no-deploy job may still pass its own scoped checks,
but it is never a successful final-release decision or fallback. External items (live payment
onboarding, email delivery proof, Google sign-in proof, SME approval, and a
human production approval) remain external gates and must not be represented as
code-side passes.
