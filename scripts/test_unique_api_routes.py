#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    registrations: dict[tuple[str, str], list[str]] = defaultdict(list)
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api"):
            continue
        for method in sorted(route.methods or set()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            registrations[(method, route.path)].append(route.name)

    duplicates = {
        key: names
        for key, names in registrations.items()
        if len(names) > 1
    }
    if duplicates:
        lines = ["Duplicate candidate API routes are not allowed:"]
        for (method, path), names in sorted(duplicates.items()):
            lines.append(f"- {method} {path}: {', '.join(names)}")
        raise AssertionError("\n".join(lines))

    print(f"Unique API route contract passed for {len(registrations)} method/path registrations.")


if __name__ == "__main__":
    main()
