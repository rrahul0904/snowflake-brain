#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_security_release_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("security_release_report", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load security release report module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, name: str, payload: dict) -> None:
    (path / name).write_text(json.dumps(payload), encoding="utf-8")


def read_report(path: Path) -> dict:
    return json.loads((path / "security-release-report.json").read_text(encoding="utf-8"))


def main() -> None:
    module = load_module()
    original_strict = os.environ.get("SECURITY_RELEASE_STRICT")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = Path(tmp)
            module.ARTIFACTS = artifacts
            module.OUT = artifacts / "security-release-report.json"

            write(artifacts, "hosted-runtime-security.json", {"status": "pass"})
            write(artifacts, "hosted-static-exposure.json", {"status": "pass"})
            write(artifacts, "production-bank-inventory.json", {"status": "blocked"})
            write(artifacts, "live-hostile-subscriber.json", {"status": "blocked", "live_bank_exercised": False})

            os.environ["SECURITY_RELEASE_STRICT"] = "false"
            module.main()
            report = read_report(artifacts)
            assert report["status"] == "evidence-pending"
            assert report["strict_release"] is False
            assert report["evidence_complete"] is False
            assert set(report["blocking_items"]) == {"production_bank_inventory", "live_black_box"}

            os.environ["SECURITY_RELEASE_STRICT"] = "true"
            try:
                module.main()
            except SystemExit:
                pass
            else:
                raise AssertionError("strict release must fail closed when evidence is incomplete")
            report = read_report(artifacts)
            assert report["status"] == "no-go"
            assert report["strict_release"] is True

            write(
                artifacts,
                "production-bank-inventory.json",
                {
                    "status": "pass",
                    "active_release_present": True,
                    "active_release_question_count": 1200,
                    "pool_counts": {"free": 216, "practice": 504, "mock_reserved": 360, "diagnostic": 120},
                },
            )
            write(artifacts, "live-hostile-subscriber.json", {"status": "pass", "live_bank_exercised": True})
            module.main()
            report = read_report(artifacts)
            assert report["status"] == "go"
            assert report["strict_release"] is True
            assert report["evidence_complete"] is True
            assert report["blocking_items"] == []

        print("SECURITY RELEASE REPORT MODES: PASS")
    finally:
        if original_strict is None:
            os.environ.pop("SECURITY_RELEASE_STRICT", None)
        else:
            os.environ["SECURITY_RELEASE_STRICT"] = original_strict


if __name__ == "__main__":
    main()
