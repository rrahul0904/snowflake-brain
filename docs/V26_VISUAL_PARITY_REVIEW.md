# V26 Visual Parity Review

## Status

**Recommendation: READY FOR USER VISUAL REVIEW**

This document compares the V26 learner experience against the user-supplied screen recording. It is deliberately not a claim of pixel-perfect identity. The implementation reproduces the reference site's visual hierarchy, spacing philosophy, interaction model, motion language, and editorial character using Snowflake-specific content and truthful product data.

PR #6 must remain **draft** until the user reviews the rendered screens. Do not merge solely because automated tests and browser capture pass.

## Acceptance reference

Primary reference: user-supplied screen recording of `claudecertificationguide.com`.

The reference is used for:

- hierarchy and composition
- dark/light palette direction
- serif/sans typography contrast
- spacing and rhythm
- home globe behavior and visual language
- curriculum/sidebar interaction pattern
- practice and mock hierarchy
- dedicated exam-player layout
- feedback affordance

The implementation intentionally does **not** copy third-party branding, proprietary text, articles, questions, source code, learner counts, or fabricated activity.

## Browser QA evidence

Automated browser capture runs the real FastAPI + SPA runtime in Chromium and captures 24 screens.

Dark:

1. Home
2. Home with globe manually rotated
3. Certification chooser
4. Curriculum — collapsed syllabus
5. Curriculum — first domain expanded
6. Lesson
7. Practice
8. Reference
9. Journal
10. Mock landing
11. Mock start
12. Interrupted sitting
13. Exam player
14. Exam player — answered + flagged
15. Feedback drawer

Light:

16. Home
17. Curriculum
18. Mock
19. Reference
20. Feedback drawer

Mobile 390px:

21. Home
22. Curriculum
23. Exam player
24. Exam navigator drawer

The capture workflow also fails if the SPA reports a route error, browser `pageerror`, or console error during the pass.

## Screen-by-screen comparison

