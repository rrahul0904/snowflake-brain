from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .config import (
    DATABASE_BACKEND,
    OBSERVABILITY_5XX_ALERT_THRESHOLD,
    OBSERVABILITY_ALERT_COOLDOWN_SECONDS,
    OBSERVABILITY_ALERT_WEBHOOK_URL,
    OBSERVABILITY_AUTH_FAILURE_ALERT_THRESHOLD,
    OBSERVABILITY_ENABLED,
    OBSERVABILITY_ERROR_WEBHOOK_URL,
    OBSERVABILITY_LOG_LEVEL,
    OBSERVABILITY_MAX_LATENCY_SAMPLES,
    OBSERVABILITY_WINDOW_SECONDS,
)


REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
_STARTED_AT = time.monotonic()
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_DYNAMIC_SEGMENT_RE = re.compile(r"/(?:\d+|[0-9a-fA-F]{16,}|[0-9a-fA-F-]{32,})(?=/|$)")
_SENSITIVE_KEY_PARTS = {
    "password",
    "secret",
    "authorization",
    "cookie",
    "token",
    "signature",
    "credential",
    "api_key",
    "apikey",
    "stripe_secret",
    "answer",
    "selected",
}
_ALLOWED_LOG_SCALARS = (str, int, float, bool, type(None))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_key(key: Any) -> str:
    return str(key or "")[:120]


def _key_is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def redact(value: Any, *, key: str = "") -> Any:
    """Recursively remove secrets/credentials before logs or external sinks.

    Operational logs deliberately do not contain request bodies, query strings,
    candidate email addresses, passwords, selected answers, bearer credentials,
    cookies, or provider secrets. This helper is also applied to explicitly
    emitted operational events as a second safety boundary.
    """
    if _key_is_sensitive(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {_safe_key(k): redact(v, key=_safe_key(k)) for k, v in list(value.items())[:50]}
    if isinstance(value, (list, tuple, set)):
        return [redact(item, key=key) for item in list(value)[:50]]
    if isinstance(value, _ALLOWED_LOG_SCALARS):
        if isinstance(value, str):
            return value[:1000]
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return str(value)
        return value
    return f"<{type(value).__name__}>"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": _utc_now(),
            "level": record.levelname.lower(),
            "event": getattr(record, "event", record.getMessage()),
            "request_id": getattr(record, "request_id", REQUEST_ID.get()),
            "fields": redact(getattr(record, "fields", {})),
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("snowflake.observability")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(getattr(logging, OBSERVABILITY_LOG_LEVEL.upper(), logging.INFO))
    return logger


_LOGGER = _build_logger()


def log_event(event: str, *, level: int = logging.INFO, request_id: str | None = None, **fields: Any) -> None:
    if not OBSERVABILITY_ENABLED:
        return
    _LOGGER.log(
        level,
        event,
        extra={
            "event": str(event)[:160],
            "request_id": request_id or REQUEST_ID.get(),
            "fields": redact(fields),
        },
    )


class MetricRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counters: dict[str, int] = defaultdict(int)
        self._latencies: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=OBSERVABILITY_MAX_LATENCY_SAMPLES)
        )
        self._recent: dict[str, deque[float]] = defaultdict(deque)
        self._last_alert: dict[str, float] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[str(name)] += int(amount)

    def observe(self, name: str, duration_ms: float) -> None:
        with self._lock:
            self._latencies[str(name)].append(max(0.0, float(duration_ms)))

    def recent_failure(self, kind: str, *, threshold: int) -> int:
        now = time.monotonic()
        with self._lock:
            values = self._recent[kind]
            while values and values[0] <= now - OBSERVABILITY_WINDOW_SECONDS:
                values.popleft()
            values.append(now)
            count = len(values)
        if threshold > 0 and count >= threshold:
            emit_alert(
                kind,
                severity="critical",
                occurrences=count,
                window_seconds=OBSERVABILITY_WINDOW_SECONDS,
            )
        return count

    def allow_alert(self, alert_type: str) -> bool:
        now = time.monotonic()
        with self._lock:
            previous = self._last_alert.get(alert_type, 0.0)
            if previous and previous > now - OBSERVABILITY_ALERT_COOLDOWN_SECONDS:
                return False
            self._last_alert[alert_type] = now
            return True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(sorted(self._counters.items()))
            latency_copy = {name: list(values) for name, values in self._latencies.items()}
            recent_copy = {name: list(values) for name, values in self._recent.items()}
        latency: dict[str, Any] = {}
        for name, values in sorted(latency_copy.items()):
            if not values:
                continue
            ordered = sorted(values)
            latency[name] = {
                "count": len(ordered),
                "p50_ms": round(_percentile(ordered, 0.50), 2),
                "p95_ms": round(_percentile(ordered, 0.95), 2),
                "max_ms": round(max(ordered), 2),
            }
        now = time.monotonic()
        recent = {
            name: sum(1 for stamp in values if stamp > now - OBSERVABILITY_WINDOW_SECONDS)
            for name, values in sorted(recent_copy.items())
        }
        return {
            "status": "ok",
            "uptime_seconds": round(max(0.0, now - _STARTED_AT), 3),
            "window_seconds": OBSERVABILITY_WINDOW_SECONDS,
            "counters": counters,
            "latency": latency,
            "recent_failures": recent,
        }

    def reset_for_tests(self) -> None:
        with self._lock:
            self._counters.clear()
            self._latencies.clear()
            self._recent.clear()
            self._last_alert.clear()


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    index = min(len(values) - 1, max(0, math.ceil(len(values) * fraction) - 1))
    return values[index]


