# Adaptive Readiness Intelligence v2

Adaptive Intelligence v2 answers a practical question:

> Given the candidate's current evidence, exam-date runway and retention state, what is the highest-value study action next?

It deliberately does **not** claim to know the candidate's probability of passing the real SnowPro exam. The displayed readiness score is an evidence composite used to prioritize study effort.

## Evidence model

The composite uses six components:

- mastery evidence — 35%
- spaced-retention evidence — 20%
- confidence calibration — 15%
- recent mock evidence — 15%
- active-bank coverage — 10%
- response-time pace — 5%

Sparse evidence is pulled toward a neutral prior rather than allowing a handful of correct answers to generate an inflated score.

Every snapshot includes an evidence confidence label:

- `low`
- `medium`
- `high`

High confidence requires substantial unique-question coverage, attempt volume and repeated mock evidence. This confidence label describes the amount of evidence behind the study indicator; it is not a statistical confidence interval for exam outcomes.

## Mastery decay

Attempts lose influence with age using an exponential half-life. Fresh evidence therefore counts more than a correct answer from months ago.

The engine also uses current SRS state. Due and substantially overdue reviews reduce retention evidence and are promoted as high-priority actions.

## Confidence-weighted evidence

Practice confidence uses the existing 1–5 scale.

- correct + appropriate confidence supports calibration;
- high-confidence incorrect answers reduce calibration and mastery;
- very fast low-confidence correct answers can be classified as probable guesses and are discounted rather than treated as full mastery.

## Response-time weighting

Pace is candidate-relative rather than enforcing one arbitrary universal time limit. The engine compares response time to the candidate's robust median and clips extreme effects.

Fast responses are not automatically rewarded as mastery. Probable-guess detection can override that signal.

## Difficulty adjustment

Question difficulty modestly adjusts mastery evidence:

- easy: 0.90
- medium: 1.00
- hard: 1.12

Difficulty can refine evidence but cannot turn an incorrect answer into mastery.

## Coverage

Coverage is based on unique attempted questions divided by the currently eligible active-release question set.

This prevents repeated drilling of a tiny slice of the bank from looking equivalent to broad SnowPro blueprint preparation.

## Mock evidence

Recent submitted timed-mock evidence is weighted toward newer sittings. With no or only one mock, the mock component remains partially anchored to a neutral prior.

The engine never rewrites historical mock results or historical immutable question links.

## Exam-date runway and study minutes

When `candidate_study_preferences.exam_date` is present, the engine calculates runway days and adjusts recommended daily minutes using:

- evidence gap;
- overdue SRS load;
- candidate's existing daily-minute preference;
- days remaining until the exam.

Recommendations are capped at 180 minutes/day so the optimizer cannot produce absurd workload demands.

## Skill priorities

Each skill priority is driven by a transparent combination of:

- mastery gap;
- coverage gap;
- confidence-calibration gap;
- probable guessing;
- pace evidence.

The recommendation exposes reason codes rather than hiding selection behind an opaque rank.

## Remediation sequence

A skill-focus recommendation follows the intended learning loop:

```text
written concept
→ focused drill
→ delayed SRS
→ mastery check
```

For unresolved retention debt, Due Today/SRS can outrank new skill coverage. Near the exam date, the plan emphasizes the highest evidence gaps, timed mocks, mock remediation and SRS rather than opening many low-priority new topics.

## Adaptive question selection

`adaptive_question_ids()` returns prioritized IDs only. It does not return stems, correct answers or explanations.

Priority combines:

- weak/high-priority skills;
- unseen questions;
- recent mistakes;
- due SRS items;
- time since last attempt;
- readiness-appropriate difficulty.

Candidate-facing question delivery must still go through the existing authenticated/tier-aware question-bank runtime. The adaptive engine is not an entitlement bypass.

## Persistence

`candidate_readiness_snapshots` stores the evidence summary used for a point-in-time recommendation.

`candidate_adaptive_recommendations` stores the corresponding prioritized actions with reason codes.

Both cascade on account deletion and are isolated by `candidate_id`.

## Candidate API

The router provides:

```text
GET /api/intelligence/adaptive/readiness
GET /api/intelligence/adaptive/recommendations
GET /api/intelligence/adaptive/question-ids
```

The router must be mounted into the application only after the integrated branch reaches the latest merged roadmap baseline. The last endpoint returns IDs only; the normal practice runtime remains responsible for candidate-safe content delivery.

## Readiness bands

Bands communicate the study state without implying pass probability:

- `building_evidence`
- `insufficient_evidence`
- `foundational`
- `developing`
- `approaching_ready`
- `strong_evidence`

A low-evidence candidate is not labeled strongly ready merely because the raw composite is high.

## Acceptance criteria

1. Sparse evidence cannot generate a high-confidence readiness claim.
2. Old attempts decay.
3. High-confidence misses harm calibration.
4. Fast low-confidence correct answers can be discounted as probable guesses.
5. Hard questions modestly weight mastery without dominating it.
6. Active-release coverage is included.
7. Due/overdue SRS affects retention and recommendations.
8. Mock evidence is recent-weighted and evidence-limited.
9. Exam-date runway changes study-minutes recommendations.
10. Recommended question IDs remain within the active eligible question set.
11. Recommendations expose reason codes and sequences.
12. Candidate data remains isolated.
13. Readiness is explicitly described as a study indicator, not a pass probability.
14. Adaptive Readiness Smoke passes on SQLite and PostgreSQL.
15. After integration, the standard certification, visual, and PostgreSQL full-suite gates remain green.
