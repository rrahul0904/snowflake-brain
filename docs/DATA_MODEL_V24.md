# V24 Certification Data Model

## Core entities

### certification_tracks
Certification identity and exam code.

### certification_task_progress
One row per certification task statement that the learner explicitly marks complete.

Primary key: `(track_id, skill_id)`.

### practice_tests
A named exam/question-bank grouping owned directly by a certification.

Important fields:
- `track_id`
- `exam_code`
- `source_kind`
- `source_path`
- `question_count`
- `version`
- `is_legacy`

### questions
A question owned directly by a certification. No course relationship exists.

Important fields:
- `track_id`
- `test_id`
- `question`
- `options_json`
- `correct_json`
- `explanation`
- `source_kind`
- `assessment_type`
- `multiple`
- `question_position`

### question_skill_map
Evidence edge from a question to a current certification task.

Important fields:
- `question_id`
- `track_id`
- `domain_id`
- `skill_id`
- `confidence`
- `reviewed`
- `evidence_json`

### question_attempts
Every answered practice question, including selected options, correctness, mode, and timestamp.

### exam_sessions
Persisted timed mock/source-exam summary.

### exam_session_answers
Per-question answers for persisted exam sessions when used by session-based flows.

### bookmarks / notes
Question-centric learner annotations.

### daily_activity
Minimal daily practice counters.

### learning_events
Certification-native activity events such as `question_answered`, `practice_test_finished`, `lab_attempted`, and `lab_passed`.

## Source provenance

`source_kind` values intentionally separate evidence classes:

- `source`: current source practice material
- `curated`: manually maintained questions
- `canonical`: deterministic supplemental questions derived from written task lessons
- `legacy`: older exam-version material; excluded from current readiness by default

## Removed legacy entities

V24 does not create or depend on:

- courses
- course sections
- media lessons
- transcript chunks
- documents from course archives
- lesson video progress
- course-root ingestion state

Questions and practice tests use direct `track_id` ownership instead.
