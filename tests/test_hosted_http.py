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
        assert command[:4] == ["vercel", "--scope", "team-slug", "curl"]
        assert "test-token" not in command
        assert "--location" not in command
        assert check is False
        assert capture_output is True
        assert timeout > 0
        headers_path = Path(command[command.index("--dump-header") + 1])
        body_path = Path(command[command.index("--output") + 1])
        headers_path.write_bytes(
            b"HTTP/2 200\r\ncontent-type: application/json\r\ncache-control: no-store\r\n\r\n"
        )
        body_path.write_bytes(b'{"status":"ready"}')
        return subprocess.CompletedProcess(command, 0, stdout=b"200", stderr=b"")

    monkeypatch.setattr(hosted_http.subprocess, "run", fake_run)
    client = httpx.Client(follow_redirects=True, timeout=5.0)
    response = hosted_http.get(client, "https://snowflakecertificationguide-bpsukc6cm-rrahul0904-5013s-projects.vercel.app/api/ready")

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
            hosted_http.get(client, "https://snowflakecertificationguide-bpsukc6cm-rrahul0904-5013s-projects.vercel.app/api/health")
        except RuntimeError as exc:
            assert str(exc).startswith("vercel_cli_request_failed:protection_bypass_unavailable:")
        else:
            raise AssertionError("expected a sanitized Vercel CLI failure")
    finally:
        client.close()


def test_security_target_allowlist_rejects_untrusted_origins() -> None:
    for url in (
        "https://other-project.vercel.app",
        "http://snowflakecertificationguide.vercel.app",
        "https://user@snowflakecertificationguide.vercel.app",
        "https://snowflakecertificationguide.vercel.app:8443",
        "https://snowflakecertificationguide.vercel.app/path",
        "https://snowflakecertificationguide.vercel.app/?x=1",
    ):
        try:
            hosted_http.validate_security_base_url(url)
        except RuntimeError as exc:
            assert str(exc) == "hosted_target_rejected:unapproved_project_origin"
        else:
            raise AssertionError(f"expected target rejection for {url}")


def test_request_allowlist_blocks_before_vercel_cli(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL_TOKEN", "test-token")
    monkeypatch.setattr(
        hosted_http.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Vercel CLI must not run")),
    )
    client = httpx.Client(timeout=5.0)
    try:
        try:
            hosted_http.get(client, "https://attacker.vercel.app/api/health")
        except RuntimeError as exc:
            assert str(exc) == "hosted_target_rejected:unapproved_project_origin"
        else:
            raise AssertionError("expected target rejection")
    finally:
        client.close()


def test_protected_redirect_is_returned_without_following(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL_TOKEN", "test-token")

    def fake_run(command, *, check, capture_output, timeout):
        assert "--location" not in command
        headers_path = Path(command[command.index("--dump-header") + 1])
        body_path = Path(command[command.index("--output") + 1])
        headers_path.write_bytes(
            b"HTTP/2 302\r\nlocation: https://attacker.example/collect\r\n\r\n"
        )
        body_path.write_bytes(b"")
        return subprocess.CompletedProcess(command, 0, stdout=b"302", stderr=b"")

    monkeypatch.setattr(hosted_http.subprocess, "run", fake_run)
    client = httpx.Client(follow_redirects=True, timeout=5.0)
    try:
        response = hosted_http.get(
            client, "https://snowflakecertificationguide.vercel.app/api/health"
        )
        assert response.status_code == 302
        assert response.headers["location"] == "https://attacker.example/collect"
    finally:
        client.close()


def test_local_static_probe_target_is_allowed_without_vercel_token(monkeypatch) -> None:
    monkeypatch.delenv("VERCEL_TOKEN", raising=False)
    hosted_http.validate_security_base_url("http://127.0.0.1:8000", allow_local=True)
    client = httpx.Client(timeout=0.1)
    try:
        try:
            hosted_http.get(client, "http://127.0.0.1:8000/api/health")
        except httpx.ConnectError:
            pass
    finally:
        client.close()
