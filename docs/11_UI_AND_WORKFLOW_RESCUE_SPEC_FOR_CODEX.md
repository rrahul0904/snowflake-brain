# Snowflake Brain - UI And Workflow Rescue Spec For Codex

Last updated: 2026-06-29

## 1. Why This Change Request Exists

The tool is still confusing because Codex reduced the sidebar labels but did not actually rebuild the user experience.

Current problem:

- The app still feels like a demo dashboard, not a study tool.
- Today page still has marketing hero language.
- Lessons page has too many controls and unclear hierarchy.
- Practice page is overloaded with mode cards, rails, filters, beta labels, icons, side panels, and mixed behavior.
- Review page is still basically old Analytics with vanity charts.
- Study Plan still exists as a competing command center.
- Topbar still shows developer/admin actions like Rebuild Index.
- The UI uses large decorative panels, gradients, and many custom classes instead of a calm certification-prep workflow.
- The app technically has guardrails, but the student still does not know exactly what to click next.

This pass is not backend architecture work.

This pass is a ruthless UI/workflow simplification pass.

## 2. Hard Rule For Codex

Do not add features.

Do not add new pages.

Do not add new charts.

Do not add new backend systems unless a current UI route cannot function without a small adapter.

Use existing APIs wherever possible.

The goal is to make the existing app understandable.

## 3. Current UI Diagnosis

### 3.1 Package Problem Still Exists

The clean package inside `dist/` may pass, but the uploaded working zip still includes junk:

- `.venv/`
- `.git/`
- `__MACOSX/`
- `.DS_Store`
- `__pycache__/`
- `data/`
- old `static/`
- nested `dist/`
- nested `review_artifacts/`

This means the source handoff is still messy.

Codex must distinguish:

- Clean distributable package.
- Dirty local working folder.

Do not upload or hand off the dirty working folder.

### 3.2 Today Page Problem

Current file:

- `frontend/views/dashboard.js`

Problems:

- It opens with a marketing hero: “Master the data cloud. Become SnowPro ready.”
- It says “Four levels. One serious Snowflake path.”
- It mixes stats, mission list, topic cards, study actions, and hero sections.
- It still feels like a landing page, not a daily workbench.
- “Done” buttons can mark tasks complete without the user actually doing the lesson/test.
- The user’s next action is not obvious.

### 3.3 Lessons Page Problem

Current file:

- `frontend/views/video.js`

Problems:

- Header says “Snowflake lesson workspace” but the layout feels like a course browser plus extra controls.
- Track, course, search, study date, course summary, assistant tab, course content, video, transcript, related questions, notes are all competing.
- Study target date inside Lessons is confusing. Target dates belong to Today/Plan, not the lesson player.
- Assistant tab in the right panel is not the right model. Tutor should be contextual and small.
- Lesson completion is not visually central.
- The user cannot easily answer:
  - Which certification am I studying?
  - Which course am I in?
  - Which lesson is next?
  - Is this real transcript or generated notes?
  - What should I do after this lesson?

### 3.4 Practice Page Problem

Current file:

- `frontend/views/quiz.js`

Problems:

- Too much UI before starting:
  - large header
  - mode cards
  - filters
  - topic filter
  - test list
  - side panel
  - mixed drill controls
- Practice Mode and Exam Mode are visually similar.
- The question rail is noisy for long tests.
- Buttons are confusing:
  - Finish practice
  - Submit answer
  - Back
  - Skip question
  - gear icon
  - arrow icon
- “Share feedback” is useless.
- “Practice mode (Beta)” makes the product feel unfinished.
- The app uses local frontend state and `recordAttempt`, not the real `exam_sessions` flow yet.
- The score report is just a toast, not a review screen.
- The user does not get a clean exam-prep experience.

### 3.5 Review Page Problem

Current file:

- `frontend/views/analytics.js`

Problems:

- It still says Analytics.
- It shows charts but does not tell the student what to repair.
- It depends on Chart.js from CDN.
- It is not aligned with the promised Review cockpit.
- It does not show:
  - missed questions
  - weak topics
  - practice history
  - content trust warnings
  - mapping warnings
  - next repair action

### 3.6 Topbar Problem

Current file:

- `frontend/components/topbar.js`

Problems:

