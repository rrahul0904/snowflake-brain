# Snowflake Certification Guide — Product Scope

Last reconciled: 2026-09-11

This document is the authoritative product-scope contract for the current Snowflake Certification Guide release.

## GA product thesis

The product is a certification-preparation system for Snowflake certifications, beginning with SnowPro Core COF-C03. It is built around blueprint-aligned written lessons, practice, mocks, adaptive learning evidence, question-bank governance, candidate accounts, verified credentials, and production operations.

## Explicitly in scope

The current GA scope includes:

- public certification discovery and source-verified exam facts;
- the five COF-C03 domains and nineteen task statements;
- written task lessons with objectives, rules, traps, examples, scenarios, sources, completion, and navigation;
- quick reference, glossary, journal, build exercises, and labs;
- diagnostic, targeted drill, spaced-repetition review, adaptive practice, quick mocks, and full timed mocks;
- server-owned mock timing, autosave, resume/discard, flags, answer review, domain analytics, and remediation;
- persisted progress, Due Today, mistake notebook, confidence calibration, study plan, and evidence-based adaptive readiness;
- Free, Premium, and Exam Pack entitlement logic;
- email/password account lifecycle and Google OIDC integration when configured;
- Credly-backed SnowPro credential verification and candidate-controlled talent visibility;
- private question-bank release governance, immutable versions, QA, human review/SME approval, activation, and rollback;
- PostgreSQL production persistence, least-privilege runtime boundaries, observability, security assurance, browser/mobile/accessibility checks, and Vercel deployment.

## Explicitly out of scope

### Video learning

Video learning is intentionally **not part of this product** and must not be tracked as pending GA work.

The active application must not introduce:

- a course or academy runtime;
- video lessons;
- a video player or transcript player;
- a media library;
- YouTube/Vimeo lesson embeds;
- video watch-position or media-progress persistence;
- video-specific provider credentials or storage.

The learner experience remains written/task-oriented. This is a deliberate product decision, not a missing feature.

### Other non-GA scope

The following are also not required for the current GA release unless separately approved later:

- recruiter marketplace search and introductions;
- user-generated content hosting;
- fabricated testimonials, pass rates, learner counts, or geographic activity;
- an open-ended AI tutor added only for parity with another product;
- unsupported certification tracks presented as fully available.

## Release rule

A release must not be blocked because video learning does not exist. Conversely, active frontend/backend code must not silently reintroduce course/video/media runtime surfaces without an explicit scope change.

`scripts/test_product_scope.py` and the existing retired-media guard in `scripts/verify_all.sh` enforce this boundary.

## Production completion boundary

Product scope and production release evidence are separate concerns.

The application can be feature-complete for the approved non-video scope while production remains NO-GO until external release evidence is complete. The remaining production-only evidence includes, as applicable:

- active private-bank inventory and exact release-count verification;
- genuine human SME approval for the activated release;
- live attacker/victim hostile-subscriber verification;
- real account-email lifecycle delivery;
- real Google sign-in/link/logout verification if Google is enabled;
- Stripe provider onboarding and E2E verification if paid billing is enabled;
- external alert-delivery proof;
- branch/ruleset governance and final exact-SHA release evidence.

Those items must remain explicit. They must never be hidden by calling the product complete before the corresponding production evidence exists.