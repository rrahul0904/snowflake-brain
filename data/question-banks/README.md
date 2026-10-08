# Snowflake Certification Question + Solution Banks

This directory is the evidence-first source corpus for Snowflake certification practice content.

## Goal

Create **at least 5,000 distinct questions and 5,000 paired solutions for every tracked Snowflake certification exam**. With 12 tracked exams, the minimum corpus is **60,000 questions + 60,000 paired solutions = 120,000 records**.

The bank is original practice material. It must **not** contain recalled/live exam questions, leaked dumps, or copied proprietary practice-exam content.

## Exam inventory baseline — 2026-10-07

| ID | Exam | Code | Target | Lifecycle |
|---|---|---:|---:|---|
| associate-platform | SnowPro Associate: Platform | SOL-C01 | 5,000+ | active / catalog reconciliation |
| core | SnowPro Core | COF-C03 | 5,000+ | active |
| specialty-gen-ai | SnowPro Specialty: Gen AI | GES-C02 | 5,000+ | active |
| specialty-snowpark | SnowPro Specialty: Snowpark | SPS-C01 | 5,000+ | retiring 2026-11-01 |
| specialty-native-apps | SnowPro Specialty: Native Apps | NAS-C02 | 5,000+ | active |
| advanced-mlops-engineer | SnowPro Advanced: MLOps Engineer | MLA-C01 | 5,000+ | active |
| advanced-security-engineer | SnowPro Advanced: Security Engineer | SEA-C01 | 5,000+ | active |
| advanced-architect | SnowPro Advanced: Architect | ARA-C01 | 5,000+ | active |
| advanced-data-engineer | SnowPro Advanced: Data Engineer | DEA-C02 | 5,000+ | active |
| advanced-data-scientist | SnowPro Advanced: Data Scientist | DSA-C03 | 5,000+ | retiring 2026-11-01 |
| advanced-administrator | SnowPro Advanced: Administrator | ADA-C02 | 5,000+ | active |
| advanced-data-analyst | SnowPro Advanced: Data Analyst | DAA-C01 | 5,000+ | active |

Recertification exams are treated as blueprint variants of their parent certification when Snowflake states that they share the same guide; they are not counted as separate 5,000-question corpora unless Snowflake publishes a distinct blueprint.

## Authoritative source hierarchy

Use Snowflake-owned sources in this order:

1. current Snowflake certification exam/study guide;
2. current `docs.snowflake.com` product documentation;
3. Snowflake server and feature release notes;
4. Snowflake University / official learning material;
5. official Snowflake product announcements and newsroom releases for lifecycle and architecture context.

Community content may identify topics or misconceptions but is never an authoritative answer source.

## Freshness layer

Durable exam fundamentals and release-specific facts are tracked separately. A release-aware question is eligible only when the feature maps to a locked exam objective. Every time-sensitive item must preserve:

- source publication/release date;
- `as_of` date;
- lifecycle state such as Preview, Public Preview, Private Preview, or General Availability;
- retirement/deprecation information where applicable.

The source manifest at `sources/release-notes-2026.json` maps current Snowflake releases and announcements to candidate certification objectives.

Release-aware content must remain proportionate: it should deepen current-product coverage without crowding out durable architecture, SQL, administration, data engineering, security, analytics, ML, and platform fundamentals. Preview-only behavior must never be presented as a durable GA fact.

## Evidence contract

Every question contains a stable ID, certification/exam code, locked blueprint objective, topic/subtopic, question type, difficulty, prompt/options, answer key, Snowflake-owned sources, freshness metadata, lifecycle notes where necessary, and QA status.

Every paired solution contains the matching question ID, correct answer, explanation, reasoning, distractor analysis, exam trap/misconception, official-source references, and optional runnable SQL/Python.

## Quality gates

A record cannot move from `draft` to `verified` unless:

1. the answer is supported by current Snowflake-owned documentation;
2. the question maps to a locked exam-guide objective;
3. no option is ambiguous under the documented assumptions;
4. no recalled or leaked certification content was used;
5. duplicate and near-duplicate checks pass;
6. deprecated/preview/edition/cloud/region-specific behavior is labeled explicitly;
7. the solution explains why distractors are wrong;
8. time-sensitive facts carry an `as_of` date and are revalidation-ready.

## Coverage strategy

The 5,000+ target is achieved through objective-weighted coverage, not paraphrase inflation. Each exam expands across factual concepts, capability boundaries, SQL/Python/configuration reasoning, architecture trade-offs, security/governance, performance/cost, loading/transformation/orchestration, failure modes, troubleshooting, cloud/edition boundaries, best practices, anti-patterns, and multi-objective scenarios.

Each certification will receive a coverage matrix over objective × topic × question type × difficulty × freshness class. Release-aware items are intentionally only a fraction of the bank; durable core knowledge remains the majority.

## Repository layout

- `certifications.json` — certification inventory and 5,000-per-exam targets
- `blueprints/2026-10-07.json` — locked objective baseline
- `sources/release-notes-2026.json` — official release/announcement freshness manifest
- `schema/question.schema.json` — question record contract
- `schema/solution.schema.json` — solution record contract
- `seed/*.jsonl` — initial cross-exam seed corpus
- `release-aware/*.jsonl` — current release-aware question/solution tranches
- `<certification-id>/questions*.jsonl` — scaled question bank
- `<certification-id>/solutions*.jsonl` — paired solution bank
- `<certification-id>/coverage.json` — objective/topic allocation and completion metrics
- `scripts/validate_question_banks.py` — integrity and final 5,000-per-exam release gate

Run `python scripts/validate_question_banks.py` for structural checks. Use `python scripts/validate_question_banks.py --require-target` for the final 5,000-per-exam completion gate.
