# Snowflake Brain - Baseline Inventory

Generated at: 2026-06-29T11:58:28

## Database Counts

| Metric | Count |
| --- | ---: |
| tracks | 9 |
| courses | 24 |
| sections | 14 |
| lessons | 1305 |
| transcript_chunks | 24229 |
| practice_tests | 279 |
| questions | 3386 |
| labs | 40 |
| flashcards | 0 |
| study_goals | 1 |
| study_plan_items | 156 |
| empty_practice_tests | 84 |
| non_empty_practice_tests | 195 |

## Frontend Routes

- `#/`
- `#/ai`
- `#/analytics`
- `#/flashcards`
- `#/labs`
- `#/plan`
- `#/quiz`
- `#/search`
- `#/video`

## Backend API Routes

- `POST` `/api/ai/ask`
- `POST` `/api/brain/ask`
- `GET` `/api/courses`
- `GET` `/api/courses/{course_id}`
- `GET` `/api/courses/{course_id}/lessons`
- `GET` `/api/courses/{course_id}/practice-tests`
- `GET` `/api/courses/{course_id}/sections`
- `GET` `/api/documents/{document_id}`
- `POST` `/api/exam-sessions`
- `GET` `/api/exam-sessions/{session_id}`
- `POST` `/api/exam-sessions/{session_id}/answers`
- `POST` `/api/exam-sessions/{session_id}/finish`
- `GET` `/api/flashcards`
- `POST` `/api/flashcards`
- `GET` `/api/flashcards/all`
- `POST` `/api/flashcards/generate`
- `DELETE` `/api/flashcards/{card_id}`
- `POST` `/api/flashcards/{card_id}/review`
- `POST` `/api/index/rebuild`
- `GET` `/api/index/status`
- `GET` `/api/labs`
- `GET` `/api/labs/{lab_id}`
- `POST` `/api/labs/{lab_id}/submit`
- `GET` `/api/lessons`
- `GET` `/api/lessons/{lesson_id}`
- `POST` `/api/lessons/{lesson_id}/notes`
- `GET` `/api/lessons/{lesson_id}/transcript`
- `GET` `/api/lessons/{lesson_id}/vtt`
- `GET` `/api/media`
- `GET` `/api/practice-tests`
- `GET` `/api/practice-tests-legacy`
- `GET` `/api/practice-tests/{test_id}/questions`
- `GET` `/api/progress/by-topic`
- `GET` `/api/progress/heatmap`
- `POST` `/api/progress/lesson`
- `GET` `/api/progress/summary`
- `GET` `/api/progress/weak-topics`
- `GET` `/api/questions`
- `GET` `/api/questions/{question_id}`
- `POST` `/api/questions/{question_id}/attempt`
- `GET` `/api/questions/{question_id}/bookmark`
- `POST` `/api/questions/{question_id}/bookmark`
- `GET` `/api/questions/{question_id}/notes`
- `POST` `/api/questions/{question_id}/notes`
- `POST` `/api/quiz/grade`
- `POST` `/api/quiz/start`
- `GET` `/api/search`
- `GET` `/api/study/content-audit`
- `GET` `/api/study/goals`
- `POST` `/api/study/goals`
- `PATCH` `/api/study/goals/{goal_id}`
- `POST` `/api/study/goals/{goal_id}/generate-plan`
- `GET` `/api/study/goals/{goal_id}/plan`
- `PATCH` `/api/study/plan-items/{item_id}`
- `GET` `/api/study/practice-classifications`
- `GET` `/api/study/question-duplicates`
- `GET` `/api/study/readiness`
- `POST` `/api/study/roadmap`
- `GET` `/api/study/today`
- `GET` `/api/summary`
- `GET` `/api/tracks`
- `GET` `/api/tracks/{track_id}/courses`

## API Smoke Tests

| Path | Status | Response Shape |
| --- | ---: | --- |
| `/api/summary` | 200 | `['courses', 'meta', 'stats']` |
| `/api/tracks` | 200 | `['tracks']` |
| `/api/tracks/snowpro-core/courses` | 200 | `['courses']` |
| `/api/practice-tests?track_id=snowpro-core&min_questions=1` | 200 | `['tests']` |
| `/api/questions?track_id=snowpro-core&limit=1` | 200 | `['questions', 'total']` |
| `/api/lessons?track_id=snowpro-core&limit=1` | 200 | `['lessons']` |
| `/api/search?q=warehouse&limit=1` | 200 | `['results']` |
| `/api/labs` | 200 | `['labs']` |
| `/api/flashcards` | 200 | `['cards', 'due_today']` |
| `/api/study/goals` | 200 | `['goals']` |
| `/api/study/today` | 200 | `['date', 'goals', 'items']` |
| `/api/study/readiness?track_id=snowpro-core` | 200 | `['tracks']` |
| `/api/study/content-audit` | 200 | `['duplicate_prompts', 'mapping_review', 'practice_quality', 'totals', 'tracks', 'transcript_quality']` |
