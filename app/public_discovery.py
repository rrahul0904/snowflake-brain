from __future__ import annotations

from html import escape
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from .certification_content import certification_catalog
from .config import APP_BASE_URL


router = APIRouter(tags=["public-discovery"])


def _rows() -> list[dict[str, Any]]:
    return list(certification_catalog().get("official_certifications") or [])


def _page(title: str, description: str, body: str, canonical_path: str) -> HTMLResponse:
    canonical = f"{APP_BASE_URL}{canonical_path}"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description, quote=True)}" />
  <link rel="canonical" href="{escape(canonical, quote=True)}" />
  <meta name="robots" content="index,follow" />
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>"""
    return HTMLResponse(html, headers={"Cache-Control": "public, max-age=300, s-maxage=3600"})


@router.get("/discover", response_class=HTMLResponse)
def discovery_index() -> HTMLResponse:
    rows = _rows()
    cards = []
    for item in rows:
        identifier = str(item.get("id") or "")
        title = str(item.get("official_title") or item.get("title") or identifier)
        exam_code = str(item.get("exam_code") or "")
        level = str(item.get("level") or "")
        availability = "Study guide available" if item.get("implemented") and item.get("launchable") else "Verified exam facts · study guide coming soon"
        cards.append(
            f'<article><p>{escape(exam_code)} · {escape(level)}</p>'
            f'<h2><a href="/discover/{escape(identifier, quote=True)}">{escape(title)}</a></h2>'
            f'<p>{escape(availability)}</p></article>'
        )
    body = (
        "<header><p>Snowflake Brain · Independent certification preparation</p>"
        "<h1>SnowPro certification guides</h1>"
        "<p>Source-verified public certification facts and independent preparation paths. "
        "Private practice questions and candidate learning data are never published here.</p></header>"
        f"<section>{''.join(cards)}</section>"
        '<p><a href="/#/certifications">Open the interactive certification catalog</a></p>'
    )
    return _page(
        "SnowPro Certification Guides | Snowflake Brain",
        "Source-verified SnowPro certification facts and independent Snowflake certification preparation guides.",
        body,
        "/discover",
    )


@router.get("/discover/{certification_id}", response_class=HTMLResponse)
def discovery_detail(certification_id: str) -> HTMLResponse:
    item = next((row for row in _rows() if str(row.get("id") or "") == certification_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Certification guide not found")

    title = str(item.get("official_title") or item.get("title") or certification_id)
    exam_code = str(item.get("exam_code") or "")
    verified = str(item.get("source_verified_at") or "not recorded")
    domains = item.get("exam_domains") or []
    source_url = str(item.get("official_exam_url") or item.get("source_url") or "https://learn.snowflake.com/en/certifications/")
    facts: list[str] = []
    for label, value in (
        ("Exam code", item.get("exam_code")),
        ("Level", item.get("level")),
        ("Fee", f"USD {item['fee_usd']} per attempt" if item.get("fee_usd") is not None else None),
        ("Credential validity", f"{item['credential_validity_months']} months" if item.get("credential_validity_months") else None),
        ("Guide version", item.get("guide_version")),
        ("Effective date", item.get("effective_date")),
    ):
        if value not in (None, ""):
            facts.append(f"<li><strong>{escape(label)}:</strong> {escape(str(value))}</li>")

    domain_html = "".join(
        f"<li><strong>{escape(str(domain.get('title') or domain.get('name') or 'Exam domain'))}</strong> — "
        f"{int(domain.get('weight') or 0)}%</li>"
        for domain in domains
    )
    interactive_track = str(item.get("configured_track_id") or item.get("id") or certification_id)
    availability = bool(item.get("implemented") and item.get("launchable"))
    prep = (
        f'<p><a href="/#/exam-guide?track_id={escape(interactive_track, quote=True)}">Open the interactive exam guide</a> · '
        f'<a href="/#/curriculum?track_id={escape(interactive_track, quote=True)}">Open the mapped curriculum</a></p>'
        if availability
        else '<p><a href="/#/certifications">Compare certification paths</a></p>'
    )
    body = (
        f"<header><p>{escape(exam_code)} · Source-verified exam guide</p><h1>{escape(title)}</h1>"
        "<p>This public page contains verified certification facts only. It does not expose private question-bank content.</p></header>"
        f"<section><h2>Verified facts</h2><ul>{''.join(facts)}</ul></section>"
        + (f"<section><h2>Weighted exam domains</h2><ol>{domain_html}</ol></section>" if domain_html else "")
        + f'<section><h2>Source and freshness</h2><p>Source verification: {escape(verified)}.</p>'
          f'<p><a href="{escape(source_url, quote=True)}" rel="nofollow noopener">Official Snowflake page</a></p></section>'
        + prep
        + '<footer><p>Snowflake Brain is independent and is not affiliated with, sponsored by, approved by, or endorsed by Snowflake Inc.</p></footer>'
    )
    return _page(
        f"{exam_code} {title} Guide | Snowflake Brain".strip(),
        f"Source-verified {exam_code} {title} certification facts, domain weights, and independent preparation guidance.",
        body,
        f"/discover/{certification_id}",
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> PlainTextResponse:
    return PlainTextResponse(
        f"User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {APP_BASE_URL}/sitemap.xml\n",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/sitemap.xml")
def sitemap() -> Response:
    paths = ["/", "/discover"] + [f"/discover/{row['id']}" for row in _rows() if row.get("id")]
    urls = "".join(
        f"<url><loc>{xml_escape(APP_BASE_URL + path)}</loc></url>"
        for path in paths
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})
