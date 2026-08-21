from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import csv
import hashlib
import hmac
import io
import json
import os
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ADMIN_TOKEN = os.getenv("FEEDBACK_ADMIN_TOKEN", "").strip()
IP_HASH_SECRET = os.getenv("FEEDBACK_IP_HASH_SECRET", ADMIN_TOKEN).strip()
SUBMISSION_LIMIT_PER_HOUR = max(5, min(100, int(os.getenv("FEEDBACK_SUBMISSION_LIMIT_PER_HOUR", "30"))))
AREA_MAP = {
    "overall experience": "Other",
    "study guide": "Study Guide",
    "practice questions": "Practice",
    "mock exam": "Mock Exam",
    "adaptive readiness": "Adaptive",
    "membership/pricing": "Membership",
    "mobile experience": "Mobile",
    "light/dark mode": "Visual Design",
    "earth/globe visual": "Visual Design",
}


def _json(handler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(body)


def _connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=8)


def _authorized(headers) -> bool:
    if not ADMIN_TOKEN:
        return False
    value = headers.get("authorization", "")
    if not value.lower().startswith("bearer "):
        return False
    return hmac.compare_digest(value[7:].strip(), ADMIN_TOKEN)


def _safe_text(value, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _safe_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, parsed))


def _client_ip(headers) -> str:
    forwarded = headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() if forwarded else ""


def _hash_ip(ip: str) -> str | None:
    if not ip or not IP_HASH_SECRET:
        return None
    return hmac.new(IP_HASH_SECRET.encode(), ip.encode(), hashlib.sha256).hexdigest()


