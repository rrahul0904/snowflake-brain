from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from html import unescape
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler
import hashlib
import json
import re
import unicodedata
from urllib.parse import urljoin, urlparse
from uuid import UUID

import httpx

CREDLY_HOSTS = {"credly.com", "www.credly.com"}
CREDLY_BADGE_PATH = re.compile(
    r"^/badges/(?P<badge_id>[0-9a-fA-F-]{36})(?:/(?:public_url|embedded|linked_in_profile))?/?$"
)
REQUEST_TIMEOUT_SECONDS = 8.0
MAX_PROVIDER_BYTES = 1_000_000
MAX_BODY_BYTES = 4096


class VerificationError(ValueError):
    pass


@dataclass(frozen=True)
class Evidence:
    badge_id: str
    credential_url: str
    credential_name: str
    issuer_name: str
    issued_to_name: str
    issued_at: str | None
    expires_at: str | None
    provider_expired: bool
    provider_status: str
    provider_text_hash: str


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = {str(k).lower(): str(v or "") for k, v in attrs}
        key = values.get("property") or values.get("name")
        if key and values.get("content"):
            self.meta[key.lower()] = values["content"]

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self.parts.append(data.strip())

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", unescape(" ".join(self.parts))).strip()


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(body)


def normalized_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", asciiish.casefold()))


def names_match(candidate_name: str, credential_name: str) -> bool:
    left = normalized_name(candidate_name)
    right = normalized_name(credential_name)
    if not left or not right:
        return False
    if left == right:
        return True
    return sorted(left.split()) == sorted(right.split())


def parse_badge_url(value: str) -> tuple[str, str]:
    parsed = urlparse((value or "").strip())
    if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() not in CREDLY_HOSTS:
        raise VerificationError("Use the public HTTPS Credly badge URL from your Credly Share page.")
    match = CREDLY_BADGE_PATH.match(parsed.path)
    if not match:
        raise VerificationError("Credly URL must look like https://www.credly.com/badges/<badge-id>/public_url.")
    badge_id = match.group("badge_id").lower()
    try:
        UUID(badge_id)
    except ValueError as exc:
        raise VerificationError("Credly badge ID is not valid.") from exc
    return badge_id, f"https://www.credly.com/badges/{badge_id}/public_url"


def safe_get(client: httpx.Client, url: str) -> httpx.Response:
    current = url
    for _ in range(4):
        parsed = urlparse(current)
        if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() not in CREDLY_HOSTS:
            raise VerificationError("Credly verification attempted to leave the approved Credly host.")
        response = client.get(current, follow_redirects=False)
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location:
                raise VerificationError("Credly returned an invalid redirect during verification.")
            current = urljoin(current, location)
            continue
        response.raise_for_status()
        if len(response.content) > MAX_PROVIDER_BYTES:
            raise VerificationError("Credly verification response was unexpectedly large.")
        return response
    raise VerificationError("Credly returned too many redirects during verification.")


def parse_date(value: str | None) -> str | None:
    text = (value or "").strip().strip(". ")
    if not text:
        return None
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def extract_evidence(badge_id: str, canonical_url: str, pages: list[PageParser]) -> Evidence:
    combined = " ".join(parser.text for parser in pages if parser.text)
    meta_values: list[str] = []
    for parser in pages:
        meta_values.extend(parser.meta.values())
    search_text = re.sub(r"\s+", " ", " ".join([combined, *meta_values])).strip()

    recipient = ""
    issued_at = None
    expires_at = None
    recipient_match = re.search(
        r"This badge was issued to\s+(.+?)\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        search_text,
        flags=re.IGNORECASE,
    )
    if recipient_match:
        recipient = recipient_match.group(1).strip(" .|-\u2022")
        issued_at = parse_date(recipient_match.group(2))

    expiry_match = re.search(
        r"Expires(?:\s+on)?\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        search_text,
        flags=re.IGNORECASE,
    )
    if expiry_match:
        expires_at = parse_date(expiry_match.group(1))

    issuer = ""
    issuer_match = re.search(
        r"(?:Issued by|Issuer:)\s*([A-Za-z0-9&.,'() /+-]+?)(?=\s+(?:Type|Level|Skills|Earning Criteria|PROVIDED BY|This badge|Expired|Valid|$))",
        search_text,
        flags=re.IGNORECASE,
    )
    if issuer_match:
        issuer = issuer_match.group(1).strip(" .|-\u2022")
    if not issuer and re.search(r"(?:Issued by|Issuer:)\s*Snowflake\b", search_text, flags=re.IGNORECASE):
        issuer = "Snowflake"

    credential_name = ""
    for parser in pages:
        for key in ("og:title", "twitter:title", "title"):
            candidate = parser.meta.get(key, "").strip()
            if candidate:
                candidate = re.sub(r"\s*[-|]\s*Credly\s*$", "", candidate, flags=re.IGNORECASE).strip()
                if candidate and candidate.casefold() != "credly":
                    credential_name = candidate
                    break
        if credential_name:
            break
    if not credential_name:
        title_match = re.search(
            r"(SnowPro[^|]{2,120}?)(?=\s+(?:Expired|Valid|Issued by|Issuer:))",
            search_text,
            flags=re.IGNORECASE,
        )
        if title_match:
            credential_name = title_match.group(1).strip(" .|-\u2022")

    expired = bool(re.search(r"\bExpired\b", search_text, flags=re.IGNORECASE))
    if expires_at:
        try:
            expired = expired or date.fromisoformat(expires_at) < date.today()
        except ValueError:
            pass

    return Evidence(
        badge_id=badge_id,
        credential_url=canonical_url,
        credential_name=credential_name,
        issuer_name=issuer,
        issued_to_name=recipient,
        issued_at=issued_at,
        expires_at=expires_at,
        provider_expired=expired,
        provider_status="expired" if expired else "active",
        provider_text_hash=hashlib.sha256(search_text.encode("utf-8")).hexdigest(),
    )


