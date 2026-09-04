# Reverse-Engineering Coverage Matrix

**Status:** canonical product-coverage record  
**Coverage artifact:** `artifacts/reverse-engineering-coverage.json`  
**Completeness gate:** `scripts/test_reverse_engineering_completeness.py`  
**Baseline release head audited:** `49b017e5926ac576930555b65ad7375abeb98c8d`

## Purpose

This document reconciles four different evidence layers that had accumulated during the Snowflake Certification Guide build:

1. the original 2026-08-13 screen-recording feature contract;
2. the 2026-08-14 authenticated-page recording contract;
3. later reference-site product evolution reviewed on 2026-09-01; and
4. Snowflake Brain product engineering that intentionally goes beyond the reference.

It is not permission to clone third-party source code, proprietary questions, articles, branding, testimonials, visual assets, or marketing copy. Snowflake Brain remains an original Snowflake-specific product.

## Source hierarchy

When requirements conflict, use this order:

1. **Security, privacy, entitlement, content-integrity, and production controls.** These never yield to visual parity.
2. **Current official Snowflake sources for Snowflake facts.** Third-party preparation sites are not factual authority for Snowflake exam details.
3. **Later explicit user instructions.** Example: the requested full-height feedback drawer supersedes older recorded panel geometry.
4. **Original recording interaction/product concepts.** Use as clean-room information architecture and workflow reference.
5. **Current reference-site evolution.** Evaluate for product value; do not automatically clone.

## Completeness rule

Every concept ends in exactly one disposition:

- `IMPLEMENTED_AND_TESTED`
- `INTENTIONALLY_NOT_IMPLEMENTED`
- `SUPERSEDED_BY_BETTER_SNOWFLAKE_NATIVE_IMPLEMENTATION`
- `EXTERNAL_CONFIGURATION`
- `FUTURE_SCOPE`

For P0/P1, the CI gate rejects `MISSING_TO_IMPLEMENT`, `PARTIAL`, `TODO`, `PLACEHOLDER`, `UNKNOWN`, and `MAYBE`.

## Current P0/P1 result

The machine-readable matrix contains **42 requirements**. **38 are P0/P1** and have explicit non-missing dispositions:

| Disposition | P0/P1 count | Meaning |
| --- | ---: | --- |
| `IMPLEMENTED_AND_TESTED` | 27 | Product behavior exists with named implementation and test evidence. |
| `SUPERSEDED_BY_BETTER_SNOWFLAKE_NATIVE_IMPLEMENTATION` | 7 | The learner/product outcome is covered by a stronger Snowflake-native implementation. |
| `EXTERNAL_CONFIGURATION` | 4 | Repository implementation exists; deployment credentials, hosted activation, or human governance remains external. |
| Missing / partial / unknown | **0** | CI must fail if this changes. |

P2 contains four explicitly evaluated concepts: interactive reference-site modes, testimonials, coming-soon waitlists, and future recruiter marketplace scope.

## Coverage by product area

| Category | Final position |
| --- | --- |
| Global shell | Implemented: navigation, account controls, mock CTA, theme, feedback, footer. |
| Home | Recording concept preserved; signed-in command center intentionally extends it with actionable learner evidence. |
| Certification discovery | Public source-checked catalog; official certification status separated from Snowflake Brain guide availability. |
| Certification facts | Implemented with explicit `null/not_verified` fields rather than guessed item count, duration, formats, or scoring. |
| Curriculum | Implemented: 5 COF-C03 domains, 19 tasks, weighted syllabus. |
| Domain | Implemented: domain detail, task rows, active expansion, completion indicators. |
| Lesson | Implemented: objective, knowledge, rules, traps, example, scenario, exercise, sources, completion, drill, navigation. |
| Progress | Superseded/extended: readiness plus SRS, mistakes, calibration, plan, remediation. |
| Drill | Implemented with pre-start screen and domain filters. |
| Diagnostic | Implemented with pre-start explanation and deliberate start. |
| Practice | Superseded/extended with SRS and governed entitlements. |
| Mock start | Implemented with interrupted-sitting resume/discard and quick/full choice. |
| Mock player | Implemented with server-owned timer, autosave, flags, navigation, resume, answer secrecy. |
| Results | Implemented with domain analytics, review, remediation, history, and separate unanswered filter. |
| Quick Reference | Implemented as task-linked decision/trap sheets. |
| Glossary | Implemented as searchable task-oriented terminology; avoids source-less invented definitions. |
| Build Exercises | Existing Snowflake labs supersede an open-ended AI Build Coach with authored scenarios, hints, checks, solutions, and validation. |
| Reference | Implemented with Snowflake-specific external resources. |
| Journal | Implemented with original certification-focused editorial content. |
| Feedback | Implemented; full-height drawer intentionally follows later explicit instruction. |
| Theme | Implemented and persistent. |
| Responsive | Implemented across desktop/tablet/mobile launch rehearsal. |
| Accessibility | Implemented baseline with keyboard/focus/labels/reduced motion/browser checks. |
| Activity globe | Superseded by truthful projected geography and privacy-thresholded activity; fake users/locations are prohibited. |
| Authentication | Implemented; Google live use still requires deployment credentials. |
| Account lifecycle | Implemented; real production mail delivery requires provider configuration. |
| Membership | Implemented with server-authoritative entitlements. |
| Billing | Code implemented; Stripe live/test hosted activation is external configuration. |
| Question bank | Runtime/release system implemented; private production import/SME activation is external configuration. |
| Content governance | Implemented with immutable versions, freshness, QA, human editorial/SME boundary, staging and rollback. |
| Adaptive readiness | Snowflake-native evidence model supersedes simplistic pass-probability treatment. |
| Learning intelligence | Snowflake-native SRS/mistakes/calibration/plan/remediation extends the reference. |
| Credentials | Credly verification foundation implemented; recruiter marketplace remains future scope. |
| Trust/legal | Active V26 now contains content-integrity/non-affiliation/provenance policy without resurrecting retired beta UI. |
| Observability | Code/tests implemented; external alert-delivery evidence remains configuration. |
| Security | Implemented release gates include SAST, dependency audit, DAST, hostile-subscriber, auth/cache/session and PostgreSQL role boundaries. |
| Production operations | Automation exists; hosted credential rotation, exact production deployment and final soak remain external release evidence. |

