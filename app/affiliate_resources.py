from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from .config import AFFILIATE_RESOURCES_ENABLED, AMAZON_ASSOCIATE_TAG


# Editorially curated resources only. No paid placement, bidding, ad network,
# behavioral targeting, impression pixels, or third-party advertising SDK is
# permitted in this catalog. The affiliate relationship affects only the
# outbound Amazon URL after the candidate chooses to click it.
BOOKS: tuple[dict[str, Any], ...] = (
    {
        "id": "snowpro-core-study-guide-verma",
        "title": "SnowPro Core Certification Study Guide",
        "author": "Jatin Verma",
        "publisher": "Packt",
        "year": 2025,
        "asin": "1835884660",
        "fit": "Exam-focused Snowflake Core foundation and hands-on review.",
        "note": "Published before COF-C03; use it as supplemental foundation material and verify current exam-specific details against the Snowflake COF-C03 curriculum and official documentation.",
    },
    {
        "id": "snowflake-definitive-guide-avila",
        "title": "Snowflake: The Definitive Guide",
        "author": "Joyce Kay Avila",
        "publisher": "O'Reilly Media",
        "year": 2022,
        "asin": "1098103815",
        "fit": "Strong architecture, storage, compute, security, sharing, and hands-on Snowflake foundation.",
        "note": "A platform reference rather than an exam-specific COF-C03 guide; use current Snowflake docs for features that changed after publication.",
    },
    {
        "id": "data-modeling-with-snowflake-2e",
        "title": "Data Modeling with Snowflake, Second Edition",
        "author": "Serge Gershkovich",
        "publisher": "Packt",
        "year": 2025,
        "asin": "1837028036",
        "fit": "Practical Snowflake-native modeling patterns useful for deeper architecture and data-engineering understanding.",
        "note": "Supplementary platform depth; it is not presented as an official SnowPro exam guide.",
    },
)

AMAZON_DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."
COMMISSION_DISCLOSURE = "We may earn a commission when you buy through these Amazon links. This does not change your price or determine which resources we recommend."


def _amazon_url(asin: str) -> str:
    base = f"https://www.amazon.com/dp/{asin}/"
    return f"{base}?{urlencode({'tag': AMAZON_ASSOCIATE_TAG})}"


def affiliate_resource_payload() -> dict[str, Any]:
    enabled = bool(AFFILIATE_RESOURCES_ENABLED and AMAZON_ASSOCIATE_TAG)
    if not enabled:
        return {
            "enabled": False,
            "provider": "amazon_associates",
            "books": [],
            "disclosure": None,
            "commission_disclosure": None,
            "advertising_policy": "No display ads, ad networks, sponsored placements, behavioral ad tracking, or third-party ad SDKs.",
        }
    return {
        "enabled": True,
        "provider": "amazon_associates",
        "books": [
            {
                "id": item["id"],
                "title": item["title"],
                "author": item["author"],
                "publisher": item["publisher"],
                "year": item["year"],
                "fit": item["fit"],
                "note": item["note"],
                "url": _amazon_url(str(item["asin"])),
                "link_disclosure": "Paid link",
            }
            for item in BOOKS
        ],
        "disclosure": AMAZON_DISCLOSURE,
        "commission_disclosure": COMMISSION_DISCLOSURE,
        "advertising_policy": "No display ads, ad networks, sponsored placements, behavioral ad tracking, or third-party ad SDKs.",
    }
