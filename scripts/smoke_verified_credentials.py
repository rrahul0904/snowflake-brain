#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-verified-credentials-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "credentials.sqlite")

from app import credential_verification as cv  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.talent_schema import ensure_talent_schema  # noqa: E402


BADGE_A = "46f92b52-581a-4bbe-8981-c0957dd022f5"
BADGE_B = "966f3a52-581a-4bbe-8981-c0957dd022f5"
BADGE_C = "766f3a52-581a-4bbe-8981-c0957dd022f5"
BADGE_D = "566f3a52-581a-4bbe-8981-c0957dd022f5"


def seed_candidate(email: str, name: str) -> dict:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO candidate_accounts(email,display_name,password_hash,password_salt,password_algorithm,plan)
            VALUES (?,?, 'not-used', 'not-used', 'scrypt', 'free')
            """,
            (email, name),
        )
        candidate_id = int(cursor.lastrowid)
    return {"id": candidate_id, "email": email, "display_name": name}


def evidence(
    badge_id: str,
    *,
    title: str = "SnowPro Core Certification",
    issuer: str = "Snowflake",
    recipient: str = "Rahul Singh",
    expired: bool = False,
    expires_at: str | None = "2028-08-24",
) -> cv.CredlyEvidence:
    return cv.CredlyEvidence(
        badge_id=badge_id,
        credential_url=f"https://www.credly.com/badges/{badge_id}/public_url",
        credential_name=title,
        issuer_name=issuer,
        issued_to_name=recipient,
        issued_at="2026-08-24",
        expires_at=expires_at,
        provider_expired=expired,
        provider_text_hash=f"hash-{badge_id}",
        provider_status="expired" if expired else "active",
    )


def set_provider(value: cv.CredlyEvidence) -> None:
    cv.fetch_credly_evidence = lambda credential_url, *, client=None: value  # type: ignore[assignment]


def main() -> None:
    run_migrations()
    ensure_talent_schema()

    badge_id, canonical = cv.parse_credly_badge_url(
        f"https://www.credly.com/badges/{BADGE_A}/public_url"
    )
    assert badge_id == BADGE_A
    assert canonical == f"https://www.credly.com/badges/{BADGE_A}/public_url"
    badge_id2, canonical2 = cv.parse_credly_badge_url(f"https://credly.com/badges/{BADGE_A}")
    assert badge_id2 == BADGE_A and canonical2 == canonical
    for invalid in (
        f"http://www.credly.com/badges/{BADGE_A}/public_url",
        f"https://example.com/badges/{BADGE_A}/public_url",
        "https://www.credly.com/badges/not-a-uuid/public_url",
        f"https://www.credly.com/users/example/badges/{BADGE_A}",
    ):
        try:
            cv.parse_credly_badge_url(invalid)
            raise AssertionError(f"Expected invalid Credly URL to fail: {invalid}")
        except cv.CredentialVerificationError:
            pass

    assert cv.names_match("Rahul Singh", "rahul singh")
    assert cv.names_match("Rahul Singh", "SINGH, Rahul")
    assert not cv.names_match("Rahul Singh", "Rahul Kumar Singh")
    assert not cv.names_match("Rahul Singh", "Different Person")

    rahul = seed_candidate("rahul@example.test", "Rahul Singh")
    second = seed_candidate("other@example.test", "Other Candidate")

    set_provider(evidence(BADGE_A))
    verified = cv.verify_credly_credential(rahul, canonical)
    assert verified["verification_status"] == "verified"
    assert verified["verified"] is True
    assert verified["issuer_name"] == "Snowflake"
    assert verified["credential_name"] == "SnowPro Core Certification"

    profile = cv.get_talent_profile(int(rahul["id"]))
    assert profile["verified_credential_count"] == 1
    assert profile["can_be_discoverable"] is True
    assert profile["recruiter_discoverable"] is False
    assert profile["public_profile"] is False

    profile = cv.update_talent_profile(
        int(rahul["id"]),
        headline="Senior Snowflake Data Engineer",
        location="Boston, MA · Remote",
        availability="open_to_work",
        recruiter_discoverable=True,
        public_profile=False,
    )
    assert profile["recruiter_discoverable"] is True
    assert profile["public_profile"] is False

    # A public profile implies recruiter discoverability.
    profile = cv.update_talent_profile(int(rahul["id"]), recruiter_discoverable=False, public_profile=True)
    assert profile["public_profile"] is True
    assert profile["recruiter_discoverable"] is True

    # The same provider badge cannot be claimed by a second account.
    try:
        cv.verify_credly_credential(second, canonical)
        raise AssertionError("Duplicate badge claim should fail")
    except cv.CredentialAlreadyClaimedError:
        pass

    # Wrong recipient remains reviewable, never auto-verified.
    set_provider(evidence(BADGE_B, recipient="Another Person"))
    mismatch = cv.verify_credly_credential(
        rahul, f"https://www.credly.com/badges/{BADGE_B}/public_url"
    )
    assert mismatch["verification_status"] == "needs_review"
    assert mismatch["verified"] is False

    # A non-Snowflake issuer is rejected even if the title says SnowPro.
    set_provider(evidence(BADGE_C, issuer="Example Training Company"))
    rejected = cv.verify_credly_credential(
        rahul, f"https://www.credly.com/badges/{BADGE_C}/public_url"
    )
    assert rejected["verification_status"] == "rejected"

    # Snowflake badges that are not SnowPro certifications do not qualify.
    set_provider(evidence(BADGE_D, title="Snowflake Partner Technical Accreditation"))
    non_snowpro = cv.verify_credly_credential(
        rahul, f"https://www.credly.com/badges/{BADGE_D}/public_url"
    )
    assert non_snowpro["verification_status"] == "rejected"

    # Reverification can expire a previously valid badge and automatically
    # remove talent visibility when it was the candidate's last active verified credential.
    set_provider(evidence(BADGE_A, expired=True, expires_at="2026-01-01"))
    expired = cv.reverify_credential(rahul, verified["credential_uid"])
    assert expired["verification_status"] == "expired"
    profile = cv.get_talent_profile(int(rahul["id"]))
    assert profile["verified_credential_count"] == 0
    assert profile["recruiter_discoverable"] is False
    assert profile["public_profile"] is False

    try:
        cv.update_talent_profile(int(second["id"]), recruiter_discoverable=True)
        raise AssertionError("Discoverability without an active verified credential should fail")
    except cv.CredentialVerificationError:
        pass

    with connect() as conn:
        events = conn.execute(
            "SELECT * FROM credential_verification_events WHERE credential_uid=? ORDER BY checked_at",
            (verified["credential_uid"],),
        ).fetchall()
        assert len(events) == 2
        assert events[0]["to_status"] == "verified"
        assert events[1]["to_status"] == "expired"

        stored = conn.execute(
            "SELECT provider_payload_json,evidence_hash FROM candidate_credentials WHERE credential_uid=?",
            (verified["credential_uid"],),
        ).fetchone()
        payload = json.loads(stored["provider_payload_json"])
        assert payload["issuer_name"] == "Snowflake"
        assert "html" not in payload
        assert "<html" not in stored["provider_payload_json"].lower()
        assert len(stored["evidence_hash"]) == 64

    cv.delete_candidate_credential(int(rahul["id"]), mismatch["credential_uid"])
    remaining = cv.list_candidate_credentials(int(rahul["id"]))
    assert all(row["credential_uid"] != mismatch["credential_uid"] for row in remaining)

    print("Verified credential smoke passed")
    print("provider=credly issuer=Snowflake credential_family=SnowPro")
    print("states=verified,expired,needs_review,rejected duplicate_claim=blocked")
    print("discoverability=private_by_default active_verified_required=true")


if __name__ == "__main__":
    try:
        main()
    finally:
        TEMP.cleanup()
