from http.server import BaseHTTPRequestHandler
import json
import os
import hmac
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ADMIN_TOKEN = os.getenv("FEEDBACK_ADMIN_TOKEN", "").strip()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        auth = self.headers.get("authorization", "")
        if not ADMIN_TOKEN or not auth.lower().startswith("bearer ") or not hmac.compare_digest(auth[7:].strip(), ADMIN_TOKEN):
            self.send_response(401)
            self.end_headers()
            return
        ok = False
        try:
            with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT to_regclass('public.beta_feedback_submissions') IS NOT NULL")
                    ok = bool(cur.fetchone()[0])
        except Exception:
            ok = False
        body = json.dumps({"ok": ok}).encode()
        self.send_response(200 if ok else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
