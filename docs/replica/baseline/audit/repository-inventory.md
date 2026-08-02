# Replica Baseline Repository Inventory

Generated: 2026-08-01T00:52:51-04:00  
Repository: `/Users/297159/Documents/Snowflake Certification Prep`

## Scope And Safety

This is a read-only baseline for Wave 0 of the replica plan. The audit inspected source files, the running Docker service, and an immutable SQLite connection. It did not import `app.main`, run migrations, trigger indexing, call mutation endpoints, or alter production source/data.

Only these audit files were created under `docs/replica/baseline/audit/`.

## Baseline Identity

| Item | Observed state | Consequence |
| --- | --- | --- |
| Git branch | `main` | Baseline branch is known. |
| Git history | Entire working tree is untracked | Git cannot currently identify ownership, regressions, or a clean rollback point. Create an intentional baseline commit before production work. |
| Git remote | None configured | No upstream recovery path exists from this checkout. |
| Live service | `snowflake-brain-lab`, port `8010 -> 8000` | Browser entry point is `http://127.0.0.1:8010/`. |
| Container created | `2026-08-01T04:37:19Z` | The live image includes the current editorial-replica shell. |
| Source mounts | `content` read-only; `data` read-write | Python/frontend source is baked into the image and requires rebuild; content is protected from container writes. |
| Authoritative database | `data/snowflake_brain.sqlite` | 95,182,848 bytes; SHA-256 `be2a4632ebf0016f910da0a24944c9c8b4be3bd32c25e4615e52be73c87d90f1`. |
| Non-authoritative database | `data/snowflake_brain.db` | Empty, 0 bytes. It must never be selected as the application database. |
| Indexed content root | `/content` | Stored in `meta.content_root`; last indexed at `2026-06-27T17:06:42.114016+00:00`. |

## Runtime Topology

```text
Browser
  -> http://127.0.0.1:8010
  -> Docker port 8010
  -> Uvicorn/FastAPI port 8000
       -> /api/* routers
       -> /static/* from baked /app/frontend
       -> SPA fallback to frontend/index.html
       -> SQLite /data/snowflake_brain.sqlite
       -> source media /content (read-only bind mount)
```

Startup is not read-only. `app.main.startup()` calls `run_migrations()` and may start background ingestion. `run_migrations()` also refreshes quality and duplicate tables. For that reason, baseline SQL was executed with:

```bash
sqlite3 'file:/Users/297159/Documents/Snowflake%20Certification%20Prep/data/snowflake_brain.sqlite?mode=ro&immutable=1'
```

## Source Inventory

### Backend

| Area | Files | Responsibility |
| --- | --- | --- |
| Application composition | `app/main.py`, `app/config.py`, `app/database.py` | FastAPI startup, mounts, configuration, migrations, connection lifecycle. |
| Content ingestion | `app/ingest.py` | Course/media/question discovery, English filtering, identity/deduplication, FTS rebuild. |
| Public serialization | `app/serializers.py` | Converts database questions and lessons into API objects. |
| Catalog/content | `app/routers/courses.py`, `app/routers/search.py`, `app/routers/index.py` | Tracks, courses, lessons, transcripts, media, documents, search, reindexing. |
| Assessment | `app/routers/questions.py` | Practice banks, questions, quiz grading, attempts, exam sessions, notes/bookmarks. |
| Learning utilities | `app/routers/flashcards.py`, `app/routers/labs.py`, `app/routers/progress.py`, `app/routers/study.py` | Flashcards, labs, progress, goals, plans, readiness, content audits. |
| Intelligence | `app/routers/skills.py`, `app/routers/intelligence.py`, `app/routers/experience.py`, `app/skill_brain.py`, `app/intelligence.py` | Skill map, readiness, mistake queues, aggregate shell/command-center payloads. |
| AI | `app/routers/ai.py` | Local retrieval plus optional hosted streaming response. |
| Data + AI academy | `app/routers/data_ai.py`, `config/data_ai_academy.json` | Separate JSON curriculum and event-backed completion/check/lab flow. |

There are 13 router modules and 79 live API operations across 75 API paths.

### Frontend

| Area | Current files/state |
| --- | --- |
| Shell | `frontend/index.html`, `frontend/app.js`, `frontend/router.js` |
| Shared UI | `frontend/components/nav.js`, `topbar.js`, `toast.js`, `frontend/ui.js`, `frontend/state.js` |
| Current replica routes | `curriculum.js`, `video.js`, `quiz.js`, `reference.js`, `journal.js` |
| Legacy/unwired views | `academy.js`, `ai.js`, `analytics.js`, `career.js`, `command.js`, `flashcards.js`, `intelligence.js`, `labs.js`, `plan.js`, `readiness.js`, `search.js` |
| Styling | `frontend/styles.css` (81,169 bytes, 1,678 lines) plus `frontend/replica.css` (15,052 bytes, 157 lines) |
| API client | `frontend/api.js` (9,295 bytes, 150 lines) |

The current canonical router exposes six paths: Curriculum, Lesson, Practice, Reference, Journal, and Article. Eighteen legacy hashes are translated through aliases.

The root-level `static/` directory is a second, stale frontend tree. Its file hashes differ from `frontend/`, while FastAPI serves `frontend/`. It is not authoritative and creates packaging/developer confusion.

