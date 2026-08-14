from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-cert-v26-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "certification.sqlite")

from fastapi.testclient import TestClient  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.main import app  # noqa: E402

run_migrations()
c = TestClient(app)


def ok(value, message):
    if not value:
        raise AssertionError(message)


h = c.get('/api/health')
ok(h.status_code == 200, 'health')
ok(h.json()['architecture'] == 'certification-native-v26', 'architecture')

html = c.get('/').text
ok('app-complete.js' in html, 'app entry')
for name in (
    'styles.css', 'replica.css', 'guide.css', 'guide-study.css', 'mock.css',
    'v26-core.css', 'v26-globe.css', 'v26-pages.css', 'v26-study-new.css',
    'v26-practice-new.css', 'v26-progress.css', 'v26-lookup.css', 'v26-mock.css',
    'v26-start-new.css', 'v26-exam-new.css', 'v26-result-new.css', 'v26-journal.css',
    'v26-footer.css', 'v26-a11y.css',
):
    ok('/static/' + name not in html, 'inactive legacy css ' + name)
for name in (
    'styles/tokens.css', 'styles/utilities.css', 'styles/shell.css', 'styles/home.css',
    'styles/study.css', 'styles/practice.css', 'styles/mock.css', 'styles/content.css',
    'styles/exam.css', 'styles/membership.css', 'styles/responsive.css', 'styles/accessibility.css',
):
    ok('/static/' + name in html, 'canonical css ' + name)

membership_source = (ROOT / 'frontend' / 'views' / 'membership-v26.js').read_text(encoding='utf-8')
for expected in ('$20', '$40', '$100', '$35', 'plus applicable taxes', '20 real practice questions every day', 'Lifetime access to a 100-question Practice Mock'):
    ok(expected in membership_source, 'membership UI contract ' + expected)

world_response = c.get('/static/assets/world-major-land.geojson')
ok(world_response.status_code == 200, 'world geometry served')
world = world_response.json()
ok(world.get('type') == 'Feature', 'world geometry feature')
ok(world.get('geometry', {}).get('type') == 'MultiPolygon', 'world geometry multipolygon')
ok(len(world.get('geometry', {}).get('coordinates', [])) >= 4, 'world geometry polygons')

globe_source = (ROOT / 'frontend' / 'components' / 'globe.js').read_text(encoding='utf-8')
ok('const LOCATIONS' not in globe_source, 'no seeded fake globe locations')
ok('getGlobeActivity' in globe_source, 'globe uses activity api')
ok('world-major-land.geojson' in globe_source, 'globe uses real local geography')
ok('ROTATION_PERIOD_MS' in globe_source, 'globe rotation configured')
ok('buildLandDots' in globe_source, 'globe derives pointillist land from real geometry')

activity = c.get('/api/activity/globe')
ok(activity.status_code == 200, 'activity globe endpoint')
activity_body = activity.json()
ok(activity_body['mode'] == 'fallback', 'empty activity uses truthful fallback')
ok(activity_body['locations'] == [], 'fallback has no fabricated locations')
ok(activity_body['minimum_public_count'] == 3, 'privacy threshold')

# A bucket below the public threshold must remain private; an aggregated bucket at
# the threshold may be returned. These are test-only rows in the isolated database.
with connect() as conn:
    conn.execute(
        "INSERT INTO learner_activity_aggregates(bucket_key,label,latitude,longitude,active_count,observed_at) VALUES (?,?,?,?,?,datetime('now'))",
        ('private-test', 'Private Test', 1.0, 1.0, 2),
    )
    conn.execute(
        "INSERT INTO learner_activity_aggregates(bucket_key,label,latitude,longitude,active_count,observed_at) VALUES (?,?,?,?,?,datetime('now'))",
        ('public-test', 'Public Test', 10.0, 20.0, 3),
    )
activity_live = c.get('/api/activity/globe').json()
ok(activity_live['mode'] == 'live', 'aggregated activity live mode')
ok(activity_live['active_total'] == 3, 'only public aggregate counted')
ok([row['bucket_key'] for row in activity_live['locations']] == ['public-test'], 'sub-threshold bucket hidden')