- It shows index status and Rebuild Index on every page.
- This is developer/admin behavior, not daily study behavior.
- It wastes the most valuable space.
- It makes the product feel like an internal tool.

### 3.7 CSS Problem

Current file:

- `frontend/styles.css`

Problems:

- 70KB CSS file.
- Too many decorative gradients.
- Too many one-off page-specific class systems.
- Too many competing card styles.
- Dense workflows are not compact enough.
- The design does not clearly separate:
  - primary action
  - secondary action
  - warning
  - diagnostic/audit
  - learning content
  - exam content

## 4. Product Direction For This UI Rescue

The product should feel like:

> A calm local certification cockpit where every screen answers: what should I do next?

Not:

> A flashy course analytics dashboard with many disconnected tools.

Use this structure:

```text
Today   = What do I do now?
Lessons = Learn the next lesson in order.
Practice = Take a real test or drill missed questions.
Review  = Repair weak areas and check readiness.
```

## 5. New UI Rules

### Rule 1 - No Marketing Copy Inside Workflow Pages

Remove phrases like:

- Master the data cloud.
- Become SnowPro ready.
- Train like the exam is scheduled.
- Four levels. One serious Snowflake path.
- Local certification academy.
- SnowPro practice studio.

Use direct labels:

- Today
- Continue studying
- Next lesson
- Next practice test
- Weak topics
- Readiness
- Content warnings

### Rule 2 - One Primary Action Per Page

Each page must have one obvious primary action.

Today:

- Continue next task.

Lessons:

- Mark lesson complete / Continue next lesson.

Practice:

- Start selected test.

Review:

- Repair weakest topic.

### Rule 3 - Developer Actions Must Move Out Of Main UI

Move these away from topbar:

- Rebuild Index
- raw indexing status
- package/debug messaging

Create a small secondary “System” or “Index” link only if needed.

### Rule 4 - Study Plan Must Not Compete With Today

Study Plan is secondary.

Today is the main command center.

Study Plan can be a small link or drawer.

Do not show two different versions of “today’s work.”

### Rule 5 - Review Is Not Analytics

Review must show repair actions first.

Charts are optional and should be removed for now.

Remove external Chart.js dependency from `frontend/index.html`.

### Rule 6 - Make Empty/Weak Data Honest

If readiness is weak, do not hide it.

Show concise warnings:

- Not enough full mock exams.
- Mostly generated notes.
- Course mapping needs review.
- Too few questions for this track.
- No recent practice.

## 6. Route And Naming Cleanup

### Keep Route Compatibility

Keep old routes working:

- `#/` still loads Today.
- `#/video` still loads Lessons.
- `#/quiz` still loads Practice.
- `#/analytics` still loads Review.

### Add Clear Route Aliases

Add aliases:

- `#/today`
- `#/lessons`
- `#/practice`
- `#/review`

### Sidebar

Sidebar should show only:

```text
Today
Lessons
Practice
Review
```

Remove:

- numbered icons if they look like steps
- progress-fill animation on nav items
- Study roadmap as a large CTA

Add small footer links:

```text
Search
Cards
Labs
System
```

Only if needed.

## 7. Topbar Rebuild

### Replace Current Topbar

Current topbar shows:

- Snowflake branding
- SnowPro Core training workspace
- index status
- streak badge
- rebuild index button

Replace with:

```text
[Snowflake Brain]        Active goal: SnowPro Core      Local mode
```

Optional right side:

```text
Last indexed: <date> | System
```

Do not show Rebuild Index globally.

### Topbar Acceptance Criteria

- Topbar height reduced.
- No large admin button.
- No raw “Checking local index...” message during normal use.
- Active certification goal is visible.
- Local/private mode is visible.

## 8. Today Page Rebuild

### File

- `frontend/views/dashboard.js`

### New Purpose

Today should answer:

1. What certification am I working on?
2. What is the next task?
3. What is overdue?
4. What should I repair?
5. Am I exam ready?

### New Layout

