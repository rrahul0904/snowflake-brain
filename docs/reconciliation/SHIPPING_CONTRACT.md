# Snowflake Brain Shipping Contract

One release is shipped only when every required item below is evidenced for one exact application SHA. A source-level or CI result cannot stand in for hosted behavior. Paid monetizable GA also requires the billing and content/provider gates in the final acceptance record.

## Candidate identity

- Candidate PR: #57 (`feat/donor-learning-suite-integration`)
- Candidate SHA: update from the exact PR head before certification
- Preview deployment ID and URL: record from Vercel deployment metadata
- Production merge SHA and deployment ID: record only after protected merge and deployment
- Active question release ID: count-only evidence; never include question content

## Required evidence

- [ ] `./scripts/verify_all.sh` and required GitHub checks pass on the exact candidate SHA.
- [ ] PostgreSQL convergence, runtime least-privilege identity, allowed/denied operations, backup and isolated restore pass.
- [ ] Governed active question release is count-verified and eligible; human/SME evidence is genuine and attributable.
- [ ] Protected Preview `/api/health`, `/api/ready` and `/api/release` pass; release SHA equals candidate SHA.
- [ ] No static bank/source-map/secret exposure; anonymous, candidate and authorized admin flows pass.
- [ ] Golden learner path passes through diagnostic, lesson, practice, build, mock, replay, review, readiness and next action.
- [ ] Desktop Chromium, desktop Firefox, mobile Chromium, keyboard and accessibility rehearsals pass.
- [ ] Auth lifecycle and email delivery pass; Google OAuth lifecycle passes if enabled.
- [ ] Stripe TEST lifecycle passes in Preview; production billing configuration and acceptance pass when paid plans are enabled.
- [ ] Operational alert reaches its configured sink; database, provider, release and rollback runbooks are exercised.
- [ ] Independent technical review resolves actionable findings; separate genuine human PR approval is recorded.
- [ ] Merge uses protected main and required conversation resolution; no force push or bypass.
- [ ] Production deployment SHA matches the merged SHA; endpoints and golden path pass after deployment.
- [ ] Application and question-release rollback are demonstrated and recorded.
- [ ] Issue #58 and release receipts point to exact SHA and evidence.

## Current status

The initial reconciliation is complete, and the local full regression plus governance-artifact checks pass on the implementation tree. Exact-head GitHub checks will rerun after push. Candidate Preview certification is blocked by authenticated Vercel access. Production question-release inventory, runtime denial evidence, real email/alert receipts and human review are pending. See [`final-reality.md`](final-reality.md) and [`BLOCKER_RECEIPT.md`](BLOCKER_RECEIPT.md) for evidence and next actions.
