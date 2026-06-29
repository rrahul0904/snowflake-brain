# Snowflake Brain - Codex Change Request After Review

Last updated: 2026-06-29

## 1. Review Summary

The current high-level design, data architecture, and task-by-task implementation plan are directionally correct.

The strongest parts are:

1. Product scope is correctly reduced to the core student loop:
   - Today
   - Lessons
   - Practice
   - Review
2. Source boundaries are correctly protected.
3. Local-first assistant is correctly positioned as default.
4. Data trust is correctly treated as a first-class requirement.
5. Exam sessions and learning events are correctly identified as the foundation for real progress.
6. Packaging hygiene is correctly called out as Phase 0.

However, the plan still needs tighter implementation controls so Codex does not:
- Add more random pages.
- Build UI before backend contracts are stable.
- Break existing working endpoints.
- Lose questions during practice rebuild.
- Create migrations that are not repeatable.
- Fake progress/readiness with weak calculations.
- Leave hidden routes broken.
- Leak paid course content into review artifacts.

## 2. Global Implementation Rules For Codex

Follow these rules before editing any code.

### Rule 1 - No New Product Surfaces

Do not add any new first-class pages, nav items, dashboards, charts, assistants, or experimental tools.

Allowed primary routes only:

- Today
- Lessons
- Practice
- Review

Allowed secondary routes only if already present:

- Search
- Flashcards
- Labs
- AI Tutor
- Analytics
- Study Plan

### Rule 2 - Preserve Existing Working APIs

Before changing a backend route, document its current request and response shape.

Do not rename or remove an existing endpoint unless:
1. The replacement endpoint exists.
2. The frontend is updated.
3. A smoke test proves the route works.
4. Backward compatibility is preserved where possible.

### Rule 3 - Data First, UI Second

For each phase, implement in this order:

1. Database/migration.
2. Backend service.
3. API endpoint.
4. API smoke test.
5. Frontend state/service wrapper.
6. Frontend UI.
7. Browser smoke test.

Do not build frontend screens against imaginary endpoints.

### Rule 4 - Source Boundary Protection

Every Lessons, Practice, Tutor, and Review query must preserve:

- `track_id`
- `course_id`
- `section_id` where applicable
- `lesson_id` where applicable
- `practice_test_id` where applicable
- `question_id` where applicable

Global search or global drills are allowed only when the user explicitly selects global mode.

### Rule 5 - No Fake Readiness

Readiness must not be shown as a confident score unless it is based on real activity and enough content coverage.

If data is weak, show:

- `insufficient_data`
- `low_confidence`
- `mapping_unreviewed`
- `no_full_mock_exam`
- `too_few_questions`
- `mostly_generated_notes`

### Rule 6 - Local First Means Local First

The app must work without:

- `ANTHROPIC_API_KEY`
- OpenAI key
- external CDN
- internet access after local course archive is mounted

External AI can be optional only.

### Rule 7 - Package Must Never Include Private Runtime Data

The clean package must never include:

- `.git/`
- `.venv/`
- `data/`
- `*.sqlite`
- `static/` old build artifacts
- `review_artifacts/`
- `dist/`
- `__pycache__/`
- `.DS_Store`
- `__MACOSX/`
- downloaded paid course content

## 3. Required Additions To Current Plan

Add the following phases before the existing Phase 2.

---

## Phase 0A - Baseline Inventory And Regression Lock

Goal:

Capture the current working state before Codex rewrites anything.

### Tasks

1. Add `docs/BASELINE_INVENTORY.md`.
2. Record current counts:
   - tracks
   - courses
   - sections
   - lessons
   - transcript chunks
   - practice tests
   - empty practice tests
   - questions
   - labs
   - flashcards
   - study goals
   - study plan items
3. Record current route inventory:
   - frontend routes
   - backend routes
   - hidden routes
4. Record current endpoint smoke-test outputs.
5. Add `scripts/baseline_inventory.py`.
6. Add `scripts/smoke_api.py`.
7. Add `scripts/check_package.py`.
8. Add `scripts/check_source_boundaries.py`.
9. Add `scripts/check_question_counts.py`.

### Acceptance Criteria

- Baseline inventory can be regenerated with one command.
- Codex can compare pre-change and post-change counts.
- Any question count drop is flagged.
- Any route removal is flagged.
- Any package leak is flagged.

