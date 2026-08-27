# Private Question Bank Deployment Runbook

The commercial SnowPro question bank is a **backend deployment artifact**, not application source code and not a frontend asset.

## Security boundary

Never place production bank JSON under:

- `frontend/`
- `static/`
- `config/`
- a public Git repository
- a browser bundle
- a publicly downloadable object-store path

`PRIVATE_QUESTION_BANK_DIR` is a development/CI or one-time administrative-import input only (default development path: `private_content/question_bank`). Vercel production does not mount this directory or read bank JSON at runtime: an approved deployment job validates and imports the artifact into PostgreSQL, then candidate delivery reads the active immutable release.

## Current beta artifact

- Certification: SnowPro Core COF-C03
- Bank version: `2026-08-14-beta-1200-v2`
- Filename: `snowpro_core_cof_c03_private_bank_1200_beta_v2.json`
- Questions: 1,200
- SHA-256: `da57f636a57180631448fda79cfdcad2acf8e38ae2f381ea891a8cea91e704c5`

The public repository contains only the non-content manifest at `docs/COF_C03_PRIVATE_BANK_1200_MANIFEST.md`.

## Pre-import validation

In an approved administrative import environment, with the private artifact available only to administrators:

```bash
sha256sum /private/question_bank/snowpro_core_cof_c03_private_bank_1200_beta_v2.json
```

The result must match the manifest SHA-256 before import.

Then run the repository's backend-only validator:

```bash
python scripts/question_bank_admin.py validate \
  /private/question_bank/snowpro_core_cof_c03_private_bank_1200_beta_v2.json
```

Validation must report `valid: true`, all 19 tasks covered, and 1,200 active questions before import.

## Import

For an administrative import job only, point the importer at the private read-only directory. Do not configure this variable in Vercel Production:

```bash
export PRIVATE_QUESTION_BANK_DIR=/private/question_bank
```

Import one reviewed artifact explicitly:

```bash
python scripts/question_bank_admin.py import \
  /private/question_bank/snowpro_core_cof_c03_private_bank_1200_beta_v2.json
```

Or dry-run a directory before importing it:

```bash
python scripts/question_bank_admin.py import-dir /private/question_bank --dry-run
```

After review, import the directory from that administrative job:

```bash
python scripts/question_bank_admin.py import-dir /private/question_bank
```

## Verify backend status

Bank authoring/coverage status is an administrator-only CLI concern:

```bash
python scripts/question_bank_admin.py status --track-id snowpro-core
```

Do not expose this status as a candidate HTTP endpoint.

## Candidate verification

After import, verify through normal candidate product flows only:

- Free practice serves only Free-entitled questions when sufficient private coverage exists.
- Free Weekly Mock is 30 questions and is timed for 45 minutes.
- Premium Quick Mock is 30 questions.
- Premium Full Mock is 100 questions.
- Exam Pack receives its persisted candidate-specific Practice Mock and Full Exam sets.
- No pre-submit response contains answer keys or explanations.
- Candidate responses do not expose bank pool names, source references, content hashes, bank size, authoring status, exposure statistics, or selection configuration.

## Rollback

Do not edit the production bank in place from the browser. Author/review a new versioned private artifact, validate it, and import it through the controlled administrative job. Retire or replace questions through versioned bank metadata and controlled backend operations.

Keep the prior private artifact in restricted backup storage according to the deployment backup policy; do not add it to Git history.

## Production launch gate

Before unrestricted public launch:

1. complete automated schema/coverage/security checks;
2. complete independent human/SME review of ambiguous or high-value mock questions;
3. confirm source freshness for Snowflake features that may have changed since the bank's source-verification date;
4. import only the approved artifact into PostgreSQL and activate the reviewed immutable release;
5. rerun tier, no-answer-leak, ownership, and browser smoke tests against the deployed bank.
