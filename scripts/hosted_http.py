"""HTTP helpers for hosted probes that may target Vercel-protected deployments."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import httpx

_PRODUCTION_HOST = "snowflakecertificationguide.vercel.app"
_PREVIEW_HOST = re.compile(
    r"snowflakecertificationguide-[a-z0-9]+-rrahul0904-5013s-projects\.vercel\.app\Z"
)


def is_approved_host(host: str) -> bool:
    host = host.lower().rstrip(".")
    return host == _PRODUCTION_HOST or _PREVIEW_HOST.fullmatch(host) is not None


def _is_loopback_http_url(parsed) -> bool:
    return (
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 8000)
        and not parsed.query
        and not parsed.fragment
    )


def validate_security_base_url(url: str, *, allow_local: bool = False) -> None:
    """Reject non-project targets before a workflow can use Vercel credentials."""
    try:
        parsed = urlsplit(url)
        valid = (
            parsed.scheme == "https"
            and parsed.username is None
            and parsed.password is None
            and parsed.port is None
            and parsed.path in ("", "/")
            and not parsed.query
            and not parsed.fragment
            and is_approved_host(parsed.hostname or "")
        ) or (
            allow_local
            and _is_loopback_http_url(parsed)
            and parsed.path in ("", "/")
        )
    except ValueError:
        valid = False
    if not valid:
        raise RuntimeError("hosted_target_rejected:unapproved_project_origin")


def _validate_request_url(url: str, *, allow_local: bool = False) -> str:
    try:
        parsed = urlsplit(url)
        valid = (
            parsed.scheme == "https"
            and parsed.username is None
            and parsed.password is None
            and parsed.port is None
            and is_approved_host(parsed.hostname or "")
        ) or (allow_local and _is_loopback_http_url(parsed))
    except ValueError:
        valid = False
        parsed = urlsplit("https://invalid")
    if not valid:
        raise RuntimeError("hosted_target_rejected:unapproved_project_origin")
    return (parsed.hostname or "").lower()


def _vercel_cli_get(url: str, *, timeout: float) -> httpx.Response:
    scope = os.environ.get("VERCEL_SCOPE", "")
    with tempfile.TemporaryDirectory(prefix="vercel-probe-") as temp_dir:
        headers_path = Path(temp_dir) / "headers.txt"
        body_path = Path(temp_dir) / "body.bin"
        curl_args = ["--silent", "--show-error"]
        curl_args.extend(
            [
                "--dump-header",
                str(headers_path),
                "--output",
                str(body_path),
                "--write-out",
                "%{http_code}",
            ]
        )
        # Vercel CLI reads VERCEL_TOKEN from the environment; do not put it in argv.
        command = ["vercel"]
        if scope:
            command.extend(["--scope", scope])
        command.extend(["curl", url, "--", *curl_args])
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"vercel_cli_request_error:{type(exc).__name__}") from None

        status_match = re.search(rb"(?:^|\s)(\d{3})\s*$", result.stdout)
        if result.returncode != 0 or status_match is None:
            diagnostic = result.stderr.decode("utf-8", "ignore")
            classification = diagnostic.lower()
            if "protection bypass" in classification or "deployment protection" in classification:
                reason = "protection_bypass_unavailable"
            elif "not authorized" in classification or "unauthorized" in classification or "401" in classification:
                reason = "vercel_authorization_denied"
            elif "team" in classification or "scope" in classification:
                reason = "vercel_team_scope_denied"
            else:
                reason = "vercel_cli_nonzero_exit"
            # Keep a short clue for diagnosis while stripping values that could
            # carry authentication material from CLI diagnostics.
            safe_diagnostic = diagnostic.splitlines()[0][:180] if diagnostic else ""
            token = os.environ.get("VERCEL_TOKEN", "")
            if token:
                safe_diagnostic = safe_diagnostic.replace(token, "[redacted]")
            safe_diagnostic = re.sub(
                r"(?i)(authorization\s*:\s*bearer\s+|x-vercel-protection-bypass\s*[:=]\s*)[^\s,;]+",
                r"\1[redacted]",
                safe_diagnostic,
            )
            raise RuntimeError(f"vercel_cli_request_failed:{reason}:{safe_diagnostic}")

        raw_headers = headers_path.read_bytes() if headers_path.exists() else b""
        blocks: list[bytes] = []
        for match in re.finditer(rb"(?m)^HTTP/[^\r\n]+\r?\n", raw_headers):
            end = raw_headers.find(b"\r\n\r\n", match.start())
            if end < 0:
                end = raw_headers.find(b"\n\n", match.start())
            if end >= 0:
                blocks.append(raw_headers[match.start() : end])
        response_headers: dict[str, str] = {}
        if blocks:
            lines = blocks[-1].decode("latin-1").replace("\r\n", "\n").split("\n")
            for line in lines[1:]:
                name, separator, value = line.partition(":")
                if separator:
                    response_headers[name.strip()] = value.strip()

        content = body_path.read_bytes() if body_path.exists() else b""
        return httpx.Response(
            int(status_match.group(1)),
            headers=response_headers,
            content=content,
            request=httpx.Request("GET", url),
        )


def get(client: httpx.Client, url: str) -> httpx.Response:
    """Use the bypass only on this project's allowlisted origins, without redirects."""
    has_vercel_token = bool(os.environ.get("VERCEL_TOKEN"))
    _validate_request_url(url, allow_local=not has_vercel_token)
    if has_vercel_token:
        return _vercel_cli_get(url, timeout=client.timeout.read or 20.0)
    return client.get(url)
