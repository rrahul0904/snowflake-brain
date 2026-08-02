# Replica Baseline API Inventory

Generated: 2026-08-01T00:52:51-04:00  
Runtime inspected: `http://127.0.0.1:8010/openapi.json`

## Summary

| Metric | Count |
| --- | ---: |
| API paths | 75 |
| API operations | 79 |
| GET | 52 |
| POST | 24 |
| PATCH | 2 |
| DELETE | 1 |

The runtime OpenAPI inventory matches the route decorators in the local source tree.

## Critical Answer-Key Leakage

The current backend does not enforce exam secrecy. This is a release blocker for the replica exam workflow.

| Severity | Endpoint | Observed exposure |
| --- | --- | --- |
| Critical | `GET /api/questions?include_answers=true` | Any caller can request `correct` and `explanation` for the question list before submission. |
| Critical | `GET /api/practice-tests/{test_id}/questions?include_answers=true` | Any caller can request all answers for a source test before starting or submitting it. |
| Critical | `GET /api/questions/{question_id}` | Always returns `correct` and `explanation`; there is no attempt/session authorization state. |
| Critical | `GET /api/lessons/{lesson_id}` | `related_questions` are serialized with answers included. |
| Critical | `POST /api/exam-sessions/{session_id}/answers` | Calculates and returns `correct: true/false` even while a session is in Exam Mode. |
| Critical | `GET /api/exam-sessions/{session_id}` | Returns the persisted `correct` field for each saved answer before the exam is finished. |
| High | `POST /api/questions/{question_id}/attempt` | Accepts a client-supplied `correct` boolean, allowing progress/readiness history to be falsified. |
| High | Exam-session endpoints | No ownership/session token is present; numeric session IDs can be read directly. This is currently a single-user local app, but the contract is unsafe to reuse. |

Runtime key inspection confirmed the exposure without printing any answer content:

- Default question lists omit `correct` and `explanation`.
- Adding `include_answers=true` returns both fields.
- Single-question and lesson-related-question responses return both fields.
- Active exam session answer objects include `correct`.

Required target contract:

1. Remove public `include_answers` switches from pre-submission endpoints.
2. Separate `QuestionPrompt` from `QuestionReview` serializers.
3. Validate answers server-side and withhold correctness in Exam Mode until finish.
4. Return immediate correctness only for checked Practice Mode questions.
5. Compute attempt correctness server-side; never trust the client flag.

## Catalog And Content APIs

| Method | Path | Source | Replica disposition |
| --- | --- | --- | --- |
| GET | `/api/summary` | `routers/courses.py` | Replace vanity totals with canonical scoped summary or remove from route startup. |
| GET | `/api/tracks` | `routers/courses.py` | Retain as certification selector contract. |
| GET | `/api/tracks/{track_id}/courses` | `routers/courses.py` | Retain; add pagination/usable-count fields. |
| GET | `/api/courses` | `routers/courses.py` | Retain for administration/search; require explicit scope in learner routes. |
| GET | `/api/courses/{course_id}` | `routers/courses.py` | Retain; avoid embedding large child collections. |
| GET | `/api/courses/{course_id}/lessons` | `routers/courses.py` | Replace hard-coded `limit=1000` with paginated section-aware contract. |
| GET | `/api/courses/{course_id}/sections` | `routers/courses.py` | Retain; include verified counts and paging links. |
| GET | `/api/courses/{course_id}/practice-tests` | `routers/courses.py` | Retain; preserve source tests as separate records. |
| GET | `/api/lessons` | `routers/courses.py` | Retain but lower maximum page size and add `total`, `has_more`, stable cursor/order. |
| GET | `/api/lessons/{lesson_id}` | `routers/courses.py` | Retain after removing answered related-question leakage. |
| GET | `/api/lessons/{lesson_id}/transcript` | `routers/courses.py` | Retain; paginate or window long transcripts when needed. |
| GET | `/api/lessons/{lesson_id}/vtt` | `routers/courses.py` | Retain; generated notes must not masquerade as timed captions. |
| POST | `/api/lessons/{lesson_id}/notes` | `routers/courses.py` | Retain as contextual lesson utility. |
| GET | `/api/documents/{document_id}` | `routers/courses.py` | Retain; document truncation must be explicit in response metadata. |
| GET | `/api/media` | `routers/courses.py` | Retain byte-range implementation; add cache headers and path tests. |

## Practice And Exam APIs

