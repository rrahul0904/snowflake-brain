# Snowflake Certification Question + Solution Banks

This directory is the evidence-first source corpus for Snowflake certification practice content.

## Goal

Create **at least 2,000 distinct questions and 2,000 paired solutions for every active/current Snowflake certification exam**, based on Snowflake-owned exam guides and official Snowflake documentation.

The bank is original practice material. It must **not** contain recalled/live exam questions, leaked dumps, or copied proprietary practice-exam content.

## Exam inventory baseline — 2026-10-07

The current SnowPro catalog lists Core, three Specialty exams, and seven Advanced role exams. In addition, Snowflake has continued to issue the Associate: Platform credential in 2026, so it is retained as an entry-level bank in this corpus.

| ID | Exam | Code | Target | Lifecycle |
|---|---|---:|---:|---|
| associate-platform | SnowPro Associate: Platform | SOL-C01 | 2,000+ | active / catalog reconciliation |
| core | SnowPro Core | COF-C03 | 2,000+ | active |
| specialty-gen-ai | SnowPro Specialty: Gen AI | GES-C02 | 2,000+ | active |
| specialty-snowpark | SnowPro Specialty: Snowpark | SPS-C01 | 2,000+ | retiring 2026-11-01 |
| specialty-native-apps | SnowPro Specialty: Native Apps | NAS-C02 | 2,000+ | active |
| advanced-mlops-engineer | SnowPro Advanced: MLOps Engineer | MLA-C01 | 2,000+ | active |
| advanced-security-engineer | SnowPro Advanced: Security Engineer | SEA-C01 | 2,000+ | active |
| advanced-architect | SnowPro Advanced: Architect | ARA-C01 | 2,000+ | active |
| advanced-data-engineer | SnowPro Advanced: Data Engineer | DEA-C02 | 2,000+ | active |
| advanced-data-scientist | SnowPro Advanced: Data Scientist | DSA-C03 | 2,000+ | retiring 2026-11-01 |
| advanced-administrator | SnowPro Advanced: Administrator | ADA-C02 | 2,000+ | active |
| advanced-data-analyst | SnowPro Advanced: Data Analyst | DAA-C01 | 2,000+ | active |

**Minimum corpus target: 24,000 distinct questions + 24,000 paired solution records.**

Recertification exams are treated as blueprint variants of their parent certification when Snowflake states that they share the same study guide; they are not counted as a separate 2,000-question corpus unless a distinct blueprint requires it.

## Evidence contract

Every question must contain:

- stable question ID
- certification ID and exam code
- blueprint domain/objective
- topic/subtopic
- question type (`single_select`, `multi_select`, `scenario`, `sql_reasoning`, `architecture_decision`, `troubleshooting`)
- difficulty (`foundation`, `exam`, `advanced`)
- prompt and options when applicable
- correct-answer key
- one or more Snowflake-owned source URLs
- source title and source retrieval/version date
- freshness status
- authoring/QA status

Every solution must contain:

- matching question ID
- correct answer
- concise explanation
- reasoning for why the answer is correct
- distractor analysis for each incorrect option when applicable
- exam trap / misconception
- official-source references
- optional runnable SQL/Python snippet where useful

## Quality gates

A record cannot be promoted from `draft` to `verified` unless:

1. the answer is supported by current Snowflake-owned documentation;
2. the question maps to an exam-guide objective;
3. no option is ambiguous under the documented assumptions;
4. no recalled or leaked certification content was used;
5. duplicate/near-duplicate similarity is below the configured threshold;
6. deprecated/preview/edition/cloud/region-specific behavior is labeled explicitly;
7. solution reasoning explains why distractors are wrong, not merely which answer is right;
8. time-sensitive facts carry an `as_of` date and can be revalidated.

## Coverage strategy

The final 2,000+ per exam is not produced by paraphrasing a small set of facts. Coverage is expanded across:

- factual concepts and terminology
- capability boundaries and feature selection
- SQL / Python / configuration reasoning
- architecture decisions and trade-offs
- security and governance scenarios
- performance and cost diagnosis
- data loading / transformation / orchestration
- failure-mode and troubleshooting cases
- multi-cloud / edition / region boundaries where exam-relevant
- best practices and anti-patterns
- chained scenarios that combine multiple objectives

Each exam receives a blueprint-weighted coverage matrix, then questions are generated against individual objective × topic × question-type × difficulty cells.

## Repository layout

- `certifications.json` — current certification inventory and official exam-guide entry points
- `schema/question.schema.json` — question record contract
- `schema/solution.schema.json` — solution record contract
- `<certification-id>/questions.jsonl` — question bank
- `<certification-id>/solutions.jsonl` — paired solution bank
- `<certification-id>/coverage.json` — objective/topic counts and 2,000-question target allocation
- `<certification-id>/sources.json` — Snowflake-owned source manifest

## Source hierarchy

Prefer sources in this order:

1. current Snowflake certification exam guide / study guide
2. current `docs.snowflake.com` product documentation
3. Snowflake University / official Snowflake learning material
4. Snowflake official product announcements only for lifecycle context

Community posts, blogs, Reddit, recalled exam questions, dumps, and third-party prep sites may be used only to discover topics or misconceptions; they are **never authoritative answer sources**.
