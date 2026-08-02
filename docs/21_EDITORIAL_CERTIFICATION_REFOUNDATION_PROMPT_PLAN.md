# Data + AI Certification Studio: Implementation Prompt Plan

Last updated: 2026-07-31

## Purpose

This prompt pack refounds the existing application as a coherent certification-learning product using the layout, interaction model, visual rhythm, and motion language shown in:

`/Users/297159/Desktop/Screen Recording 2026-07-31 at 11.26.33 AM.mov`

The implementation target is a pixel-faithful reconstruction of the reference experience with Snowflake Brain's own name, course content, questions, and certification data. Match the reference page geometry, component placement, density, typography roles, color relationships, responsive behavior, transitions, hover states, and exam workflow. Do not copy the reference product's name, logo, written content, proprietary questions, or certification claims.

## How To Use This Plan

1. Run the Master Prompt once at the beginning of the implementation task.
2. Run Phase 0 before changing application code.
3. Execute one phase at a time in order.
4. Rebuild Docker and review the live browser after every phase.
5. Do not begin the next phase until the current acceptance criteria pass.
6. Preserve the existing downloaded courses, questions, videos, transcripts, progress, and SQLite database.

## Target Product

Working name: **Data + AI Certification Studio**

Product promise:

> A private, content-first workspace for learning Data and AI platforms, completing certification practice, and receiving evidence-based guidance from owned course material.

Primary learner workflow:

`Choose certification -> Follow curriculum -> Study lesson -> Practise -> Review evidence -> Repeat`

Primary navigation:

- Curriculum
- Practice
- Reference
- Journal

Contextual utilities, not primary destinations:

- AI tutor
- Search
- Notes
- Bookmarks
- Progress
- Career roadmap

The current `Career Lab`, `AI Academy`, `Learn`, `Labs`, `Intelligence`, and `Readiness` experiences must be consolidated into the four primary areas instead of remaining separate top-level products.

## Product Principles

1. **Content before dashboards.** Show the lesson, question, resource, or next action before showing analytics.
2. **One job per screen.** Every screen must have one dominant action.
3. **No fake evidence.** Counts, progress, and readiness must come from stored records.
4. **No invented feature language.** Prefer `Curriculum`, `Lesson`, `Practice Test`, `Reference`, and `Progress` over branded internal terminology.
5. **English only.** All visible UI, transcripts, generated study notes, questions, and explanations must be English.
6. **Preserve source boundaries.** Courses, practice tests, and lessons remain grouped according to their source and certification.
7. **No mixed certifications.** The selected certification filters curriculum, practice, references, and progress globally.
8. **Contextual AI.** AI assistance appears beside a lesson or question and cites source material. It is not a disconnected chat destination.
9. **Restraint over decoration.** Avoid metric strips, oversized progress circles, nested cards, excessive pills, glass panels, and repeated marketing copy.
10. **Fast by default.** Routes must not fetch or render the entire content archive.

## Reference Fidelity Contract

The phrase `match the reference` means all of the following:

- Reconstruct each reference screen at the same viewport proportions before adapting it responsively.
- Match header height, content rails, maximum widths, gutters, vertical spacing, alignment, and visible information density.
- Match the visual hierarchy: small metadata, editorial display heading, restrained body copy, thin rules, compact controls, and sparse accent use.
- Match component states: default, hover, focus, active, selected, disabled, correct, incorrect, flagged, answered, and submitted.
- Match navigation behavior and the transition from editorial pages into the immersive exam workspace.
- Match motion character and timing, not merely the final static frame.
- Substitute Snowflake Brain content and branding without changing the composition.
- Do not add dashboards, sidebars, cards, charts, metrics, pills, or utilities that are absent from the corresponding reference screen.

Fidelity must be verified with image overlays and interaction recordings. A subjective statement such as `looks similar` is not acceptance evidence.

## Exact Layout Map

### Global Editorial Shell

- Full-width near-black page with a single compact top navigation bar.
- Brand at the left, four quiet navigation links near the center-left, compact account/progress controls at the right, and one warm accent action.
- Main content sits on a narrow centered editorial rail with large calm margins.
- Footer is low-density and aligned to the same content rail.
- No persistent application sidebar on curriculum, reference, journal, or test-setup pages.

