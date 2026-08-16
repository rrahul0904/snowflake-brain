# Question Bank Editorial Maturity Runbook

This runbook defines how the Snowflake Certification Guide matures commercial question-bank content without allowing automated systems to impersonate human content reviewers or Snowflake subject-matter experts.

## Core rule: approvals belong to immutable versions

Automated QA, content review and SME approval are bound to `question_versions.id`, not just to a mutable `question_id`.

A question therefore has three distinct states:

1. **Automated QA** — structural/editorial heuristics have passed for the current immutable version.
2. **Human content review** — a named reviewer has approved the current version's clarity, explanation and distractor quality.
3. **Human SME review** — a named subject-matter expert has approved the technical correctness of that same current version.

If question content changes and creates a new immutable version, prior approvals are stale for release purposes until the new version is reviewed.

## Automated QA

Run:

```bash
python scripts/question_editorial_admin.py qa-run --track-id snowpro-core
```

The QA engine is conservative. It does **not** determine Snowflake technical truth. It detects editorial risk signals such as:

- too few options;
- invalid correct-answer indexes;
- duplicate options;
- single/multiple-answer flag mismatch;
- missing/very short explanations;
- cross-question dependencies;
- near-duplicate stems;
- extreme option-length cues;
- all/none-of-the-above meta options;
- absolute wording requiring ambiguity review;
- scenario questions with little context;
- terminology/casing checks;
- missing/invalid difficulty;
- difficulty-distribution skew;
- answer-position skew;
- official-source provenance missing/unverified/needs-review when the freshness system is available.

Blockers fail automated QA. Warnings reduce the QA score but are editorial signals, not automatic assertions that the content is wrong.

## Human content review

After current-version QA passes:

```bash
python scripts/question_editorial_admin.py review QUESTION_ID content approved \
  --actor reviewer-name \
  --notes "Reviewed stem, options, distractors and explanation."
```

Use `changes_requested` instead of `approved` when the item needs editing.

Content review should consider:

- whether the stem has one clear task;
- whether all required context is present;
- whether distractors are plausible but incorrect for the intended concept;
- whether option wording avoids accidental cues;
- whether the explanation teaches why the correct answer is correct and why major distractors are not;
- whether the scenario resembles a realistic Snowflake decision;
- whether terminology matches current Snowflake language;
- whether the item is independent of surrounding questions.

## Human SME review

SME review cannot occur before current-version content review is approved.

```bash
python scripts/question_editorial_admin.py review QUESTION_ID sme approved \
  --actor snowflake-sme-name \
  --notes "Technical behavior and answer validated against current official source."
```

The system intentionally requires a non-empty human actor and never auto-populates SME approval from QA, source fingerprints, or model output.

## Release readiness

Check an immutable release snapshot:

```bash
python scripts/question_editorial_admin.py release-readiness cof-c03-release-002
```

A release passes only when every release item has:

- current-version automated QA passed;
- current-version content approval;
- current-version SME approval.

Use the guarded promotion command:

```bash
python scripts/question_editorial_admin.py release-promote cof-c03-release-002 qa_passed --actor release-manager
python scripts/question_editorial_admin.py release-promote cof-c03-release-002 sme_approved --actor release-manager
python scripts/question_editorial_admin.py release-promote cof-c03-release-002 staging --actor release-manager
```

## Optional hard database gate

Installing the editorial maturity schema does not invalidate or block today's active bank. Enforcement is opt-in per track.

Only after a release is fully mature should an administrator enable the database-level gate:

```bash
python scripts/question_editorial_admin.py policy-set \
  --track-id snowpro-core \
  --enforce on \
  --minimum-qa-score 70 \
  --release-key cof-c03-release-002 \
  --actor editorial-admin
```

Once enabled, PostgreSQL/SQLite triggers reject protected release lifecycle transitions when the exact `question_version_id` in the release lacks required QA/content/SME approval.

Do not disable the gate to force through a content deadline. Resolve the editorial state or create a corrected release.

## Bank health

Run:

```bash
python scripts/question_editorial_admin.py bank-health --track-id snowpro-core
```

The report is domain-oriented rather than relying on a raw question count. Per domain it includes:

- number of active questions;
- current QA pass percentage;
- current human content approval percentage;
- current SME approval percentage;
- average QA score;
- official-source provenance verification percentage when phase-5 provenance is installed;
- difficulty distribution;
- first-correct-answer position distribution.

The latest blocker/warning/info counts are also reported.

## Editorial release batches

Use separate content branches/releases rather than editing the active bank in place, for example:

```text
content/cof-c03-release-002
content/cof-c03-release-003
```

Recommended flow:

```text
Draft bank batch
→ automated QA
→ resolve blockers / review warnings
→ human content approval
→ human SME approval
→ freshness/provenance gate
→ release staging
→ regression/exam allocation checks
→ active release
```

## Relationship to official-source freshness

When the content freshness system is installed:

- verified provenance improves bank-health evidence;
- missing/unverified provenance is surfaced as an editorial QA warning;
- an official-source change produces a QA blocker (`source_needs_review`) on the next QA run;
- source monitoring still never rewrites the question or answer;
- editorial and SME reviewers decide whether a source change actually requires content changes.

Both the freshness gate and editorial gate must pass before production activation once their per-track enforcement policies are enabled.

## What automation must not do

Automation must not:

- mark its own model output as human-reviewed;
- create a fake SME identity;
- infer SME approval merely because official docs are unchanged;
- silently rewrite answers after a documentation change;
- suppress duplicate/ambiguity warnings to improve a score;
- carry approvals from an old immutable question version onto a new one.

## Acceptance checklist

Before calling an editorial batch mature:

1. Automated QA runs on the exact immutable question versions in the release.
2. All blockers are resolved.
3. Warnings are reviewed rather than blindly ignored.
4. Content review is approved by a named human reviewer for every release item.
5. Technical correctness is approved by a named SME for every release item.
6. Source provenance/freshness is verified when that system is enabled.
7. Domain coverage is reviewed against the COF-C03 blueprint rather than raw question count alone.
8. Difficulty mix is intentional.
9. Answer positions are not obviously patterned.
10. Near-duplicate findings are resolved or explicitly justified.
11. Explanations are instructional and not answer-only restatements.
12. Release readiness is 100% for current versions.
13. The hard editorial gate is enabled only after the bank reaches the desired maturity baseline.
14. Question Editorial Maturity Smoke passes on SQLite and PostgreSQL.
15. The standard certification, visual and PostgreSQL full-suite gates remain green after integration.