### Stop Conditions

Pause if:

- Baseline script cannot open the database.
- Existing question counts cannot be measured.
- Existing practice-test counts cannot be measured.
- Existing routes cannot be listed.

---

## Phase 0B - API Contract Freeze

Goal:

Prevent frontend/backend drift.

### Tasks

1. Add `docs/API_CONTRACTS.md`.
2. Document request/response contracts for:
   - `/api/summary`
   - `/api/tracks`
   - `/api/tracks/{track_id}/courses`
   - `/api/courses/{course_id}/sections`
   - `/api/courses/{course_id}/lessons`
   - `/api/lessons/{lesson_id}`
   - `/api/practice-tests`
   - `/api/practice-tests/{test_id}/questions`
   - `/api/search`
   - `/api/brain/ask`
   - existing study plan endpoints
   - existing flashcard endpoints
   - existing lab endpoints
3. Add Pydantic response models where missing.
4. Make frontend API calls use a single API client module.
5. Add error response format:
   - `error`
   - `message`
   - `details`
   - `request_id`

### Acceptance Criteria

- Every primary route uses documented APIs.
- Frontend has no scattered raw fetch calls.
- Failed APIs render useful UI errors.
- No frontend screen silently fails.

---

## Phase 0C - Migration And Seeding Safety

Goal:

Make DB changes repeatable and safe.

### Tasks

1. Add a simple migration runner if one does not exist.
2. Add `schema_migrations` table:
   - `version`
   - `name`
   - `applied_at`
3. Every new table must use `CREATE TABLE IF NOT EXISTS`.
4. Every new index must use `CREATE INDEX IF NOT EXISTS`.
5. Seeding scripts must be idempotent.
6. Add rollback notes for every migration, even if manual.
7. Add migration command to README.

### Acceptance Criteria

- Running migrations twice does not duplicate rows.
- Running seed scripts twice does not duplicate classifications.
- Existing data remains intact.
- SQLite file can be deleted and rebuilt from source archive.

### Stop Conditions

Pause if:

- Migration destroys existing questions.
- Migration changes source practice-test boundaries.
- Migration merges tests by title.
- Migration changes course IDs without mapping old IDs.

---

## 4. Changes To Phase 1 - Simplify Visible Product Scope

Keep current Phase 1, but add these tasks.

### Additional Tasks

1. Add route-level feature registry:
   - `primary`
   - `secondary`
   - `hidden`
   - `disabled`
2. Sidebar must render only routes marked `primary`.
3. Hidden routes must still be accessible directly by URL.
4. Add route smoke tests for:
   - Today
   - Lessons
   - Practice
   - Review
   - Search
   - Flashcards
   - Labs
   - AI Tutor
   - Analytics
   - Study Plan
5. Add empty-state UI for hidden routes if not actively rebuilt.

### Additional Acceptance Criteria

- No route produces a blank white screen.
- No hidden route appears in primary nav.
- Renaming Dashboard to Today does not break old dashboard route.
- Renaming Analytics to Review does not break old analytics route.

---

## 5. Changes To Phase 2 - Data Trust And Exam Session Foundation

Current Phase 2 is correct, but too broad. Split it into smaller implementation units.

---

## Phase 2A - Content Trust Tables

Goal:

Add content trust without touching exam behavior.

### Tables

- `content_quality_audit`
- `course_track_overrides`
- `practice_test_classification`
- `question_duplicates`

### Tasks

1. Create tables and indexes.
2. Add idempotent seeders.
3. Seed lesson quality:
   - `transcript_like`
   - `generated_notes`
   - `missing_transcript`
   - `non_english_filtered`
4. Seed practice classifications:
   - `full_mock_exam`
   - `practice_test`
   - `section_quiz`
   - `assignment`
   - `lab`
   - `empty_shell`
   - `ignore`
5. Seed duplicate question signatures.
6. Add admin/read endpoints:
   - `/api/content-audit/summary`
   - `/api/content-audit/lessons`
   - `/api/content-audit/practice-tests`
   - `/api/content-audit/course-mapping`
   - `/api/content-audit/question-duplicates`

### Acceptance Criteria

- Empty practice shells are classified and visible.
- Generated notes are classified and visible.
- Duplicate groups are visible.
- No UI behavior changes yet.
- No question count changes.

