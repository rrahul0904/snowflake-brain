# Snowflake Certification Guide

A private, local-first Snowflake certification preparation product built around the workflow a learner actually needs:

**choose a certification → understand its curriculum blueprint → learn every task statement → diagnose weaknesses → drill weak skills → complete build exercises → sit timed mocks → review quick-reference/glossary → track readiness until prepared to pass.**

The learner-facing product is deliberately **not** a video/course player. Written certification tasks, practice evidence, build exercises, and readiness are the product. Legacy archive/media tables remain only for migration compatibility and optional question ingestion.

## What is implemented

### All current official SnowPro certifications

The product exposes launchable curricula for the current Snowflake certification catalog:

- SnowPro Associate: Platform — `SOL-C01`
- SnowPro Core — `COF-C03`
- SnowPro Specialty: Snowpark — `SPS-C01`
- SnowPro Specialty: Native Apps — `NAS-C01`
- SnowPro Specialty: Gen AI — `GES-C01`
- SnowPro Advanced: Architect — `ARA-C01`
- SnowPro Advanced: Security Engineer — `SEA-C01`
- SnowPro Advanced: Data Engineer — `DEA-C02`
- SnowPro Advanced: Data Scientist — `DSA-C03`
- SnowPro Advanced: Administrator — `ADA-C02`
- SnowPro Advanced: Data Analyst — `DAA-C01`

Custom learning tracks such as Snowflake Cost Optimization remain available but are clearly separated from official SnowPro certifications.

Current public certification metadata lives in:

```text
config/certification_catalog.json
```

The long-lived curriculum map and the supplemental official curricula live in:

```text
config/certification_skill_map.json
config/certification_curricula_supplement.json
```

For the six supplemental curricula, Snowflake's public certification overview exposes capability areas but not detailed machine-readable domain percentages. Their percentages are therefore explicitly treated as **normalized curriculum planning weights**, not represented as official exam-domain weightings.

### Certification home

- official catalog grouped into Associate/Core, Specialty, and Advanced
- current public exam codes
- certification selector independent of course ingestion
- certification summary and task completion
- direct entry to Diagnostic and Curriculum
- Custom Learning Tracks section separate from official exams

### Blueprint-driven curriculum

The canonical learning hierarchy is:

```text
Certification
  → curriculum domains
    → task statements / skills
      → written lesson
      → scenario practice
      → build exercise
      → task completion
```

### Written task lessons

Every task route supports:

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

SnowPro Core COF-C03 has a fully authored editorial lesson for every configured task in:

```text
config/study_content_core.json
```

Every other official curriculum receives a complete structured lesson from its task objective, vocabulary, traps, official certification metadata, and the common lesson contract. Those lessons are fully functional today and can be upgraded to deeper editorial prose without changing application architecture.

### Guaranteed local practice bank

A clean installation does not depend on imported courses or practice-test archives to make the product usable.

When certification practice first runs, the backend creates a deterministic local canonical question bank from each task lesson. Questions cover:

- task objective
- decision rules
- configured traps
- trap correction
- anti-patterns
- build checks
- worked examples
- application scenarios

The system creates enough unique local questions per certification to support at least a full 65-question mock even when no external question archive is installed.

Canonical questions are persisted in SQLite and linked to their exact task with high-confidence deterministic mappings. Human-reviewed imported questions remain preferred evidence.

Question-to-skill resolution order is:

1. human-reviewed mapping
2. persisted mapping at confidence `>= 0.70`
3. heuristic fallback

### Diagnostic

Diagnostic selection is balanced across configured curriculum domains instead of a single random question bucket.

It answers:

> Where am I weak before I start studying?

### Drill Mode

Drill Mode supports:

- explicit task/skill targeting
- explicit domain targeting
- weak-skill prioritization
- unseen-question priority
- repeated-miss priority
- low-accuracy priority
- attempt-history awareness
- preference for stronger mapping provenance

### Mock Exam

Mock selection uses configured curriculum weights instead of `ORDER BY RANDOM()`.

The learner gets:

- Quick Mock
- Full Mock
- timed pacing
- question navigator
- free navigation
- mark-for-review
- automatic submission when time expires
- explanations deferred until submission
- persistent mock score/elapsed-time evidence
- post-exam actions into Progress, Curriculum, and Drill

Mock scores are persisted as raw `score / total` and normalized to percentage by the readiness model.

### Build Exercises

Configured Snowflake SQL challenges open in the local lab runner and validate solution structure without sending SQL to a live Snowflake account.

Every written task also includes a task exercise even when a dedicated validator has not yet been authored.

```text
config/snowflake_lab_challenges.json
app/lab_challenges.py
frontend/views/labs.js
```

### Quick Reference

Quick Reference is generated from the same canonical task lessons used by Curriculum.

It includes:

- task objective
- key concepts
- compact decision rules
- exam traps
- curriculum weights
- links to deeper lessons
- browser `Print / Save PDF`

