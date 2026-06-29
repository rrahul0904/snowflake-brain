# Snowflake Brain - API Contracts

Last updated: 2026-06-29

## 1. Purpose

This document freezes the current backend API shapes before major Lessons and Practice rewrites.

Rules:

- Do not remove an endpoint without a replacement.
- Preserve response keys where possible.
- Frontend calls should go through `frontend/api.js`.
- New errors should use a structured shape when practical:
  - `error`
  - `message`
  - `details`
  - `request_id`

## 2. Core Summary And Scope APIs

### `GET /api/summary`

Purpose:

Return global indexed-content summary.

Response:

```json
{
  "stats": {
    "tracks": 9,
    "courses": 24,
    "practice_tests": 195,
    "lessons": 1305,
    "questions": 3386,
    "documents": 24,
    "flashcards": 0,
    "labs": 40
  },
  "meta": {},
  "courses": []
}
```

### `GET /api/tracks`

Purpose:

Return certification tracks and counts.

Response:

```json
{
  "tracks": [
    {
      "id": "snowpro-core",
      "title": "SnowPro Core",
      "description": "",
      "position": 1,
      "course_count": 7,
      "lesson_count": 21,
      "question_count": 2049,
      "practice_test_count": 49
    }
  ]
}
```

### `GET /api/tracks/{track_id}/courses`

Purpose:

Return courses scoped to one certification track.

Response:

```json
{
  "courses": [
    {
      "id": "course-id",
      "track_id": "snowpro-core",
      "track_title": "SnowPro Core",
      "title": "Course title",
      "lesson_count": 21,
      "question_count": 2049,
      "document_count": 0,
      "practice_test_count": 5
    }
  ]
}
```

### `GET /api/courses/{course_id}/sections`

Purpose:

Return source sections for one course.

Response:

```json
{
  "sections": [
    {
      "id": "section-id",
      "title": "Section title",
      "path": "",
      "position": 1,
      "lesson_count": 10
    }
  ]
}
```

### `GET /api/courses/{course_id}/lessons`

Purpose:

Return lessons scoped to one course.

Response:

```json
{
  "lessons": [
    {
      "id": "lesson-id",
      "course_id": "course-id",
      "course_title": "Course title",
      "section": "Section title",
      "title": "Lesson title",
      "position": 1,
      "video_path": "path.mp4",
      "vtt_path": "path.vtt",
      "transcript_path": "path.vtt",
      "duration_s": 300,
      "duration": 300,
      "excerpt": "..."
    }
  ]
}
```

### `GET /api/lessons/{lesson_id}`

Purpose:

Return lesson detail, transcript text, related questions, and notes.

Response:

```json
{
  "id": "lesson-id",
  "course_id": "course-id",
  "title": "Lesson title",
  "transcript_text": "...",
  "related_questions": [],
  "notes": []
}
```

## 3. Practice And Question APIs

### `GET /api/practice-tests`

Query:

- `track_id`
- `course_id`
- `q`
- `min_questions`

Purpose:

Return practice test records.

Response:

```json
{
  "tests": [
    {
      "track_id": "snowpro-core",
      "track_title": "SnowPro Core",
      "course_id": "course-id",
      "course_title": "Course title",
      "test_id": "test-id",
      "test_title": "Practice Test 1",
      "original_title": "Practice Test 1",
      "test_position": 1,
      "question_count": 98,
      "easy_count": 0,
      "medium_count": 98,
      "hard_count": 0
    }
  ]
}
```

### `GET /api/practice-tests/{test_id}/questions`

Query:

- `include_answers`

Purpose:

Return all questions for a single source practice test.

Response:

```json
{
  "test": {
    "id": "test-id",
    "title": "Practice Test 1",
    "question_count": 98
  },
  "questions": [],
  "total": 98
}
```

### `GET /api/questions`

Query:

- `track_id`
- `course_id`
- `test_id`
- `q`
- `tags`
- `difficulty`
- `unanswered`
- `bookmarked`
- `limit`
- `offset`
- `include_answers`

Response:

```json
{
  "questions": [],
  "total": 3386
}
```

### `POST /api/quiz/start`

Body:

```json
{
  "track_id": "snowpro-core",
  "course_id": "course-id",
  "test_id": "test-id",
  "count": 50,
  "mode": "random",
  "tags": [],
  "difficulty": "medium",
  "unanswered_only": false
}
```

Response:

```json
{
  "questions": [],
  "total": 50
}
```

### `POST /api/quiz/grade`

Body:

```json
{
  "answers": [
    {
      "question_id": "question-id",
      "selected": [0]
    }
  ]
}
```

Response:

```json
{
  "score": 1,
  "total": 1,
  "results": []
}
```

## 4. Exam Session APIs

### `POST /api/exam-sessions`

Body:

```json
{
  "track_id": "snowpro-core",
  "course_id": "course-id",
  "practice_test_id": "test-id",
  "mode": "practice"
}
```

Response:

```json
{
  "session": {
    "id": 1,
    "track_id": "snowpro-core",
    "course_id": "course-id",
    "practice_test_id": "test-id",
    "mode": "practice",
    "total_questions": 98,
    "status": "in_progress",
    "answered_count": 0
  }
}
```

### `GET /api/exam-sessions/{session_id}`

Response:

```json
{
  "session": {},
  "answers": []
}
```

### `POST /api/exam-sessions/{session_id}/answers`

Body:

```json
{
  "question_id": "question-id",
  "selected": [0]
}
```

Response:

```json
{
  "ok": true,
  "correct": true
}
```

### `POST /api/exam-sessions/{session_id}/finish`

Response:

```json
{
  "session": {},
  "score": 1,
  "total": 98,
  "answered": 1
}
```

## 5. Search And Tutor APIs

### `GET /api/search`

Query:

- `q`
- `limit`

Response:

```json
{
  "results": []
}
```

### `POST /api/brain/ask`

Purpose:

Local-first tutor/search answer endpoint.

Expected body:

```json
{
  "question": "Explain micro-partitions",
  "track_id": "snowpro-core",
  "course_id": "course-id",
  "lesson_id": "lesson-id",
  "question_id": "question-id"
}
```

Response:

```json
{
  "answer": "...",
  "sources": []
}
```

Important:

This endpoint must remain usable without an external AI key.

## 6. Study Plan APIs

### `GET /api/study/goals`

Response:

```json
{
  "goals": []
}
```

### `POST /api/study/goals`

Body:

```json
{
  "track_id": "snowpro-core",
  "target_exam_date": "2026-10-06",
  "weekly_hours": 10,
  "daily_question_target": 40,
  "auto_generate": true
}
```

Response:

```json
{
  "goal": {},
  "generated_items": 156
}
```

### `POST /api/study/roadmap`

Body:

```json
{
  "track_ids": ["snowpro-core", "associate-platform", "advanced-architect"],
  "target_end_date": "2026-10-06",
  "weekly_hours": 10,
  "daily_question_target": 40,
  "replace_existing": false
}
```

Response:

```json
{
  "goals": [],
  "skipped": [],
  "target_end_date": "2026-10-06"
}
```

### `GET /api/study/today`

Response:

```json
{
  "date": "2026-06-29",
  "goals": [],
  "items": []
}
```

### `GET /api/study/readiness`

Query:

- `track_id`

Response:

```json
{
  "tracks": []
}
```

### `GET /api/study/content-audit`

Response:

```json
{
  "totals": {},
  "transcript_quality": {},
  "practice_quality": {},
  "tracks": [],
  "duplicate_prompts": [],
  "mapping_review": []
}
```

## 7. Flashcard APIs

### `GET /api/flashcards`

Response:

```json
{
  "cards": []
}
```

### `GET /api/flashcards/all`

Response:

```json
{
  "cards": []
}
```

### `POST /api/flashcards`

Body:

```json
{
  "front": "Question",
  "back": "Answer",
  "source": "manual",
  "source_id": "question-id",
  "tags": []
}
```

Response:

```json
{
  "ok": true,
  "id": 1
}
```

## 8. Lab APIs

### `GET /api/labs`

Response:

```json
{
  "labs": []
}
```

### `GET /api/labs/{lab_id}`

Response:

```json
{
  "id": 1,
  "title": "Lab title",
  "description": "...",
  "starter_sql": "...",
  "solution_sql": "...",
  "expected_output": "...",
  "hint": "...",
  "tags": [],
  "difficulty": "medium"
}
```

### `POST /api/labs/{lab_id}/submit`

Body:

```json
{
  "sql": "CREATE WAREHOUSE ..."
}
```

Response:

```json
{
  "passed": true,
  "feedback": "..."
}
```

## 9. Content Audit APIs

### `GET /api/study/practice-classifications`

Query:

- `classification`
- `reviewed`
- `limit`

Response:

```json
{
  "classifications": []
}
```

### `GET /api/study/question-duplicates`

Query:

- `status`
- `limit`

Response:

```json
{
  "duplicates": []
}
```

