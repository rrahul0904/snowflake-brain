# Data Model and Authorities

The live schema is defined by application schema code and ordered migrations. This document describes domain relationships; it is not a replacement for those migrations.

```mermaid
erDiagram
  CANDIDATE ||--o{ CANDIDATE_SESSION : owns
  CANDIDATE ||--o{ LEARNING_EVIDENCE : records
  CANDIDATE ||--o{ MOCK_SITTING : takes
  CANDIDATE ||--o{ MISTAKE_REVIEW : repairs
  CERTIFICATION ||--o{ DOMAIN : contains
  DOMAIN ||--o{ TASK : contains
  TASK ||--o{ QUESTION_MAPPING : maps
  QUESTION ||--o{ QUESTION_VERSION : versions
  QUESTION_RELEASE ||--o{ RELEASE_QUESTION : includes
  QUESTION_VERSION ||--o{ RELEASE_QUESTION : pins
  MOCK_SITTING ||--o{ SITTING_ANSWER : records
  CANDIDATE ||--o{ ENTITLEMENT : receives
  QUESTION_RELEASE ||--o{ EDITORIAL_EVENT : governed_by
```

Candidate identity and session ownership scope all private learning state. Learning evidence, mistakes, confidence, review schedules and mock results are candidate-owned and feed readiness; readiness is derived and persisted as a current evidence snapshot, not an independent authority. Historical sittings pin immutable question-version IDs, preserving their original content linkage after release changes.

Question releases reference immutable versions. Activation and rollback alter the active release pointer through audited server-side operations. Content quality/review evidence and release eligibility are separate from a question's presence in source files.

Entitlement state is server-owned and changes only through trusted billing transitions or explicit authorized administrative action. Raw provider events and idempotency keys protect replay handling.

See `docs/DATA_MODEL_V24.md`, `docs/QUESTION_BANK_BACKEND.md` and `docs/postgres-production-runbook.md` for schema and operational details.
