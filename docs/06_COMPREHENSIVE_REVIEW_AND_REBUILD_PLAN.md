# Snowflake Brain - Comprehensive Review And Rebuild Plan

Last updated: 2026-06-29

## 1. Purpose

This document is the review handoff for Snowflake Brain. It explains what the product is supposed to become, what exists today, what is broken, what has already been implemented, and the phase-by-phase plan to rebuild it into a serious certification preparation workspace.

This is written for a technical reviewer, designer, or engineer who needs to understand the project without reading every source file first.

## 2. Executive Verdict

The current app has useful raw foundations:

- Local Docker app.
- FastAPI backend.
- SQLite database.
- Course/video/question ingestion.
- Track, course, lesson, test, question, search, lab, progress, flashcard, and study-plan routes.
- A working local browser app.

The product is not yet good enough as a student learning system. The biggest problem is not one CSS issue. The issue is product structure:

- Lessons still feel like indexed files, not a guided course player.
- Practice tests are not yet presented like serious exams.
- The AI assistant is not consistently grounded in the current lesson/question context.
- The UI has multiple competing visual systems.
- The content audit is only now becoming visible.
- The study plan foundation exists, but it is not yet deeply integrated into lessons and practice.

The rebuild should proceed from workflow to UI, not the other way around.

## 3. Product Vision

Snowflake Brain should be a private certification academy built from the user's downloaded paid course archive.

The product should help a student:

1. Select certification goals.
2. Follow a daily study plan.
3. Watch course lessons in source order.
4. Take full practice tests without merging them together.
5. Review wrong answers.
6. Ask an assistant that answers from the local course archive.
7. Track readiness by certification and topic.

The app should not feel like:

- A random file browser.
- A merged transcript dump.
- A generic quiz toy.
- A dashboard template copied across unrelated pages.

## 4. Primary User Scenario

Target scenario:

- A student wants to complete 3 Snowflake certifications in 100 days.
- The app starts with certification selection and exam dates.
- The app generates a daily study plan from the indexed lessons, tests, labs, and review work.
- The dashboard answers: "What should I do today?"
- Each course and practice test remains scoped to its source.
- Every mistake becomes review material.

Recommended first 3-cert path based on current indexed content:

1. SnowPro Core.
2. SnowPro Associate Platform.
3. SnowPro Advanced Architect.

Reason:

- SnowPro Core has the strongest question bank.
- Associate Platform has enough exam-like content to support a focused track.
- Advanced Architect has better indexed support than Advanced Data Engineer in the current dump.

## 5. Current Indexed Content Snapshot

Live audit from the local app:

| Metric | Count |
| --- | ---: |
| Certification tracks | 9 |
| Courses | 24 |
| Lessons | 1,305 |
| Practice test records | 279 |
| Questions | 3,386 |
| Documents | 24 |
| Generated English notes | 1,007 lessons |
| Transcript-like lessons | 298 lessons |

Important interpretation:

- The app saying "1,305 lessons" is technically true.
- But many lessons are generated fallback notes, not clean transcript text.
- This must be made visible in the UI with quality labels.

## 6. Architecture Snapshot

Runtime:

- Docker Compose service: `snowflake-brain`.
- Container name: `snowflake-brain-lab`.
- Local URL: `http://127.0.0.1:8010`.
- Backend: FastAPI.
- Frontend: vanilla ES modules.
- Database: SQLite.
- Search: SQLite FTS.

Important source areas:

- `app/main.py`: app setup and router registration.
- `app/database.py`: migrations and schema.
- `app/ingest.py`: course/question/transcript indexing.
- `app/routers/courses.py`: tracks, courses, lessons, documents, media.
- `app/routers/questions.py`: questions, practice tests, quiz start/grade/attempts.
- `app/routers/study.py`: study goals, roadmap, daily plan, readiness, content audit.
- `frontend/router.js`: SPA routes.
- `frontend/views/dashboard.js`: dashboard.
- `frontend/views/plan.js`: study plan page.
- `frontend/views/video.js`: lessons page.
- `frontend/views/quiz.js`: practice page.
- `frontend/styles.css`: current shared styling.

## 7. Data Model Status

Implemented core entities:

- `certification_tracks`
- `courses`
- `course_sections`
- `lessons`
- `transcript_chunks`
- `practice_tests`
- `questions`
- `question_attempts`
- `lesson_progress`
- `notes`
- `bookmarks`
- `flashcards`
- `lab_exercises`
- `lab_submissions`
- `daily_activity`
- `study_goals`
- `study_plan_items`

Recently added:

- `study_goals`
- `study_plan_items`
- indexes for study, lesson, test, and question workflows

Still needed:

