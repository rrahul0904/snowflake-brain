# Snowflake Brain - Certification Intelligence Engine v6

This build adds a serious intelligence layer on top of the all-certification skill map.

## Added

- Certification portfolio readiness across all mapped certifications.
- Evidence-based readiness model with pass-probability range.
- Skill mastery model with 0-7 maturity levels.
- Question-to-skill heuristic tagging support.
- Diagnostic blueprint endpoint.
- Mistake taxonomy and repair queue.
- Daily command brief.
- Premium Intelligence UI route at `#/intelligence`.

## New API routes

- `GET /api/intelligence/portfolio`
- `GET /api/intelligence/command-brief?track_id=snowpro-core`
- `GET /api/intelligence/skill-mastery?track_id=snowpro-core`
- `GET /api/intelligence/readiness?track_id=snowpro-core`
- `GET /api/intelligence/mistake-queue?track_id=snowpro-core`
- `GET /api/intelligence/diagnostic?track_id=snowpro-core&count=30`
- `POST /api/intelligence/reindex-skill-map?track_id=snowpro-core`

## New tables

- `question_skill_map`
- `content_skill_map`
- `skill_mastery_snapshots`
- `diagnostic_sessions`
- `diagnostic_answers`
- `mistake_events`
- `repair_tasks`
- `readiness_snapshots`

## Product direction

The app should behave like an exam operating system:

1. Diagnose current state.
2. Map evidence to skills.
3. Identify blockers.
4. Issue a daily command brief.
5. Force repair loops.
6. Prove readiness with exams and labs.
