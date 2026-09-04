# Production Release Certification

This checklist records the independently verifiable evidence required before
the Snowflake Certification Guide release may be promoted to production. It is
an operational record, not an authorization to deploy or activate content.

## Candidate and CI evidence

* Pull request: [#40](https://github.com/rrahul0904/snowflake-brain/pull/40)
* Initial certified candidate: `c48b84e44e22fec2728ed185128430687b7e30ef`.
  Any later PR head, including documentation-only changes, must complete the
  required checks again before approval.
* The certification record is the required-check set on the exact PR head;
  reviewers must reject stale, cancelled, or superseded runs.
* Historical run evidence for the initial candidate includes the
  [production launch gate](https://github.com/rrahul0904/snowflake-brain/actions/runs/33899328893),
  [PostgreSQL smoke](https://github.com/rrahul0904/snowflake-brain/actions/runs/33899328895),
  [certification smoke](https://github.com/rrahul0904/snowflake-brain/actions/runs/33899328917),
  [security assurance](https://github.com/rrahul0904/snowflake-brain/actions/runs/33899328940), and
  [visual parity](https://github.com/rrahul0904/snowflake-brain/actions/runs/33899328915).

## Production database and runtime gate

* The release migration set includes `024_operations_snapshot_activity_metrics`.
  It must be applied through the deployment-only migration credential after
  merge and before the first deployment of this release.
* The Vercel request-serving `DATABASE_URL` must authenticate as
  `snowflake_app_runtime`, with `LOGIN`, no elevated PostgreSQL attributes, and
  only the grants required by the application. The migration credential must
  never be installed in Vercel runtime configuration.
* The credential-rotation operator must run
  `scripts/provision_hosted_runtime.py` with approved deployment credentials,
  retain only its safe status output, and redeploy only after it reports
  `runtime_dsn_rotated: true`.
* After deployment, `/api/ready` and `/api/release` must identify PostgreSQL
  readiness and the exact deployed Git SHA without exposing credentials.

## Private-bank release gate

* The corpus remains private. It is acquired only by the controlled GitHub
  Actions workflow and validated against SHA-256
  `da57f636a57180631448fda79cfdcad2acf8e38ae2f381ea891a8cea91e704c5`.
* The release key is `cofc03-2026-08-14-beta-1200-v2` with the expected
  inventory: 1,200 total, 216 free, 504 practice, 360 mock-reserved, and 120
  diagnostic questions.
* Required transition order is `qa_passed` → documented SME approval →
  `staging` → explicit `active`. Do not activate on an import, CI, or deploy.
* Only count-only inventory evidence may be attached to release records; do
  not commit, upload, log, or render question content or answer keys.

## Human and commercial gates

* One independent GitHub reviewer must approve the exact certified PR head.
  The author and automation must not self-approve, force-merge, or override
  branch protection.
* A designated Snowflake-content SME must approve the imported bank in the
  controlled release workflow. This is separate from code review.
* A designated production operator owns the final deploy, post-deploy smoke,
  and rollback decision. The current canonical production deployment remains
  the rollback target until those checks succeed.
* Billing stays fail-closed unless a designated billing owner has supplied
  verified production Stripe price configuration and completed the documented
  checkout/webhook rehearsal. No commercial claim may be made before that
  evidence exists.

## Current release state

At document creation, the PR is ready for review and its then-current required
checks are successful. Production-side validation has found a pending release
migration, a non-login runtime role, and an empty private bank; these are
deliberate post-merge operational gates, not evidence that the release is live.
The private-bank QA workflow can be manually dispatched only after its workflow
definition reaches the default branch, as required by GitHub Actions.
