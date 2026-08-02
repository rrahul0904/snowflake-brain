# Exact Replica: Multi-Agent Implementation Plan

Last updated: 2026-07-31

## Objective

Rebuild the existing Snowflake Certification Prep application as a pixel-faithful replica of the layout, interaction model, visual system, responsive behavior, and animations shown in:

`/Users/297159/Desktop/Screen Recording 2026-07-31 at 11.26.33 AM.mov`

The replica must use this application's own product name, Snowflake/Data + AI course material, local questions, videos, transcripts, and progress data. Do not copy the reference product's trademark, logo, written articles, proprietary questions, or certification claims.

This is not a loose inspiration exercise. The recording is the binding visual and interaction reference.

## Replica Scope

Match exactly:

- Page composition and content rails
- Header placement, dimensions, navigation, and active states
- Typography roles, scale relationships, line lengths, and spacing
- Background, surface, border, text, and accent color relationships
- Component dimensions, density, and alignment
- Curriculum, reference, journal, practice setup, and exam workflows
- Hover, focus, pressed, selected, disabled, answered, flagged, and submitted states
- Page entry, disclosure, modal, selection, and route transition animations
- Desktop behavior shown in the recording
- Equivalent responsive compositions for tablet and mobile

Do not preserve from the current UI:

- Permanent left dashboard sidebar
- Large rounded dashboard panels
- Metric strips and vanity counters
- Unrelated top-level tools
- Glassmorphism and decorative gradients
- Excessive pills
- Nested cards
- Invented names such as Intelligence, Evidence Gate, Repair Queue, or Command Center

## Target Information Architecture

Primary navigation:

1. Curriculum
2. Practice
3. Reference
4. Journal

Contextual functions:

- AI Tutor
- Search
- Notes
- Bookmarks
- Progress
- Certification selector

Primary workflow:

`Select certification -> Open curriculum -> Study lesson -> Take practice test -> Review evidence -> Continue study`

## Technical Constraints

- Repository: `/Users/297159/Documents/Snowflake Certification Prep`
- Backend: existing FastAPI application
- Frontend: existing static JavaScript application
- Database: existing SQLite database
- Runtime: existing Docker Compose service on `http://127.0.0.1:8010/`
- Preserve all source data and existing IDs.
- Use non-destructive migrations only.
- Keep source courses and source practice tests separate.
- All visible learning content must be English.
- Basic local retrieval must work without a hosted model API key.
- Route loads must not fetch the entire archive.

## Agent Topology

Use one orchestrator and seven specialist agents. Agents work in separate branches or worktrees and only modify their assigned files. The orchestrator owns integration and resolves shared-file changes.

### Agent 0: Orchestrator And Integrator

Owns:

- Integration branch
- Task sequencing
- Shared contracts
- Merge order
- Docker rebuilds
- Final browser review

May edit:

- `frontend/index.html`
- `frontend/app.js`
- `frontend/router.js`
- `app/main.py`
- Integration documentation

Must not redesign specialist work during integration. Return rejected work to the responsible agent with screenshot or test evidence.

### Agent 1: Reference Reconstruction Analyst

Owns documentation and reference evidence only.

Outputs:

- `docs/replica/01-reference-screen-inventory.md`
- `docs/replica/02-layout-measurements.md`
- `docs/replica/03-visual-tokens.md`
- `docs/replica/04-motion-storyboard.md`
- `docs/replica/05-responsive-rules.md`
- `docs/replica/reference-frames/`

Responsibilities:

- Extract a frame at every page, state, hover, menu, and transition.
- Record exact timestamps.
- Measure header height, rails, gutters, columns, component bounds, and spacing.
- Sample colors from multiple clean pixels.
- Identify typography roles and likely font categories.
- Measure animation start/end frames and derive duration/easing characteristics.
- Document scroll behavior and fixed/sticky regions.

No production source changes.

### Agent 2: Design System And Global Shell

Exclusive ownership:

- `frontend/styles/replica-tokens.css`
- `frontend/styles/replica-shell.css`
- `frontend/styles/replica-motion.css`
- `frontend/components/replica-header.js`
- `frontend/components/replica-footer.js`

Responsibilities:

- Implement sampled tokens from Agent 1.
- Rebuild the exact compact header and footer.
- Implement global page rails and responsive breakpoints.
- Implement shared focus, hover, active, loading, and reduced-motion behavior.
- Provide reusable primitives without creating a generic dashboard card system.