---

## Phase 2B - Manual Review Overrides

Goal:

Allow bad Codex/heuristic mappings to be corrected without changing source ingestion.

### Tasks

1. Add endpoint to list mapping candidates:
   - suspicious course-track mappings
   - low-confidence mappings
   - courses mapped only by title keywords
2. Add endpoint to apply course track override.
3. Add endpoint to review practice-test classification.
4. Add endpoint to review duplicate question status.
5. Add `reviewed_by` and `reviewed_at` where missing.
6. Frontend Review page should expose read-only audit first.
7. Editing overrides can be a secondary action.

### Acceptance Criteria

- Manual course-track override wins over inferred mapping.
- Practice-test classification override wins over seed classification.
- Review status survives app restart.
- Codex does not hardcode one-off course fixes in frontend.

---

## Phase 2C - Exam Session Tables

Goal:

Add real practice/exam persistence.

### Tables

- `exam_sessions`
- `exam_session_answers`
- `learning_events`

### Required Additional Fields

Add these fields to `exam_sessions` if not already planned:

- `correct_count`
- `incorrect_count`
- `unanswered_count`
- `duration_s`
- `started_from`
- `metadata_json`

Add these fields to `exam_session_answers` if not already planned:

- `is_final`
- `answered_index`
- `time_spent_s`
- `explanation_seen`
- `created_at`
- `updated_at`

### Tasks

1. Add exam session start endpoint.
2. Add save answer endpoint.
3. Add finish endpoint.
4. Add abandon endpoint.
5. Add resume endpoint.
6. Add score report endpoint.
7. Add missed-question review endpoint.
8. Add learning event writes.

### Acceptance Criteria

- Practice mode can save one answer at a time.
- Exam mode can save answers without revealing correctness.
- Finished sessions persist after refresh.
- Score report loads after page refresh.
- Abandoned sessions can be resumed or marked abandoned.

---

## 6. Changes To Phase 3 - Lessons Course Player Rebuild

Current Phase 3 is good. Add stricter state and source rules.

### Additional Backend Tasks

1. Add `/api/lesson-player/state`.
2. Add `/api/lesson-player/next`.
3. Add `/api/lesson-player/previous`.
4. Add `/api/lessons/{lesson_id}/complete`.
5. Add `/api/lessons/{lesson_id}/related-questions`.
6. Add server-side validation that lesson belongs to selected course and track.
7. Add fallback handling for missing video path.
8. Add fallback handling for generated notes only.
9. Add fallback handling for missing transcript.

### Additional Frontend Tasks

1. Save selected track, course, section, and lesson in URL query params.
2. On refresh, restore the same lesson.
3. Disable Mark Complete until a valid lesson is loaded.
4. Display content trust badge near transcript title.
5. Show warning when lesson has generated notes only.
6. Show warning when duration is missing.
7. Related questions must come only from the selected course unless global mode is explicitly enabled.

### Additional Acceptance Criteria

- Refreshing the page does not reset the selected lesson.
- A lesson from another course cannot appear in the selected course outline.
- Related questions never leak from another certification by default.
- Lesson completion updates Today within one refresh.
- Missing video/transcript does not crash the page.

---

## 7. Changes To Phase 4 - Practice Exam Runner Rebuild

Current Phase 4 is necessary, but Codex needs exact behavior.

### Additional Backend Tasks

1. Add `/api/practice/catalog?track_id=&course_id=`.
2. Add `/api/practice/tests/{test_id}/intro`.
3. Add `/api/exam-sessions`.
4. Add `/api/exam-sessions/{session_id}`.
5. Add `/api/exam-sessions/{session_id}/answers`.
6. Add `/api/exam-sessions/{session_id}/finish`.
7. Add `/api/exam-sessions/{session_id}/score-report`.
8. Add `/api/exam-sessions/{session_id}/misses`.
9. Add server-side question count validation.

### Practice Mode Rules

- Show one question at a time.
- User selects answer.
- User clicks Submit Answer.
- Backend saves answer.
- Backend returns correctness immediately.
- UI shows explanation, source, and exam trap.
- User moves to next question.

### Exam Mode Rules

- Show one question at a time or list navigation.
- User can change answers before final submit.
- Backend saves answers but does not return correctness.
- User clicks Submit Test.
- Backend grades all answers.
- UI shows score report only after finish.

