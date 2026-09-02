#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute, iter_route_contexts  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    """Reject duplicate effective candidate API method/path registrations.

    FastAPI >=0.137 preserves included routers as a route tree instead of
    cloning every APIRoute into a flat ``app.routes`` list.  The public
    ``iter_route_contexts`` helper exposes each effective path with all include
    prefixes applied, which is the routing contract this guard actually needs
    to validate.
    """
    registrations: dict[tuple[str, str], list[str]] = defaultdict(list)
    for route_context in iter_route_contexts(app.routes):
        original = route_context.original_route
        if not isinstance(original, APIRoute):
            continue
        path = str(route_context.path)
        if not path.startswith("/api"):
            continue
        for method in sorted(original.methods or set()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            registrations[(method, path)].append(str(route_context.name or original.name))

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

    required = {
        ("POST", "/api/mock/sessions/{session_id}/events"),
        ("GET", "/api/mock/sessions/{session_id}/replay"),
    }
    missing = sorted(required - set(registrations))
    if missing:
        rendered = ", ".join(f"{method} {path}" for method, path in missing)
        raise AssertionError(f"Required candidate API route registrations are missing: {rendered}")

    print(f"Unique API route contract passed for {len(registrations)} method/path registrations.")


if __name__ == "__main__":
    main()