- Track/course mapping override table.
- Content quality table or generated audit snapshots.
- Question duplicate review table.
- Exam session table for full timed attempts.
- Domain/objective mapping table.
- AI source citation table or structured retrieval result log.

## 8. Implemented Foundation

Implemented during the latest foundation slice:

- Study goal creation and listing.
- Study goal update.
- Daily plan generation.
- Multi-certification roadmap generation.
- Today's study queue.
- Study-plan task completion.
- Readiness scoring by track.
- Content audit endpoint.
- Frontend API bindings.
- New Study Plan page.
- Dashboard mission list connected to real plan tasks.
- Docker rebuild and live endpoint verification.

Live active goal:

- Track: SnowPro Core.
- Target date: 2026-10-06.
- Generated items: 156.

## 9. Critical Product Gaps

### Gap 1: Lessons Are Not Courseware Yet

Current issue:

- Lessons still feel like a searchable mixed archive.
- Generated notes can appear as if they are transcripts.
- Course sections and ordering are not yet presented strongly enough.

Required fix:

- Rebuild Lessons as a course player.
- Track selector.
- Course selector.
- Section outline.
- Ordered lesson list.
- Video center.
- Transcript/study-notes tab.
- Related questions/tests.
- Assistant scoped to the current lesson.

### Gap 2: Practice Is Not Yet A Serious Exam Runner

Current issue:

- Practice tests and random drills coexist awkwardly.
- Full tests are not visually prioritized.
- The exam workflow should be clearer.

Required fix:

- Practice Test catalog by track and course.
- Test intro page.
- Practice mode and exam mode cards.
- Full question navigation.
- Submit Answer for practice mode.
- Submit Test for exam mode.
- Final score report.
- Missed-question review.

### Gap 3: AI Tutor Is Not Contextual Enough

Current issue:

- Assistant exists, but the product needs stronger current-context grounding.

Required fix:

- Assistant input must include selected track, course, lesson, test, question, selected answer, and correct answer when available.
- Output must include concise explanation, key facts, exam tip, and source list.
- No external API should be required for the first local assistant mode.

### Gap 4: UI Is Not Unified

Current issue:

- Dashboard, lessons, quiz, search, labs, and AI pages feel like different products.

Required fix:

- One design system.
- One layout grammar.
- Compact professional panels.
- Clear student workflow.
- No giant decorative blocks inside dense study pages.
- No mixing Udemy imitation and glass dashboard styles without a design system bridge.

### Gap 5: Content Quality Is Not Managed

Current issue:

- Many lessons use generated notes.
- Duplicate questions remain.
- Track mapping can be wrong.

Required fix:

- Content audit UI.
- Track/course mapping overrides.
- Duplicate question review.
- Transcript quality labels.
- Practice test classification: full mock, quiz, micro quiz, drill source.

## 10. Rebuild Roadmap

### Phase 1: Foundation And Data Hierarchy

Status: mostly implemented.

Goal:

Preserve certification, course, section, lesson, practice test, and question boundaries.

Remaining work:

- Add mapping override table.
- Add duplicate review table.
- Add practice test classification.

Acceptance criteria:

- A course only shows its own lessons.
- A practice test only shows its own questions.
- Global search is the only global mixed mode.

### Phase 2: Scoped Backend APIs

Status: implemented for the main workflows.

Existing APIs:

- `/api/tracks`
- `/api/tracks/{track_id}/courses`
- `/api/courses/{course_id}/sections`
- `/api/courses/{course_id}/lessons`
- `/api/courses/{course_id}/practice-tests`
- `/api/practice-tests/{test_id}/questions`
- `/api/study/...`

Remaining work:

- Add admin-quality APIs for mapping overrides, duplicate review, and transcript quality.

### Phase 3: Lessons Page Rebuild

Status: next phase.

Deliverable:

A course-scoped lessons experience.

Implementation tasks:

1. Load tracks.
2. Select track.
3. Load courses for selected track.
4. Select course.
5. Load sections and lessons for selected course.
6. Render sectioned lesson outline.
7. Open selected lesson.
8. Render video player.
9. Render tabs: Overview, Transcript, Notes, Q&A/Assistant.
10. Show transcript quality badge: Transcript, Generated Notes, Missing.
11. Show related practice tests/questions for the selected course.
12. Persist lesson progress.

Acceptance criteria:

- Selecting SnowPro Core does not show Cost Optimization lessons.
- Selecting Cost Optimization does not show SnowPro Core lessons.
- Lesson list is ordered by source course order.
- Non-English transcript chunks are not shown as-is.
- Generated notes are labeled clearly.

### Phase 4: Practice Page Rebuild

Deliverable:

