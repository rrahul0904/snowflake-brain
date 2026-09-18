# LeetQuiz donor integration

Branch: `feat/donor-leetquiz`

This branch ports the LeetQuiz patterns that fit Snowflake Brain without creating a second question authority.

Implemented:
- candidate Question Studio / custom quiz builder
- blueprint-safe Question Explorer that never enumerates the private bank
- adaptive/domain/difficulty/unanswered session composition through the existing secure allocator
- Socratic tutor interaction pattern linked to Snowflake task reasoning
- mistake/adaptive repair handoff
- candidate question-correction reports available only after the candidate was served the question
- candidate correction history plus admin editorial triage/resolution API
- private text/Markdown/PDF/image editorial intake with source/transcript hashing and official-source provenance
- PDF/image intake fails closed without a human-supplied transcript; no OCR or model output is silently treated as authoritative text
- all source intake remains `needs_review`, `import_ready=false`, and cannot auto-generate or activate questions
- existing grading, entitlement, no-answer-leak, learning-intelligence, immutable-question and private-bank release controls remain authoritative

Intentional Snowflake Brain differences:
- no public question inventory or public question-detail SEO pages, because commercial bank wording is private deployment content
- certification catalog/exam-guide pages remain the public discovery/SEO surface instead
- no public answer-key discussion threads; candidate reports enter a moderated editorial queue so one learner cannot leak answers to another
- curated Community Insights remain separate from question correction
- no browser-side answer-key corpus
- no second database or question model
- no AI-generated SME approval

Private source intake:
```bash
python scripts/question_source_intake.py source.pdf \
  --source-key snowflake-doc-key \
  --source-url https://docs.snowflake.com/... \
  --transcript reviewed-source.txt
```

The CLI stores the source package only under a private output boundary (repository-local output must be under `private_content/`), fingerprints the source and normalized text, registers official provenance, and creates editorial review work. It does not publish or import a question bank.

Candidate Question Studio and correction reporting never expose raw source files, answer keys, pool labels, hashes, bank-size metadata, or other candidates' reports.
