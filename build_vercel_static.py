from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
PUBLIC = ROOT / "public"
STATIC = PUBLIC / "static"
INDEX = FRONTEND / "index-v26.html"

STYLESHEET_RE = re.compile(
    r'\s*<link rel="stylesheet" href="/static/styles/([^"?]+)(?:\?[^"]*)?"\s*/>'
)


def main() -> None:
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    STATIC.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FRONTEND, STATIC)

    html = INDEX.read_text(encoding="utf-8")
    stylesheet_names = STYLESHEET_RE.findall(html)
    if not stylesheet_names:
        raise RuntimeError("index-v26.html contains no stylesheet links to bundle")

    chunks: list[str] = []
    for name in stylesheet_names:
        path = FRONTEND / "styles" / name
        if not path.is_file():
            raise RuntimeError(f"Missing stylesheet referenced by index-v26.html: {name}")
        chunks.append(f"/* {name} */\n{path.read_text(encoding='utf-8').rstrip()}\n")

    bundle = STATIC / "styles" / "app.bundle.css"
    bundle.write_text("\n".join(chunks), encoding="utf-8")

    html = STYLESHEET_RE.sub("", html)
    bundled_link = (
        '  <link rel="stylesheet" href="/static/styles/app.bundle.css?v=20260921-launch-perf1" />\n'
    )
    if "</head>" not in html:
        raise RuntimeError("index-v26.html is missing </head>")
    html = html.replace("</head>", bundled_link + "</head>", 1)
    (PUBLIC / "index.html").write_text(html, encoding="utf-8")

    print(
        f"Prepared Vercel static frontend: {len(stylesheet_names)} stylesheets -> "
        f"{bundle.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