### Additional Acceptance Criteria

- A test with 98 questions starts a session with exactly 98 questions.
- Empty tests cannot start sessions.
- Assignments/labs cannot start exam sessions unless explicitly supported.
- Practice Test 1 and Practice Test 2 remain separate even if titles are similar.
- Refreshing during an exam does not lose answers.
- Back/forward navigation does not corrupt session state.

---

## 8. Changes To Phase 5 - Local Tutor Rebuild

Current Phase 5 is right, but add guardrails.

### Additional Backend Tasks

1. Add `/api/tutor/context-preview`.
2. Add source ranking:
   - current question
   - current explanation
   - current lesson transcript
   - related questions
   - course documents
   - global search only when enabled
3. Add answer confidence:
   - `high`
   - `medium`
   - `low`
4. Add refusal/fallback when context is insufficient.
5. Add source objects:
   - `source_type`
   - `source_id`
   - `title`
   - `course_id`
   - `track_id`
   - `snippet`
6. Add no-external-key test.

### Additional Frontend Tasks

1. Tutor panel in Lessons gets lesson context automatically.
2. Tutor panel in Practice gets question context automatically.
3. Standalone AI Tutor route should show local mode status.
4. If external AI key is missing, UI should not show an error as failure.
5. Show sources under every answer.
6. Show low-confidence warning when needed.

### Additional Acceptance Criteria

- Tutor never requires external API key.
- Tutor can explain why selected answer is wrong.
- Tutor can summarize the selected lesson.
- Tutor never invents sources.
- Tutor clearly says when the local archive does not contain enough context.

---

## 9. Changes To Phase 6 - Study Plan And Real Progress

Current Phase 6 needs a clearer readiness formula.

### Add Readiness Statuses

Use these statuses instead of only one score:

- `not_started`
- `insufficient_data`
- `learning`
- `needs_review`
- `exam_ready_low_confidence`
- `exam_ready`
- `stale`

### Add Readiness Inputs

Readiness calculation must use:

1. Lesson completion percent.
2. Practice question coverage.
3. Practice accuracy.
4. Full mock exam score.
5. Number of full mock exams completed.
6. Recency of last practice.
7. Weak-topic unresolved count.
8. Flashcard due count.
9. Content quality confidence.
10. Course mapping confidence.

### Tasks

1. Add `/api/readiness/{track_id}`.
2. Add `/api/readiness/summary`.
3. Store readiness snapshots or compute deterministically.
4. Add weak-topic queue from missed questions.
5. Add overdue task handling.
6. Add confidence warnings.

### Acceptance Criteria

- Readiness cannot be high if no full mock exam exists.
- Readiness cannot be high if course mapping is unreviewed.
- Readiness cannot be high if question coverage is too low.
- Today page explains why readiness is low.
- Finishing a test changes readiness.

---

## 10. Changes To Phase 7 - Review And Analytics

Review should be a repair cockpit, not a chart dump.

### Required Review Sections

1. Certification readiness.
2. Weak topics.
3. Missed questions.
4. Practice history.
5. Due flashcards.
6. Content quality.
7. Mapping review.
8. Duplicate question review.
9. Unsupported/low-confidence tracks.

### Do Not Build

Do not build vanity charts that do not lead to an action.

Examples to avoid:

- generic total questions chart
- decorative streak chart
- huge heatmap with no repair action
- random course count cards

### Acceptance Criteria

- Every Review section has a next action.
- User can retake missed questions.
- User can create/review flashcards from misses.
- User can see why a readiness score is low.
- User can see which tracks lack enough material.

---

## 11. Changes To Phase 8 - UI Consolidation

Add design-system constraints before styling.

### Required Components

- `AppShell`
- `PrimaryNav`
- `PageHeader`
- `TrackSelector`
- `CourseSelector`
- `StatusBadge`
- `ContentQualityBadge`
- `TestCard`
- `LessonRow`
- `QuestionCard`
- `ScoreReport`
- `EmptyState`
- `ErrorState`
- `LoadingState`

### UI Rules

1. No page-specific button styles unless unavoidable.
2. No decorative hero sections inside workflows.
3. No separate visual identity per page.
4. Dense workflows should use compact rows/tables.
5. All primary actions should be visible above the fold.
6. Every async area needs loading/error/empty states.