sm = c.get('/api/skills/map').json()
catalog = c.get('/api/skills/catalog').json()['official_certifications']
ok([(x['id'], x['exam_code']) for x in catalog] == [('snowpro-core', 'COF-C03'), ('advanced-data-engineer', 'DEA-C02'), ('advanced-architect', 'ARA-C01')], 'exact focused certification catalog')
ok(all(x['id'] not in {'cost-optimization', 'cortex-genai'} for x in catalog), 'no fake certification paths')
cert = next(x for x in sm['certifications'] if x['id'] == 'snowpro-core')
domains = cert['domains']
ok(len(domains) == 5, 'domains')
ok([int(x['weight']) for x in domains] == [31, 20, 18, 21, 10], 'weights')
ok(sum(len(x['skills']) for x in domains) == 19, 'tasks')

cfg = c.get('/api/mock/config?track_id=snowpro-core').json()
ok(cfg['quick_mock']['question_count'] == 30, 'quick count')
ok(cfg['quick_mock']['time_limit_minutes'] == 45, 'quick time')
ok(cfg['full_mock']['question_count'] == 100, 'full count')
ok(cfg['full_mock']['time_limit_minutes'] == 120, 'full time')
ok(cfg['pass_scaled_score'] == 750, 'threshold')

ok(c.get('/api/auth/me').json() == {'authenticated': False, 'candidate': None, 'membership': None}, 'guest membership state')
ok(c.post('/api/mock/sessions', json={'track_id': 'snowpro-core', 'mode': 'quick-mock'}).status_code == 401, 'guest mock gate')
signup = c.post('/api/auth/register', json={'display_name': 'V26 Smoke Candidate', 'email': 'v26-smoke@example.com', 'password': 'v26-smoke-password'})
ok(signup.status_code == 201 and signup.json()['membership']['tier'] == 'free', signup.text)
ok(c.post('/api/mock/sessions', json={'track_id': 'snowpro-core', 'mode': 'quick-mock'}).status_code == 403, 'free mock gate')
with connect() as conn:
    candidate_id = signup.json()['candidate']['id']
    conn.execute("INSERT INTO candidate_memberships(candidate_id,tier,plan_code,status,source) VALUES (?, 'premium','premium_20','active','smoke_fixture')", (candidate_id,))
ok(c.get('/api/auth/me').json()['membership']['tier'] == 'premium', 'server Premium state')

s = c.post('/api/mock/sessions', json={'track_id': 'snowpro-core', 'mode': 'quick-mock'})
ok(s.status_code == 200, s.text)
session = s.json()
ok(len(session['questions']) == 30, 'mock questions')
q = session['questions'][0]
ok('correct' not in q and 'explanation' not in q, 'answer leak')
ok(c.put(f"/api/mock/sessions/{session['session_id']}/answers/{q['id']}", json={'selected': [0]}).status_code == 200, 'autosave')
ok(c.put(f"/api/mock/sessions/{session['session_id']}/questions/{q['id']}/flag", json={'flagged': True}).status_code == 200, 'flag')
r = c.get(f"/api/mock/sessions/{session['session_id']}").json()
rq = next(x for x in r['questions'] if x['id'] == q['id'])
ok(rq['selected'] == [0] and rq['flagged'], 'resume')
res = c.post(f"/api/mock/sessions/{session['session_id']}/submit", json={'reason': 'learner'})
ok(res.status_code == 200, res.text)
result = res.json()
ok(len(result['reviews']) == 30, 'review')
ok('correct' in result['reviews'][0], 'grading reveal')

cancel_candidate = c.post('/api/mock/sessions', json={'track_id': 'snowpro-core', 'mode': 'quick-mock'})
ok(cancel_candidate.status_code == 200, 'cancel candidate start')
cancel_id = cancel_candidate.json()['session_id']
cancel = c.post(f'/api/mock/session-control/{cancel_id}/cancel', json={})
ok(cancel.status_code == 200 and cancel.json()['status'] == 'cancelled', 'discard sitting')

f = c.post('/api/feedback', json={'title': 'V26 smoke', 'category': 'other', 'description': 'smoke', 'route': '#/home', 'track_id': 'snowpro-core'})
ok(f.status_code == 200 and f.json()['ok'], 'feedback')

print('V26 functional + visual-contract smoke: PASS')
