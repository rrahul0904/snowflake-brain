# V24 Certification-Native Cleanup

## Goal

Remove the previous course/video/archive product architecture rather than merely hiding it from the UI.

## Completed in V24

- New clean default SQLite database: `data/snowflake_certification.sqlite`.
- Certification-native schema with direct `track_id` ownership for questions and practice tests.
- Removed course, section, media lesson, document, transcript, archive-ingestion, and video-progress tables.
- Removed `CONTENT_ROOT` and automatic archive ingestion configuration.
- Removed course/video ingestion engine and course/index/search/AI archive routers.
- Removed fake certification `courses` previously created only to satisfy the old data model.
- Rebuilt question APIs on certification ownership.
- Rebuilt exam selection on certification ownership and explicit source provenance.
- Legacy exam-version questions are excluded from current readiness by default.
- Current source questions outrank supplemental generated questions when available.
- Rebuilt mastery/readiness against current certification questions and current task IDs.
- Rebuilt evidence audit so retired task IDs are classified as stale and do not count toward current mapping trust.
- Removed legacy lab database/static fallbacks.
- Removed old learner/product frontend views and video/archive route aliases.
- Reduced navigation to certification preparation surfaces.
- Reduced frontend API client to the active certification API surface.
- Removed course/content archive volume from Docker and Compose.
- Trimmed Python dependencies to the active certification runtime.
- Added `scripts/smoke_certification_native.py` as a hard architecture guard.
- Replaced old verification workflow with V24 certification-native checks.

## Current product hierarchy

```text
Certification
  -> Weighted domain
     -> Task statement
        -> Written lesson
        -> Build exercise
        -> Question evidence
  -> Diagnostic / Drill / Mock / Source exams
  -> Attempts + Task completion
  -> Mastery + Readiness
```

## Not a migration layer

The V24 runtime does not keep the old course schema around for compatibility. Historical data remains available in Git history and any historical local database files a developer may already have, but the V24 default runtime opens a new certification database and creates only certification-native tables.

## CI note

The repository's GitHub Actions account previously failed before runner assignment because of billing/spending-limit status. A failed workflow that executes zero steps is an infrastructure/account blocker, not evidence that V24 tests failed. Local verification remains `scripts/verify_all.sh` until Actions can obtain a runner.
