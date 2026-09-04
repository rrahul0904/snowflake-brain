#!/usr/bin/env python3
"""Capture privacy-safe FinOps costs from explicitly supplied provider values.

Provider billing APIs are intentionally not scraped.  Operators may provide a
JSON array in FINOPS_MANUAL_COSTS_JSON; absent values remain NOT_CONNECTED.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.admin_operations import ensure_admin_operations_schema
from app.database import connect, run_migrations


def main() -> int:
    run_migrations()
    ensure_admin_operations_schema()
    now = datetime.now(timezone.utc)
    start = now.strftime("%Y-%m-%d")
    end = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    raw = os.getenv("FINOPS_MANUAL_COSTS_JSON", "").strip()
    values = json.loads(raw) if raw else []
    if not isinstance(values, list):
        raise SystemExit("FINOPS_MANUAL_COSTS_JSON must be a JSON array")
    allowed = {"ACTUAL", "ESTIMATED", "NOT_CONNECTED"}
    with connect() as conn:
        for item in values:
            evidence = str(item.get("evidence_classification", "ESTIMATED")).upper()
            if evidence not in allowed:
                raise SystemExit(f"Invalid evidence_classification: {evidence}")
            provider = str(item["service_provider"])
            category = str(item.get("cost_category", "other"))
            source = str(item.get("measurement_source", "manual"))
            conn.execute(
                "DELETE FROM finops_cost_snapshots WHERE service_provider=? AND cost_category=? AND period_start=? AND period_end=? AND measurement_source=?",
                (provider, category, start, end, source),
            )
            conn.execute(
                "INSERT INTO finops_cost_snapshots(service_provider,service_name,cost_category,period_start,period_end,amount,currency,measurement_source,evidence_classification,usage_quantity,usage_unit,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (provider, str(item.get("service_name", provider)), category, start, end, item.get("amount"), str(item.get("currency", "USD")), source, evidence, item.get("usage_quantity"), str(item.get("usage_unit", "")), str(item.get("notes", ""))[:500]),
            )
    print(json.dumps({"captured": len(values), "period_start": start, "unconnected": not values}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