## Specific gaps closed in this wave

### Public source-verified certification discovery

`#/certifications` and `#/exam-guide` can be visited without login, but only the public certification catalog is exposed. `skill map`, lessons, practice, labs, question bank, readiness, mocks, candidate state, and protected frontend modules remain authentication-gated.

For focused certifications, the catalog stores verified source URLs and a verification date. If a fact was not confirmed from the authoritative Snowflake source used in this release, it remains `null` with `source_status=not_verified` and is omitted from the page.

### Sidebar completion

The study shell accepts candidate completion state. Curriculum/domain pages fetch task progress once and pass it into the shell. The active expanded domain shows completion ticks. Mark Complete updates the lesson button and sidebar state without an N+1 request pattern.

### Unanswered mock review

Result review now separates:

- All
- Correct
- Incorrect (wrong **and answered**)
- Unanswered
- Flagged

Existing targeted drill and mock remediation remain the preferred retry path; no duplicate copied retry mode is added.

### Content integrity and IP

Useful concepts from historical PR #30 were ported into active V26 via:

- `docs/CONTENT_INTEGRITY_AND_IP_POLICY.md`
- `#/content-integrity`
- the active V26 footer

The retired `beta-demo` architecture is not restored. The product does not claim copyright/trademark registration that has not occurred.

## Current-reference evolution dispositions

### Completion ticks

**Implemented.** They provide direct learner value and fit the existing progress model.

### Unanswered/skipped result filtering

**Implemented.** This removes ambiguity between wrong answered questions and skipped questions.

### Concept Check / Exam Sim / Build Coach

**Superseded by better Snowflake-native implementation.** The current product already has:

- inline task practice scenario;
- governed task/domain drills and timed mocks;
- authored lab scenarios;
- starter SQL;
- progressive hints;
- validation tests;
- expected output;
- solution SQL and teardown.

An open-ended AI tutor is not added merely for parity because it introduces cost, hallucination, prompt-governance, abuse, and observability requirements without closing a P0/P1 learner gap.

### Testimonials/social proof

**Intentionally not implemented.** No real consented candidate testimonial corpus was provided. Workflow examples are labeled as examples rather than pass testimonials. Learner counts, locations, pass rates, and testimonials must never be fabricated.

### Coming-soon waitlists

**Future scope.** Public exam facts provide value now without introducing a marketing-consent/email lifecycle solely for parity.

## Private-bank quality evidence

The repository contains only the private-bank manifest and release/audit tooling, not the 1,200 commercial questions.

`scripts/audit_private_bank_quality.py` is the approved aggregate-only audit. Given the exact private artifact, it validates:

- pinned SHA-256;
- schema/version/track/exam;
- total/pool/domain/task/difficulty/type counts;
- duplicate IDs;
- malformed answer structures;
- correct/distractor rationale completeness;
- HTTPS source references and source-verification dates;
- normalized duplicate-stem count using hashes only;
- correct-option positional distribution;
- correct-answer-length signal;
- multi-select structural validity.

Its output contains no stems, options, rationales, source titles, or question IDs.

The full-corpus run remains an external/private release operation because the artifact must not be committed into Git or public CI artifacts.

## Production completeness is separate

`REVERSE ENGINEERING COMPLETE` does **not** mean `PRODUCTION GO`.

Production still requires deployment-specific evidence such as:

- hosted least-privilege runtime credential activation;
- exact-head healthy Vercel deployment;
- private bank import and real SME approval;
- Stripe account/onboarding and provider provisioning;
- production email and observability delivery proof;
- hosted attacker/victim security verification;
- independent GitHub approval;
- final exact-production soak/rollback evidence.

Those gates must continue independently and must not be fabricated to satisfy this matrix.