### Glossary

The glossary is searchable and exam oriented:

- task/feature title
- objective/definition
- aliases and vocabulary
- exam context/trap
- direct task link

### Snowflake Certification Blog

The built-in Blog contains original exam and technical deep dives linked back into the task curriculum.

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

### Persistent Progress

Task completion is stored in SQLite through:

```text
GET  /api/skills/task-progress
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

### Evidence-based readiness

Readiness is not page-view completion.

The model consumes:

- written task completion
- mapped question attempts
- accuracy
- repeated misses
- timed/mock attempts
- lab evidence
- mapping quality
- task/skill coverage

The API deliberately reports two separate concepts:

```text
readiness_score
readiness_confidence
```

`readiness_score` represents observed learner performance.

`readiness_confidence` represents how much evidence exists to trust that score, using mapping trust, practice volume, skill coverage, mock evidence, and task completion.

Mastery is entirely certification-task based:

```text
1 exposed            written task exists
2 learned            task marked complete
3 practiced          sufficient question attempts
4 accurate           sufficient accuracy evidence
5 timed_accurate     timed/mock accuracy evidence
6 lab_proven         applicable lab passed
7 exam_ready         strong combined evidence
```

Video watches, transcript progress, and course lesson counts do not contribute to this mastery ladder.

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

Legacy video/archive URLs redirect into the certification product. The old learner-facing `curriculum.js`, `lesson.js`, and `video.js` views were removed.

## Architecture

The application intentionally remains lightweight and local-first:

- Python 3.13
- FastAPI
- Pydantic
- SQLite with WAL / FTS5
- vanilla HTML/CSS/native ES modules
- HTTPX
- Docker / Docker Compose
- no React/Node build pipeline required
- no authentication for the current local single-user deployment
- lab SQL uses offline validation and is never executed against Snowflake by default

The sophistication lives in certification modeling, task content, evidence mapping, adaptive selection, and readiness—not infrastructure theater.

## Important configuration files

```text
config/certification_catalog.json                Current official/custom certification metadata
config/certification_skill_map.json              Original implemented curricula
config/certification_curricula_supplement.json   Remaining official certification curricula
config/study_content_core.json                   Fully authored COF-C03 written lessons
config/snowflake_lab_challenges.json             Validated hands-on challenges
```

## Important backend modules

```text
app/certification_content.py            Catalog overlay + written lesson engine
app/skill_brain.py                      Complete merged curriculum/skill lookup
app/intelligence.py                     Mastery, mistakes, readiness, confidence
app/evidence.py                         Mapping audit/review foundation
app/routers/skills.py                   Catalog, lessons, completion, resources
app/routers/certification_practice.py   Canonical bank + targeted diagnostic/drill/mock engine
app/routers/labs.py                     Offline challenge API
app/routers/experience.py               Video-free certification startup payload
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

### Progress

```text
GET  /api/skills/task-progress?track_id=snowpro-core
POST /api/skills/task-progress
```

### Practice

```text
POST /api/certification-quiz/start
POST /api/quiz/grade
POST /api/questions/{question_id}/attempt
POST /api/certification-mock/record
```

Targeted drill:

```json
{
  "track_id": "snowpro-core",
  "mode": "drill",
  "skill_id": "warehouse-cost-control",
  "count": 15
}
```

Full mock:

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

Local verification entry point:

```bash
bash scripts/verify_all.sh
```

Key portable smoke tests:

```text
scripts/smoke_evidence.py
scripts/smoke_certification_guide.py
scripts/smoke_static_routes.mjs
```

The certification smoke is designed to prove:

- all 11 official certification catalog entries exist
- all 11 official certifications are implemented and launchable
- current exam codes are overlaid correctly
- every configured task returns a complete lesson contract
- all 10 COF-C03 tasks use curated editorial content
- every official certification can generate 65 unique questions on a fresh DB
- deterministic canonical questions have persisted task mappings
- human-reviewed mappings outrank canonical mappings in targeted drill selection
- diagnostic selection is domain balanced
- mock selection follows configured weights
- mock results persist and normalize correctly
- task completion persists
- readiness returns score and confidence separately
- mastery contains no video/course lesson evidence
- removed video views remain absent
- frontend route and syntax contracts remain valid

## Content quality levels

### Editorially curated

- SnowPro Core — COF-C03 — all 10 configured task lessons

### Structured curriculum lessons

Every other official SnowPro certification is fully launchable through the same lesson/practice/mock/progress engine. Its current first version uses the structured curriculum lesson generator, with official certification metadata, task-specific objective/vocabulary/traps, practice scenarios, exercises, and source links.

That is a content-depth distinction, not missing product functionality.

## Product principle

The application should always answer three questions clearly:

1. **What does this Snowflake certification require?**
2. **What do I currently know based on evidence?**
3. **What should I learn, practise, or build next to be ready to pass?**

Anything that does not improve those three answers should not become learner-facing product complexity.
