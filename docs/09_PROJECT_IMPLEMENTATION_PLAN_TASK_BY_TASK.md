# Snowflake Brain - Project Implementation Plan Task By Task

Last updated: 2026-06-29

## 1. Implementation Rule

Do not add new product surfaces until the core student workflow is correct.

The rebuild order is:

1. Clean package.
2. Reduce visible scope.
3. Fix data trust.
4. Rebuild Lessons.
5. Rebuild Practice.
6. Make local tutor useful.
7. Wire real progress/readiness.
8. Polish UI.

## 2. Phase 0 - Package And Repo Hygiene

Goal:

Create a clean, professional source package and remove confusion from review artifacts.

### Tasks

1. Update `.gitignore`.
2. Update `.dockerignore`.
3. Replace hardcoded host course path in `docker-compose.yml` with `CONTENT_ROOT_HOST`.
4. Add `scripts/package_review.sh`.
5. Ensure package script includes only:
   - `app/`
   - `frontend/`
   - `docs/`
   - `requirements.txt`
   - `Dockerfile`
   - `docker-compose.yml`
   - `README.md`
   - `REVIEW_PACKAGE.md`
   - `.gitignore`
   - `.dockerignore`
6. Ensure package script excludes:
   - `.git/`
   - `.venv/`
   - `data/`
   - `*.sqlite`
   - `static/`
   - `review_artifacts/`
   - `dist/`
   - `__pycache__/`
   - `.DS_Store`
   - `__MACOSX/`
7. Run package script.
8. Inspect zip contents.

### Acceptance Criteria

- No SQLite DB in package.
- No virtualenv in package.
- No paid course content in package.
- No nested review zip in package.
- Package can be rebuilt with one command.

## 3. Phase 1 - Simplify Visible Product Scope

Goal:

Make the product navigation match the real student workflow.

### Tasks

1. Change visible nav to:
   - Today
   - Lessons
   - Practice
   - Review
2. Keep existing secondary routes available but hidden:
   - Search
   - Flashcards
   - Labs
   - AI Tutor
   - Analytics
   - Study Plan
3. Rename Dashboard concept to Today.
4. Rename Analytics concept to Review when used as primary nav.
5. Keep Study Plan reachable from Today or a secondary CTA.

### Acceptance Criteria

- Sidebar shows only 4 primary workflows.
- Hidden routes still load directly.
- User is guided into the core study loop.

## 4. Phase 2 - Data Trust And Exam Session Foundation

Goal:

Add the model needed for trustworthy content, real exams, and event-driven progress.

### Tasks

1. Add `content_quality_audit`.
2. Add `course_track_overrides`.
3. Add `practice_test_classification`.
4. Add `question_duplicates`.
5. Add `exam_sessions`.
6. Add `exam_session_answers`.
7. Add `topic_objectives`.
8. Add `learning_events`.
9. Seed practice test classifications from current data.
10. Seed lesson quality audit from current data.
11. Seed duplicate question groups.
12. Add content-audit API output for:
    - transcript quality
    - duration missing
    - practice test classification
    - duplicate groups
    - mapping review candidates
13. Add endpoints for practice classifications.
14. Add endpoints for question duplicates.
15. Add exam-session start/save/finish endpoints.
16. Record learning events for:
    - lesson completion
    - quiz question answer
    - exam session start
    - practice test finish

### Acceptance Criteria

- Empty practice shells are visible and classified.
- Full mock exams are classified.
- Duplicate question groups are visible.
- Missing lesson durations are visible.
- Exam sessions can be started and finished.
- Learning events are written for real activity.

## 5. Phase 3 - Lessons Course Player Rebuild

Goal:

Make Lessons a real course-scoped learning experience.

### Backend Tasks

1. Verify `/api/tracks`.
2. Verify `/api/tracks/{track_id}/courses`.
3. Verify `/api/courses/{course_id}/sections`.
4. Verify `/api/courses/{course_id}/lessons`.
5. Verify `/api/lessons/{lesson_id}`.
6. Add lesson quality metadata to lesson APIs.
7. Add related questions endpoint scoped by course/lesson.
8. Add lesson complete endpoint that records:
   - `lesson_progress`
   - `learning_events`
   - related study plan item completion where applicable.

### Frontend Tasks

1. Replace current mixed lesson browser.
2. Add track selector.
3. Add course selector scoped to selected track.
4. Add section outline.
5. Add ordered lesson playlist.
6. Add video player.
7. Add tabs:
   - Overview
   - Transcript
   - Notes
   - Assistant
8. Add content quality badge:
   - Real transcript
   - Generated notes
   - Missing transcript
9. Add related questions panel.
10. Add Mark Complete action.

### Acceptance Criteria

- SnowPro Core shows only SnowPro Core courses/lessons.
- Cost Optimization shows only Cost Optimization course/lessons.
- Section order is stable.
- Lesson order is stable.
- Generated notes are labeled clearly.
- Lesson completion writes a learning event.

## 6. Phase 4 - Practice Exam Runner Rebuild

Goal:

Make Practice a serious certification test runner.

### Backend Tasks