### Curriculum

- Centered page heading followed by sparse grouped link rows.
- Course and learning groups use thin dividers and typographic hierarchy rather than dashboard cards.
- Supplemental articles appear as a compact asymmetrical editorial grid.
- Hover changes border/text/accent treatment without moving surrounding layout.

### Reference And Journal

- Reference uses a simple text-first directory grouped by source category.
- Journal uses compact article tiles with controlled accent thumbnails or code fragments.
- Article detail uses a narrow reading column, serif heading, generous line height, inline code blocks, and restrained section spacing.

### Practice Setup

- Test title and explanatory copy are centered in a narrow column.
- Exam statistics form one compact horizontal row.
- Mode/domain controls sit below the introduction with one primary start action.
- The page remains editorial and spacious; it is not a configuration dashboard.

### Active Exam

- Replace the editorial shell with a focused workspace.
- Left rail: compact exam navigator, domain legend, question numbers, flagged and answered states, and submit action.
- Center: readable scenario/question column, answer choices, and previous/next controls.
- Right or contextual edge: timer/progress/status only where shown by the reference and only in Exam Mode.
- Keep all three regions viewport-height with independent scrolling where necessary.
- Answer selection, flags, navigator state, and progress update without page reload or layout shift.

## Exact Visual Direction

Reconstruct the reference's warm, dark editorial system:

- Near-black brown background sampled from the recording
- Slightly warmer/lighter content surfaces sampled from the recording
- Warm coral primary accent sampled from the recording
- Cream primary text and muted stone secondary text sampled from the recording
- Domain colors only where they convey category or exam state
- Serif display typography for important editorial headings
- Sans-serif typography for controls and body copy
- Monospace typography for metadata, timers, code, and domain labels

Layout rules:

- Use the same compact top-navigation composition as the reference for normal pages.
- Use a lesson outline only on lesson pages.
- Use an exam navigator only during an active exam.
- Keep content width readable; do not stretch prose across the full viewport.
- Match the reference's square or lightly rounded controls; do not import the current product's large rounded panels.
- Do not put cards inside cards.
- Do not add decorative gradient orbs or generic illustrations.
- Use whitespace, typography, and alignment to create hierarchy.
- Preserve responsive behavior without overlapping text or horizontal page scrolling.

Before defining CSS tokens, sample representative pixels from the extracted reference frames and record the resulting colors, type scale, spacing scale, radii, border opacity, and shadow treatment in `docs/refoundation/03-reference-design-tokens.md`.

## Motion And Interaction Contract

Recreate the motion visible in the recording. Motion must feel quiet, deliberate, and editorial.

- Page entry: opacity from `0` to `1` with `translateY(8px)` to `0`, 240ms, cubic-bezier(0.22, 1, 0.36, 1).
- Staggered content reveal: 35ms between sibling groups, capped at 210ms total delay.
- Navigation underline/active marker: 180ms ease-out, transform-based.
- Button hover: color/border transition 140ms; no bounce or scale larger than 1.01.
- Card/article hover: border and background transition 180ms; optional `translateY(-2px)` only where present in the reference.
- Accordion and curriculum disclosure: grid-row or measured-height transition 220ms with opacity transition 160ms.
- Modal or setup panel: backdrop 160ms; panel opacity/translate transition 220ms.
- Exam answer selection: immediate border/fill change within 100ms, followed by feedback reveal at 180ms in Practice Mode.
- Navigator state changes: 120ms color transition with no reflow.
- Route transition: old content fades for 100ms, route commits, new content enters for 220ms; preserve scroll deliberately per route.
- Loading: use skeleton lines matching final geometry; never show a blank full-page spinner.
- Respect `prefers-reduced-motion: reduce` by removing transforms and reducing transitions to near-instant state changes.

Do not add parallax, floating objects, glass shimmer, continuous ambient animation, elastic easing, or decorative motion absent from the reference.

## Fidelity Verification

For every completed phase:

1. Extract the corresponding reference frame from the recording.
2. Capture the implementation at the same CSS viewport and device scale.
3. Produce a 50% opacity overlay and a pixel-difference image.
4. Record the implemented interaction at 60 fps for motion comparison.
5. Document mismatches in spacing, alignment, typography, color, state, timing, and responsive behavior.
6. Iterate until no major geometry mismatch remains and the visual difference is limited to product content and branding.

Required review viewports: `390x844`, `768x1024`, `1440x900`, and the desktop reference aspect ratio.

## Data Architecture Guardrails

Canonical hierarchy:

`CertificationTrack -> Course -> Section -> Lesson -> Asset`

Assessment hierarchy:

`CertificationTrack -> Course -> PracticeTest -> Question -> Attempt`

Learning evidence:

`LearningEvent -> track_id + course_id + lesson_id/question_id/test_id/lab_id`

Reference content:

`ReferenceItem -> track_id + domain_id + source_type + source_id + title + excerpt + URL/path`

Journal content:

`JournalItem -> track_id + domain_id + title + body/path + reading_minutes + published_at`

AI retrieval result:

`TutorAnswer -> answer + citations[] + confidence + retrieval_scope`

Rules:

- Apply non-destructive migrations only.
- Do not replace the existing database.
- Do not change existing source IDs during visual refactoring.
- Visible counts must be calculated from canonical, deduplicated records.
- Keep generated study notes explicitly marked as generated.
- Never present generated notes as original transcripts.
- Do not store answer keys in public list endpoints.

---

# Master Prompt

```text
You are working in the existing Snowflake Certification Prep repository at:

/Users/297159/Documents/Snowflake Certification Prep

Refound this application as a focused Data + AI certification-learning product. Do not create a new repository, parallel application, or disposable prototype. Work with the existing FastAPI backend, static JavaScript frontend, SQLite database, Docker configuration, downloaded content archive, and current routes.

Before coding, inspect the repository and analyze the reference recording frame by frame:

/Users/297159/Desktop/Screen Recording 2026-07-31 at 11.26.33 AM.mov

The reference is the binding layout, UI, workflow, and motion target. Reconstruct its page geometry, visual hierarchy, color relationships, component states, responsive composition, transitions, and animation timing as faithfully as possible. Replace only its branding and content with this product's Snowflake/Data + AI material. Do not copy its name, logo, proprietary written content, questions, or certification claims.

The new product must be content-first, fast, restrained, and coherent. Its primary navigation is Curriculum, Practice, Reference, and Journal. AI assistance, search, notes, progress, and the career roadmap are contextual utilities, not competing applications.

Non-negotiable requirements:
- Preserve all owned local videos, questions, transcripts, courses, progress, and database records.
- Keep certifications and source courses separated.
- English-only visible content.
- Remove duplicate visible lessons and questions using canonical records.
- Never display fake counts or readiness.
- Timers appear only in Exam Mode.
- Practice Mode provides immediate answer feedback and source-based explanation.
- Exam Mode defers scoring and explanation until submission.
- AI tutor answers from local course context and includes clickable citations.
- No API key may be required for basic local retrieval and source-grounded responses.
- Avoid dashboard-heavy composition, nested cards, large progress orbs, excessive pills, and marketing copy.
- Use the existing repo patterns unless a small change is necessary to support the target architecture.
- Make narrowly scoped edits and run tests after each phase.
- Rebuild the Docker service after frontend or server changes.
- Verify every changed workflow in the in-app browser on desktop and mobile widths.
- Treat screenshot overlays, pixel-difference images, and interaction recordings as required acceptance evidence.
- Do not approve a phase merely because it is generally attractive or uses a similar palette.

Do not implement multiple phases in one uncontrolled pass. Complete only the requested phase, report files changed and tests run, and leave the live review URL open.
```

---

# Phase 0 Prompt: Audit And Baseline

