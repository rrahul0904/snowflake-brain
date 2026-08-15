# SnowPro Core private question bank

The commercial question bank is a backend asset. Candidates do not browse, enumerate, export, or inspect the bank itself.

## Candidate contract

Candidates see only the product surface their membership permits:

- Free: authenticated written curriculum, Free practice allowance, diagnostic practice, and one 20-question weekly timed mock.
- Premium 100: up to 100 practice questions/day and 2 Full Mock starts/month.
- Premium 250: up to 250 practice questions/day and 4 Full Mock starts/month.
- Premium 500: up to 500 practice questions/day and unlimited Full Mock starts.
- Exam Pack: candidate-specific lifetime 100-question Practice Mock plus one candidate-specific Full Exam start during the existing 30-day window.

Candidate HTTP responses must not contain:

- bank pool names
- authoring status/version
- private source references
- content hashes
- exposure counts
- global bank size or authoring milestones
- correct answer or explanation before submission
- internal source-test inventory
- raw selection strategy/configuration

There is intentionally no candidate-facing question-bank admin or status API.

## Private content boundary

Production JSON bank files live under `PRIVATE_QUESTION_BANK_DIR`, mounted read-only into the application container. `private_content/` is ignored by Git. Never place commercial question-bank JSON under `frontend/`, `config/`, or another committed repository path.

The current repository is safe to contain the schema/import/selection code but not the proprietary question wording.

## Authoring object

Each private question contains:

- certification/exam version
- domain and one of the 19 task statements
- question type and cognitive level
- difficulty band: foundation, applied, exam, challenge
- pool: free, practice, diagnostic, mock_reserved
- question stem and choices
- correct option indices
- correct rationale
- optional per-option distractor rationales
- concepts and trap tags
- official Snowflake documentation references
- source verification date
- authoring status/version

`active` is the only authoring status eligible for candidate selection.

## Validation

The importer rejects, among other things:

- unknown task/domain IDs
- a task assigned to the wrong domain
- duplicate IDs/stems
- malformed or duplicate answer choices
- invalid correct indices
- missing rationale
- unsupported pool/difficulty/type/status
- source references outside `docs.snowflake.com`

Run:

```bash
python scripts/question_bank_admin.py validate /private/question_bank/core-v1.json
python scripts/question_bank_admin.py import /private/question_bank/core-v1.json
python scripts/question_bank_admin.py status --track-id snowpro-core
```

`status` is CLI-only authoring information.

## COF-C03 app blueprint allocations

For the current app simulation:

| Mode | D1 | D2 | D3 | D4 | D5 | Total |
|---|---:|---:|---:|---:|---:|---:|
| Free Weekly Mock | 6 | 4 | 4 | 4 | 2 | 20 |
| Quick Mock | 9 | 6 | 5 | 7 | 3 | 30 |
| Full Mock | 31 | 20 | 18 | 21 | 10 | 100 |
| Exam Pack Practice Mock | 31 | 20 | 18 | 21 | 10 | 100 |

These are preparation-simulation settings, not a claim that a live Snowflake exam presents exactly this many questions per domain.

## Difficulty composition

Current selection targets:

- Free Weekly: 30% foundation, 40% applied, 25% exam, 5% challenge.
- Quick Mock: 35% applied, 50% exam, 15% challenge.
- Full/Exam Pack 100Q: 15% foundation, 35% applied, 40% exam, 10% challenge.
- Diagnostic: 20% foundation, 40% applied, 30% exam, 10% challenge.

The selector first satisfies task/domain coverage where the bank supports it, then difficulty and exposure goals.

## Exposure and candidate history

Every server-selected question records:

- candidate
- question
- mode/session
- served time
- answer time
- selected options
- server-computed correctness
- response time and optional confidence
- question version

Global exposure tracks served/correct/incorrect counts. Selection prefers unseen and less-exposed questions. The client cannot set correctness; the server recomputes it from the stored answer key.

## Exam Pack sets

Exam Pack Practice Mock questions are assigned to the candidate once and persisted. Repeating the lifetime Practice Mock returns the same candidate-specific set, with question/option ordering still allowed to randomize.

The one Full Exam receives a separately persisted candidate-specific set.

## Authoring milestones

The backend status tool tracks these planning targets:

- Internal MVP: 600 active questions
- Beta: 1,200
- Commercial v1: 2,000
- Mature bank: 3,000+

These milestone counts are backend planning information and are not displayed to candidates.