```text
Today
-------------------------------------------------
Active goal: [SnowPro Core v]  Target: <date>

[Continue next task]
Title: Watch lesson / Take test / Review misses
Primary CTA: Continue
Secondary: View plan

-------------------------------------------------
Today's queue
[task row] [Start]
[task row] [Start]
[task row] [Start]

-------------------------------------------------
Weakest repair
Topic: Warehouses / RBAC / Snowpipe
CTA: Practice 10 questions

-------------------------------------------------
Readiness
Status: Learning / Needs Review / Insufficient Data
Warnings:
- No full mock exam completed
- 42 missed questions unresolved
- Generated notes in 1,007 lessons

-------------------------------------------------
Recent activity
Last lesson
Last test
Last score
```

### Remove From Today

Remove:

- hero section
- four-level marketing grid
- decorative readiness doughnut
- large generic stat cards
- “Master the data cloud” copy
- fake motivational sections
- primary Labs/Flashcards/Search links unless tied to next action

### Today Acceptance Criteria

- User can tell the next task in 5 seconds.
- Main CTA is visible above the fold.
- No chart library required.
- Done button is not the main completion model.
- If a user clicks a task, it passes relevant `track_id`, `course_id`, `lesson_id`, or `practice_test_id` in URL params.

## 9. Lessons Page Rebuild

### File

- `frontend/views/video.js`

### New Purpose

Lessons should feel like a course player, not a search dashboard.

### New Layout

```text
Lessons
Track: [SnowPro Core v]  Course: [Course v]

-------------------------------------------------
Left: Course outline
- Section 1
  - Lesson 1
  - Lesson 2
- Section 2
  - Lesson 3

Center: Lesson content
[Video or missing video state]
Lesson title
Content quality badge
Transcript / Notes tabs

Right: Study panel
Next action: Mark complete
Related questions
Ask about this lesson
```

### Remove From Lessons

Remove:

- study target date input
- “Course content / AI assistant” tab at top of side panel
- big decorative header
- generic “Snowflake certification prep” strip
- global search as a central behavior
- any cross-course related questions by default

### Add To Lessons

Add:

- breadcrumb:
  - Track > Course > Section > Lesson
- simple content quality badge:
  - Real transcript
  - Generated notes
  - Missing transcript
- clear Next Lesson button
- clear Mark Complete button
- if generated notes only, show:
  - “Generated notes only. Original transcript was missing or unusable.”
- if no duration:
  - show “Duration unavailable” quietly, not as `0:00`.

### Lessons Acceptance Criteria

- Track/course selectors are at top, not buried.
- Course outline is always visible on desktop.
- Mark Complete is the obvious next action.
- Refresh keeps selected lesson.
- Related questions are scoped to selected course by default.
- Missing video/transcript does not make the page feel broken.

## 10. Practice Page Rebuild

### File

- `frontend/views/quiz.js`

### New Purpose

Practice should feel like a serious exam runner.

### Step 1 - Practice Catalog

Show this before test starts:

```text
Practice
Track: [SnowPro Core v]  Course: [Course v]

Tabs:
[Full exams] [Practice tests] [Topic drills] [Missed questions]

Test cards:
Practice Test 1
98 questions
Source course: <course>
Primary CTA: Start Practice
Secondary CTA: Start Exam
```

### Remove From Setup

Remove:

- large mode cards
- topic chips at top unless in Topic Drills tab
- “Practice mode beta”
- “Share feedback”
- visual noise in the intro
- selected deck side panel if redundant

### Step 2 - Running Practice Mode

```text
Practice Mode
Question 12 of 98                         Exit

<Question>

A. ...
B. ...
C. ...
D. ...

[Submit answer]

After submit:
Correct / Incorrect
Explanation
Why this matters for exam
[Add to flashcards] [Ask tutor] [Next question]
```

Rules:

- Show explanation only after Submit Answer.
- Do not disable navigation unnecessarily.
- Keep bottom action bar simple.
- No gear icon.
- No arrow icon for bookmark.
- Use text labels:
  - Mark for review
  - Bookmark
  - Add flashcard

### Step 3 - Running Exam Mode

```text
Exam Mode
Question 12 of 98       Answered 9/98       Finish test

<Question>

A. ...
B. ...
C. ...
D. ...

[Save and next]
```

Rules:

- Do not show correctness until final submit.
- Allow user to jump questions through a collapsed Question Map.
- Preserve answers on refresh if exam session APIs exist.
- If real persistence is not wired yet, show a clear warning:
  - “This session is saved only in this browser until exam session persistence is complete.”