| Screen | Reference | Current V26 | Change made | Remaining difference |
|---|---|---|---|---|
| Home — dark | Very dark warm brown/near-black background, cream serif hero, salmon/copper highlight, restrained home nav, centered CTAs, pointillist globe | Uses `#181111` family, warm cream type, muted salmon accent, home nav reduced to Reference/Journal plus certification controls, centered editorial hero | Retuned palette from earlier brown/orange approximation; narrowed lede; adjusted vertical rhythm; reduced home navigation; removed fake social proof | Copy is Snowflake-original and therefore differs. Reference displays third-party learner proof that V26 intentionally does not fabricate. |
| Home globe | Dotted/pointillist world, continuously rotating geography, city/activity annotations, subtle grid | Real geographic polygons are loaded locally, converted into pointillist land dots, projected orthographically, rotated together with graticule and activity layer | Replaced static decorative SVG continents and hard-coded city list with real geography + one projection state | In fallback mode, no city labels appear because there is no verified live activity. This is intentional truthfulness, not a missing visual. |
| Globe rotation | Geography visibly changes as Earth rotates | Land dots, coastlines, grid and activity points all use the same changing projection; drag rotates longitude/latitude; auto rotation resumes | Full rewrite of globe renderer | Reference motion speed may differ slightly; V26 uses a calm ~56-second full rotation. |
| Certification chooser | Four editorial certification columns with one active path and secondary future paths | Four featured SnowPro paths, current path emphasized subtly; remaining official catalog collapsed under `More SnowPro paths` | Reduced from a crowded all-catalog layout to the reference-like four-column hierarchy | Snowflake's real path names/statuses differ from the third-party certification set. |
| Curriculum — collapsed | Persistent left study nav; compact domain syllabus; domains open on demand | Five collapsed editorial rows with number, title, description, weight, completion, plus control | Removed domain cards and changed default from all-expanded to collapsed | Text wraps differently because Snowflake domain names are much longer. |
| Curriculum — expanded | One domain reveals module/task rows beneath it | First/selected domain expands inline; remaining domains stay collapsed | Added true expand/collapse state and browser QA for both states | Snowflake task count/content differs by blueprint. |
| Lesson | Technical handbook feel, typography and separators carry hierarchy | Narrow reading column; serif title; flat text sections; Key Concept/Traps/Worked Example use restrained accent rules; interactive scenario remains bordered | Removed most filled cards and component chrome | Some Snowflake lessons are longer than reference content, so page length varies. |
| Practice | Clear practice choices without dashboard clutter | Diagnostic, targeted drill, quick mock and full mock shown in a restrained 2×2 editorial grid | Removed dashboard metrics and heavier card treatments | Four Snowflake modes are original product behavior, not copied reference content. |
| Reference | Grouped two-column textual resource rows | Official Documentation, Courses & Learning, Developer Resources shown as flat rows with hairline dividers | Replaced marketing-card feel with editorial rows | Resource names and group contents are Snowflake-specific. |
| Journal | `SYSTEM REPOSITORY` / editorial journal, three-column article grid | `SYSTEM REPOSITORY` / `SnowPro Journal`, three-column editorial cards with restrained metadata | Reworked heading and article metadata; flattened card surfaces | V26 currently has more article entries visible on a long page; content remains Snowflake-original. |
| Mock landing | Extremely simple centered title, four facts, one primary start action, diagnostic alternative | Same information hierarchy: title, explanation, 5 / 100 / 120 / 750 facts, Start Mock Exam, diagnostic alternative | Removed dashboard treatment and secondary clutter | 100/120 are Snowflake Brain simulation settings, not copied from the reference site's exam. |
| Mock start | Left-aligned mock title; interrupted block when present; Quick/Full choice; Exam Format; Domain Weights; Before You Start; one wide start CTA | Same hierarchy in a narrower ~760px editorial column | Split page title from `Choose Your Sitting`; reduced card height; made info/weights vertical; flattened instructions | Exact vertical spacing still differs slightly because Snowflake domain labels are longer. |
| Interrupted sitting | Resume and discard path before starting another sitting | Active session shows remaining time plus Discard Sitting and Resume Exam | Added real backend discard and removed obsolete duplicate bridge control | No material interaction gap observed. |
| Exam player | Dedicated chrome-free exam mode, narrow navigator, timer/saved state, domain filters, question map, large watermark, flag, answer rows, sticky previous/next progress | Dedicated exam shell with same core layout and persisted backend behavior | Narrowed navigator; quieter states; enlarged watermark; flattened answers/context; added domain filters and bottom progress dots | Question stems/options can be longer than reference. Minor typography/proportion differences remain acceptable for review. |
| Answered + flagged exam | Answer selection and flag are visually persistent | Selected answer gets soft accent/letter fill; flag state persists; navigator marks answered/flagged | Browser QA captures this exact state after backend save | No material behavior gap observed. |
| Feedback | Floating feedback affordance opening a right-side feedback experience | Circular FAB opens a full-height right drawer with backdrop, Title, Category, Description, Email, submit | Implemented per user's explicit V26 requirement; added focus transfer/trap, Escape close and focus return | The extracted recording frame looked more like a floating panel than a full-height drawer. V26 intentionally follows the user's later explicit full-height-drawer instruction. |
| Light mode | Near-white/off-white page, dark type, dark rust accent, same hierarchy | `#faf9f7` background, dark brown type, `#8b4633` accent; all major routes captured in Chromium | Replaced earlier beige-heavy light palette and reviewed home/curriculum/mock/reference/feedback | Minor exact color/contrast differences remain because pixels were sampled from a screen recording, not original design tokens. |
| Mobile home | Same editorial hierarchy adapted to narrow viewport | 390px capture: compact header, large serif hero, stacked CTAs, responsive real globe | Added 390px layout and touch-drag globe support | Reference mobile behavior was not fully demonstrated in the recording, so mobile follows the same design system rather than claiming exact parity. |
| Mobile exam | Navigator collapses; question remains readable; exam mode remains dedicated | 390px capture with mobile question layout plus separate navigator drawer capture | Responsive exam navigator and no-horizontal-overflow rules | Mobile reference coverage is limited. |