```text
Execute Phase 0 only. Do not modify application behavior or styling.

1. Inventory the current routes, navigation items, API endpoints, database tables, content counts, page-load requests, and frontend asset sizes.
2. Identify which current features map into Curriculum, Practice, Reference, and Journal.
3. Identify duplicate or conflicting features that should be removed from primary navigation.
4. Record current desktop and mobile screenshots for every primary route.
5. Extract reference frames at every route change, modal, menu, hover, answer selection, and exam navigation state visible in the recording.
6. Create a timestamped motion storyboard documenting entry, exit, hover, reveal, selection, and scroll behavior.
7. Measure reference geometry and record header height, content width, gutters, columns, spacing, typography roles, borders, radii, and representative sampled colors.
8. Measure initial page load, route transition time, API latency, and console errors on localhost.
9. Confirm where course, lesson, practice-test, question, transcript, progress, and AI retrieval data originate.
10. Produce a migration map showing old route -> new route or contextual utility.

Create:
- docs/refoundation/00-baseline.md
- docs/refoundation/01-route-migration-map.md
- docs/refoundation/02-acceptance-matrix.md
- docs/refoundation/baseline-metrics.json
- docs/refoundation/03-reference-design-tokens.md
- docs/refoundation/04-reference-layout-measurements.md
- docs/refoundation/05-motion-storyboard.md
- docs/refoundation/reference-frames/

Acceptance criteria:
- No application source files changed.
- Every current route has an explicit disposition.
- Counts are verified directly against SQLite.
- Known content-quality and performance risks are documented.
- Every visible reference state has a timestamp and extracted frame.
- Layout measurements and motion timings are sufficiently precise to implement without guessing.
```

# Phase 1 Prompt: Product Shell And Design System

```text
Execute Phase 1 only, using the approved Phase 0 documents.

Replace the dashboard-style shell with a faithful implementation of the reference editorial shell.

Implement:
- Working product name in one configuration location.
- Top navigation: Curriculum, Practice, Reference, Journal.
- One global certification selector.
- Compact account/progress access without a permanent analytics dashboard.
- Reference-matched warm dark editorial tokens for color, typography, spacing, borders, and focus states.
- Responsive mobile menu.
- Route aliases from old URLs so bookmarks do not break.
- A simple selected-certification home state that resumes the learner's next lesson or practice activity.

Remove from primary navigation:
- Career Lab
- AI Academy
- Intelligence
- Learn
- Exam Studio
- Labs
- Readiness
- Brain Search
- Memory Deck
- Repair Queue
- Context Tutor

Their useful functionality must remain available through later contextual integration or route aliases. Do not delete backend features in this phase.

Acceptance criteria:
- Exactly four primary navigation destinations.
- Certification selection persists and filters the shell.
- No fake hero claims, vanity counts, or progress orbs.
- Existing lesson and practice routes remain reachable through aliases.
- No horizontal overflow at 390px, 768px, 1440px, and 1920px.
- Keyboard focus is visible.
- Existing APIs continue to pass smoke tests.
- Desktop screenshot overlay has no major mismatch in shell geometry, spacing, or typography hierarchy.
- Navigation, button, route-entry, disclosure, and reduced-motion behaviors match the motion storyboard.
```

# Phase 2 Prompt: Curriculum And Lesson Experience

```text
Execute Phase 2 only.

Build the Curriculum experience around the canonical hierarchy:
Certification -> Course -> Section -> Lesson.

Curriculum page:
- Show only courses belonging to the globally selected certification.
- Preserve original course names and source grouping.
- Show verified lesson count, duration when known, and completion.
- Provide search within the selected certification.
- Keep generated notes distinct from source transcripts.
- Do not render all lessons until a course is opened.

Lesson page:
- Use an immersive video or content stage.
- Use a collapsible course outline grouped by section.
- Provide Overview, Transcript, Notes, and Practice tabs.
- Make transcript timestamps seek the video.
- Show only English transcript text.
- Add a contextual AI Tutor panel that knows the current lesson and cites lesson/transcript sources.
- Link relevant practice questions and references.
- Record completion from real video/content progress.

Integrate the current Data + AI Foundations material as a real course inside Curriculum rather than a separate AI Academy destination.

Acceptance criteria:
- Selecting one certification never shows courses from another.
- Course ordering and sections are stable.
- No `duration unknown` text; omit unavailable duration gracefully.
- No generated study note is labeled transcript.
- Lesson outline scroll and drag scrollbar work.
- Changing lesson does not reload the entire archive.
- Video, transcript seeking, notes, contextual tutor, and related practice work end to end.
```

