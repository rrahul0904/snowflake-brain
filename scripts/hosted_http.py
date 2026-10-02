"""HTTP helpers for hosted probes that may target Vercel-protected deployments."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def _vercel_cli_get(url: str, *, follow_redirects: bool, timeout: float) -> httpx.Response:
    token = os.environ.get("VERCEL_TOKEN", "")
    scope = os.environ.get("VERCEL_SCOPE", "")
    with tempfile.TemporaryDirectory(prefix="vercel-probe-") as temp_dir:
        headers_path = Path(temp_dir) / "headers.txt"
        body_path = Path(temp_dir) / "body.bin"
        curl_args = ["--silent", "--show-error"]
        if follow_redirects:
            curl_args.append("--location")
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
        command = ["vercel", "--token", token]
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
            # Do not include CLI output: it can contain deployment or account details.
            diagnostic = result.stderr.decode("utf-8", "ignore").lower()
            if "protection bypass" in diagnostic or "deployment protection" in diagnostic:
                reason = "protection_bypass_unavailable"
            elif "not authorized" in diagnostic or "unauthorized" in diagnostic or "401" in diagnostic:
                reason = "vercel_authorization_denied"
            elif "team" in diagnostic or "scope" in diagnostic:
                reason = "vercel_team_scope_denied"
            else:
                reason = "vercel_cli_nonzero_exit"
            raise RuntimeError(f"vercel_cli_request_failed:{reason}")

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
    """Use Vercel's authenticated protection bypass only for Vercel deployments."""
    host = (urlsplit(url).hostname or "").lower()
    if os.environ.get("VERCEL_TOKEN") and host.endswith(".vercel.app"):
        return _vercel_cli_get(url, follow_redirects=client.follow_redirects, timeout=client.timeout.read or 20.0)
    return client.get(url)
