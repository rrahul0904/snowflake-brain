from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.postgres_backend import _rewrite_sql

ROOT = Path(__file__).resolve().parent.parent


def test_postgres_datetime_compatibility() -> None:
    cases = {
        "SELECT datetime('now') AS now": ["CURRENT_TIMESTAMP"],
        "SELECT datetime(due_at) FROM candidate_srs_state": ["CAST(due_at AS TIMESTAMPTZ)"],
        "SELECT 1 WHERE datetime(last_seen_at) < datetime('now','-5 minutes')": [
            "CAST(last_seen_at AS TIMESTAMPTZ)",
            "CURRENT_TIMESTAMP - INTERVAL '5 minutes'",
        ],
        "SELECT 1 WHERE datetime(expires_at) > datetime(?)": [
            "CAST(expires_at AS TIMESTAMPTZ)",
            "CAST(%s AS TIMESTAMPTZ)",
        ],
    }
    for source, expected_fragments in cases.items():
        rewritten = _rewrite_sql(source)
        for expected in expected_fragments:
            assert expected in rewritten, (source, rewritten)
        assert "datetime(" not in rewritten.lower(), (source, rewritten)


def test_first_paint_does_not_wait_for_auth() -> None:
    source = (ROOT / "frontend" / "app-complete.js").read_text(encoding="utf-8")
    route_index = source.index("await handleRoute()")
    auth_index = source.index("refreshCandidate({notify:true})")
    assert route_index < auth_index, "candidate bootstrap must run after the first route paint"
    assert "await refreshCandidate().catch" not in source
    assert (
        'window.addEventListener("candidate-change",()=>{renderCandidateAccess();renderNav();handleRoute()})'
        in source
    )


def test_static_frontend_build() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert config.get("buildCommand") == "python3 build_vercel_static.py"

    subprocess.run([sys.executable, "build_vercel_static.py"], cwd=ROOT, check=True)
    index = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
    assert index.count('rel="stylesheet"') == 1
    assert "/static/styles/app.bundle.css" in index
    assert "/static/app-complete.js" in index

    bundle = ROOT / "public" / "static" / "styles" / "app.bundle.css"
    assert bundle.is_file()
    text = bundle.read_text(encoding="utf-8")
    assert "tokens.css" in text
    assert "admin-operations.css" in text


if __name__ == "__main__":
    test_postgres_datetime_compatibility()
    test_first_paint_does_not_wait_for_auth()
    test_static_frontend_build()
    print("Launch performance contract passed.")
