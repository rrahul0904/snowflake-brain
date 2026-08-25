from __future__ import annotations

import re

from starlette.requests import Request

from .observability import (
    ObservabilityMiddleware as BaseObservabilityMiddleware,
    record_auth_failure,
    record_exam_event,
    record_stripe_webhook_failure,
)


_SESSION_SUBMIT_RE = re.compile(r"^/api/mock/sessions/[^/]+/submit$")


class ObservabilityMiddleware(BaseObservabilityMiddleware):
    """Feature-signal middleware resilient to framework route-template changes.

    Starlette 1.6 reports APIRouter route templates without the app-level
    `/api` include prefix (for example `/auth/login`). The actual request path
    remains `/api/auth/login`. Operational/security feature signals therefore
    key off the normalized request URL, while the base middleware continues to
    own request IDs, generic HTTP metrics, latency, logs, and exception capture.
    """

    @staticmethod
    def _record_feature_signal(request: Request, route: str, status_code: int) -> None:
        method = request.method.upper()
        path = str(request.url.path or "/")
        failed = status_code >= 400

        if method == "POST" and path == "/api/auth/login" and status_code == 401:
            record_auth_failure("invalid_credentials")
        if method == "POST" and path == "/api/billing/webhook" and failed:
            record_stripe_webhook_failure("http_rejected" if status_code < 500 else "processing_error")
        if method == "POST" and path == "/api/mock/sessions":
            record_exam_event("start", "failure" if failed else "success")
        if method == "POST" and _SESSION_SUBMIT_RE.fullmatch(path):
            record_exam_event("submit", "failure" if failed else "success")