| Method | Path | Source | Replica disposition |
| --- | --- | --- | --- |
| GET | `/api/questions` | `routers/questions.py` | Retain only as paginated prompt catalog; remove answer switch. |
| GET | `/api/practice-tests` | `routers/questions.py` | Retain; add paging and quality classification. |
| POST | `/api/exam-sessions` | `routers/questions.py` | Retain; capture immutable ordered question IDs and mode policy at start. |
| GET | `/api/exam-sessions/{session_id}` | `routers/questions.py` | Retain after hiding correctness for active Exam Mode. |
| POST | `/api/exam-sessions/{session_id}/answers` | `routers/questions.py` | Retain; Practice and Exam response policies must differ. |
| POST | `/api/exam-sessions/{session_id}/finish` | `routers/questions.py` | Retain; return deterministic score plus review payload. |
| GET | `/api/practice-tests/{test_id}/questions` | `routers/questions.py` | Retain prompt-only; remove answer switch and add pagination. |
| GET | `/api/practice-tests-legacy` | `routers/questions.py` | Deprecate after contract parity; do not use in replica UI. |
| GET | `/api/questions/{question_id}` | `routers/questions.py` | Split into prompt endpoint and authorized review endpoint. |
| POST | `/api/quiz/start` | `routers/questions.py` | Deprecate in favor of exam-session start; it does not persist a fixed session. |
| POST | `/api/quiz/grade` | `routers/questions.py` | Fold into Practice check and Exam finish contracts. |
| POST | `/api/questions/{question_id}/attempt` | `routers/questions.py` | Replace client-trusted correctness with server calculation. |
| GET | `/api/questions/{question_id}/bookmark` | `routers/questions.py` | Retain contextually. |
| POST | `/api/questions/{question_id}/bookmark` | `routers/questions.py` | Retain contextually. |
| GET | `/api/questions/{question_id}/notes` | `routers/questions.py` | Retain contextually. |
| POST | `/api/questions/{question_id}/notes` | `routers/questions.py` | Retain contextually. |

## Search And Tutor APIs

| Method | Path | Source | Replica disposition |
| --- | --- | --- | --- |
| GET | `/api/search` | `routers/search.py` | Retain FTS path; add certification/course/type filters. |
| POST | `/api/brain/ask` | `routers/ai.py` | Retain as no-key local retrieval contract; require context scope and typed citations. |
| POST | `/api/ai/ask` | `routers/ai.py` | Keep optional hosted streaming enhancement, never as the only answer path. |

The current local tutor search is not consistently scoped to a certification or current lesson. Its fallback executes `%LIKE%` scans over full lesson transcripts and question explanations. The target contract must accept and enforce `track_id`, optional `course_id`, `lesson_id`, `practice_test_id`, `question_id`, and exam-integrity policy.

## Progress And Study APIs

| Method | Path | Source | Replica disposition |
| --- | --- | --- | --- |
| GET | `/api/progress/summary` | `routers/progress.py` | Retain; scope by certification. |
| GET | `/api/progress/by-topic` | `routers/progress.py` | Replace Python aggregation with indexed/materialized skill evidence. |
| GET | `/api/progress/weak-topics` | `routers/progress.py` | Retain only as derived contextual result. |
| GET | `/api/progress/heatmap` | `routers/progress.py` | Retain as contextual progress view. |
| POST | `/api/progress/lesson` | `routers/progress.py` | Retain; validate lesson existence and track scope. |
| GET | `/api/study/goals` | `routers/study.py` | Retain as contextual progress/settings feature. |
| POST | `/api/study/goals` | `routers/study.py` | Retain. |
| POST | `/api/study/roadmap` | `routers/study.py` | Retain outside primary navigation. |
| PATCH | `/api/study/goals/{goal_id}` | `routers/study.py` | Retain. |
| POST | `/api/study/goals/{goal_id}/generate-plan` | `routers/study.py` | Retain after source-boundary validation. |
| GET | `/api/study/goals/{goal_id}/plan` | `routers/study.py` | Retain with pagination. |
| PATCH | `/api/study/plan-items/{item_id}` | `routers/study.py` | Retain. |
| GET | `/api/study/today` | `routers/study.py` | Retain as curriculum continuation utility, not a primary destination. |
| GET | `/api/study/readiness` | `routers/study.py` | Consolidate with one canonical progress/readiness contract. |
| GET | `/api/study/content-audit` | `routers/study.py` | Retain as admin/debug API, not learner route startup. |
| GET | `/api/study/practice-classifications` | `routers/study.py` | Retain as admin/quality API. |
| GET | `/api/study/question-duplicates` | `routers/study.py` | Retain as admin/quality API. |