# Phase 3 Prompt: Practice Library And Exam Engine

```text
Execute Phase 3 only.

Build a source-faithful Practice area.

Practice library:
- Filter by selected certification, course, domain, and source practice test.
- Keep source tests separate as Practice Test 1, Practice Test 2, and so on.
- Display verified question counts after deduplication.
- Do not merge unrelated tests into one pool unless the user explicitly starts a custom drill.

Test setup:
- Explain Practice Mode and Exam Mode before starting.
- Show question count, expected duration, domain coverage, and passing rule.
- Allow a complete source test or a custom domain drill.

Practice Mode:
- No timer.
- Explicit Check Answer button.
- Immediate correct/incorrect state.
- Explanation with local source citation.
- Previous, Next, Bookmark, Notes, and Ask Tutor controls.

Exam Mode:
- Full-screen focused workspace.
- Timer, question navigator, answered/unanswered state, flags, and domain colors.
- Previous and Next controls.
- Submit Exam confirmation.
- No explanations before submission.
- Results include score, domain breakdown, missed questions, and recommended lessons.

Acceptance criteria:
- Tests retain their source boundaries and full question counts.
- Duplicate questions are not repeated within one session.
- Timer never appears in Practice Mode.
- Answers persist during navigation.
- Submit produces a deterministic score.
- Exam state survives a browser refresh.
- UI remains responsive with 100+ questions.
```

# Phase 4 Prompt: Reference And Journal

```text
Execute Phase 4 only.

Create two content-led supporting areas.

Reference:
- Curated official documentation, owned course resources, downloadable files, lab references, and verified external links.
- Group by selected certification and domain.
- Clearly label official, course-owned, generated, and external sources.
- Provide concise descriptions and source metadata.

Journal:
- Long-form study guides, architecture explanations, comparison articles, and exam-preparation notes.
- Use readable editorial article layouts.
- Include domain, reading time, source type, and last-updated date.
- Do not generate placeholder articles merely to fill the page.
- Existing career and role strategy material may appear as a clearly labeled journal collection.

Acceptance criteria:
- Every visible item opens a real source.
- No empty cards or fabricated publication dates.
- Certification filtering applies consistently.
- Article typography remains readable at desktop and mobile widths.
- Reference and Journal use the same shell and design language as Curriculum and Practice.
```

# Phase 5 Prompt: Contextual Local AI Tutor

```text
Execute Phase 5 only.

Move AI assistance into the learning workflow.

Implement one contextual tutor component used by lessons, questions, results, and references.

Required behaviors:
- Lesson context: explain, summarize, compare, quiz, or locate a concept in the transcript.
- Question context: provide a hint, explain choices after checking, cite the relevant lesson, and generate one follow-up question.
- Results context: explain weak domains and propose a source-grounded repair sequence.
- Reference context: answer from selected documents.

Retrieval requirements:
- Default to the selected certification and current page context.
- Search canonical lessons, English transcript chunks, questions, and references.
- Return clickable source citations with course, lesson, and timestamp when available.
- Display retrieval scope and distinguish local retrieval from optional external-model generation.
- Provide a useful local extractive response when no model API key is configured.
- Never display an API-key error as the tutor's answer.
- Do not claim confidence unsupported by retrieval evidence.

Acceptance criteria:
- Tutor is not a primary navigation destination.
- Every factual answer includes at least one valid local citation or says evidence was not found.
- Citations navigate to the correct lesson/question/reference.
- No cross-certification sources leak into scoped answers.
- Basic local assistance works without Anthropic or OpenAI credentials.
```

# Phase 6 Prompt: Progress And Readiness

