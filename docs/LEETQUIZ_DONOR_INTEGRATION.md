# LeetQuiz Donor Integration

This branch adapts useful certification-learning mechanics into Snowflake Brain without importing LeetQuiz source code, proprietary question wording, exam dumps, or a second application architecture.

## Capability disposition

| Donor capability | Snowflake Brain implementation |
| --- | --- |
| Question explorer | Candidate-safe Question Explorer limited to questions already served to the signed-in account |
| Stronger practice UX | Custom targeted session composer that delegates selection to the existing entitlement/release-aware practice allocator |
| Custom quizzes | Domain/task/difficulty/count/unanswered filters feed the existing drill session |
| Adaptive filtering | Existing Adaptive Readiness and selection engine remain authoritative; this branch does not fork the intelligence model |
| AI tutor pattern | Snowflake Coach returns Socratic concept guidance, mapped task decision rules, and exam traps without revealing an answer |
| Text/PDF/image ingestion | Private administrator intake CLI creates a hashed, review-only package under gitignored private storage; text is native, PDF may use pdftotext, image may use tesseract, and either binary type can use an operator-reviewed transcript |
| Correction workflow | Candidates can flag a previously served question; the report enters the existing content-feedback queue with question ID and reason |
| Discussion pattern | Public peer-to-peer answer discussion is intentionally replaced by candidate-private notes plus moderated correction reports to reduce answer leakage and dump propagation |
| Content QA | Existing question editorial QA, immutable versioning, human content review, independent SME approval, staging, and activation remain mandatory |
| SEO/discovery | Public certification landing paths, sitemap/robots, canonical metadata, and structured product/certification discovery metadata are added without exposing authenticated learning content |

## Private ingestion boundary

Run only in an administrative environment:

```bash
python scripts/content_intake_admin.py source.pdf \
  --actor reviewer@example.com \
  --track-id snowpro-core
```

If local PDF extraction is unavailable, supply a reviewed transcript:

```bash
python scripts/content_intake_admin.py source.pdf \
  --actor reviewer@example.com \
  --transcript /private/transcripts/source.txt
```

Image intake follows the same rule and can use local Tesseract when installed or a reviewed transcript.

The output defaults to `private_content/intake/`, which is gitignored. Intake material is **not** inserted into the candidate question bank and is never served to learners. It is only source material for independent authoring and must still pass the existing governed content pipeline.

## Exam-integrity boundary

The following are rejected as source strategies:

- live or recalled certification exam questions;
- braindumps/dumps/leaks;
- third-party commercial question-bank wording without appropriate rights;
- candidate-visible raw intake artifacts;
- automatic promotion from ingestion to production;
- public discussion that reveals answer keys or reconstructs a private bank.

## Release path

`private intake → independent authoring → private bank import → automated QA → human content review → independent SME approval → staging → activation`

This branch does not alter the protected production bank or its release governance.