def _parse_client_time(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _csv_safe(value):
    """Prevent user-controlled cells from becoming spreadsheet formulas."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + text
    return text


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            declared_length = _safe_int(self.headers.get("content-length", "0"), 0, 0, 12001)
            if declared_length > 12000:
                return _json(self, 413, {"ok": False, "error": "Feedback payload is too large."})
            body = json.loads(self.rfile.read(declared_length) or b"{}")
            message = _safe_text(body.get("message"), 3000)
            if len(message) < 2:
                return _json(self, 422, {"ok": False, "error": "Feedback message is required."})
            rating = body.get("rating")
            rating = int(rating) if str(rating or "").isdigit() else None
            if rating is not None and rating not in range(1, 6):
                rating = None
            raw_area = _safe_text(body.get("area"), 120) or "Other"
            area = AREA_MAP.get(raw_area.lower(), raw_area)
            email = _safe_text(body.get("email"), 320) or None
            context = _safe_text(body.get("context"), 220) or None
            route = _safe_text(body.get("route"), 180) or None
            theme = _safe_text(body.get("theme"), 20) or None
            viewport = _safe_text(body.get("viewport"), 40) or None
            user_agent = _safe_text(self.headers.get("user-agent"), 512) or None
            client_created_at = _parse_client_time(_safe_text(body.get("created_at"), 80))
            ip_hash = _hash_ip(_client_ip(self.headers))

            with _connect() as conn:
                if ip_hash:
                    recent = conn.execute(
                        """SELECT COUNT(*)::int AS n
                           FROM public.beta_feedback_submissions
                           WHERE ip_hash=%s AND submitted_at >= now() - interval '1 hour'""",
                        (ip_hash,),
                    ).fetchone()["n"]
                    if recent >= SUBMISSION_LIMIT_PER_HOUR:
                        return _json(self, 429, {"ok": False, "error": "Too many feedback submissions. Please try again later."})

                row = conn.execute(
                    """
                    INSERT INTO public.beta_feedback_submissions
                      (rating,area,message,email,context,route,theme,viewport,user_agent,ip_hash,source,client_created_at,metadata)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'public-beta',%s,%s::jsonb)
                    RETURNING feedback_uid, submitted_at
                    """,
                    (rating, area, message, email, context, route, theme, viewport, user_agent, ip_hash,
                     client_created_at, json.dumps({"schema": "beta_feedback_v4", "raw_area": raw_area})),
                ).fetchone()
                conn.commit()
            print(json.dumps({"event": "BETA_FEEDBACK_PERSISTED", "feedback_uid": str(row["feedback_uid"]), "area": area, "rating": rating}), flush=True)
            return _json(self, 201, {"ok": True, "feedback_id": str(row["feedback_uid"]), "submitted_at": row["submitted_at"]})
        except json.JSONDecodeError:
            return _json(self, 400, {"ok": False, "error": "Invalid JSON payload."})
        except Exception as exc:
            print(json.dumps({"event": "BETA_FEEDBACK_ERROR", "type": type(exc).__name__}), flush=True)
            return _json(self, 503, {"ok": False, "error": "Feedback storage is temporarily unavailable."})

    def do_GET(self):
        if not _authorized(self.headers):
            return _json(self, 401, {"ok": False, "error": "Unauthorized"})
        try:
            query = parse_qs(urlparse(self.path).query)
            q = _safe_text((query.get("q") or [""])[0], 200)
            area = _safe_text((query.get("area") or [""])[0], 120)
            theme = _safe_text((query.get("theme") or [""])[0], 20)
            route = _safe_text((query.get("route") or [""])[0], 180)
            rating_raw = _safe_text((query.get("rating") or [""])[0], 2)
            rating = int(rating_raw) if rating_raw.isdigit() and 1 <= int(rating_raw) <= 5 else None
            page = _safe_int((query.get("page") or ["1"])[0], 1, 1, 1000000)
            limit = _safe_int((query.get("limit") or ["50"])[0], 50, 10, 100)
            export = (query.get("format") or [""])[0] == "csv"

            clauses = ["1=1"]
            params = []
            if q:
                clauses.append("(message ILIKE %s OR COALESCE(email,'') ILIKE %s OR COALESCE(context,'') ILIKE %s OR COALESCE(route,'') ILIKE %s)")
                needle = f"%{q}%"
                params.extend([needle] * 4)
            if area:
                clauses.append("area = %s")
                params.append(area)
            if theme:
                clauses.append("theme = %s")
                params.append(theme)
            if route:
                clauses.append("COALESCE(route,'') ILIKE %s")
                params.append(f"%{route}%")
            if rating:
                clauses.append("rating = %s")
                params.append(rating)
            where = " AND ".join(clauses)

            with _connect() as conn:
                summary = conn.execute(
                    """SELECT COUNT(*)::int AS total,
                              ROUND(AVG(rating)::numeric,2) AS avg_rating,
                              COUNT(*) FILTER (WHERE rating=5)::int AS five_star,
                              COUNT(*) FILTER (WHERE COALESCE(email,'')<>'')::int AS with_email
                       FROM public.beta_feedback_submissions"""
                ).fetchone()
                filtered_total = conn.execute(
                    f"SELECT COUNT(*)::int AS n FROM public.beta_feedback_submissions WHERE {where}", params
                ).fetchone()["n"]
                fetch_limit = 5000 if export else limit
                offset = 0 if export else (page - 1) * limit
                rows = conn.execute(
                    f"""SELECT feedback_uid,rating,area,message,email,context,route,theme,viewport,source,submitted_at,client_created_at
                        FROM public.beta_feedback_submissions WHERE {where}
                        ORDER BY submitted_at DESC LIMIT %s OFFSET %s""",
                    [*params, fetch_limit, offset],
                ).fetchall()

            if export:
                out = io.StringIO()
                writer = csv.writer(out)
                writer.writerow(["feedback_id","submitted_at","rating","area","message","email","context","route","theme","viewport","source","client_created_at"])
                for row in rows:
                    writer.writerow([
                        _csv_safe(row.get("feedback_uid")), _csv_safe(row.get("submitted_at")), _csv_safe(row.get("rating")),
                        _csv_safe(row.get("area")), _csv_safe(row.get("message")), _csv_safe(row.get("email")),
                        _csv_safe(row.get("context")), _csv_safe(row.get("route")), _csv_safe(row.get("theme")),
                        _csv_safe(row.get("viewport")), _csv_safe(row.get("source")), _csv_safe(row.get("client_created_at")),
                    ])
                data = out.getvalue().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename=beta-feedback.csv")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)
                return

            return _json(self, 200, {
                "ok": True,
                "summary": dict(summary),
                "filtered_total": filtered_total,
                "page": page,
                "limit": limit,
                "rows": [dict(row) for row in rows],
                "retention": "persistent_database_no_automatic_deletion",
            })
        except Exception as exc:
            print(json.dumps({"event": "BETA_FEEDBACK_ADMIN_ERROR", "type": type(exc).__name__}), flush=True)
            return _json(self, 500, {"ok": False, "error": "Unable to load feedback."})
