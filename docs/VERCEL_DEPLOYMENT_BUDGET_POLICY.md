# Vercel deployment budget policy

Normal implementation work must be certified locally and in GitHub Actions. It
must not create a Vercel Preview or Production deployment.

## Allowed deployments

| Classification | Allowed when | Required record |
| --- | --- | --- |
| `FINAL_RELEASE` | Predeployment certification is green, final review is complete, and an approved release SHA is selected. | Release artifact and deployment record |
| `PRODUCTION_HOTFIX` | A production incident has an owner and an explicitly approved remediation SHA. | Incident reference and postmortem follow-up |
| `MANUAL_APPROVED_PREVIEW` | A named reviewer has approved hosted verification that cannot be done locally. | Approval and purpose in the release record |

All other branch pushes and implementation commits are skipped. The existing
production workflow remains intact for `main`; this policy does not disable
Vercel integration or alter production promotion behavior.

## Manual release certification override

The release owner records one of the three classifications above, verifies the
exact final SHA with `bash scripts/release_predeploy_certify.sh`, requires the
no-deploy certification workflow to pass, and then creates the single required
deployment through the established release workflow. The admin console cannot
create deployments.