def fetch_evidence(credential_url: str) -> Evidence:
    badge_id, canonical = parse_badge_url(credential_url)
    pages: list[PageParser] = []
    with httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={
            "User-Agent": "SnowflakeCertificationPlatform-DemoVerifier/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    ) as client:
        for url in (canonical, f"https://www.credly.com/embedded_badge/{badge_id}"):
            try:
                response = safe_get(client, url)
            except (httpx.HTTPError, VerificationError):
                continue
            parser = PageParser()
            parser.feed(response.text)
            pages.append(parser)
    if not pages:
        raise VerificationError("Credly could not be reached or the public badge is unavailable. Check that the badge is public and retry.")
    return extract_evidence(badge_id, canonical, pages)


def decision(candidate_name: str, evidence: Evidence) -> tuple[str, str]:
    if normalized_name(evidence.issuer_name) != "snowflake":
        return "rejected", "The Credly badge is not issued by Snowflake."
    if "snowpro" not in (evidence.credential_name or "").casefold():
        return "rejected", "The Snowflake-issued badge is not recognized as a SnowPro certification credential."
    if not evidence.issued_to_name:
        return "needs_review", "Credly evidence was found, but the public page did not expose the recipient name for automatic ownership matching."
    if not names_match(candidate_name, evidence.issued_to_name):
        return "needs_review", "Credly recipient name does not exactly match the candidate profile name."
    if evidence.provider_expired:
        return "expired", "Credly reports that this SnowPro credential is expired."
    return "verified", "Snowflake issuer, SnowPro credential, and candidate name matched the public Credly evidence."


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0") or "0")
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            return send_json(self, 413, {"ok": False, "error": "Verification payload is too large or empty."})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return send_json(self, 400, {"ok": False, "error": "Invalid JSON payload."})

        candidate_name = str(body.get("candidate_name") or "").strip()[:120]
        credential_url = str(body.get("credential_url") or "").strip()[:500]
        if len(candidate_name) < 2:
            return send_json(self, 422, {"ok": False, "error": "Enter the candidate name exactly as it appears on the Credly badge."})
        try:
            evidence = fetch_evidence(credential_url)
            status, reason = decision(candidate_name, evidence)
            safe_evidence = asdict(evidence)
            safe_evidence.pop("provider_text_hash", None)
            return send_json(self, 200, {
                "ok": True,
                "verification_status": status,
                "verified": status == "verified",
                "reason": reason,
                "evidence": safe_evidence,
            })
        except VerificationError as exc:
            return send_json(self, 422, {"ok": False, "error": str(exc)})
        except httpx.HTTPError:
            return send_json(self, 503, {"ok": False, "error": "Credly is temporarily unavailable. Please retry."})
        except Exception as exc:
            print(json.dumps({"event": "BETA_CREDLY_VERIFY_ERROR", "type": type(exc).__name__}), flush=True)
            return send_json(self, 500, {"ok": False, "error": "Unable to verify the credential right now."})

    def do_GET(self):
        return send_json(self, 405, {"ok": False, "error": "Use POST with candidate_name and credential_url."})