### Agent 3: Curriculum, Reference, And Journal

Exclusive ownership:

- `frontend/views/replica-curriculum.js`
- `frontend/views/replica-reference.js`
- `frontend/views/replica-journal.js`
- `frontend/views/replica-article.js`
- `frontend/styles/replica-editorial.css`

Responsibilities:

- Recreate the text-first curriculum layout.
- Recreate the reference directory layout.
- Recreate the article grid and article reading layout.
- Implement lesson entry points using existing course data.
- Keep certification filtering global and deterministic.
- Match all reference disclosure and hover behavior.

### Agent 4: Practice Setup And Exam Workspace

Exclusive ownership:

- `frontend/views/replica-practice.js`
- `frontend/views/replica-exam.js`
- `frontend/components/exam-navigator.js`
- `frontend/styles/replica-practice.css`
- `frontend/styles/replica-exam.css`

Responsibilities:

- Recreate the centered mock-exam setup page.
- Build the immersive active-exam layout from the recording.
- Implement answer states, flags, navigator, domains, progress, timer, and submission.
- Keep Practice Mode untimed with immediate checking.
- Keep Exam Mode timed with deferred scoring.
- Preserve state across navigation and browser refresh.
- Support 100+ questions without rendering or interaction lag.

### Agent 5: Backend Data Contracts And Performance

Exclusive ownership:

- New or revised endpoints under `app/routers/`
- `app/serializers.py`
- Database query helpers
- Data migration scripts
- Backend tests

Responsibilities:

- Provide paginated curriculum, lesson, test, question, reference, and journal contracts.
- Preserve source boundaries.
- Implement canonical deduplication without deleting owned source files.
- Return verified counts.
- Keep answer keys out of pre-submission exam payloads.
- Add attempt persistence and deterministic scoring.
- Eliminate route-wide archive scans.

Coordinate endpoint contracts with Agents 3, 4, and 6 before implementation.

### Agent 6: Contextual Local AI Tutor

Exclusive ownership:

- `frontend/components/contextual-tutor.js`
- `frontend/styles/replica-tutor.css`
- `app/routers/ai.py`
- Retrieval-specific tests

Responsibilities:

- Embed the tutor in lessons, checked practice questions, results, and reference pages.
- Retrieve only from the selected certification/course/lesson/question context.
- Return concise English answers with clickable local citations.
- Provide useful extractive synthesis without an external API key.
- Never display an API-key error as the answer.
- Never reveal an answer before submission in Exam Mode.

### Agent 7: Visual, Motion, Accessibility, And Performance QA

Owns tests and reports, not feature implementation.

Outputs:

- `tests/visual/`
- `tests/e2e/`
- `docs/replica/qa/visual-diffs/`
- `docs/replica/qa/motion-comparisons/`
- `docs/replica/qa/final-report.md`

Responsibilities:

- Capture implementation screenshots at reference dimensions.
- Generate 50% overlays and pixel-difference images.
- Record implementation interactions at 60 fps.
- Compare duration, easing character, state sequence, and layout stability.
- Test keyboard, focus, contrast, reduced motion, and screen-width behavior.
- Measure route transition time, API latency, DOM size, and memory use.
- Reject work with major geometry, state, workflow, or motion mismatches.

## Shared-File Rule

Specialist agents must not edit:

- `frontend/index.html`
- `frontend/app.js`
- `frontend/router.js`
- `app/main.py`
- Existing `frontend/styles.css`

Instead, they create the scoped files listed above. Agent 0 performs all imports and route registration in one controlled integration pass. This prevents agents from overwriting each other.

## Execution Waves

### Wave 0: Freeze And Baseline

Agents: 0 and 7

Tasks:

1. Record current git state and preserve unrelated user changes.
2. Capture every current route at 390, 768, 1440, and reference desktop width.
3. Record current API timing, console errors, content counts, and route timing.
4. Create a route migration matrix.
5. Establish visual test commands and artifact folders.

Gate:

- No production changes.
- Baseline is reproducible.

### Wave 1: Reverse Engineer The Recording

Agent: 1

Tasks:

1. Use `ffprobe` to retain the recording frame rate and dimensions.
2. Extract frames around every visible interaction and scene change.
3. Measure all page geometry from clean browser-content bounds, excluding browser chrome.
4. Build a component/state inventory.
5. Build a frame-based motion storyboard.
6. Sample visual tokens and document confidence/variance.