### Step 4 - Score Report

Do not use a toast as the score report.

Show a real score report screen:

```text
Score Report
Score: 72/98
Accuracy: 73%

Breakdown:
Correct
Incorrect
Unanswered

Next actions:
[Review missed questions]
[Create flashcards from misses]
[Retake this test]
[Go to Review]
```

### Practice Acceptance Criteria

- A test with 98 questions starts with 98 questions.
- Empty shells do not show in Full exams or Practice tests.
- Practice mode and Exam mode feel visibly different.
- Score report persists or clearly says persistence is not complete.
- The user can review missed questions after finishing.
- No icon-only controls for important actions.

## 11. Review Page Rebuild

### File

- `frontend/views/analytics.js`

Rename internal concept to Review, even if old route remains `#/analytics`.

### New Purpose

Review should tell the user what to fix.

### New Layout

```text
Review
Track: [SnowPro Core v]

-------------------------------------------------
Readiness
Status: Needs Review
Why:
- No full mock completed
- 42 unresolved missed questions
- RBAC accuracy under 60%

Primary action:
Repair weakest topic

-------------------------------------------------
Weak topics
[RBAC] 54% accuracy  [Practice 10]
[Warehouses] 61%     [Review misses]

-------------------------------------------------
Missed questions
Question | Topic | Source test | Action

-------------------------------------------------
Practice history
Test | Date | Score | Review

-------------------------------------------------
Content warnings
Generated notes
Missing durations
Mapping review candidates
Duplicate question groups
```

### Remove From Review

Remove:

- Chart.js dependency.
- generic topic chart.
- heatmap as primary content.
- vanity overview cards unless tied to action.

### Review Acceptance Criteria

- Every section has an action.
- The page explains why readiness is low.
- User can go from weak topic to practice.
- User can go from missed question to review.
- Content-quality warnings are visible but not overwhelming.

## 12. CSS Refactor Scope

### File

- `frontend/styles.css`

Do not attempt a full design system rewrite in one giant pass.

First create stable reusable classes.

### Add Core Layout Classes

```css
.page
.page-header
.page-title
.page-subtitle
.toolbar
.two-column
.three-column
.panel
.panel-header
.stack
.row
.metric
.badge
.warning
.empty-state
.error-state
.loading-state
.primary-action
.secondary-action
.danger-action
```

### Then Map Existing Pages To These Classes

Refactor only the four primary pages first:

- Today
- Lessons
- Practice
- Review

Do not polish secondary routes yet.

### Visual Direction

Use:

- calmer dark background
- fewer gradients
- smaller headers
- denser cards
- consistent buttons
- clear primary CTA
- clear warnings

Avoid:

- hero sections
- decorative large cards
- gradient overload
- page-specific visual identities
- icon-only important buttons

## 13. CDN Removal

### File

- `frontend/index.html`

Remove:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

Do not replace it unless Review truly needs charts.

For now, use plain HTML progress bars and tables.

Acceptance criteria:

- App works with internet disabled.
- No console error from missing Chart.js.
- Review still renders.

## 14. Existing API Usage

Use existing APIs first:

Today:

- `getTodayPlan`
- `getStudyGoals`
- `getStudyReadiness`
- `getContentAudit`
- `getProgressSummary`

Lessons:

- `getTracks`
- `getCourses`
- `getLessons`
- `getLesson`
- `getTranscript`

Practice:

- `getTracks`
- `getCourses`
- `getPracticeTests`
- `startQuiz`
- `getQuestion`
- `recordAttempt`

Review:

- `getStudyReadiness`
- `getTopicProgress`
- `getContentAudit`
- `getProgressSummary`

Only add backend endpoints if the UI truly cannot do the required workflow with these.

## 15. Implementation Order

### Pass 1 - Navigation And Topbar

1. Add route aliases:
   - `#/today`
   - `#/lessons`
   - `#/practice`
   - `#/review`
2. Keep old routes.
3. Simplify sidebar.
4. Move Study roadmap out of primary visual treatment.
5. Simplify topbar.
6. Remove global Rebuild Index button.

### Pass 2 - Today

1. Remove hero.
2. Build Next Task panel.
3. Build Today queue.
4. Build Readiness warnings.
5. Build Weakest repair panel.
6. Build Recent activity panel.
7. Ensure task links include URL params.

