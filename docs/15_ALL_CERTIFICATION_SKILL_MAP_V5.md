# Snowflake Brain - All Certification Skill Map v5

Last updated: 2026-06-29

## Goal

v5 expands the Skill Brain from a SnowPro Core-only map into a shared certification intelligence module for six Snowflake certification paths.

The app can now reason across:

1. SnowPro Core
2. SnowPro Advanced: Architect
3. SnowPro Advanced: Data Engineer
4. SnowPro: Snowpark Developer
5. SnowPro: Cortex AI / GenAI
6. Snowflake Cost Optimization

## What changed

### Config

Updated:

```text
config/certification_skill_map.json
```

The config now contains all six certifications with:

- certification id
- title
- exam code placeholder
- readiness rules
- domains
- skill ids
- skill titles
- objectives
- aliases
- question tags
- exam traps

### Labs

Updated:

```text
config/snowflake_lab_challenges.json
```

Labs are now mapped across certifications instead of SnowPro Core only.

Examples:

- Core: warehouse cost-safe setup, COPY INTO, VARIANT/FLATTEN, RBAC, Time Travel, Streams/Tasks
- Architect: managed access RBAC, tags/masking policy, replication/failover planning
- Data Engineer: Snowpipe, stream/task MERGE, dynamic tables
- Snowpark: DataFrame transform, Python UDF
- Cortex / GenAI: COMPLETE structured output, Cortex Search/RAG, AI governance masking
- Cost Optimization: resource monitors, query cost attribution, transient retention

### Backend

Updated:

```text
app/lab_challenges.py
app/routers/labs.py
```

Changes:

- Lab catalog now builds skill lookup across every configured certification.
- `/api/labs` accepts optional `certification` or `track_id` filter.
- Lab completion events now store the configured lab id instead of always storing NULL.

### Frontend

Updated:

```text
frontend/api.js
frontend/views/labs.js
```

Changes:

- Labs page now loads the certification skill map.
- Labs page has a certification selector.
- Skill mini-strip updates based on selected certification.
- Lab list filters to the selected certification.
- Lab cards show certification + domain.

## Why this matters

The app now has a single shared Skill Brain that can connect:

```text
Certification → Domain → Skill → Lesson → Question → Lab → Mistake → Readiness
```

This is the foundation for the platform to decide what to study, what to practice, what lab to complete, and what is blocking certification readiness.

## Important note

This is a practical starter skill map for coaching and local study organization. It should be reviewed against the latest official Snowflake exam guides before being treated as a final official blueprint.
