# Question Supply Chain

```text
Source and provenance
  -> package validation and content hash
  -> automated QA and duplicate/coverage checks
  -> source vetting and freshness check
  -> attributable human review
  -> independent SME approval
  -> staging import and dry run
  -> audited activation of immutable release
  -> candidate delivery under identity, quota and sitting rules
  -> immutable sitting linkage, feedback and correction workflow
  -> retirement or rollback
```

Content lifecycle states are `DRAFT`, `AUTO_QA`, `SOURCE_VETTED`, `HUMAN_REVIEWED`, `SME_APPROVED`, `STAGING`, `ACTIVE`, and `RETIRED`. Automation may validate and recommend; it cannot create human review or SME approval. Release membership pins question version IDs and hashes. Activation records an audit event; rollback restores a prior eligible release without rewriting historical sittings.

Packages carry certification/blueprint/domain/task/objective IDs, question and version IDs, stem/options/key/explanation/rationales, difficulty, provenance and validation dates, lifecycle and quality states, content hash, review evidence and release eligibility. Import must be schema-checked, duplicate-checked, coverage-checked, dry-runnable and idempotent.

Protected source banks remain outside public Git and frontend assets. Production evidence is count-only and must not query or log question content. PR #59 generated records remain drafts until genuine item-level review and SME promotion are evidenced. The PR's current metadata reports zero exam-parity, Exam+ and expert-stretch verified records; this repository must not change those claims without new evidence.

Implementation references: `app/question_bank.py`, `app/question_editorial.py`, `app/question_bank_releases.py`, `app/question_versions.py`, `docs/PRIVATE_QUESTION_BANK_DEPLOYMENT.md`, `docs/question-bank-editorial-runbook.md`.