Gate:

- Every target screen has a reference frame and measurement sheet.
- Every visible animation has an onset frame, end frame, duration, and state description.
- Agents are not allowed to guess layout dimensions that can be measured.

### Wave 2: Contracts And Skeleton

Agents: 2 and 5 in parallel

Agent 2 builds the shell and CSS primitives.

Agent 5 defines and implements paginated backend contracts.

Gate:

- Header/footer overlay matches reference geometry.
- APIs return selected-certification data only.
- No full archive is loaded on route entry.

### Wave 3: Editorial Pages And Exam Experience

Agents: 3 and 4 in parallel

Agent 3 implements Curriculum, Reference, Journal, and Article.

Agent 4 implements Practice Setup and Active Exam.

Gate:

- Static visual overlays have no major geometry mismatch.
- Exam supports 100+ questions.
- Timer is absent in Practice Mode.
- Source tests remain separate.

### Wave 4: Contextual Intelligence

Agent: 6

Tasks:

1. Integrate tutor entry points without changing page composition.
2. Add source-grounded local answers and citations.
3. Add hints and explanations only at valid workflow states.
4. Test no-key behavior.

Gate:

- Tutor is contextual, not a top-level chat page.
- Every factual answer includes evidence.

### Wave 5: Integration

Agent: 0

Merge order:

1. Agent 5 backend contracts
2. Agent 2 tokens, motion, and shell
3. Agent 3 editorial pages
4. Agent 4 practice and exam
5. Agent 6 tutor
6. Agent 7 test harness updates

Tasks:

- Register imports and routes.
- Add legacy route aliases.
- Rebuild Docker.
- Run smoke, API, data-boundary, and browser tests.
- Open the live app at `http://127.0.0.1:8010/`.

Gate:

- No duplicate navigation systems.
- No legacy dashboard shell is visible on replica routes.
- Existing data and progress remain intact.

### Wave 6: Pixel And Motion Convergence

Agents: 1, 2, 3, 4, and 7

Process for each target screen:

1. Agent 7 captures the implementation at the reference viewport.
2. Agent 7 generates overlay and difference images.
3. Agent 1 classifies mismatches against measurements.
4. Responsible implementation agent fixes only its owned files.
5. Repeat until the gate passes.

Gate:

- No major differences in header, content rail, columns, control placement, or typography hierarchy.
- No unexplained animation timing or state-sequence mismatch.
- Differences are limited to Snowflake/Data + AI branding and content.

### Wave 7: Responsive And Production QA

Agent: 7, fixes returned to owning agent

Test widths:

- `390x844`
- `768x1024`
- `1440x900`
- Exact desktop reference aspect ratio

Required journeys:

1. Select certification and open curriculum.
2. Open a course, section, and lesson.
3. Start Practice Mode, answer, check, read citation, and continue.
4. Start Exam Mode, navigate, flag, refresh, resume, submit, and review.
5. Open Reference and follow a real source.
6. Open Journal and read an article.
7. Ask the contextual tutor from a lesson and checked question.

Gate:

- No horizontal overflow.
- No text overlap or clipped controls.
- Keyboard workflow passes.
- Reduced motion passes.
- Route transitions feel immediate.
- No full-page blank loading state.

## Master Orchestrator Prompt

```text
You are the implementation orchestrator for the existing repository:

/Users/297159/Documents/Snowflake Certification Prep

Your task is to coordinate a pixel-faithful reconstruction of the website shown in:

/Users/297159/Desktop/Screen Recording 2026-07-31 at 11.26.33 AM.mov

Use the existing FastAPI backend, static JavaScript frontend, SQLite database, Docker service, and owned course archive. Do not create a replacement repository or disconnected prototype.

The reference recording is binding for layout, UI hierarchy, visual relationships, responsive behavior, workflow, component states, and animations. Reproduce these as exactly as measurable. Use this product's own name and Snowflake/Data + AI content. Do not copy the reference trademark, logo, proprietary writing, questions, or certification claims.

Read and enforce:

docs/22_MULTI_AGENT_EXACT_REPLICA_PLAN.md

Create separate specialist worktrees or branches and assign the exact ownership boundaries in that plan. Do not allow parallel agents to edit shared integration files or the existing global stylesheet. Require each agent to return changed files, tests, screenshots, and unresolved mismatches.

Do not merge a phase based on subjective approval. Require reference-frame overlays, pixel-difference images, interaction recordings, functional tests, and performance measurements. Integrate in the documented order, rebuild Docker, and verify the complete workflow in the browser.
```