METRICS = MetricRegistry()


def metrics_snapshot() -> dict[str, Any]:
    return METRICS.snapshot()


def reset_observability_for_tests() -> None:
    METRICS.reset_for_tests()


def request_id_from_header(value: str | None) -> str:
    candidate = str(value or "").strip()
    if candidate and _REQUEST_ID_RE.fullmatch(candidate):
        return candidate
    return uuid.uuid4().hex


def _safe_route(request: Request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if template:
        return str(template)[:240]
    path = str(request.url.path or "/")
    return _DYNAMIC_SEGMENT_RE.sub("/{id}", path)[:240]


def _event_payload(event: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": _utc_now(),
        "event": event,
        "request_id": REQUEST_ID.get(),
        "fields": redact(fields),
    }


def _post_sink(url: str, payload: dict[str, Any]) -> None:
    if not url:
        return
    try:
        httpx.post(url, json=payload, timeout=2.0)
    except Exception as exc:  # never let telemetry break candidate traffic
        log_event("observability_sink_failed", level=logging.WARNING, sink="http", error_type=type(exc).__name__)


def _dispatch_sink(url: str, payload: dict[str, Any]) -> None:
    if not url:
        return
    thread = threading.Thread(target=_post_sink, args=(url, payload), daemon=True, name="observability-sink")
    thread.start()


def emit_alert(alert_type: str, *, severity: str = "critical", **fields: Any) -> None:
    if not METRICS.allow_alert(alert_type):
        return
    clean = {"alert_type": alert_type, "severity": severity, **fields}
    METRICS.increment(f"alert.{alert_type}")
    log_event("operational_alert", level=logging.CRITICAL, **clean)
    _dispatch_sink(OBSERVABILITY_ALERT_WEBHOOK_URL, _event_payload("operational_alert", clean))


def report_exception(exc: BaseException, *, route: str, method: str, duration_ms: float) -> None:
    fields = {
        "exception_type": type(exc).__name__,
        "route": route,
        "method": method,
        "duration_ms": round(duration_ms, 2),
    }
    METRICS.increment("exception.unhandled")
    log_event("unhandled_exception", level=logging.ERROR, **fields)
    _dispatch_sink(OBSERVABILITY_ERROR_WEBHOOK_URL, _event_payload("unhandled_exception", fields))


def record_request(method: str, route: str, status_code: int, duration_ms: float) -> None:
    method = method.upper()
    status_class = f"{int(status_code) // 100}xx"
    METRICS.increment("http.requests.total")
    METRICS.increment(f"http.status.{status_class}")
    METRICS.increment(f"http.route.{method} {route}.{status_class}")
    METRICS.observe(f"http.route.{method} {route}", duration_ms)
    if status_code >= 500:
        METRICS.recent_failure("api_5xx", threshold=OBSERVABILITY_5XX_ALERT_THRESHOLD)
    log_event(
        "http_request_completed",
        level=logging.ERROR if status_code >= 500 else logging.INFO,
        method=method,
        route=route,
        status_code=int(status_code),
        duration_ms=round(duration_ms, 2),
    )


def record_db_operation(operation: str, duration_ms: float, *, ok: bool, backend: str | None = None) -> None:
    operation = re.sub(r"[^A-Z_]", "", str(operation or "UNKNOWN").upper())[:24] or "UNKNOWN"
    backend = backend or DATABASE_BACKEND
    METRICS.increment("db.operations.total")
    METRICS.increment(f"db.operation.{backend}.{operation}.{'ok' if ok else 'error'}")
    METRICS.observe(f"db.operation.{backend}.{operation}", duration_ms)
    if not ok:
        METRICS.increment("db.errors.total")


def record_readiness_failure(dependency: str, *, error_type: str = "unavailable") -> None:
    METRICS.increment(f"readiness.failure.{dependency}")
    emit_alert("database_unavailable" if dependency == "database" else "dependency_unavailable", dependency=dependency, error_type=error_type)


def record_auth_failure(reason: str = "rejected") -> None:
    METRICS.increment("auth.failures.total")
    METRICS.increment(f"auth.failure_reason.{_metric_token(reason)}")
    METRICS.recent_failure("auth_failures", threshold=OBSERVABILITY_AUTH_FAILURE_ALERT_THRESHOLD)


def record_stripe_webhook_failure(reason: str = "processing_error") -> None:
    METRICS.increment("stripe.webhook.failures.total")
    METRICS.increment(f"stripe.webhook.failure_reason.{_metric_token(reason)}")
    emit_alert("stripe_webhook_failure", reason=_metric_token(reason))


def record_exam_event(action: str, outcome: str) -> None:
    action = _metric_token(action)
    outcome = _metric_token(outcome)
    METRICS.increment(f"exam.{action}.{outcome}")
    if outcome == "failure":
        emit_alert(f"exam_{action}_failure", action=action)


def record_release_event(action: str, outcome: str, *, release_key: str | None = None) -> None:
    action = _metric_token(action)
    outcome = _metric_token(outcome)
    METRICS.increment(f"release.{action}.{outcome}")
    fields: dict[str, Any] = {"action": action, "outcome": outcome}
    if release_key:
        fields["release_key"] = str(release_key)[:120]
    log_event("question_bank_release_operation", level=logging.ERROR if outcome == "failure" else logging.INFO, **fields)
    if outcome == "failure":
        emit_alert("release_activation_failure" if action == "activate" else "release_operation_failure", **fields)


def record_background_failure(job: str, exc: BaseException | str) -> None:
    error_type = type(exc).__name__ if isinstance(exc, BaseException) else str(exc)
    METRICS.increment(f"background.{_metric_token(job)}.failure")
    emit_alert("background_job_failure", job=_metric_token(job), error_type=_metric_token(error_type))


def _metric_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower()).strip("_")
    return token[:80] or "unknown"


