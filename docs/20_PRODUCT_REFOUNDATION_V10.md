# Snowflake Brain v10 Product Re-Foundation

This build corrects the product direction after the v8/v9 drift. The application is centered again on the real local course archive and the certification evidence loop:

Video lesson → transcript → mapped skill → related questions → Snowflake lab challenge → mistake repair → readiness evidence.

## Scope implemented

1. Preserve the real video player as the primary Learn experience
   - `frontend/views/video.js` remains the main Learn route.
   - Video playback uses `/api/media?path=<lesson.video_path>`.
   - Course selector, certification selector, lesson outline, transcript cues, practice links, lab links, and mark-complete are kept in one workspace.

2. Fix router asset versioning
   - `frontend/index.html`, `frontend/router.js`, and frontend imports now use `20260630-refoundationv10`.
   - This prevents stale v8/v9 JavaScript from loading after rebuilds.

3. Fix global certification state
   - `frontend/ui.js` now owns normalized active-certification helpers.
   - `frontend/components/topbar.js` normalizes the selected certification from `/api/experience/command-center` and updates the URL with `track_id`.
   - Per-track course selection is stored separately so Cost Optimization course choices do not leak into Data Engineer/Core views.

4. Rebuild Practice as serious Exam Studio
   - `frontend/views/quiz.js` now has diagnostic, adaptive drill, readiness exam, and source-test modes.
   - Added timer, answered/unanswered counts, mark-for-review, question navigator, no explanation until submit, source breakdown, and detailed score report.

5. Preserve Labs as SQL challenge runner
   - `frontend/views/labs.js` keeps the W3Schools/LeetCode-style scenario + worksheet + validation test layout.
   - Solutions remain locked until validation is attempted.

6. Rebuild Readiness as evidence gate
   - `frontend/views/readiness.js` uses `/api/experience/command-center` and the intelligence readiness model.
   - The page focuses on blockers, required evidence, domain weakness, and next actions.

7. Add local-first AI/search fallback
   - `app/routers/ai.py` now streams deterministic local-course answers when `ANTHROPIC_API_KEY` is not set.
   - `frontend/views/ai.js` also falls back to `/api/brain/ask` so the tutor does not appear broken without cloud credentials.

8. Add route smoke tests
   - Router now writes `window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__` after every route render.
   - Added `scripts/smoke_static_routes.mjs` for no-browser stale asset/route checks.
   - Added `scripts/smoke_routes.mjs` for Playwright browser route smoke testing against the running Docker app.

## Validation run

Commands run in this package:

```bash
python3 -m compileall app
python3 -m py_compile app/routers/ai.py app/routers/experience.py
node --check frontend/router.js
node --check frontend/api.js
for f in frontend/views/*.js frontend/components/*.js frontend/app.js frontend/ui.js; do node --check "$f"; done
node scripts/smoke_static_routes.mjs
python3 scripts/smoke_api.py
scripts/package_review.sh 2026-06-30-product-refoundation-v10
python3 scripts/check_package.py
```

The browser Playwright smoke test is included but must be run on the user machine after Docker is up.

```bash
npm i -D playwright
npx playwright install chromium
SNOWFLAKE_BRAIN_BASE_URL=http://localhost:8010 node scripts/smoke_routes.mjs
```