## Agent 1 Prompt: Reference Reconstruction

```text
Analyze the reference recording frame by frame. Do not change production source code.

Extract every unique page and interaction state. Measure browser-content geometry, spacing, type hierarchy, component bounds, sampled colors, borders, radii, fixed regions, scroll regions, and responsive clues. For each visible animation, record start frame, end frame, duration, affected properties, and state sequence. Do not invent motion timings when they can be measured from the 120 fps source.

Produce all Agent 1 outputs listed in docs/22_MULTI_AGENT_EXACT_REPLICA_PLAN.md. Make the measurements sufficiently precise that implementation agents do not need to guess.
```

## Agent 2 Prompt: Shell And Design System

```text
Implement only the replica tokens, global shell, header, footer, and shared motion primitives. Use Agent 1's measured values. Do not edit shared integration files or frontend/styles.css. Do not add a sidebar, dashboard cards, metric strips, glass effects, or visual elements absent from the reference.

Return desktop/mobile screenshots, overlay evidence, keyboard focus evidence, reduced-motion evidence, changed files, and tests.
```

## Agent 3 Prompt: Editorial Learning Pages

```text
Implement Curriculum, Reference, Journal, and Article using the exact reference compositions and existing application data. Work only in your assigned files. Preserve certification and course boundaries. Use text hierarchy and dividers rather than dashboard cards. Implement measured hover, disclosure, route-entry, and loading behavior.

Return route screenshots at all required viewports, visual differences, changed files, and tests.
```

## Agent 4 Prompt: Practice And Exam

```text
Implement the exact practice setup and immersive exam workflow shown in the reference. Work only in your assigned files. Practice Mode has no timer and provides explicit Check Answer feedback. Exam Mode has timer, navigator, flags, state persistence, deferred scoring, submission, and results. Maintain responsive performance for 100+ questions.

Match the measured exam columns, navigator density, answer states, controls, colors, and animations. Return interaction recording, refresh-resume evidence, visual differences, changed files, and tests.
```

## Agent 5 Prompt: Backend And Data

```text
Implement paginated, source-faithful APIs required by the replica UI. Preserve IDs and source boundaries. Use non-destructive migrations. Deduplicate canonical display records without deleting source files. Return verified counts. Do not expose answer keys before exam submission. Remove route-time full-archive scans and add deterministic attempt persistence/scoring.

Return API contracts, migration notes, query timings, changed files, and tests.
```

## Agent 6 Prompt: Contextual Tutor

```text
Implement one contextual tutor used inside lessons, checked practice questions, results, and references. Do not create a top-level AI chat destination. Basic answers must use local retrieval and work without an external API key. Include clickable source citations and retrieval scope. Never reveal exam answers before submission.

Return no-key test evidence, citation tests, changed files, and integration notes.
```

## Agent 7 Prompt: Independent QA Gate

```text
Act as an independent replica QA gatekeeper. Do not approve work because it looks generally polished. Compare each implementation screen with the measured reference frame at the same viewport. Generate overlays and pixel differences. Compare interaction recordings for state order, duration, easing character, and layout shift.

Also test keyboard behavior, focus, contrast, reduced motion, responsive widths, 100+ question performance, route timing, API timing, console errors, and complete learner journeys. Report findings by severity and route. Reject any phase with major geometry, workflow, state, or motion mismatches.
```

## Definition Of Done

The replica is complete only when:

- The four primary routes use one coherent reference-matched shell.
- Curriculum, Reference, Journal, Practice Setup, and Active Exam match the recorded layout and behavior.
- Visual overlays show no major geometry mismatch.
- Motion comparison shows the same state sequence and materially equivalent timing/easing.
- Only branding and owned content differ from the reference.
- Certification and source boundaries are preserved.
- Practice and Exam Mode behavior is correct.
- Local contextual tutor works without an API key and cites sources.
- Verified counts replace inflated or duplicate counts.
- All visible learning content is English.
- Required desktop, tablet, and mobile journeys pass.
- Docker is running and the final browser URL is available for review.

