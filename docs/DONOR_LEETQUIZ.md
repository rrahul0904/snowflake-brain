# LeetQuiz donor integration

Branch: `feat/donor-leetquiz`

This branch ports the LeetQuiz patterns that fit Snowflake Brain without creating a second question authority.

Implemented:
- candidate Question Studio / custom quiz builder
- blueprint-safe Question Explorer that never enumerates the private bank
- adaptive/domain/difficulty/unanswered session composition through the existing secure allocator
- Socratic tutor interaction pattern linked to Snowflake task reasoning
- mistake/adaptive repair handoff
- editorial ingestion boundary documented in-product: raw text/PDF/image material must be normalized privately and pass the existing provenance, QA, independent SME, staging and activation controls
- existing grading, entitlement, no-answer-leak, learning-intelligence and private-bank controls remain authoritative

Intentionally not duplicated:
- no public question inventory
- no browser-side answer-key corpus
- no second database or question model
- no raw PDF/image extraction inside the public Vercel candidate runtime
- no AI-generated SME approval

Raw document/image extraction belongs in the private editorial pipeline before `question_bank_admin.py` import. This preserves the production security boundary.
