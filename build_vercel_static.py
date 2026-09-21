from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
PUBLIC = ROOT / "public"
STATIC = PUBLIC / "static"


def main() -> None:
    if not FRONTEND.is_dir():
        raise RuntimeError("frontend directory is required for the Vercel static build")
    index = FRONTEND / "index-v26.html"
    if not index.is_file():
        raise RuntimeError("frontend/index-v26.html is required for the Vercel static build")

    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FRONTEND, STATIC)
    shutil.copy2(index, PUBLIC / "index.html")

    print(f"Prepared Vercel static frontend at {PUBLIC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