### Pass 3 - Lessons

1. Rebuild layout as outline/content/study panel.
2. Remove study date strip.
3. Add breadcrumb.
4. Add content quality badge.
5. Add clear Mark Complete / Next Lesson.
6. Keep assistant contextual and small.

### Pass 4 - Practice

1. Replace intro with clean catalog tabs.
2. Remove mode cards.
3. Split Start Practice and Start Exam buttons.
4. Simplify question runner.
5. Replace icon buttons with text labels.
6. Add real score report screen.
7. Keep rail collapsed by default for long tests.

### Pass 5 - Review

1. Replace Analytics heading with Review.
2. Remove Chart.js dependency.
3. Replace charts with readiness reasons and action tables.
4. Add weak topic actions.
5. Add content warning section.

### Pass 6 - CSS Cleanup

1. Add reusable classes.
2. Convert only primary routes.
3. Remove unused hero/marketing CSS after conversion.
4. Verify no layout overflow.

## 16. Stop Conditions

Stop and report blocker if:

- Any primary route renders blank.
- Any primary CTA does not work.
- Track/course filters leak content from another course.
- Practice test question count changes.
- A 98-question test does not load 98 questions.
- App requires internet to render primary pages.
- Topbar still shows developer controls.
- Review remains only charts with no actions.
- Today still looks like a marketing landing page.

## 17. Verification Checklist

Run:

```bash
python3 -m compileall app
python3 scripts/smoke_api.py
python3 scripts/check_source_boundaries.py
python3 scripts/check_question_counts.py
node --check frontend/router.js
node --check frontend/app.js
node --check frontend/api.js
node --check frontend/components/nav.js
node --check frontend/components/topbar.js
node --check frontend/views/dashboard.js
node --check frontend/views/video.js
node --check frontend/views/quiz.js
node --check frontend/views/analytics.js
scripts/package_review.sh
python3 scripts/check_package.py
```

Manual browser checks:

```text
#/today
#/lessons
#/practice
#/review
#/video
#/quiz
#/analytics
#/plan
#/search
#/flashcards
#/labs
#/ai
```

For each primary route confirm:

```text
- page loads
- one obvious primary action
- no marketing hero
- no console error
- no text overflow
- no CDN dependency
- track/course state works
```

## 18. Codex Execution Prompt

Paste this into Codex:

```text
You are not adding features. You are rescuing the Snowflake Brain UI because the current build is confusing and not usable.

Read:
- docs/07_HIGH_LEVEL_DESIGN.md
- docs/08_DATA_MODEL_AND_DATA_ARCHITECTURE.md
- docs/09_PROJECT_IMPLEMENTATION_PLAN_TASK_BY_TASK.md
- docs/10_CODEX_CHANGE_REQUEST_AFTER_REVIEW.md
- docs/11_UI_AND_WORKFLOW_RESCUE_SPEC_FOR_CODEX.md

Your job:
Make the existing app feel like a simple certification prep cockpit.

Primary routes:
- Today
- Lessons
- Practice
- Review

Do not add new pages.
Do not add new charts.
Do not add new backend architecture unless required for a broken UI interaction.
Do not work on secondary routes except to keep them from breaking.

Fix in this order:
1. Navigation and topbar.
2. Today page.
3. Lessons page.
4. Practice page.
5. Review page.
6. CSS cleanup.

Required UI changes:
- Remove marketing hero sections.
- Remove Chart.js CDN dependency.
- Move Rebuild Index out of the global topbar.
- Make Today show next task, today's queue, readiness warnings, weak repair, and recent activity.
- Make Lessons a course player with outline, video/transcript, content quality badge, related questions, and Mark Complete.
- Make Practice a clean catalog plus separate Practice Mode and Exam Mode flows.
- Replace score toast with a real score report.
- Make Review a repair cockpit, not Analytics charts.
- Use text labels for important actions instead of icon-only buttons.
- Keep old routes working while adding clear aliases: #/today, #/lessons, #/practice, #/review.

After each route is changed:
- run JS syntax check for that file.
- load the route manually.
- confirm no blank screen.
- confirm there is one obvious primary action.

Stop if question counts drop, tests merge, content leaks across courses, or primary routes break.
```