def metrics_token_matches(supplied: str | None, expected: str) -> bool:
    if not expected:
        return False
    candidate = str(supplied or "")
    if candidate.lower().startswith("bearer "):
        candidate = candidate[7:].strip()
    return hmac.compare_digest(candidate, expected)


class TimedConnection:
    """Transparent connection proxy that records DB operation latency safely."""

    def __init__(self, raw: Any, backend: str):
        self._raw = raw
        self._backend = backend

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)

    def execute(self, statement: str, params: Iterable[Any] | None = None):
        operation = _sql_operation(statement)
        started = time.perf_counter()
        try:
            cursor = self._raw.execute(statement, params or ())
        except Exception:
            record_db_operation(operation, (time.perf_counter() - started) * 1000, ok=False, backend=self._backend)
            raise
        record_db_operation(operation, (time.perf_counter() - started) * 1000, ok=True, backend=self._backend)
        return cursor

    def executemany(self, statement: str, params: Iterable[Iterable[Any]]):
        operation = _sql_operation(statement)
        started = time.perf_counter()
        try:
            cursor = self._raw.executemany(statement, params)
        except Exception:
            record_db_operation(operation, (time.perf_counter() - started) * 1000, ok=False, backend=self._backend)
            raise
        record_db_operation(operation, (time.perf_counter() - started) * 1000, ok=True, backend=self._backend)
        return cursor

    def executescript(self, script: str):
        started = time.perf_counter()
        try:
            cursor = self._raw.executescript(script)
        except Exception:
            record_db_operation("SCRIPT", (time.perf_counter() - started) * 1000, ok=False, backend=self._backend)
            raise
        record_db_operation("SCRIPT", (time.perf_counter() - started) * 1000, ok=True, backend=self._backend)
        return cursor


def instrument_connection(raw: Any, backend: str) -> TimedConnection:
    return raw if isinstance(raw, TimedConnection) else TimedConnection(raw, backend)


def _sql_operation(statement: str) -> str:
    match = re.match(r"\s*([A-Za-z]+)", str(statement or ""))
    operation = (match.group(1) if match else "UNKNOWN").upper()
    if operation == "WITH":
        lowered = statement.lower()
        for candidate in ("select", "insert", "update", "delete"):
            if re.search(rf"\b{candidate}\b", lowered):
                return candidate.upper()
    if operation == "BEGIN":
        return "TRANSACTION"
    return operation


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request_id_from_header(request.headers.get("x-request-id"))
        token = REQUEST_ID.set(request_id)
        started = time.perf_counter()
        route = _safe_route(request)
        try:
            response = await call_next(request)
            route = _safe_route(request)
            duration_ms = (time.perf_counter() - started) * 1000
            record_request(request.method, route, response.status_code, duration_ms)
            self._record_feature_signal(request, route, response.status_code)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            route = _safe_route(request)
            duration_ms = (time.perf_counter() - started) * 1000
            record_request(request.method, route, 500, duration_ms)
            self._record_feature_signal(request, route, 500)
            report_exception(exc, route=route, method=request.method.upper(), duration_ms=duration_ms)
            raise
        finally:
            REQUEST_ID.reset(token)

    @staticmethod
    def _record_feature_signal(request: Request, route: str, status_code: int) -> None:
        failed = status_code >= 400
        if request.method.upper() == "POST" and route == "/api/auth/login" and status_code == 401:
            record_auth_failure("invalid_credentials")
        if request.method.upper() == "POST" and route == "/api/billing/webhook" and failed:
            record_stripe_webhook_failure("http_rejected" if status_code < 500 else "processing_error")
        if request.method.upper() == "POST" and route == "/api/mock/sessions":
            record_exam_event("start", "failure" if failed else "success")
        if request.method.upper() == "POST" and route == "/api/mock/sessions/{session_id}/submit":
            record_exam_event("submit", "failure" if failed else "success")
