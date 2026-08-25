from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import UUID, uuid4

import httpx

from .database import connect
from .talent_schema import ensure_talent_schema


CREDLY_HOSTS = {"credly.com", "www.credly.com"}
CREDLY_BADGE_PATH = re.compile(
    r"^/badges/(?P<badge_id>[0-9a-fA-F-]{36})(?:/(?:public_url|embedded|linked_in_profile))?/?$"
)
SNOWFLAKE_ISSUERS = {"snowflake"}
REQUEST_TIMEOUT_SECONDS = 8.0
MAX_PROVIDER_BYTES = 1_000_000


class CredentialVerificationError(ValueError):
    pass


class CredentialAlreadyClaimedError(CredentialVerificationError):
    pass


@dataclass(frozen=True)
class CredlyEvidence:
    badge_id: str
    credential_url: str
    credential_name: str
    issuer_name: str
    issued_to_name: str
    issued_at: str | None
    expires_at: str | None
    provider_expired: bool
    provider_text_hash: str
    provider_status: str


class _PageTextParser(HTMLParser):
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", asciiish.casefold()))


def names_match(candidate_name: str, credential_name: str) -> bool:
    """Conservative ownership check for automatic verification.

    Exact normalized equality is accepted. Token equality is accepted so
    punctuation/order/capitalization differences do not force manual review.
    Additional/missing name tokens are deliberately *not* auto-accepted; those
    cases remain reviewable rather than silently binding someone else's badge.
    """
    left = _normalized_name(candidate_name)
    right = _normalized_name(credential_name)
    if not left or not right:
        return False
    if left == right:
        return True
    return sorted(left.split()) == sorted(right.split())