A serious practice test and exam runner.

Implementation tasks:

1. Track selector.
2. Course selector.
3. Practice test catalog.
4. Full test intro page.
5. Practice mode.
6. Exam mode.
7. Question runner.
8. Submit Answer.
9. Submit Test.
10. Score report.
11. Missed-question review.
12. Auto-create flashcards from misses.

Acceptance criteria:

- Practice Test 1, 2, 3 stay separate.
- A 98-question test loads 98 questions.
- Practice mode grades one question at a time.
- Exam mode grades only after Submit Test.

### Phase 5: Local RAG Assistant

Deliverable:

Assistant grounded in the local course archive.

Implementation tasks:

1. Build retrieval over lessons, transcript chunks, documents, questions, and explanations.
2. Add context-specific retrieval.
3. Add source citations.
4. Add current question explanation flow.
5. Add current lesson explanation flow.
6. Add "create flashcard from answer" action.

Acceptance criteria:

- Assistant cites local course/test/lesson sources.
- Assistant can explain the current quiz question.
- Assistant can summarize the current lesson.
- Assistant can answer without requiring an external API key.

### Phase 6: Study Planner Integration

Status: backend foundation implemented, UI partially visible.

Remaining work:

1. Goal setup UI.
2. 3-cert and 6-cert roadmap templates.
3. Calendar-style plan view.
4. Daily task completion tied to real lesson/test actions.
5. Readiness formula refinement.
6. Weak-topic repair queue.

Acceptance criteria:

- Dashboard answers "what should I do today?"
- Completing a lesson updates the plan.
- Submitting a practice block updates readiness.
- Weak topics generate review tasks.

### Phase 7: Analytics And Content Quality

Deliverable:

Trustworthy visibility into the archive and progress.

Implementation tasks:

1. Track-level readiness.
2. Domain-level readiness.
3. Practice test score trends.
4. Duplicate question audit.
5. Transcript quality audit.
6. Track mapping audit.
7. Content repair queue.

Acceptance criteria:

- User can see why counts are what they are.
- User can identify duplicates.
- User can identify weak/unsupported tracks.
- User can fix wrong course mappings.

### Phase 8: UI Consolidation

Deliverable:

One polished product UI.

Implementation tasks:

1. Define layout tokens.
2. Define components: sidebar, topbar, page head, panel, table, selector, test card, lesson row, progress bar.
3. Remove dead/competing CSS.
4. Replace page-specific hacks.
5. Verify desktop and narrow layouts.
6. Run browser screenshots for Dashboard, Study Plan, Lessons, Practice, AI Tutor.

Acceptance criteria:

- Pages feel like one product.
- Text does not overflow buttons/cards.
- Dense study workflows are compact and readable.
- UI no longer feels like unrelated prototypes.

## 11. Proposed 100-Day Plan Logic

For a 3-certification roadmap ending 2026-10-06:

- SnowPro Core: 2026-06-29 to 2026-07-31.
- SnowPro Associate Platform: 2026-08-01 to 2026-09-03.
- SnowPro Advanced Architect: 2026-09-04 to 2026-10-06.

Daily task types:

- Lesson.
- Question drill.
- Practice test.
- Mock exam.
- Lab.
- Flashcard/review.

Generation principles:

- Lessons first.
- Daily drill every study day.
- Full mock exams weekly after initial ramp-up.
- Labs every 10 days.
- Final 10 days focused on flashcards and missed questions.

## 12. Testing And Verification Plan

Backend:

- `python3 -m compileall app`
- FastAPI TestClient endpoint checks.
- SQLite count queries.
- Docker live API checks.

Frontend:

- Node syntax checks for touched ES modules.
- Browser smoke test for each route.
- Screenshot verification for Dashboard, Study Plan, Lessons, Practice.

Data:

- Track/course counts.
- Course lesson scope.
- Practice test question counts.
- Duplicate prompt report.
- Transcript quality report.

Acceptance gate before each phase closes:

- Docker rebuild succeeds.
- Live route works on `http://127.0.0.1:8010`.
- No new cross-track leakage.
- No silent merge of source tests.

## 13. Packaging Notes

The review zip should include:

- Source code.
- Frontend code.
- Markdown docs.
- Docker files.
- Requirements.

The review zip should exclude:

- `data/`
- SQLite databases.
- Downloaded paid course content.
- Virtual environments.
- Python caches.
- Node modules.
- Browser/cache artifacts.

Reason:

The reviewer needs source code and planning docs, not private course assets or local runtime data.

## 14. Immediate Next Action

The next engineering task should be Phase 3:

Rebuild Lessons as a scoped course player.

Do not start another broad UI polish pass until Lessons is structurally correct.