```text
Execute Phase 6 only.

Implement understated, evidence-based progress.

Progress should answer:
- What have I completed?
- What am I repeatedly missing?
- What should I do next?
- What evidence supports exam readiness?

Use:
- Lesson completion
- Practice-test attempts
- Domain accuracy
- Repeated-miss history
- Lab completion
- Recency
- Full mock-exam results

Do not use:
- Arbitrary percentages
- Decorative streaks as the primary signal
- Fake mastery from content availability
- Generated readiness without supporting evidence

Surface progress through:
- Compact header access
- Curriculum completion
- Practice results
- A focused progress page reached from the account/progress control

Acceptance criteria:
- Every readiness component has an inspectable calculation.
- Empty history produces a clear baseline, not a misleading score.
- Recommended next actions link to real lessons, tests, or labs.
- Data updates immediately after a completed activity.
```

# Phase 7 Prompt: Content Hygiene And Performance

```text
Execute Phase 7 only.

Harden content quality and performance.

Content work:
- Canonicalize duplicate lessons and questions.
- Preserve source provenance and aliases.
- Detect non-English transcripts and exclude them from visible study content.
- Separate generated notes from source transcripts.
- Classify empty tests, micro quizzes, assignments, labs, and full mock exams correctly.
- Reconcile all displayed counts with canonical database queries.

Performance work:
- Paginate or virtualize large lesson and question collections.
- Avoid loading transcripts until requested.
- Avoid fetching all questions for test-library pages.
- Add indexes for common certification/course/test filters.
- Cache stable summary data with explicit invalidation after reindexing.
- Prevent repeated shell API requests during route changes.
- Keep route modules lazy-loaded.

Performance targets on localhost after warm startup:
- Initial shell usable within 1.5 seconds.
- Normal route transition under 500 milliseconds.
- Curriculum list API under 300 milliseconds.
- Practice-test list API under 300 milliseconds.
- No route renders thousands of DOM nodes.
- No unbounded API list endpoint is used by the frontend.

Acceptance criteria:
- Document before-and-after measurements.
- Counts remain correct after deduplication.
- Search and AI citations resolve canonical IDs.
- No hanging routes or console errors during a ten-minute navigation test.
```

# Phase 8 Prompt: Final QA And Controlled Cutover

```text
Execute Phase 8 only.

Perform final product QA and cut over from the old information architecture.

Test the complete learner journey for every available certification:
1. Select certification.
2. Open curriculum.
3. Select course and lesson.
4. Play/seek video or read lesson.
5. Use transcript and notes.
6. Ask contextual tutor and open a citation.
7. Start Practice Mode and check an answer.
8. Start Exam Mode, navigate, flag, submit, and review results.
9. Open recommended repair lesson.
10. Inspect Reference, Journal, and progress.

QA viewports:
- 390x844
- 768x1024
- 1440x900
- 1920x1080

Verify:
- No horizontal overflow.
- No overlapping or clipped text.
- No invisible controls.
- Keyboard navigation and visible focus.
- Correct active navigation state.
- No stale branding.
- English-only visible study content.
- No broken media or citations.
- No console errors.
- No route hangs.
- Docker restarts cleanly with the persistent database.

Create:
- docs/refoundation/final-qa-report.md
- docs/refoundation/route-and-feature-matrix.md
- docs/refoundation/known-limitations.md

Remove old primary navigation and obsolete route-specific marketing copy only after all aliases and target workflows pass.

Acceptance criteria:
- All automated checks pass.
- Browser workflow passes at all four viewports.
- Existing user data remains intact.
- The live review URL opens the new Curriculum experience.
```

---

## Phase Review Template

Use this response format after each implementation phase:

```text
Phase:
Status:

What changed:
-

Files changed:
-

Data migrations:
-

Verification:
- Automated checks:
- API checks:
- Desktop browser:
- Mobile browser:

Known limitations:
-

Live review URL:
```

## Definition Of Done

The refoundation is complete when:

- The application presents one coherent certification-learning identity.
- The primary navigation has exactly four destinations.
- All six Snowflake certification tracks remain separated and usable.
- Data + AI Foundations appears as real curriculum content, not a separate branded mini-app.
- Lessons, practice, references, journal content, tutor citations, and progress share one data model and design system.
- Practice and Exam modes are behaviorally distinct.
- AI help is contextual and source-grounded.
- Visible counts are canonical and deduplicated.
- The application remains fast with the full local archive.
- The browser experience is polished and usable on desktop and mobile.