## Skills, Intelligence, And Aggregate Experience APIs

| Method | Path | Source | Replica disposition |
| --- | --- | --- | --- |
| GET | `/api/skills/map` | `routers/skills.py` | Retain configuration payload; cache strongly. |
| GET | `/api/skills/summary` | `routers/skills.py` | Retain after mapping is populated. |
| GET | `/api/skills/{skill_id}/resources` | `routers/skills.py` | Retain as contextual lesson/question discovery. |
| GET | `/api/intelligence/portfolio` | `routers/intelligence.py` | Remove from route startup; keep optional progress detail. |
| GET | `/api/intelligence/command-brief` | `routers/intelligence.py` | Retire invented product framing; preserve only useful derived data. |
| GET | `/api/intelligence/skill-mastery` | `routers/intelligence.py` | Rework around materialized evidence; current cold request is 2.16s. |
| GET | `/api/intelligence/readiness` | `routers/intelligence.py` | Rework/materialize; every measured request is about 2.26s. |
| GET | `/api/intelligence/mistake-queue` | `routers/intelligence.py` | Keep as contextual results/review data. |
| GET | `/api/intelligence/diagnostic` | `routers/intelligence.py` | Keep only if diagnostic sessions become deterministic and persisted. |
| POST | `/api/intelligence/reindex-skill-map` | `routers/intelligence.py` | Admin/background operation only; never a learner-page action. |
| GET | `/api/experience/shell` | `routers/experience.py` | Reduce to tiny certification/navigation bootstrap or replace. |
| GET | `/api/experience/command-center` | `routers/experience.py` | Remove from replica startup; cold request measured 4.45s and returns 63.5 KB. |

## Labs, Flashcards, Data + AI, And Index APIs

| Method | Path | Source | Replica disposition |
| --- | --- | --- | --- |
| GET | `/api/labs/config` | `routers/labs.py` | Contextual Reference/Lesson utility. |
| GET | `/api/labs` | `routers/labs.py` | Contextual Reference/Lesson utility; require certification scope. |
| GET | `/api/labs/{lab_id}` | `routers/labs.py` | Retain; do not return solutions before evaluation. |
| POST | `/api/labs/{lab_id}/submit` | `routers/labs.py` | Retain. |
| GET | `/api/flashcards` | `routers/flashcards.py` | Contextual Review utility. |
| GET | `/api/flashcards/all` | `routers/flashcards.py` | Add pagination before substantial use. |
| POST | `/api/flashcards` | `routers/flashcards.py` | Retain. |
| POST | `/api/flashcards/generate` | `routers/flashcards.py` | Retain as lesson utility. |
| POST | `/api/flashcards/{card_id}/review` | `routers/flashcards.py` | Retain. |
| DELETE | `/api/flashcards/{card_id}` | `routers/flashcards.py` | Retain. |
| GET | `/api/data-ai/curriculum` | `routers/data_ai.py` | Integrate into the canonical Curriculum model instead of parallel top-level academy. |
| POST | `/api/data-ai/lessons/{lesson_id}/complete` | `routers/data_ai.py` | Adapt to canonical learning events/progress. |
| POST | `/api/data-ai/checks/{check_id}/submit` | `routers/data_ai.py` | Adapt to canonical Practice check contract. |
| POST | `/api/data-ai/labs/{lab_id}/submit` | `routers/data_ai.py` | Adapt to canonical lab contract. |
| GET | `/api/index/status` | `routers/index.py` | Admin/status use only. |
| POST | `/api/index/rebuild` | `routers/index.py` | Admin/background use only; protect against accidental UI invocation. |

## Contract Gaps Before Replica Work

1. No dedicated paginated Journal/Article API exists; the current journal is hardcoded in frontend JavaScript.
2. Reference results do not have a stable typed citation/link contract.
3. Curriculum lesson responses have no `total` or cursor metadata.
4. Exam sessions do not persist an ordered question list, timer deadline, flags, current position, or mode-specific disclosure policy.
5. There is no results/review authorization boundary separating active prompts from submitted answers.
6. There are three overlapping readiness/progress families (`progress`, `study`, `intelligence`) without one canonical calculation.
7. Data + AI is a parallel JSON/event model rather than the Track/Course/Section/Lesson model.
