from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.auth import password_digest  # noqa: E402
from app.credential_verification import (  # noqa: E402
    CredentialVerificationError,
    names_match,
    parse_credly_badge_url,
)


def test_credly_url_is_canonicalized() -> None:
    badge_id = "123e4567-e89b-12d3-a456-426614174000"
    parsed_id, canonical = parse_credly_badge_url(
        f"https://credly.com/badges/{badge_id}/linked_in_profile"
    )
    assert parsed_id == badge_id
    assert canonical == f"https://www.credly.com/badges/{badge_id}/public_url"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.credly.com/badges/123e4567-e89b-12d3-a456-426614174000/public_url",
        "https://evil.example/badges/123e4567-e89b-12d3-a456-426614174000/public_url",
        "https://127.0.0.1/badges/123e4567-e89b-12d3-a456-426614174000/public_url",
        "https://www.credly.com.evil.example/badges/123e4567-e89b-12d3-a456-426614174000/public_url",
    ],
)
def test_credly_verifier_rejects_non_approved_hosts(url: str) -> None:
    with pytest.raises(CredentialVerificationError):
        parse_credly_badge_url(url)


def test_candidate_name_matching_is_conservative() -> None:
    assert names_match("Jane Q. Doe", "Doe, Jane Q")
    assert names_match("José Singh", "Jose Singh")
    assert not names_match("Jane Doe", "Jane Q Doe")
    assert not names_match("Jane Doe", "John Doe")


def test_password_digest_is_salted_and_deterministic_per_salt() -> None:
    salt_a = "00" * 16
    salt_b = "11" * 16
    password = "LongCandidatePassword!123"
    digest_a = password_digest(password, salt_a)
    assert digest_a == password_digest(password, salt_a)
    assert digest_a != password_digest(password, salt_b)
    assert digest_a != password_digest("DifferentCandidatePassword!123", salt_a)
