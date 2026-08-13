# Screen Recording Feature Contract

This document records the learner-facing behaviors observed in the user-provided screen recording on 2026-08-13. It is a product contract for the Snowflake Certification Guide rebuild. Reproduce the interaction patterns and feature coverage with Snowflake-specific content and original implementation; do not copy third-party source code, proprietary question text, or branding.

## Global shell
- Sticky horizontal header with brand, primary navigation, certification selector, primary mock-exam CTA, and light/dark theme toggle.
- Theme switches the whole product and persists between routes.
- Certification selector supports an `All certifications` state and named certification tracks, with current/coming-soon state.
- Floating feedback action fixed at the lower-right of normal pages.
- Feedback panel opens from the floating action and includes: required title, category segmented controls (Bug / Feature Request / Content Issue / Other), description, optional email, submit, and close.
- Cohesive light and dark themes, with the exam experience using the same design language.

## Home
- Certification-program/version eyebrow.
- Large editorial hero statement with highlighted italic word.
- Short exam-preparation value proposition.
- Two primary CTAs: choose certification and explore curriculum.
- Social proof line.
- Animated/interactive active-learner globe visualization with learner/location markers and a recent-activity caption.
- Footer/disclaimer and useful program links.

## Certification chooser
- Dedicated `Choose your certification` page/section.
- Multiple certification cards showing exam code, title, level, audience/description, status badge, item/question count, duration, domain count, version/effective date, and CTA.
- Live/current certification is visually distinguished from future/coming-soon tracks.
- FAQ accordion below certification cards.

## Curriculum / learn
- Track-aware header with Curriculum / Practice / Reference / Journal.
- Persistent study sidebar on wide screens.
- Sidebar sections: Study Tools, Curriculum domains, Practice, Look Up.
- Study tools include progress dashboard and drill mode.
- Domain navigation uses numbered rows, colored domain dots, titles, and expandable affordances.
- Practice links include build exercises and diagnostic test.
- Lookup links include quick reference and glossary.
- Main curriculum page starts with exam-domain overview and real-exam metadata.
- Domain cards show domain weight, colored domain indicator, title, summary, module count, and navigation CTA.

## Reference
- Dedicated Reference page.
- Resources grouped by category/section.
- Two-column resource-card layout on desktop.
- Cards include resource title and concise description.
- External documentation/resources open externally/new tab as appropriate.
- Observed category patterns: official documentation/specs, courses & learning, engineering blog/resources.

## Journal / blog
- Dedicated Journal page.
- Editorial card grid.
- Cards support optional category/topic badges, read-time metadata, title, excerpt, publication date, and open/read affordance.
- Supports certification-focused journal collections/landing sections.

## Mock exam landing
- Intentionally simple centered landing experience.
- Mock Exam title and concise explanation.
- Compact exam facts/metrics row (scenario/domain coverage, quick/full question counts, quick/full time limits, pass threshold/readiness threshold).
- One primary Start Mock Exam CTA.
- Secondary diagnostic link for learners who are not ready.

## Mock start / sitting selector
- Detect interrupted/in-progress sitting and offer Resume Exam or Discard.
- Choose Your Sitting section with quick and full-length options.
- Sitting cards show question count, duration, description, and a marker for the full sitting mirroring the real-exam simulation.
- Exam Format section with scenario/question count, time limit, scoring model, pass mark.
- Domain Weights section with colored domain dots and percentages.
- Before You Start callout with randomized question/option behavior, flagging, free navigation, non-pausable timer, post-submit explanations, readiness caveat, and skip/navigation behavior.
- Full-width Start button for the selected sitting.

## Exam player
- Dedicated exam shell distinct from normal study pages but visually consistent.
- Top bar shows product/exam identity and certification name.
- Top-right persistent time remaining with timer icon.
- Exam navigator sidebar shows questions remaining.
- Navigator supports Overview and Flagged views plus domain/category filters with colored dots.
- Numbered question grid for free navigation.
- Clear active/current question state.
- Submit Exam button in navigator.
- Main question header includes current question number / total and mapped domain/category indicator.
- Large faint question-number watermark in the background.
- Flag button per question.
- Large readable question stem.
- Scenario/context callout panel with category label and contextual description.
- Answer choices displayed as full-width selectable rows with letter labels.
- Supports single-select and multi-select questions.
- Sticky bottom exam navigation with Previous, progress-dot strip, and Next.
- Quick and full sittings use the same player shell.
- Session persists across navigation/refresh, timer continues, answers/flags persist, and submission is server-owned.

## Results / review contract
- Score/readiness result after submission.
- Detailed explanations after submission only.
- Preserve flagged state for review.
- Domain-weighted performance and weak-area follow-up should feed learner progress/readiness.

## Accessibility and behavior
- Theme toggle.
- Keyboard/screen-reader-friendly semantics should be preserved in our implementation.
- No dead CTAs: every button/link observed above must resolve to a working Snowflake-specific route/action.
- Mobile should adapt the normal sidebar/header and convert the exam navigator into a drawer/sheet.

## Snowflake-specific adaptation
- Brand and copy must be Snowflake-specific and original.
- Use the repository's canonical SnowPro Core COF-C03 five-domain / 19-task blueprint.
- Use Snowflake-specific score/readiness wording and the app's configured quick/full mock settings.
- Keep COF-C02 source material visibly legacy and excluded from COF-C03 readiness.
- Do not copy third-party article text, exam questions, logos, or source code.