## SQLite Model Inventory

The database contains 35 non-FTS application tables plus FTS5 support tables.

### Source And Curriculum

- `certification_tracks(id, title, description, position)`
- `courses(id, track_id, track_title, title, path, source_url, indexed metadata)`
- `course_sections(id, course_id, title, path, position, lesson_count)`
- `lessons(id, course_id, section_id, title, media/transcript paths, duration, transcript_text, position)`
- `transcript_chunks(id, lesson_id, chunk_idx, text, start_s, end_s)`
- `documents(id, course_id, title, path, body, excerpt)`

### Assessment

- `practice_tests(id, course_id, track_id, title, position, question_count, source_path)`
- `questions(id, course_id, test_id, question, options_json, correct_json, explanation, source_path, tags, difficulty, position)`
- `question_attempts`, `bookmarks`, `notes`
- `exam_sessions`, `exam_session_answers`

### Learning State And Intelligence

- `lesson_progress`, `daily_activity`, `learning_events`
- `study_goals`, `study_plan_items`
- `flashcards`, `lab_exercises`, `lab_submissions`
- `question_skill_map`, `content_skill_map`, `topic_objectives`
- `diagnostic_sessions`, `diagnostic_answers`
- `mistake_events`, `repair_tasks`, `readiness_snapshots`, `skill_mastery_snapshots`

### Governance And Quality

- `practice_test_classification`
- `question_duplicates`
- `content_quality_audit`
- `course_track_overrides`
- `schema_migrations`, `meta`

### Search

- `search_fts`
- External-content FTS indexes `question_fts`, `lesson_fts`, and `chunk_fts`

Exact columns and counts are recorded in [data-counts.json](./data-counts.json).

## Source Boundary Findings

1. All 3,386 questions have a valid `course_id`, a valid `test_id`, and a source path that exactly equals the parent `practice_tests.source_path`.
2. There are 195 non-empty source tests and exactly 195 question `test_id` values. Declared `practice_tests.question_count` matches actual question rows for every test.
3. The archive has 4 lesson-only courses, 10 practice-only courses, and 10 mixed courses. This is legitimate and must remain visible in product behavior.
4. Track/course/test foreign-key-style relationships are internally consistent: no orphan lessons, sections, questions, or mismatched test tracks were found.
5. Source boundaries are preserved in storage but can be intentionally dissolved by `/api/quiz/start` when only `track_id` is supplied. The replica must use `practice_test_id` for full source tests and reserve track-wide mixing for an explicitly labelled custom drill.
6. Two course mappings require manual review: a Data Scientist practice course is mapped to `snowpro-core`, and a Data Engineers course is mapped to `advanced-architect`. No reviewed overrides exist in `course_track_overrides`.

## Duplicate And Content Quality Findings

- Question prompts: 28 exact normalized duplicate groups, 57 rows in those groups, and 29 excess copies.
- Cross-boundary duplicates: all 28 groups span tests; 22 groups span courses.
- Conflicting answer keys: 18 duplicate-prompt groups contain more than one `correct_json` value. These cannot be automatically collapsed without option-level/source review.
- Lesson titles: 3 within-course normalized-title groups, 11 rows, 8 excess title copies. They are generic headings such as `Introduction`, so title-only deletion would be unsafe.
- Transcript quality: 1,007 lessons (77.16%) expose generated English study notes; only 298 are classified as transcript-like.
- Question quality: 746 questions have no explanation and 1 has no correct answer. All options/correct-answer JSON values are syntactically valid.
- Practice-test quality: 84 empty shells, 162 section quizzes, 6 practice tests, and 27 full mock exams.

## Immediate Baseline Conclusions

1. The data is large enough for the target product, but displayed counts must distinguish source records from usable records.
2. Storage boundaries are stronger than the current presentation and quiz-start contracts.
3. Exam answer secrecy is not enforced server-side. See [api-inventory.md](./api-inventory.md).
4. The reported slowness is reproducible and concentrated in uncached intelligence calculations and all-at-once lesson rendering. See [performance-risks.md](./performance-risks.md).
5. Production implementation should not begin until the working tree has a recoverable baseline and the database has a verified backup; neither action was performed because this task prohibited mutation.

## Commands Used

The following command families were used. All database inspection used immutable/read-only URI mode.

```bash
git status --short
git branch --show-current
git remote -v
find . -maxdepth ...
rg -n ... app frontend
sed -n ...
nl -ba ...
wc -c -l ...
shasum -a 256 data/snowflake_brain.sqlite
stat -f ... data/snowflake_brain.sqlite data/snowflake_brain.db
sqlite3 'file:...snowflake_brain.sqlite?mode=ro&immutable=1' 'SELECT ...'
/usr/bin/curl -sS http://127.0.0.1:8010/openapi.json
/usr/bin/curl -sS -o /dev/null -w ... http://127.0.0.1:8010/api/...
/usr/bin/jq ...
docker compose ps
docker inspect snowflake-brain-lab ...
docker image inspect ...
lsof -nP -iTCP:8010 -sTCP:LISTEN
```

No `POST`, `PATCH`, or `DELETE` request was sent to the running application.
