from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .config import FORCE_HTTPS, SECURITY_RATE_LIMIT_ENABLED


class SecurityBoundaryMiddleware(BaseHTTPMiddleware):
    """Single-process safety net; production CDN/WAF limits remain mandatory."""

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._denials: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if FORCE_HTTPS and request.url.scheme != "https" and request.url.path != "/api/health":
            return RedirectResponse(str(request.url.replace(scheme="https")), status_code=307)

        key = self._client_signal(request)
        bucket, limit, window = self._policy(request)
        if SECURITY_RATE_LIMIT_ENABLED and not self._allow(key, bucket, limit, window):
            return JSONResponse(
                status_code=429,
                content={"detail": {"code": "rate_limited", "message": "Too many requests. Please try again later."}},
                headers={"Retry-After": str(window)},
            )

        response = await call_next(request)
        if response.status_code in {401, 403, 429}:
            self._record_denial(key)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def _client_signal(self, request: Request) -> str:
        peer = request.client.host if request.client else "unknown"
        agent = request.headers.get("user-agent", "")[:256]
        return hashlib.sha256(f"{peer}|{agent}".encode()).hexdigest()

    def _policy(self, request: Request) -> tuple[str, int, int]:
        path = request.url.path
        if path in {"/api/auth/register", "/api/auth/login"}:
            return "auth", 30, 300
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            return "mutation", 300, 60
        if path.startswith("/api/mock/sessions/") or path == "/api/mock/history":
            return "premium_content", 360, 60
        return "general", 900, 60

    def _allow(self, key: str, bucket: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        denial_penalty = self._denial_count(key, now, 300)
        effective_limit = max(5, limit // 2) if denial_penalty >= 20 else limit
        with self._lock:
            values = self._requests[(key, bucket)]
            while values and values[0] <= now - window:
                values.popleft()
            if len(values) >= effective_limit:
                return False
            values.append(now)
            return True

    def _record_denial(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            values = self._denials[key]
            while values and values[0] <= now - 300:
                values.popleft()
            values.append(now)

    def _denial_count(self, key: str, now: float, window: int) -> int:
        with self._lock:
            values = self._denials[key]
            while values and values[0] <= now - window:
                values.popleft()
            return len(values)
