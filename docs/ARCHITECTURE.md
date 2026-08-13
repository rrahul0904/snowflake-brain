# V24 Architecture

## Boundary

Snowflake Certification Guide is a certification-preparation application. The runtime does not ingest, index, stream, or track video courses, captions, transcripts, course folders, or lesson media.

The product source of truth is the certification model:

```text
Certification
  -> Blueprint
     -> Weighted domain
        -> Task statement
           -> Written task content
           -> Question evidence
           -> Build exercise
```

Learning evidence flows back upward:

```text
Question attempt / task completion / lab result / timed mock
  -> task mastery
  -> domain mastery
  -> certification readiness
```

## Runtime modules

### Configuration and content

- `config/snowpro_core_cof_c03_blueprint.json`: canonical Core C03 domain/task contract.
- `config/study_content_core.json`: fully written content for all 19 Core tasks.
- `config/certification_skill_map.json`: configured certification metadata; Core is overridden by the current C03 blueprint at runtime.
- `config/certification_curricula_supplement.json`: additional certification curriculum definitions.
- `config/certification_catalog.json`: certification catalog metadata.
- `config/snowflake_lab_challenges.json`: certification-linked build exercises.

### Backend

- `app/main.py`: FastAPI entry point; registers only certification routers.
- `app/database.py`: clean certification-native SQLite schema.
- `app/skill_brain.py`: resolves certification/domain/task definitions and task matching.
- `app/certification_content.py`: written-task and catalog content API helpers.
- `app/intelligence.py`: question mapping, mastery, diagnostics, mistakes, readiness.
- `app/evidence.py`: mapping trust, stale-edge detection, human review.
- `app/lab_challenges.py`: build exercise catalog and offline validation.

Routers:

- `app/routers/skills.py`
- `app/routers/questions.py`
- `app/routers/certification_practice.py`
- `app/routers/intelligence.py`
- `app/routers/experience.py`
- `app/routers/labs.py`

### Frontend

- `frontend/router.js`: certification-only route table.
- `frontend/api.js`: certification-only API client.
- `frontend/views/guide.js`: overview, curriculum, domains, tasks, progress, reference, glossary.
- `frontend/views/quiz.js`: diagnostic/drill/mock exam player.
- `frontend/views/labs.js`: build exercise workspace.
- `frontend/views/journal.js`: certification technical articles.

## Exam engine

`POST /api/certification-quiz/start` selects questions by certification task mapping.

Selection modes:

- Diagnostic: balanced across configured domains.
- Drill: prioritizes weak/unseen/missed task evidence.
- Quick/full mock: allocates questions by current blueprint weights.
- Source exam: exact `practice_tests.id`, ordered by original question position.

Question source priority for current certification practice:

1. current source material (`source`)
2. curated material (`curated`)
3. deterministic supplemental material (`canonical`)

Legacy exam-version material (`legacy`) is excluded from current readiness and default practice selection.

## Mapping precedence

Question-to-task assignment uses:

1. human-reviewed persisted edge
2. persisted edge with confidence >= 0.70
3. heuristic fallback against the current configured task list

Persisted edges that reference task IDs retired from the current blueprint are ignored. `app/evidence.py` reports them as stale edges so old taxonomies cannot silently inflate mapping trust.

## Persistence boundary

The V24 default database is `data/snowflake_certification.sqlite`, deliberately separate from historical local databases.

There are no course, lesson, transcript, video, document, or archive tables in the V24 schema.

## Verification

Run:

```bash
scripts/verify_all.sh
```

The hard cleanup gate is `scripts/smoke_certification_native.py`. It verifies the clean table model, direct question-to-certification ownership, C03 blueprint shape, exact-set grading, stale-edge handling, deleted runtime files, and banned legacy runtime identifiers.