## Globe implementation architecture

### Geography

- Local asset: `frontend/assets/world-major-land.geojson`
- Source metadata identifies Natural Earth 1:110m public-domain derived geometry.
- The browser does not draw invented continent shapes.
- A point-in-polygon pass derives a pointillist land field from the real polygons.
- Coastlines are drawn faintly from the same polygon rings.

### Projection and animation

Every visual geographic layer shares one orthographic projection state:

```text
real geographic geometry
        |
        v
orthographic projection <---- longitude + latitude rotation
        |
        +---- pointillist land
        +---- coastlines
        +---- graticule
        +---- privacy-safe activity markers
```

Behavior:

- roughly one full automatic rotation every 56 seconds
- pointer/touch drag in horizontal and limited vertical directions
- short pause after manual drag, then auto rotation resumes
- rear-hemisphere activity disappears naturally
- projection responds to `ResizeObserver`
- device pixel ratio capped for performance
- animation does not advance while the page is hidden
- `prefers-reduced-motion` disables automatic rotation

## Real candidate activity and privacy

Endpoint:

`GET /api/activity/globe`

The current application **does not manufacture learner locations**.

Display rules:

- rolling window: 30 minutes
- public minimum group count: 3
- data model accepts only already-coarsened aggregate buckets
- sub-threshold buckets are never returned
- the app does not accept client geolocation pings for this feature
- the app does not derive or retain precise user location/IP solely for this globe

Two supported states:

### Live state

When a trusted deployment telemetry process writes privacy-reviewed aggregate geographic buckets, the UI may show:

`N learners active in the last 30 minutes`

and render those aggregate points.

### Truthful fallback state — current default

When no qualifying activity exists:

`Snowflake certification study, worldwide`

The genuine rotating Earth remains visible, but **no fake candidate dots/cities are inserted**.

## Intentional non-parity

The following reference details are deliberately not copied:

1. Third-party brand identity.
2. Third-party certification names/codes.
3. Third-party question/article text.
4. Claimed `150,000+` learner social proof.
5. Pre-seeded city markers presented as live users.
6. Reference exam counts/timing where they conflict with Snowflake Brain configuration.
7. OS-level VoiceOver UI visible in the recording.

## CSS architecture

The active application now loads one canonical style system under `frontend/styles/`:

- `tokens.css`
- `utilities.css`
- `shell.css`
- `home.css`
- `study.css`
- `practice.css`
- `mock.css`
- `content.css`
- `exam.css`
- `responsive.css`
- `accessibility.css`

The active HTML no longer loads the old stacked V26 style generations. Superseded `v26-*.css` layers were removed as their rules were migrated.

Some much older legacy CSS/JS files remain in the repository for historical compatibility/reference, but the V26 shell does not load them. Smoke tests explicitly guard the active runtime from re-enabling legacy styles.

## Functional regression coverage

The V26 smoke verifies:

- architecture remains certification-native
- COF-C03 has 5 domains and 19 tasks
- domain weights are 31 / 20 / 18 / 21 / 10
- Quick Mock = 30 questions / 45 minutes
- Full Mock = 100 questions / 120 minutes
- practice threshold = 750
- correct answer/explanation are not leaked in-progress
- answer autosave
- flag persistence
- refresh/resume persistence
- submit and post-submit review reveal
- discard interrupted sitting
- feedback backend persistence
- real geography asset is served
- no hard-coded fake globe location list exists
- empty activity returns truthful fallback
- privacy threshold hides a 2-person test bucket and permits a 3-person aggregate bucket
- pointillist land is derived from real geometry
- canonical CSS is active and superseded V26 CSS is inactive

## Remaining visual review items for the user

