from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import hosted_http


def test_vercel_get_uses_protected_request_and_returns_response(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL_TOKEN", "test-token")
    monkeypatch.setenv("VERCEL_SCOPE", "team-slug")

    def fake_run(command, *, check, capture_output, timeout):
        assert command[:5] == ["vercel", "--token", "test-token", "--scope", "team-slug"]
        assert check is False
        assert capture_output is True
        assert timeout > 0
        headers_path = Path(command[command.index("--dump-header") + 1])
        body_path = Path(command[command.index("--output") + 1])
        headers_path.write_bytes(
            b"HTTP/2 302\r\nlocation: https://login.vercel.com/\r\n\r\n"
            b"HTTP/2 200\r\ncontent-type: application/json\r\ncache-control: no-store\r\n\r\n"
        )
        body_path.write_bytes(b'{"status":"ready"}')
        return subprocess.CompletedProcess(command, 0, stdout=b"200", stderr=b"")

    monkeypatch.setattr(hosted_http.subprocess, "run", fake_run)
    client = httpx.Client(follow_redirects=True, timeout=5.0)
    response = hosted_http.get(client, "https://snowflakecertificationguide-test.vercel.app/api/ready")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"status": "ready"}
    client.close()


def test_vercel_get_redacts_cli_error_to_safe_classification(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL_TOKEN", "test-token")
    monkeypatch.setattr(
        hosted_http.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, stdout=b"", stderr=b"Deployment protection bypass unavailable for project"
        ),
    )

    client = httpx.Client(timeout=5.0)
    try:
        try:
            hosted_http.get(client, "https://snowflakecertificationguide-test.vercel.app/api/health")
        except RuntimeError as exc:
            assert str(exc) == "vercel_cli_request_failed:protection_bypass_unavailable"
        else:
            raise AssertionError("expected a sanitized Vercel CLI failure")
    finally:
        client.close()
