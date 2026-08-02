# Snowflake Brain - v4 Skill Brain + Lab Runner

Last updated: 2026-06-29

## 1. Purpose

v4 starts turning Snowflake Brain from a content browser into a certification training brain.

The app now has three explicit intelligence layers:

1. **Skill Brain** - a certification blueprint that maps Snowflake exam domains to skills, aliases, exam traps, question tags, and objectives.
2. **Lab Runner** - W3Schools-style challenge UI for Snowflake SQL skills: problem, workspace, validation, solution, and next actions.
3. **Readiness Repair** - readiness now includes skill-level weak areas, not only broad counts.

## 2. New Config Files

### `config/certification_skill_map.json`

Defines SnowPro Core skills such as:

- RBAC role hierarchy and least privilege
- Warehouse sizing, suspend/resume, and cost control
- Stages, file formats, and COPY INTO
- Snowpipe and continuous loading
- VARIANT, JSON pathing, and FLATTEN
- Time Travel, Fail-safe, and zero-copy clone
- Streams and tasks for incremental pipelines

Each skill has:

- domain
- objective
- aliases
- question tags
- exam traps
- readiness rules

### `config/snowflake_lab_challenges.json`

Defines guided Snowflake labs:

- Create a Cost-Safe Virtual Warehouse
- Load CSV Data with Stage, File Format, and COPY INTO
- Query Semi-Structured JSON with VARIANT and FLATTEN
- Design Least-Privilege RBAC
- Recover and Clone Data with Time Travel
- Build an Incremental Pipeline with Streams and Tasks

Each lab has:

- problem statement
- scenario
- instructions
- input/context
- expected output
- starter SQL
- validation tests
- hints
- solution SQL
- teardown SQL
- related question tags
- exam traps

## 3. New Backend Modules

### `app/skill_brain.py`

Loads the certification skill map and provides:

- skill flattening
- keyword/alias matching
- skill inference for lessons/questions
- matched skills for arbitrary text

### `app/lab_challenges.py`

Loads lab challenge config and performs offline validation.

Supported validation types:

- `contains_all`
- `contains_any`
- `regex`
- `ordered_contains`
- `minimum_statement_count`

## 4. New API Endpoints

### Skill Brain

```text
GET /api/skills/map
GET /api/skills/summary?track_id=snowpro-core
GET /api/skills/{skill_id}/resources?track_id=snowpro-core
```

### Labs

```text
GET  /api/labs/config
GET  /api/labs
GET  /api/labs/{lab_id}
POST /api/labs/{lab_id}/submit
```

Lab submit payload:

```json
{
  "sql": "CREATE OR REPLACE WAREHOUSE ..."
}
```

Lab submit response:

```json
{
  "passed": false,
  "passed_count": 3,
  "total": 5,
  "score_pct": 60,
  "feedback": "3/5 checks passed. Fix the failed checks, then submit again.",
  "results": []
}
```

## 5. New Labs UX

The Labs page now follows the challenge-runner model:

```text
Left: lab path and skill readiness
Center-left: problem statement, instructions, expected result, hints, exam traps
Center-right: SQL worksheet, run validation, locked solution
Bottom: validation checks and next actions
```

The solution is locked until the learner runs validation at least once.

## 6. Offline vs Live Mode

v4 uses offline validation by default:

```bash
SNOWFLAKE_LABS_MODE=offline
```

Offline mode validates SQL structure and required clauses locally. It does not need Snowflake credentials.

Future live mode can add:

```bash
SNOWFLAKE_LABS_MODE=live
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_ROLE=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_DATABASE=
SNOWFLAKE_SCHEMA=
```

Live mode is intentionally not implemented yet because offline mode is safer for certification prep and does not risk running destructive SQL.

## 7. Readiness Improvements

Readiness now includes a skill brain panel:

- weakest mapped skills
- question count per skill
- attempts per skill
- accuracy per skill
- links to practice and labs

## 8. Verification

Run:

```bash
python3 -m compileall app
node --check frontend/views/labs.js
node --check frontend/views/readiness.js
node --check frontend/api.js
node --check frontend/router.js
scripts/package_review.sh 2026-06-29-skillbrain-v4
python3 scripts/check_package.py dist/snowflake-brain-source-2026-06-29-skillbrain-v4.zip
```

## 9. What v4 Does Not Do Yet

- It does not connect to a live Snowflake account.
- It does not execute SQL.
- It does not auto-map every lesson/question with permanent DB fields yet.
- It does not create a proctored exam simulator.

Those should be v5/v6 work.
