from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .auth import COOKIE_NAME, candidate_for_token
from .config import FORCE_HTTPS, SECURITY_RATE_LIMIT_ENABLED


SYSTEM_PROBE_API_EXACT = {
    "/api/health",
    "/api/ready",
}
PUBLIC_API_EXACT = SYSTEM_PROBE_API_EXACT | {
    "/api/activity/globe",
    "/api/feedback",
}
PUBLIC_API_PREFIXES = (
    "/api/auth/",
    "/api/billing/",
)
PUBLIC_STATIC_VIEWS = {
    "/static/views/home-v26.js",
    "/static/views/membership-v26.js",
    "/static/views/info-v26.js",
}


class SecurityBoundaryMiddleware(BaseHTTPMiddleware):
    """Single-process safety net; production CDN/WAF limits remain mandatory."""

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._denials: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Infrastructure liveness/readiness probes need to remain callable from
        # the local container/network even when public application traffic is
        # forced to HTTPS at the edge. They expose no candidate data.
        if FORCE_HTTPS and request.url.scheme != "https" and request.url.path not in SYSTEM_PROBE_API_EXACT:
            return RedirectResponse(str(request.url.replace(scheme="https")), status_code=307)

        if self._cross_site_mutation(request):
            return JSONResponse(
                status_code=403,
                content={"detail": {"code": "cross_site_request_blocked", "message": "Cross-site state changes are not allowed."}},
            )

        key = self._client_signal(request)
        bucket, limit, window = self._policy(request)
        if SECURITY_RATE_LIMIT_ENABLED and not self._allow(key, bucket, limit, window):
            return JSONResponse(
                status_code=429,
                content={"detail": {"code": "rate_limited", "message": "Too many requests. Please try again later."}},
                headers={"Retry-After": str(window)},
            )

        protected = self._requires_candidate(request)
        if protected:
            candidate = candidate_for_token(request.cookies.get(COOKIE_NAME))
            if not candidate:
                self._record_denial(key)
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": {
                            "code": "authentication_required",
                            "message": "Create a free candidate account or sign in to access certification content.",
                        }
                    },
                    headers={"Cache-Control": "private, no-store"},
                )
            request.state.candidate = candidate

        response = await call_next(request)
        if response.status_code in {401, 403, 429}:
            self._record_denial(key)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if protected or request.url.path.startswith(("/api/auth", "/api/billing", "/api/mock")):
            response.headers["Cache-Control"] = "private, no-store"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def _requires_candidate(self, request: Request) -> bool:
        path = request.url.path
        if path.startswith("/static/views/"):
            return path not in PUBLIC_STATIC_VIEWS
        if not path.startswith("/api/"):
            return False
        if path in PUBLIC_API_EXACT:
            return False
        return not any(path.startswith(prefix) for prefix in PUBLIC_API_PREFIXES)

    def _cross_site_mutation(self, request: Request) -> bool:
        if request.method in {"GET", "HEAD", "OPTIONS"} or request.url.path == "/api/billing/webhook":
            return False
        # Cookie-authenticated browser mutations must remain same-origin. API and
        # automated clients without browser fetch metadata are allowed to rely on
        # the normal authentication boundary.
        if not request.cookies.get(COOKIE_NAME):
            return False
        fetch_site = (request.headers.get("sec-fetch-site") or "").lower()
        if fetch_site == "cross-site":
            return True
        origin = request.headers.get("origin")
        if not origin:
            return False
        parsed = urlparse(origin)
        request_host = request.headers.get("host", "")
        return bool(parsed.netloc and parsed.netloc != request_host)

    def _client_signal(self, request: Request) -> str:
        peer = request.client.host if request.client else "unknown"
        agent = request.headers.get("user-agent", "")[:256]
        return hashlib.sha256(f"{peer}|{agent}".encode()).hexdigest()

    def _policy(self, request: Request) -> tuple[str, int, int]:
        path = request.url.path
        if path in {"/api/auth/register", "/api/auth/login", "/api/auth/google/link"}:
            return "auth", 30, 300
        if path == "/api/auth/google/start":
            return "oauth_start", 30, 300
        if path == "/api/billing/checkout":
            return "billing_checkout", 20, 300
        if path == "/api/billing/webhook":
            return "billing_webhook", 1200, 60
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