1. Verify practice test classification.
2. Add practice catalog endpoint grouped by:
   - full mock exams
   - practice tests
   - section quizzes
   - topic drills
   - missed questions
   - bookmarked questions
3. Add exam-session API support for:
   - start
   - save answer
   - finish
   - score report
   - missed-question review
4. Add auto-flashcard creation from missed questions.
5. Add event writes for practice completion.

### Frontend Tasks

1. Replace current practice page structure.
2. Add track selector.
3. Add course selector.
4. Add catalog groups.
5. Add test intro page.
6. Add Practice Mode.
7. Add Exam Mode.
8. Add question runner.
9. Add explicit Submit Answer button in Practice Mode.
10. Add explicit Submit Test button in Exam Mode.
11. Add score report.
12. Add missed-question review.
13. Add "Create flashcard" for misses.

### Acceptance Criteria

- Full mock exams are separate from section quizzes.
- Empty shells do not appear as tests.
- Practice Test 1 and Practice Test 2 remain separate.
- A 98-question test loads 98 questions.
- Practice mode gives immediate feedback.
- Exam mode waits until final submit.
- Score report persists.

## 7. Phase 5 - Local Tutor Rebuild

Goal:

Make the assistant useful and local-first.

### Backend Tasks

1. Make `/api/brain/ask` the default tutor endpoint.
2. Make external LLM endpoint optional.
3. Add request context fields:
   - `track_id`
   - `course_id`
   - `lesson_id`
   - `practice_test_id`
   - `question_id`
   - `selected_answer`
   - `correct_answer`
4. Retrieve from:
   - current question
   - explanation
   - answer options
   - current lesson
   - transcript chunks
   - documents
   - related questions
5. Return:
   - answer
   - why correct
   - why other options are wrong
   - exam trap
   - sources

### Frontend Tasks

1. Replace main AI Tutor dependency on external API.
2. Embed tutor in Lessons.
3. Embed tutor in Practice.
4. Show source citations.
5. Add quick prompts:
   - Explain this question.
   - Why is my answer wrong?
   - Summarize this lesson.
   - Give me an exam trap.

### Acceptance Criteria

- AI Tutor works without `ANTHROPIC_API_KEY`.
- Every answer includes local sources.
- Quiz tutor understands current question and selected answer.
- Lesson tutor understands current lesson.

## 8. Phase 6 - Study Plan And Real Progress

Goal:

Make the plan respond to real learning activity.

### Tasks

1. Link lesson completion to plan item completion.
2. Link practice session finish to plan item completion.
3. Link flashcard reviews to plan item completion.
4. Link lab submissions to plan item completion.
5. Recalculate readiness from learning events.
6. Add weak-topic repair queue.
7. Add overdue task handling.
8. Improve plan generation using:
   - transcript quality
   - question availability
   - full mock availability
   - prior attempts
   - weak topics
   - missing durations

### Acceptance Criteria

- Today page updates from real activity.
- Readiness changes after finishing tests.
- Weak-topic review tasks appear after misses.
- Done button is secondary to real completion events.

## 9. Phase 7 - Review And Analytics

Goal:

Turn Review into an actionable repair center.

### Tasks

1. Show certification readiness.
2. Show domain/topic readiness.
3. Show practice test history.
4. Show missed questions.
5. Show due flashcards.
6. Show duplicate question audit.
7. Show content quality audit.
8. Show course mapping review.

### Acceptance Criteria

- User knows what to repair next.
- User can identify weak tracks.
- User can see unsupported certifications.
- User can inspect messy source data honestly.

## 10. Phase 8 - UI Consolidation

Goal:

Make the app feel like one product after workflow correctness is proven.

### Tasks

1. Define UI tokens.
2. Define common components:
   - page header
   - toolbar
   - selector
   - panel
   - table
   - progress bar
   - badge
   - test card
   - lesson row
3. Remove duplicate/old CSS.
4. Remove unused page-specific styles.
5. Verify desktop layout.
6. Verify narrow layout.
7. Take screenshots of:
   - Today
   - Lessons
   - Practice
   - Review

### Acceptance Criteria

- Pages feel consistent.
- Text does not overflow.
- Important controls are obvious.
- Dense workflows are compact and usable.

## 11. Phase 9 - Packaging And Handoff

Goal:

Create a clean review artifact after implementation.

### Tasks

1. Run backend checks.
2. Run frontend syntax checks.
3. Run Docker rebuild.
4. Run API smoke tests.
5. Run package script.
6. Inspect zip contents.
7. Update implementation status document.

### Acceptance Criteria

- Clean source zip exists in `dist/`.
- Package excludes database and private content.
- Docs match implementation status.

## 12. Stop Conditions

Pause implementation if:

- Track mapping is uncertain for many courses.
- Rebuild drops expected questions.
- Practice test question counts do not match source.
- Transcript filtering removes too much useful content.
- UI leaks content across tracks/courses.
- A feature requires external AI to function.

## 13. Verification Commands

Backend:

```bash
python3 -m compileall app
```

Frontend syntax:

```bash
/Users/297159/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check frontend/router.js
```

Docker:

```bash
CONTENT_ROOT_HOST="/path/to/downloads" docker compose up -d --build
```

Package:

```bash
scripts/package_review.sh
```

