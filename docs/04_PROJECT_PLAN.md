# Snowflake Brain Rebuild - Project Plan

## Principle

Implementation must proceed in small verified slices. Each slice should end with browser verification against real downloaded course content.

## Phase 0 - Planning And Agreement

Status: current phase.

Tasks:

1. Create high-level tasks document.
2. Create design document.
3. Create data model document.
4. Create implementation project plan.
5. Review with user before continuing feature work.

Deliverables:

- `docs/01_HIGH_LEVEL_TASKS.md`
- `docs/02_DESIGN_DOCUMENT.md`
- `docs/03_DATA_MODEL.md`
- `docs/04_PROJECT_PLAN.md`

Exit criteria:

- User approves the rebuild direction.

## Phase 1 - Foundation And Data Hierarchy

Goal:

Make the backend preserve certification, course, section, lesson, practice test, and question boundaries.

Tasks:

1. Add `certification_tracks`.
2. Add `course_sections`.
3. Add `practice_tests`.
4. Add track fields to `courses`.
5. Add test and question ordering fields to `questions`.
6. Implement track inference.
7. Update index rebuild to populate all hierarchy tables.
8. Preserve source section and lesson order.
9. Preserve source practice test and question order.
10. Refresh course counts after indexing.

Verification:

- Query DB for tracks and counts.
- Query one SnowPro Core course and confirm lessons only belong to that course.
- Query one course with practice tests and confirm Practice Test 1, Practice Test 2, etc.

## Phase 2 - Scoped Backend APIs

Goal:

Frontend should not need to load global mixed content for normal workflows.

Tasks:

1. Add `/api/tracks`.
2. Add `/api/tracks/{track_id}/courses`.
3. Add `/api/courses/{course_id}/sections`.
4. Add `/api/courses/{course_id}/lessons`.
5. Add `/api/courses/{course_id}/practice-tests`.
6. Add `/api/practice-tests/{test_id}/questions`.
7. Add filtering by `track_id`, `course_id`, and `test_id` for questions.
8. Keep global search separate.

Verification:

- SnowPro Core API returns only SnowPro Core courses.
- Cost Optimization API returns only that course's lessons and tests.
- Practice test API returns the full expected question count.

## Phase 3 - Lessons Page Rebuild

Goal:

Replace mixed lesson browsing with course-scoped courseware.

Tasks:

1. Add track selector.
2. Add course selector scoped to selected track.
3. Show section list for selected course.
4. Show ordered lesson playlist grouped by section.
5. Open selected lesson in main panel.
6. Show video.
7. Show English transcript or generated English notes.
8. Add related practice tests/questions for that course.
9. Add assistant panel for selected lesson.

Verification:

- Select SnowPro Core track.
- Select SnowPro Core course.
- Confirm no Cost Optimization lessons appear.
- Select Cost Optimization course.
- Confirm only Cost Optimization lessons appear.
- Confirm transcript is English only.

## Phase 4 - Practice Page Rebuild

Goal:

Create a serious practice test runner.

Tasks:

1. Add track selector.
2. Add course selector.
3. Add practice test catalog.
4. Show full question count for every test.
5. Start complete practice test.
6. Start mixed drill as secondary option.
7. Practice mode:
   - Select answer.
   - Submit Answer.
   - Show correct or incorrect.
   - Show downloaded explanation.
   - Record attempt.
8. Exam mode:
   - Save answers.
   - Submit Test.
   - Show final score.
   - Show missed-question review.
9. Replace oversized question map with compact navigation.
10. Add assistant beside current question.

Verification:

- Select a test with 100+ questions.
- Confirm all questions load.
- Submit one answer and see result.
- Submit full exam and see score.

## Phase 5 - Local RAG Assistant

Goal:

Assistant should answer using the indexed local course dump.

Tasks:

1. Build retrieval over:
   - lessons
   - transcript chunks
   - documents
   - questions
   - explanations
2. Add `/api/assistant/ask`.
3. Include current context:
   - current lesson
   - current question
   - selected answer
4. Generate concise source-grounded answer.
5. Return source metadata and links.
6. Show assistant in Lessons and Practice pages.

Verification:

- Ask about current question.
- Answer cites local sources.
- Ask about current lesson.
- Answer cites lesson or transcript chunk.

## Phase 6 - Six-Month Study Planner

Goal:

Turn the app into a daily certification coach.

Tasks:

1. Add study goal setup.
2. Let student choose certifications and exam dates.
3. Generate weekly milestones.
4. Generate daily tasks.
5. Track task completion.
6. Calculate readiness by track:
   - lesson completion
   - practice accuracy
   - mock exam score
   - weak topics
7. Show today's plan on dashboard.

Verification:

- Create six certification goals.
- Generate six-month plan.
- Dashboard shows today's lessons, test block, review, and lab.

## Phase 7 - UI Polish And Browser Demo

Goal:

Make the app presentable and usable.

Tasks:

1. Replace generic dashboard styling with certification console layout.
2. Use compact panels and clear hierarchy.
3. Remove unnecessary timers.
4. Add clear submit buttons.
5. Keep text readable and contained.
6. Test desktop and narrow layouts.
7. Rebuild Docker image.
8. Re-index archive.
9. Demo in browser.

Verification:

- Browser screenshot for Lessons.
- Browser screenshot for Practice.
- API counts match indexed DB.
- No non-English transcript samples in indexed lessons.

## Suggested Implementation Order

1. Phase 1 data hierarchy.
2. Phase 2 scoped APIs.
3. Phase 3 Lessons page.
4. Phase 4 Practice page.
5. Phase 5 local assistant.
6. Phase 6 study planner.
7. Phase 7 polish and demo.

## Stop Conditions

Pause and review before continuing if:

- Track inference maps many courses incorrectly.
- Index rebuild drops a large number of expected questions.
- A practice test's question count does not match source metadata.
- Transcript filtering removes too much useful English content.
- UI scope leaks content from another course or track.

