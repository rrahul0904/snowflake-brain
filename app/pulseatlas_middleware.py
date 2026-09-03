from __future__ import annotations

import os
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_PROJECT = {
    "organizationId": "portfolio_primary",
    "projectId": "proj_snowflake_brain",
    "projectSlug": "snowflake-brain",
}
_MOCK_SUBMIT = re.compile(r"^/api/mock/sessions/\d+/submit$")


def _environment() -> str:
    value = os.getenv("PULSEATLAS_ENVIRONMENT", "production")
    return value if value in {"development", "preview", "production"} else "production"


def event_for_request(method: str, path: str, status_code: int) -> tuple[str, str, dict[str, Any]] | None:
    if status_code >= 400:
        return None
    method = method.upper()
    if method == "GET" and path == "/api/health":
        return ("health_check", "health", {"component": "snowflake-brain", "status": "ok"})
    if method == "POST" and path == "/api/quiz/grade":
        return ("practice_session_completed", "product", {"mode": "practice"})
    if method == "POST" and _MOCK_SUBMIT.fullmatch(path):
        return ("mock_completed", "product", {})
    return None


def _post(event_name: str, category: str, properties: dict[str, Any]) -> None:
    endpoint = os.getenv("PULSEATLAS_ENDPOINT", "").strip()
    write_key = os.getenv("PULSEATLAS_WRITE_KEY", "").strip()
    if not endpoint or not write_key:
        return
    try:
        url = httpx.URL(endpoint)
        if url.scheme != "https" and url.host not in {"localhost", "127.0.0.1"}:
            return
        httpx.post(
            endpoint,
            headers={"content-type": "application/json", "x-pulseatlas-write-key": write_key},
            json={
                "id": f"evt_{uuid.uuid4()}",
                "schemaVersion": 1,
                **_PROJECT,
                "environment": _environment(),
                "eventName": event_name,
                "eventCategory": category,
                "occurredAt": datetime.now(timezone.utc).isoformat(),
                "properties": properties,
            },
            timeout=1.5,
        )
    except Exception:
        # Portfolio observability is intentionally fail-open.
        return


def dispatch(event: tuple[str, str, dict[str, Any]] | None) -> None:
    if not event:
        return
    threading.Thread(target=_post, args=event, daemon=True, name="pulseatlas-sink").start()


class PulseAtlasMiddleware(BaseHTTPMiddleware):
    """Emit only route/status-derived events; never inspect request/response bodies."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        dispatch(event_for_request(request.method, request.url.path, response.status_code))
        return response