### Acceptance Criteria

- Today, Lessons, Practice, and Review look like the same product.
- No text overflow in course/test cards.
- Mobile/narrow view remains usable.
- Page refresh does not lose active route state.

---

## 12. Add Phase 10 - Test And Verification Gate

Goal:

Prevent Codex from claiming completion without proof.

### Tasks

1. Add `scripts/verify_all.sh`.
2. It must run:
   - backend compile
   - backend API smoke tests
   - frontend syntax checks
   - package check
   - source boundary check
   - question count check
   - route smoke test
3. Add `docs/IMPLEMENTATION_STATUS.md`.
4. Every phase must update implementation status:
   - done
   - partial
   - blocked
   - not started
5. Add screenshot checklist for:
   - Today
   - Lessons
   - Practice catalog
   - Practice mode
   - Exam mode
   - Score report
   - Review

### Acceptance Criteria

- One command verifies the app.
- Status doc matches actual implementation.
- Codex cannot mark a phase done without passing checks.
- Any failed check prints a clear reason.

---

## 13. Revised Stop Conditions

Pause implementation immediately if any of these happen:

1. Total question count drops unexpectedly.
2. Any practice test loses questions.
3. A full mock exam is merged with another test.
4. Course lessons appear under the wrong certification.
5. Tutor requires external API key.
6. Study readiness is shown as high with insufficient data.
7. Clean package includes SQLite DB, paid content, `.venv`, `.git`, or old artifacts.
8. Existing route becomes blank or unreachable.
9. Migration cannot be safely rerun.
10. Frontend uses hardcoded local machine paths.
11. Backend silently swallows API errors.
12. UI marks tasks complete without writing learning events.

## 14. Revised Verification Commands

Backend compile:

```bash
python3 -m compileall app
```

Baseline inventory:

```bash
python3 scripts/baseline_inventory.py
```

API smoke test:

```bash
python3 scripts/smoke_api.py
```

Source boundary check:

```bash
python3 scripts/check_source_boundaries.py
```

Question count check:

```bash
python3 scripts/check_question_counts.py
```

Package check:

```bash
python3 scripts/check_package.py
```

Frontend syntax:

```bash
node --check frontend/router.js
```

Docker rebuild:

```bash
CONTENT_ROOT_HOST="/path/to/downloads" docker compose up -d --build
```

Full verification:

```bash
scripts/verify_all.sh
```

Package:

```bash
scripts/package_review.sh
```

## 15. Codex Execution Prompt

Use this prompt for Codex.

```text
You are improving Snowflake Brain. Do not add new product surfaces.

First read:
- docs/07_HIGH_LEVEL_DESIGN.md
- docs/08_DATA_MODEL_AND_DATA_ARCHITECTURE.md
- docs/09_PROJECT_IMPLEMENTATION_PLAN_TASK_BY_TASK.md
- docs/10_CODEX_CHANGE_REQUEST_AFTER_REVIEW.md

Your job is not to redesign the app. Your job is to stabilize and rebuild the core student workflow.

Follow this execution order:
1. Add baseline inventory and verification scripts.
2. Add API contract documentation.
3. Add migration safety.
4. Clean package and repo artifacts.
5. Simplify visible nav to Today, Lessons, Practice, Review.
6. Add data trust tables and seeders.
7. Add exam session and learning event model.
8. Rebuild Lessons as a course-scoped player.
9. Rebuild Practice as a persistent exam runner.
10. Make local tutor work without external API keys.
11. Recalculate progress/readiness from learning events.
12. Build Review as a repair cockpit.
13. Only then consolidate UI.

Hard rules:
- Do not remove existing working endpoints without replacement.
- Do not merge practice tests by title.
- Do not leak content across tracks/courses.
- Do not include SQLite DB, paid content, .venv, or .git in packages.
- Do not make the tutor require ANTHROPIC_API_KEY.
- Do not show high readiness when data is insufficient.
- Do not mark tasks complete without learning_events.

Before each phase:
- update docs/IMPLEMENTATION_STATUS.md as in progress.

After each phase:
- run scripts/verify_all.sh where possible.
- update docs/IMPLEMENTATION_STATUS.md with what passed, failed, and remains partial.

If a stop condition is hit, stop coding and write the blocker clearly.
```
