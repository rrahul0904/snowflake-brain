# Authenticated Page Recording Contract — 2026-08-14

Reference: user-supplied screen recording `Screen Recording 2026-08-14 at 12.53.15 PM.mov`.

This contract applies to layout, hierarchy, interaction patterns, spacing rhythm, navigation behavior, and visual density. It does **not** copy Claude branding, proprietary content, or Claude-specific exam facts. Snowflake-specific content, COF-C03 blueprint values, membership entitlements, and security rules remain authoritative.

## Global authenticated shell

- Light theme is the default when no preference has been saved; dark theme remains available.
- Header order: Snowflake Certified brand → Curriculum / Practice / Reference / Journal → compact certification selector → account control → mock CTA → theme toggle.
- Study routes use a persistent desktop sidebar with these groups:
  - Study Tools: Progress Dashboard, Drill Mode
  - Curriculum: five weighted domains
  - Practice: Build Exercises, Diagnostic Test
  - Look Up: Quick Reference, Glossary
- The active domain expands its task links inline in the sidebar.
- Main study content stays narrow and centered in the remaining viewport rather than stretching edge-to-edge.
- Study-page headings are editorial but moderate in scale; the oversized home-display treatment is not reused.
- Footer is compact and low-noise.
- Feedback remains available from the floating control.
- Authentication remains fail-closed. The recording contract never overrides candidate-login requirements.

## Page-by-page mapping

| Reference page / state | Snowflake route | Required structure |
| --- | --- | --- |
| Exam Domains | `#/curriculum` | Intro + five 2-column weighted domain cards; final odd card occupies the left column. |
| Domain Detail | `#/domain` | Back chevron; colored domain eyebrow + weight; title/lede; Task Statements; compact task rows; active sidebar domain expanded. |
| Task Lesson | `#/skill` | Same study shell and expanded active domain; compact task heading; learning sections, decision rules, traps, scenario, build exercise, sources. |
| Progress | `#/progress` | Your Progress intro; centered readiness panel `/100`; Lessons/Practice/Drill contribution rows; empty-state box when applicable; five-domain progress list. |
| Drill Mode | `#/practice?mode=drill` | Dedicated pre-start screen; four summary tiles; domain filter chips; one Start Session CTA. It must not auto-launch on route entry. |
| Build Exercises | `#/exercises` | Intro + five domain-grouped exercise blocks; task exercise links in two columns where space allows. |
| Diagnostic Assessment | `#/practice?mode=diagnostic` | Dedicated pre-start screen; How It Works facts; domain coverage + weights; What to Expect note; one start CTA. It must not auto-launch on route entry. |
| Quick Reference Sheets | `#/quick-reference` | Landing intro; print-friendly cue; five weighted domain-sheet cards; usage-note block. Domain selection opens detailed reference rows. |
| Glossary | `#/glossary` | Landing intro; five domain cards; usage-note block. Domain selection opens searchable task-level terms. |
| Mock Exam | `#/mock` | Centered title/lede; four uncluttered exam facts; one primary access-aware CTA; short scoring note. |
| Resources | `#/reference` | Narrow centered layout; left-aligned intro; section headings; compact 2-column resource cards. |
| SnowPro Journal | `#/journal` | Narrow centered editorial layout; vertical accent beside heading; 3-column article cards; read time, title/summary, date, arrow. |

## Snowflake-native facts that supersede the reference

- Certification: SnowPro Core COF-C03.
- Five current configured domains with weights 31 / 20 / 18 / 21 / 10.
- Nineteen task statements.
- App Quick Mock: 30 questions / 45 minutes.
- App Full Mock: 100 questions / 120 minutes.
- App practice readiness threshold: 750.
- Free candidates must be authenticated and retain the configured Free-plan limits; anonymous visitors receive no certification-prep content.
- Diagnostic uses the product's current Free entitlement rather than copying the reference site's question count.

## Executable visual acceptance

`scripts/capture_v26_visuals.py` must capture and structurally assert every route above in the authenticated light-theme pass, in addition to existing guest authentication, dark-theme, mock-player, feedback, membership/account, and mobile coverage.

A page is not considered recording-aligned merely because it renders. The capture must find its route-specific contract selector (domain-card grid, task rows, readiness panel, drill stats/filter chips, diagnostic card, lookup grid, grouped exercises, etc.).
