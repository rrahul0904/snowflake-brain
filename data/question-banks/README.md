# Snowflake Certification Question + Solution Banks

This directory is the evidence-first source corpus for Snowflake certification practice content.

## Goal and current publishing state

The repository materializes **5,000 distinct questions and 5,000 paired solutions for every tracked Snowflake certification exam**. With 12 tracked exams, the canonical corpus is **60,000 questions + 60,000 paired solutions = 120,000 records**.

As of **2026-10-08**, the 5,000-per-certification target is materialized, the advanced automated QA gate passes, and a Word/PDF publishing set has been produced for all 12 tracked certifications. See `publishing/2026-10-08.json` for the publishing receipt and corpus fingerprints.

The bank is original practice material. It must **not** contain recalled/live exam questions, leaked dumps, or copied proprietary practice-exam content.

## Exam inventory baseline

| ID | Exam | Code | Target | Lifecycle |
|---|---|---:|---:|---|
| associate-platform | SnowPro Associate: Platform | SOL-C01 | 5,000 | active / catalog reconciliation |
| core | SnowPro Core | COF-C03 | 5,000 | active |
| specialty-gen-ai | SnowPro Specialty: Gen AI | GES-C02 | 5,000 | active |
| specialty-snowpark | SnowPro Specialty: Snowpark | SPS-C01 | 5,000 | retiring 2026-11-01 |
| specialty-native-apps | SnowPro Specialty: Native Apps | NAS-C02 | 5,000 | active |
| advanced-mlops-engineer | SnowPro Advanced: MLOps Engineer | MLA-C01 | 5,000 | active |
| advanced-security-engineer | SnowPro Advanced: Security Engineer | SEA-C01 | 5,000 | active |
| advanced-architect | SnowPro Advanced: Architect | ARA-C01 | 5,000 | active |
| advanced-data-engineer | SnowPro Advanced: Data Engineer | DEA-C02 | 5,000 | active |
| advanced-data-scientist | SnowPro Advanced: Data Scientist | DSA-C03 | 5,000 | retiring 2026-11-01 |
| advanced-administrator | SnowPro Advanced: Administrator | ADA-C02 | 5,000 | active |
| advanced-data-analyst | SnowPro Advanced: Data Analyst | DAA-C01 | 5,000 | active |

Recertification exams are treated as blueprint variants of their parent certification when Snowflake states that they share the same guide; they are not counted as separate 5,000-question corpora unless Snowflake publishes a distinct blueprint.

## Authoritative source hierarchy

Use Snowflake-owned sources in this order:

1. current Snowflake certification exam/study guide;
2. current `docs.snowflake.com` product documentation;
3. Snowflake server and feature release notes;
4. Snowflake University / official learning material;
5. official Snowflake product announcements and newsroom releases for lifecycle and architecture context.

Community content may identify topics or misconceptions but is never an authoritative answer source.

## Evidence and quality contract

Every question contains a stable ID, certification/exam code, locked blueprint objective, topic/subtopic, question type, difficulty, prompt/options, answer key, Snowflake-owned sources, freshness metadata, lifecycle notes where necessary, and QA status.

Every paired solution contains the matching question ID, correct answer, explanation, reasoning, distractor analysis, exam trap/misconception, official-source references, and optional runnable SQL/Python.

Automated release gates enforce parseability, stable IDs, question/solution pairing, answer-key consistency, Snowflake-owned source URLs, blueprint membership, exact normalized-prompt uniqueness, 5,000-per-exam counts, diversity, release-aware lifecycle requirements, and within-exam semantic near-duplicate detection. The 2026-10-08 advanced QA receipt reports **0 blocking errors** and **0 within-exam semantic near-duplicate pairs**.

A record does **not** become individually `verified` merely because these automated gates pass. Generated records remain `draft` until explicitly promoted after source and ambiguity review. This distinction is preserved in `status.json` and in the published documents.

## Freshness layer

Durable exam fundamentals and release-specific facts are tracked separately. A release-aware question is eligible only when the feature maps to a locked exam objective. Every time-sensitive item must preserve source publication/release date, `as_of` date, lifecycle state, and retirement/deprecation information where applicable.

Release-aware content remains a minority of the bank so that current-product coverage does not crowd out durable architecture, SQL, administration, data engineering, security, analytics, ML, and platform fundamentals.

## Repository layout

- `certifications.json` - certification inventory and 5,000-per-exam targets
- `blueprints/2026-10-07.json` - locked objective baseline
- `coverage/authoring-targets.5000.json` - internal objective-level authoring allocation
- `generator/` - deterministic Snowflake concept/source catalog
- `seed/*.jsonl` - curated durable seed corpus
- `release-aware/*.jsonl` - curated release-aware corpus
- `generated/` - derived 4,995-per-exam materialization output (CI artifact; not required to be committed)
- `schema/` - question/solution contracts
- `publishing/2026-10-08.json` - publishing receipt and corpus hashes
- `status.json` - current completion/QA status
- `scripts/generate_question_banks_5000.py` - deterministic materializer
- `scripts/validate_question_banks.py` - structural/final 5,000-per-exam release gate
- `scripts/qa_question_banks_advanced.py` - semantic, diversity, content, and publishing QA

Run:

```bash
python scripts/generate_question_banks_5000.py --clean
python scripts/validate_question_banks.py --require-target
python scripts/qa_question_banks_advanced.py --report data/question-banks/generated/advanced-qa-report.json
```

The `Question Bank Validation` GitHub Actions workflow performs these steps and packages the canonical publishing source as `snowflake-certification-banks-5000-each`.