def parse_credly_badge_url(value: str) -> tuple[str, str]:
    raw = (value or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() not in CREDLY_HOSTS:
        raise CredentialVerificationError("Use the public HTTPS Credly badge URL from your Credly Share page.")
    match = CREDLY_BADGE_PATH.match(parsed.path)
    if not match:
        raise CredentialVerificationError("Credly URL must look like https://www.credly.com/badges/<badge-id>/public_url.")
    badge_id = match.group("badge_id").lower()
    try:
        UUID(badge_id)
    except ValueError as exc:
        raise CredentialVerificationError("Credly badge ID is not valid.") from exc
    canonical = f"https://www.credly.com/badges/{badge_id}/public_url"
    return badge_id, canonical


def _safe_credly_get(client: httpx.Client, url: str) -> httpx.Response:
    current = url
    for _ in range(4):
        parsed = urlparse(current)
        if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() not in CREDLY_HOSTS:
            raise CredentialVerificationError("Credly verification attempted to leave the approved Credly host.")
        response = client.get(current, follow_redirects=False)
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location:
                raise CredentialVerificationError("Credly returned an invalid redirect during verification.")
            current = urljoin(current, location)
            continue
        response.raise_for_status()
        if len(response.content) > MAX_PROVIDER_BYTES:
            raise CredentialVerificationError("Credly verification response was unexpectedly large.")
        return response
    raise CredentialVerificationError("Credly returned too many redirects during verification.")


def _parse_date(value: str | None) -> str | None:
    text = (value or "").strip().strip(". ")
    if not text:
        return None
    formats = (
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _extract_evidence(badge_id: str, canonical_url: str, pages: list[tuple[str, _PageTextParser]]) -> CredlyEvidence:
    combined = " ".join(parser.text for _, parser in pages if parser.text)
    combined = re.sub(r"\s+", " ", combined).strip()
    meta_values: list[str] = []
    for _, parser in pages:
        meta_values.extend(parser.meta.values())
    search_text = re.sub(r"\s+", " ", " ".join([combined, *meta_values])).strip()

    recipient = ""
    issued_at: str | None = None
    expires_at: str | None = None

    recipient_match = re.search(
        r"This badge was issued to\s+(.+?)\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        search_text,
        flags=re.IGNORECASE,
    )
    if recipient_match:
        recipient = recipient_match.group(1).strip(" .|-\u2022")
        issued_at = _parse_date(recipient_match.group(2))

    expiry_match = re.search(
        r"Expires(?:\s+on)?\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        search_text,
        flags=re.IGNORECASE,
    )
    if expiry_match:
        expires_at = _parse_date(expiry_match.group(1))

    issuer = ""
    issuer_match = re.search(r"(?:Issued by|Issuer:)\s*([A-Za-z0-9&.,'() /+-]+?)(?=\s+(?:Type|Level|Skills|Earning Criteria|PROVIDED BY|This badge|Expired|Valid|$))", search_text, flags=re.IGNORECASE)
    if issuer_match:
        issuer = issuer_match.group(1).strip(" .|-\u2022")
    if not issuer:
        simple_issuer = re.search(r"(?:Issued by|Issuer:)\s*(Snowflake)\b", search_text, flags=re.IGNORECASE)
        if simple_issuer:
            issuer = simple_issuer.group(1)

    credential_name = ""
    for _, parser in pages:
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
        # Credly embedded pages place the credential title immediately before
        # the status/issuer text. Restrict the accepted value to SnowPro titles
        # so surrounding navigation copy cannot become credential metadata.
        title_match = re.search(r"(SnowPro[^|]{2,120}?)(?=\s+(?:Expired|Valid|Issued by|Issuer:))", search_text, flags=re.IGNORECASE)
        if title_match:
            credential_name = title_match.group(1).strip(" .|-\u2022")

    provider_expired = bool(re.search(r"\bExpired\b", search_text, flags=re.IGNORECASE))
    if expires_at:
        try:
            provider_expired = provider_expired or date.fromisoformat(expires_at) < date.today()
        except ValueError:
            pass

    provider_status = "expired" if provider_expired else "active"
    text_hash = hashlib.sha256(search_text.encode("utf-8")).hexdigest()
    return CredlyEvidence(
        badge_id=badge_id,
        credential_url=canonical_url,
        credential_name=credential_name,
        issuer_name=issuer,
        issued_to_name=recipient,
        issued_at=issued_at,
        expires_at=expires_at,
        provider_expired=provider_expired,
        provider_text_hash=text_hash,
        provider_status=provider_status,
    )


def fetch_credly_evidence(credential_url: str, *, client: httpx.Client | None = None) -> CredlyEvidence:
    badge_id, canonical = parse_credly_badge_url(credential_url)
    own_client = client is None
    session = client or httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={
            "User-Agent": "SnowflakeCertificationGuide-CredentialVerifier/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    pages: list[tuple[str, _PageTextParser]] = []
    try:
        for url in (canonical, f"https://www.credly.com/embedded_badge/{badge_id}"):
            try:
                response = _safe_credly_get(session, url)
            except (httpx.HTTPError, CredentialVerificationError):
                continue
            parser = _PageTextParser()
            parser.feed(response.text)
            pages.append((str(response.url), parser))
    finally:
        if own_client:
            session.close()
    if not pages:
        raise CredentialVerificationError("Credly could not be reached or the public badge is unavailable. Check that the badge is public and retry.")
    return _extract_evidence(badge_id, canonical, pages)


def _verification_decision(candidate_name: str, evidence: CredlyEvidence) -> tuple[str, str]:
    issuer_key = _normalized_name(evidence.issuer_name)
    if issuer_key not in SNOWFLAKE_ISSUERS:
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


def _safe_payload(evidence: CredlyEvidence) -> dict[str, Any]:
    payload = asdict(evidence)
    # This is already a normalized safe subset. Raw HTML is deliberately never
    # persisted because the verification record only needs the issuer facts.
    return payload


def _credential_row(row: Any) -> dict[str, Any]:
    value = dict(row)
    value["verified"] = value.get("verification_status") == "verified"
    value["active"] = value.get("verification_status") == "verified"
    return value


def verify_credly_credential(candidate: dict[str, Any], credential_url: str) -> dict[str, Any]:
    ensure_talent_schema()
    evidence = fetch_credly_evidence(credential_url)
    status, reason = _verification_decision(str(candidate.get("display_name") or ""), evidence)
    now = _utc_now()
    safe_payload = _safe_payload(evidence)
    payload_json = json.dumps(safe_payload, sort_keys=True, separators=(",", ":"))
    evidence_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    with connect() as conn:
        existing = conn.execute(
            "SELECT * FROM candidate_credentials WHERE provider='credly' AND provider_badge_id=?",
            (evidence.badge_id,),
        ).fetchone()
        if existing and int(existing["candidate_id"]) != int(candidate["id"]):
            raise CredentialAlreadyClaimedError("This Credly badge is already attached to another candidate account.")

        old_status = str(existing["verification_status"]) if existing else ""
        credential_uid = str(existing["credential_uid"]) if existing else str(uuid4())
        verified_at = now if status in {"verified", "expired"} else (existing["verified_at"] if existing else None)
        verification_error = "" if status in {"verified", "expired"} else reason

        if existing:
            conn.execute(
                """
                UPDATE candidate_credentials
                   SET credential_name=?, issuer_name=?, issued_to_name=?, issued_at=?, expires_at=?,
                       credential_url=?, verification_status=?, verification_method='credly_public_url',
                       verified_at=?, last_checked_at=?, verification_error=?, evidence_hash=?,
                       provider_payload_json=?, updated_at=datetime('now')
                 WHERE credential_uid=? AND candidate_id=?
                """,
                (
                    evidence.credential_name,
                    evidence.issuer_name,
                    evidence.issued_to_name,
                    evidence.issued_at,
                    evidence.expires_at,
                    evidence.credential_url,
                    status,
                    verified_at,
                    now,
                    verification_error,
                    evidence_hash,
                    payload_json,
                    credential_uid,
                    int(candidate["id"]),
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO candidate_credentials(
                  credential_uid,candidate_id,provider,provider_badge_id,credential_name,issuer_name,
                  issued_to_name,issued_at,expires_at,credential_url,verification_status,
                  verification_method,verified_at,last_checked_at,verification_error,evidence_hash,
                  provider_payload_json
                ) VALUES (?,?, 'credly',?,?,?,?,?,?,?,?, 'credly_public_url',?,?,?,?,?)
                """,
                (
                    credential_uid,
                    int(candidate["id"]),
                    evidence.badge_id,
                    evidence.credential_name,
                    evidence.issuer_name,
                    evidence.issued_to_name,
                    evidence.issued_at,
                    evidence.expires_at,
                    evidence.credential_url,
                    status,
                    verified_at,
                    now,
                    verification_error,
                    evidence_hash,
                    payload_json,
                ),
            )

        conn.execute(
            """
            INSERT INTO credential_verification_events(
              event_uid,credential_uid,candidate_id,provider,from_status,to_status,reason,
              evidence_url,evidence_hash,checked_at
            ) VALUES (?,?,?,'credly',?,?,?,?,?,?)
            """,
            (
                str(uuid4()),
                credential_uid,
                int(candidate["id"]),
                old_status,
                status,
                reason,
                evidence.credential_url,
                evidence_hash,
                now,
            ),
        )
        if status != "verified":
            conn.execute(
                "UPDATE candidate_talent_profiles SET recruiter_discoverable=0, public_profile=0, updated_at=datetime('now') "
                "WHERE candidate_id=? AND NOT EXISTS (SELECT 1 FROM candidate_credentials WHERE candidate_id=? AND verification_status='verified')",
                (int(candidate["id"]), int(candidate["id"])),
            )
        row = conn.execute(
            "SELECT * FROM candidate_credentials WHERE credential_uid=? AND candidate_id=?",
            (credential_uid, int(candidate["id"])),
        ).fetchone()
    result = _credential_row(row)
    result["verification_reason"] = reason
    return result


def reverify_credential(candidate: dict[str, Any], credential_uid: str) -> dict[str, Any]:
    ensure_talent_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT credential_url FROM candidate_credentials WHERE credential_uid=? AND candidate_id=?",
            (credential_uid, int(candidate["id"])),
        ).fetchone()
    if not row:
        raise CredentialVerificationError("Credential not found.")
    return verify_credly_credential(candidate, str(row["credential_url"]))


def list_candidate_credentials(candidate_id: int) -> list[dict[str, Any]]:
    ensure_talent_schema()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT credential_uid,provider,provider_badge_id,credential_name,issuer_name,issued_to_name,
                   issued_at,expires_at,credential_url,verification_status,verification_method,
                   verified_at,last_checked_at,verification_error,created_at,updated_at
              FROM candidate_credentials
             WHERE candidate_id=?
             ORDER BY CASE verification_status WHEN 'verified' THEN 0 WHEN 'needs_review' THEN 1 WHEN 'expired' THEN 2 ELSE 3 END,
                      credential_name, created_at DESC
            """,
            (candidate_id,),
        ).fetchall()
    return [_credential_row(row) for row in rows]


def delete_candidate_credential(candidate_id: int, credential_uid: str) -> None:
    ensure_talent_schema()
    with connect() as conn:
        cursor = conn.execute(
            "DELETE FROM candidate_credentials WHERE credential_uid=? AND candidate_id=?",
            (credential_uid, candidate_id),
        )
        if cursor.rowcount == 0:
            raise CredentialVerificationError("Credential not found.")
        remaining = conn.execute(
            "SELECT 1 FROM candidate_credentials WHERE candidate_id=? AND verification_status='verified' LIMIT 1",
            (candidate_id,),
        ).fetchone()
        if not remaining:
            conn.execute(
                "UPDATE candidate_talent_profiles SET recruiter_discoverable=0, public_profile=0, updated_at=datetime('now') WHERE candidate_id=?",
                (candidate_id,),
            )


def get_talent_profile(candidate_id: int) -> dict[str, Any]:
    ensure_talent_schema()
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO candidate_talent_profiles(candidate_id) VALUES (?)",
            (candidate_id,),
        )
        row = conn.execute("SELECT * FROM candidate_talent_profiles WHERE candidate_id=?", (candidate_id,)).fetchone()
        verified_count = conn.execute(
            "SELECT COUNT(*) AS n FROM candidate_credentials WHERE candidate_id=? AND verification_status='verified'",
            (candidate_id,),
        ).fetchone()
    result = dict(row)
    result["recruiter_discoverable"] = bool(result.get("recruiter_discoverable"))
    result["public_profile"] = bool(result.get("public_profile"))
    result["verified_credential_count"] = int((verified_count or {"n": 0})["n"])
    result["can_be_discoverable"] = result["verified_credential_count"] > 0
    return result


def update_talent_profile(
    candidate_id: int,
    *,
    headline: str | None = None,
    location: str | None = None,
    availability: str | None = None,
    recruiter_discoverable: bool | None = None,
    public_profile: bool | None = None,
) -> dict[str, Any]:
    ensure_talent_schema()
    profile = get_talent_profile(candidate_id)
    allowed_availability = {"not_looking", "open_to_work", "open_to_contract", "available_now"}
    next_availability = availability if availability is not None else str(profile["availability"])
    if next_availability not in allowed_availability:
        raise CredentialVerificationError("Invalid availability value.")
    next_discoverable = bool(profile["recruiter_discoverable"]) if recruiter_discoverable is None else recruiter_discoverable
    next_public = bool(profile["public_profile"]) if public_profile is None else public_profile
    if next_public:
        next_discoverable = True
    if (next_discoverable or next_public) and not profile["can_be_discoverable"]:
        raise CredentialVerificationError("Verify at least one active SnowPro credential before enabling recruiter or public discoverability.")

    with connect() as conn:
        conn.execute(
            """
            UPDATE candidate_talent_profiles
               SET headline=?, location=?, availability=?, recruiter_discoverable=?, public_profile=?,
                   updated_at=datetime('now')
             WHERE candidate_id=?
            """,
            (
                (headline if headline is not None else str(profile["headline"]))[:160].strip(),
                (location if location is not None else str(profile["location"]))[:160].strip(),
                next_availability,
                1 if next_discoverable else 0,
                1 if next_public else 0,
                candidate_id,
            ),
        )
    return get_talent_profile(candidate_id)


__all__ = [
    "CredentialAlreadyClaimedError",
    "CredentialVerificationError",
    "CredlyEvidence",
    "delete_candidate_credential",
    "fetch_credly_evidence",
    "get_talent_profile",
    "list_candidate_credentials",
    "names_match",
    "parse_credly_badge_url",
    "reverify_credential",
    "update_talent_profile",
    "verify_credly_credential",
]
