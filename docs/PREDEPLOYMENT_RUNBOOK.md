# Predeployment runbook

1. Start from a clean release-candidate checkout; record the exact SHA.
2. Run `bash scripts/release_predeploy_certify.sh` and retain its secret-free
   artifact. The command must not invoke Vercel, Stripe live mode, or private
   bank activation.
3. Require the no-deploy certification workflow, PostgreSQL migration/role
   checks, security gates, and local browser matrix to pass for that exact SHA.
4. Freeze the SHA. Any source change invalidates the certification evidence.
5. Obtain independent approval and confirm external gates: SME approval for the
   private bank, live Stripe onboarding, real Google/email/alert proof.
6. Create one `FINAL_RELEASE` deployment through the established production
   workflow, then run the hosted health/readiness smoke and compare its SHA.

Rollback is a release decision, not a development shortcut: halt promotion if
the hosted health check, migration readiness, payment verification, or bank
governance evidence is red; retain the previous known-good production release
and investigate without creating speculative deployments. This runbook never
contains values for credentials or connection strings.
