# Snowflake Certification Guide

A private, local-first Snowflake certification preparation product modeled around the actual workflow a certification learner needs:

**choose a certification → understand the exam blueprint → learn every task statement → diagnose weaknesses → drill weak skills → complete build exercises → sit timed mocks → review quick-reference/glossary → track readiness until prepared to pass.**

The learner-facing product is deliberately **not** a video/course player. The certification blueprint and written task lessons are the product. Legacy archive/media tables remain only for migration compatibility and existing local question ingestion.

## Current product

### Certification home

- Official SnowPro catalog grouped into Associate/Core, Specialty, and Advanced certifications.
- Current public exam codes and certification metadata are separated from the internal curriculum map.
- Implemented tracks open immediately.
- Official certifications whose full curriculum has not been implemented are shown honestly as `coming soon` rather than opening empty pages.
- Custom learning tracks such as Cost Optimization are clearly separated from official SnowPro certifications.

Current catalog metadata lives in:

```text
config/certification_catalog.json
```

### Blueprint-driven curriculum

The canonical learning hierarchy is:

```text
Certification
  → weighted exam domains
    → task statements / skills
      → written lesson
      → scenario practice
      → build exercise
      → task completion
```

The certification blueprint is defined in:

```text
config/certification_skill_map.json
```

### Written task lessons

Each task lesson supports the same study contract:

- What You Need to Know
- Key Concept
- Decision Rules
- Common Anti-Patterns
- Exam Traps and corrections
- Worked Example
- Practice Scenario
- Build Exercise
- Official/reference Sources
- Mark Complete
- Drill This Task
- Next Lesson

SnowPro Core COF-C03 currently has a fully authored editorial lesson for every configured task in:

```text
config/study_content_core.json
```

Other implemented curriculum tracks always receive a structured task lesson generated from their configured objective, aliases, traps, and official certification metadata, so implemented routes do not render blank study pages. They can be upgraded to fully curated editorial lessons independently without changing the application architecture.

### Diagnostic

The diagnostic uses certification-domain mappings to build a balanced baseline across the blueprint. It is designed to answer:

> Where am I weak before I start studying?

### Drill Mode

Drill selection is evidence driven rather than a simple random question bucket.

Priority order includes:

- explicit task/skill target
- explicit domain target
- unseen questions
- repeatedly missed questions
- low-accuracy questions
- weak-skill evidence
- lower-attempt evidence

Question-to-skill resolution prefers:

1. human-reviewed mapping
2. persisted mapping at confidence `>= 0.70`
3. heuristic fallback

### Mock Exam

Mock selection follows configured domain weights rather than `ORDER BY RANDOM()`.

The learner gets:

- Quick Mock
- Full Mock
- timed pacing
- question navigator
- free navigation
- mark-for-review
- auto-submit when time expires
- explanations only after submission
- persistent mock results
- post-exam repair links to Progress, Curriculum, and Drill

Completed mocks are stored as finished exam sessions and immediately feed readiness evidence.

### Build Exercises

Configured Snowflake SQL challenges open in the local lab runner and validate SQL structure without sending SQL to a Snowflake account.

Every written task also contains an exercise even when a dedicated validator has not yet been authored.

Relevant files:

```text
config/snowflake_lab_challenges.json
app/lab_challenges.py
frontend/views/labs.js
```

### Quick Reference

Quick Reference is generated from the same canonical task lessons used by Curriculum, so the final-review material cannot silently drift away from the teaching content.

It includes:

- task objective
- key concepts
- compact decision rules
- exam traps
- domain weights
- links to deeper task lessons
- browser `Print / Save PDF`

### Glossary

The glossary is searchable and exam oriented. Entries combine:

- task/feature title
- objective/definition
- aliases and vocabulary
- exam context/trap
- direct link to the lesson

### Snowflake Certification Blog

The built-in Blog provides original exam and technical deep dives that link back into task lessons instead of living as disconnected articles.

Current topics include:

- SnowPro Core COF-C03 preparation
- Snowflake RBAC and role hierarchy
- warehouse scale up vs scale out
- result cache, warehouse cache, and Query Profile
- stage vs file format vs COPY INTO
- Snowpipe vs warehouse COPY
- VARIANT and LATERAL FLATTEN
- Time Travel vs clone vs Fail-safe
- Secure Data Sharing, masking, and row access policies
- streams vs tasks

### Progress and readiness

Readiness is not page-view completion.

The model consumes:

- written task completion
- mapped question attempts
- accuracy
- repeated misses
- timed/mock attempts
- lab evidence
- mapping quality
- domain/skill coverage

The API reports two separate concepts:

```text
readiness_score
readiness_confidence
```

`readiness_score` represents observed learner performance.

`readiness_confidence` represents how much evidence exists to trust that score, using mapping trust, practice volume, skill coverage, mock evidence, and task completion.

This prevents a learner with a few lucky answers from receiving a falsely authoritative readiness signal.

## Product routes

Certification-guide routes:

```text
#/home
#/curriculum
#/domain
#/skill
#/progress
#/diagnostic
#/drill
#/mock
#/exercises
#/quick-reference
#/glossary
```

