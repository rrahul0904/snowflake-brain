from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-cert-v26-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "certification.sqlite")

from fastapi.testclient import TestClient  # noqa: E402
from app.database import run_migrations  # noqa: E402
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
for name in ('styles.css', 'replica.css', 'guide.css', 'guide-study.css', 'mock.css'):
    ok('/static/' + name not in html, 'legacy css ' + name)
sm = c.get('/api/skills/map').json()
cert = next(x for x in sm['certifications'] if x['id'] == 'snowpro-core')
domains = cert['domains']
ok(len(domains) == 5, 'domains')
ok([int(x['weight']) for x in domains] == [31, 20, 18, 21, 10], 'weights')
ok(sum(len(x['skills']) for x in domains) == 19, 'tasks')
cfg = c.get('/api/mock/config?track_id=snowpro-core').json()
ok(cfg['quick_mock']['question_count'] == 30, 'quick count')
ok(cfg['full_mock']['question_count'] == 100, 'full count')
ok(cfg['pass_scaled_score'] == 750, 'threshold')
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
f = c.post('/api/feedback', json={'title': 'V26 smoke', 'category': 'other', 'description': 'smoke', 'route': '#/home', 'track_id': 'snowpro-core'})
ok(f.status_code == 200 and f.json()['ok'], 'feedback')
print('V26 functional smoke: PASS')