These are subjective rather than correctness blockers:

- whether the Snowflake-original hero copy should be shorter/longer
- whether the globe should rotate slightly faster/slower
- whether the Journal heading should be slightly smaller
- whether Mock Start should be a little narrower
- whether the exam question type scale should be a little tighter
- whether the user prefers the explicit full-height feedback drawer or wants the smaller floating-panel geometry from the recording

None of these require rebuilding the architecture again.

## Final recommendation

**READY FOR USER VISUAL REVIEW**

Do **not** merge PR #6 yet. Present the current rendered screenshots to the user, collect any final visual adjustments, rerun both smoke and Chromium capture, and only then move the PR out of draft.

---

## 2026-09-01 — Reverse-engineering completeness acceptance

This dated section does not replace the historical review above. It records the later completeness wave performed after the V26 product acquired production identity, entitlement, learning-intelligence, credential, and release-governance features.

### New public acceptance scope

The V26 Visual Parity workflow now also executes:

`scripts/capture_reverse_engineering_public_pages.py`

This clean-room browser matrix captures the following guest/public routes:

- Home
- Certifications
- SnowPro Core exam guide
- SnowPro Advanced: Data Engineer exam guide
- SnowPro Advanced: Architect exam guide
- Content Integrity
- Membership
- About
- Terms
- Privacy

For each route it captures:

- 1440×1000
- 1024×900
- 768×900
- 390×844

in both:

- light theme
- dark theme

This adds **80 public screenshots** to the existing authenticated V26 capture and fails on browser console/page errors or horizontal overflow.

### Public/private content assertion

The same browser pass deep-links anonymously into `#/curriculum?track_id=snowpro-core` and requires the authentication gate. It fails if the study navigation or curriculum list renders for the guest. Public certification facts therefore do not relax the protected study-content boundary.

### Completeness-specific visual contracts

The browser matrix additionally requires:

- certification fact cards to render for the focused certification catalog;
- visible separation between official certification existence and Snowflake Brain study-guide availability;
- source verification on exam-guide pages;
- a visible link to the official Snowflake certification page;
- active Content Integrity copy including independence/no-dump language;
- no horizontal overflow at the four required viewports;
- light/dark theme application on every public route.

The existing authenticated capture continues to cover curriculum, expanded domain, lesson, progress, drill setup, build exercises, diagnostic setup, Quick Reference, Glossary, Mock, Reference, Journal, interrupted sitting, exam player, answered/flagged state, feedback, and mobile exam/navigation behavior.

### Product differences explicitly accepted

The 2026-09-01 coverage matrix records these intentional differences rather than treating them as parity defects:

1. Signed-in home retains a Snowflake-native prep command center because Due Today, mistakes, readiness, and exam pacing are actionable learner state.
2. Real projected geography and privacy-thresholded aggregate activity replace fabricated learner/city social proof.
3. Deterministic lab hints, validation, expected output, and solutions replace an open-ended AI Build Coach.
4. Targeted drill and persisted mock remediation replace a duplicated result-page retry mode.
5. Testimonials and pass-rate social proof remain absent until real, consented candidate evidence exists.
6. Coming-soon certification waitlists remain future marketing-consent scope; verified exam facts are public now.

### Machine-verifiable completeness evidence

Canonical evidence is now split between:

- `docs/REVERSE_ENGINEERING_COVERAGE_MATRIX.md`
- `artifacts/reverse-engineering-coverage.json`
- `scripts/test_reverse_engineering_completeness.py`
- `.github/workflows/reverse-engineering-completeness.yml`

The CI gate rejects unexplained P0/P1 `MISSING_TO_IMPLEMENT`, `PARTIAL`, `TODO`, `PLACEHOLDER`, `UNKNOWN`, or `MAYBE` states.

This is a **reverse-engineering completeness** designation only. It does not override production deployment, private-bank SME approval, Stripe account readiness, hosted security evidence, or independent GitHub approval requirements.