Direct workspaces:

```text
#/practice
#/labs
#/reference
#/journal
#/article
```

Legacy video/archive URLs redirect into the certification product. The old learner-facing video/course views were removed.

## Architecture

The application intentionally stays lightweight and local-first:

- Python 3.13
- FastAPI
- Pydantic
- SQLite with WAL/FTS5
- vanilla HTML/CSS/native ES modules
- HTTPX
- Docker / Docker Compose
- no React build pipeline required
- no authentication for the current single-user local deployment
- lab SQL uses offline validation and is never executed against Snowflake by default

The sophistication lives in the certification model, evidence graph, practice selection, and readiness logic rather than infrastructure complexity.

## Important configuration files

```text
config/certification_catalog.json       Current official/custom certification metadata
config/certification_skill_map.json     Implemented domains and task statements
config/study_content_core.json          Fully authored COF-C03 written lessons
config/snowflake_lab_challenges.json    Validated hands-on challenges
```

## Important backend modules

```text
app/certification_content.py            Catalog overlay + written lesson engine
app/intelligence.py                     Mastery, mistakes, readiness, confidence
app/evidence.py                         Mapping audit/review foundation
app/routers/skills.py                   Catalog, lessons, completion, task resources
app/routers/certification_practice.py   Targeted diagnostic/drill/mock selection
app/routers/labs.py                     Offline challenge API
app/routers/experience.py               Certification-product startup payload
```

## Main APIs

### Certification content

```text
GET  /api/skills/map
GET  /api/skills/catalog
GET  /api/skills/content-coverage
GET  /api/skills/summary?track_id=snowpro-core
GET  /api/skills/{skill_id}/lesson?track_id=snowpro-core
GET  /api/skills/{skill_id}/resources?track_id=snowpro-core
```

### Task progress

```text
GET  /api/skills/task-progress?track_id=snowpro-core
POST /api/skills/task-progress
```

Example:

```json
{
  "track_id": "snowpro-core",
  "skill_id": "warehouse-cost-control",
  "completed": true
}
```

### Practice

```text
POST /api/certification-quiz/start
POST /api/quiz/grade
POST /api/questions/{question_id}/attempt
POST /api/certification-mock/record
```

Example targeted drill:

```json
{
  "track_id": "snowpro-core",
  "mode": "drill",
  "skill_id": "warehouse-cost-control",
  "count": 15
}
```

Example full mock selection:

```json
{
  "track_id": "snowpro-core",
  "mode": "full-mock",
  "count": 65
}
```

### Intelligence

```text
GET  /api/intelligence/skill-mastery?track_id=snowpro-core
GET  /api/intelligence/readiness?track_id=snowpro-core
GET  /api/intelligence/mistake-queue?track_id=snowpro-core
GET  /api/intelligence/diagnostic?track_id=snowpro-core
GET  /api/intelligence/evidence-audit?track_id=snowpro-core
POST /api/intelligence/evidence-review
```

### Labs

```text
GET  /api/labs/config
GET  /api/labs
GET  /api/labs/{lab_id}
POST /api/labs/{lab_id}/submit
```

## Run locally

### Docker

```bash
docker compose up --build
```

Open:

```text
http://localhost:8010
```

API docs:

```text
http://localhost:8010/docs
```

### Python development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
AUTO_INGEST=false \
BRAIN_DB=./data/snowflake_brain.sqlite \
uvicorn app.main:app --reload --port 8010
```

`CONTENT_ROOT` may still be configured for legacy/local question ingestion, but learner-facing certification content no longer depends on videos or transcripts.

## Verification

Run the local verification suite:

```bash
bash scripts/verify_all.sh
```

The portable certification-product smoke verifies:

- current certification catalog overlays
- current exam codes
- full COF-C03 editorial content coverage
- usable content for every implemented task
- persistent task completion
- skill-targeted drills
- domain-balanced diagnostics
- blueprint-weighted mocks
- mock persistence and score normalization
- readiness confidence
- reviewed question-mapping precedence
- video-free mastery evidence
- video-free route contract
- frontend syntax

Key smoke scripts:

```text
scripts/smoke_evidence.py
scripts/smoke_certification_guide.py
scripts/smoke_static_routes.mjs
```

## Current content status

### Fully curated

- SnowPro Core — COF-C03 — all 10 configured task lessons

### Implemented with structured curriculum lessons

- SnowPro Advanced: Data Engineer
- SnowPro Advanced: Architect
- SnowPro Specialty: Snowpark
- SnowPro Specialty: Gen AI
- Snowflake Cost Optimization (custom learning track)

These tracks are fully navigable through the same engine. Their task lessons currently use the structured curriculum-derived fallback until each track receives the same editorial depth as Core.

### Official catalog visible as coming soon

Official SnowPro certifications without an implemented curriculum are shown in the catalog but cannot launch an empty guide. That is intentional product behavior.

## Product principle

The application should always answer three questions clearly:

1. **What does this Snowflake certification require?**
2. **What do I currently know based on evidence?**
3. **What should I study, practise, or build next to be ready to pass?**

Anything that does not improve those three answers should not become learner-facing product complexity.
