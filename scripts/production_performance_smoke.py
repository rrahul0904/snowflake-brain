#!/usr/bin/env python3
"""Record bounded, repeatable public production probe latency without secrets."""
from __future__ import annotations

import argparse
import json
import time
from urllib.request import urlopen


def fetch(url: str) -> dict[str, object]:
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=12) as response:  # nosec B310: explicit operator URL
            response.read()
            return {"status": response.status, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}
    except Exception as exc:
        return {"status": "error", "duration_ms": round((time.perf_counter() - started) * 1000, 2), "error": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://snowflakecertificationguide.vercel.app")
    parser.add_argument("--iterations", type=int, default=10)
    args = parser.parse_args()
    endpoints = ("/api/health", "/api/ready", "/api/release", "/api/skills/map", "/api/skills/catalog", "/api/activity/globe")
    report = {path: [fetch(args.base_url.rstrip("/") + path) for _ in range(max(1, args.iterations))] for path in endpoints}
    print(json.dumps(report, indent=2))
    return 0 if all(all(sample["status"] == 200 for sample in samples) for samples in report.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
