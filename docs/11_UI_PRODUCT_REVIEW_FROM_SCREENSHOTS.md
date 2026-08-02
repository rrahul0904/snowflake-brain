# Snowflake Brain - UI/Product Review From Current Screenshots

Last updated: 2026-06-29

## 1. Blunt Verdict

The tool still looks and feels like a prototype.

The sidebar has been reduced to the right high-level workflow:

- Today
- Lessons
- Practice
- Review

But the actual pages behind those items are still not rebuilt properly. The current UI is still a mix of old dashboard styling, unfinished course-player ideas, broken contrast, placeholder analytics, and practice-test scaffolding.

The problem is not just "make it prettier." The problem is that the core workflows are still not product-quality:

1. Lessons does not feel like a course player.
2. Practice does not feel like a real exam system.
3. Review does not feel like a repair cockpit.
4. The visual system is inconsistent and sometimes unreadable.
5. The app still exposes technical/indexed content instead of guiding the student.

## 2. Screenshot 1 - Lessons Page Problems

### What Is Broken

The Lessons page is currently unacceptable.

Observed issues:

- Large white lesson list area appears inside a dark product shell.
- Text inside the white area is almost unreadable because the contrast is broken.
- Lesson rows look disabled or washed out.
- The page shows "duration unknown" for every lesson.
- The page does not look like a course player.
- There is no strong video-player area.
- There is no clear right-side course outline like Udemy-style courseware.
- Search is too prominent for a lesson workflow.
- The selected course panel is visually heavy but not useful enough.
- The current course/section/lesson hierarchy is not clear.
- The page still feels like a generated file index, not a student learning experience.

### Why It Feels Bad

The user expects:

- Select certification.
- Select course.
- See sections.
- Click lesson.
- Watch video.
- Read transcript or generated notes.
- Ask assistant.
- Mark complete.

The current screen instead shows:

- Search box.
- Course card.
- Collapsible section-ish area.
- Broken lesson list styling.
- No confident learning flow.

### Required Fix

Rebuild Lessons as a real course player.

Required layout:

```text
Top:
  Track selector | Course selector | course progress

Main:
  Left/center:
    video player
    lesson title
    tabs: Overview | Transcript | Notes | Assistant

  Right:
    Course content
      Section 1
        lesson 1
        lesson 2
      Section 2
        lesson 1
        lesson 2
```

Required behavior:

- Selecting a track scopes courses.
- Selecting a course scopes lessons.
- Lessons are grouped by section.
- Generated notes show a visible badge.
- Missing duration is shown as a warning, not repeated noisily on every row.
- Mark Complete writes `lesson_completed`.
- Related questions come only from the selected course unless global mode is explicitly enabled.

## 3. Screenshot 2 - Review Page Problems

### What Is Broken

The Review page is still an Analytics page with weak charts.

Observed issues:

- Header says "Analytics" even though sidebar says "Review."
- Page title says "Performance breakdown," but it does not help the student repair anything.
- Four metric cards show:
  - Answered
  - Accuracy
  - Streak
  - Readiness
- Topic mastery chart is mostly empty.
- 90-day activity heatmap is decorative.
- There are no next actions.
- There is no missed-question review.
- There is no weak-topic repair queue.
- There is no due flashcard section.
- There is no content quality section.
- There is no mapping review.
- There is no duplicate question review.
- There is no explanation for why readiness is low.

### Why It Feels Bad

The page is called Review, but it does not let the student review.

The student needs:

- What did I get wrong?
- What topic is weak?
- What should I retake?
- Which flashcards are due?
- Which certification is unsupported?
- Why is my readiness low?
- Which content is low quality?

The current page gives passive charts instead of repair actions.

### Required Fix

Rebuild Review as a repair cockpit.

Required sections:

1. Certification readiness.
2. Weak topics.
3. Missed questions.
4. Practice history.
5. Due flashcards.
6. Content quality.
7. Mapping review.
8. Duplicate question review.
9. Unsupported / low-confidence tracks.

Every section must have a next action.

Examples:

- Retake missed questions.
- Review due flashcards.
- Open weak-topic lesson.
- Start topic drill.
- Review duplicate group.
- Review course mapping.

Do not build vanity charts unless they lead to an action.

## 4. Screenshot 3 - Practice Page Problems

### What Is Broken

The Practice page still does not feel like a professional exam runner.

Observed issues:

- Top content appears partially cut off.
- Text appears merged: `Practicemode`.
- Text appears merged: `LocalAI tutor`.
- The current selected track is SnowPro Snowpark, but the topbar still says Snowflake / SnowPro Core training workspace.
- The UI does not clearly separate:
  - Practice mode
  - Exam mode
  - Test catalog
  - Current test intro
- Test list is visually heavy but not actionable enough.
- Practice tests are shown, but the experience still does not feel like "start a serious exam."
- The AI Assistant tab exists but does not look integrated.
- There is no clear score/report flow visible.
- There is no visible persistent exam-session state.

### Why It Feels Bad

The practice page should feel like:

1. Choose certification.
2. Choose course/test bank.
3. Choose full mock / practice test / topic drill / missed questions.
4. Start practice mode or exam mode.
5. Answer questions.
6. Submit answer or submit test.
7. Review results.

The current page still feels like a catalog experiment.

### Required Fix

Rebuild Practice as a proper exam runner.

Required top-level structure:

```text
Track selector
Course selector

Practice catalog:
  Full Mock Exams
  Course Practice Tests
  Topic Drills
  Missed Questions
  Bookmarked Questions

Selected test intro:
  title
  question count
  estimated duration
  practice mode button
  exam mode button

Question runner:
  question
  answer choices
  submit answer / submit test
  explanation
  source
  assistant

Score report:
  score
  accuracy
  missed questions
  weak topics
  create flashcards
```

Required behavior:

- Empty shells cannot start sessions.
- Assignments/labs cannot appear as full tests.
- Full mock exams stay separate.
- Practice Test 1 and Practice Test 2 stay separate.
- A test with 44 questions starts with exactly 44 questions.
- Exam mode persists answers after refresh.
- Practice mode gives immediate feedback.
- Exam mode hides correctness until final submit.

## 5. Global UI Problems

### 5.1 Visual System Is Still Not Unified

The shell is dark glass.

Some inner areas are:

- dark panels
- purple panels
- near-white panels
- washed-out rows
- chart cards
- old Udemy-inspired containers

This is why the app looks patched together.

### 5.2 Contrast Is Broken

The Lessons screen has white or pale panels with near-white text.

This is a hard usability failure.

Rule:

Every page must pass basic contrast by inspection before being considered usable.

### 5.3 Topbar Context Is Wrong

The topbar says:

```text
Snowflake
SnowPro Core training workspace
```

But the Practice page is showing SnowPro Snowpark.

This creates trust damage.

The topbar must reflect the selected track or become generic:

```text
Snowflake Brain
Local certification workspace
```

### 5.4 The App Still Shows Counts Instead Of Guidance

The app says:

- 3,386 questions
- 1,305 lessons

But the user wants:

- What do I study now?
- Which course is next?
- Which test should I take?
- What is weak?
- What is wrong in my answers?

Counts are secondary.

## 6. What Must Happen Next

Do not add new pages.

Do not polish random CSS.

Do not add another dashboard.

The next work must be in this order:

1. Fix topbar context.
2. Fix unreadable contrast immediately.
3. Rebuild Lessons page structurally.
4. Rebuild Practice page structurally.
5. Rebuild Review as a repair cockpit.
6. Only then consolidate UI styling.

## 7. Immediate Hotfixes

These should be done before deeper rebuild work:

### Hotfix 1 - Fix Unreadable Lesson List

Remove the white/pale lesson list background or switch text to dark.

Preferred:

- Keep the page dark.
- Use compact lesson rows.
- Use clear selected state.

### Hotfix 2 - Fix Topbar Context

Stop showing SnowPro Core globally when another track is selected.

Use generic text until selected-track state is globally managed.

### Hotfix 3 - Rename Review Header

Change:

```text
Analytics
Performance breakdown
```

To:

```text
Review
Repair your weak areas
```

### Hotfix 4 - Fix Practice Header Text

Fix merged text:

- `Practicemode`
- `LocalAI tutor`

Use proper labels:

- `Practice mode`
- `Local AI tutor`

## 8. Proper Phase Order From Here

### Phase A - UI Stabilization Hotfix

Scope:

- Contrast fix.
- Topbar context fix.
- Review naming fix.
- Practice label spacing fix.

Acceptance:

- No unreadable text.
- No wrong global SnowPro Core label.
- No merged labels.

### Phase B - Lessons Rebuild

Scope:

- Course player.
- Section outline.
- Video.
- Transcript/notes badge.
- Related questions.
- Lesson completion event.

Acceptance:

- Course scope is strict.
- Refresh restores selected lesson.
- Missing transcript/video does not crash page.

### Phase C - Practice Rebuild

Scope:

- Catalog.
- Full mocks.
- Practice mode.
- Exam mode.
- Persistent sessions.
- Score report.

Acceptance:

- Full tests stay separate.
- Question counts match source.
- Exam refresh does not lose answers.

### Phase D - Review Rebuild

Scope:

- Readiness reasons.
- Weak topics.
- Missed questions.
- Practice history.
- Flashcards due.
- Content quality.
- Mapping review.
- Duplicate review.

Acceptance:

- Every section has an action.
- No vanity charts.

### Phase E - UI System Consolidation

Scope:

- Shared components.
- Shared colors.
- Shared panel styles.
- Shared buttons.
- Shared loading/error/empty states.

Acceptance:

- Today, Lessons, Practice, Review feel like one product.

## 9. Final Assessment

The app is not acceptable yet.

The good news:

- The backend foundation exists.
- The indexed content exists.
- The guardrail scripts exist.
- The source boundaries are measurable.
- The package checks exist.

The bad news:

- The user-facing product still feels bad.
- The pages still look like prototypes.
- Review does not review.
- Lessons does not teach.
- Practice does not yet feel like a real exam runner.

The next change should be a small UI stabilization hotfix, followed by a real Lessons rebuild.

