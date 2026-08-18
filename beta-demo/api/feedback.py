from http.server import BaseHTTPRequestHandler
import json


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = min(int(self.headers.get("content-length", "0")), 12000)
            raw = self.rfile.read(length)
            body = json.loads(raw or b"{}")
            safe = {
                "event": "BETA_FEEDBACK_V3",
                "rating": body.get("rating"),
                "area": str(body.get("area", ""))[:120],
                "message": str(body.get("message", ""))[:3000],
                "email": str(body.get("email", ""))[:320],
                "context": str(body.get("context", ""))[:220],
                "route": str(body.get("route", ""))[:180],
                "theme": str(body.get("theme", ""))[:20],
                "viewport": str(body.get("viewport", ""))[:40],
                "created_at": str(body.get("created_at", ""))[:80],
            }
            print(json.dumps(safe, ensure_ascii=False), flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
        except Exception:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":false}')
