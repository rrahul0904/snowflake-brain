from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from ..database import connect

router = APIRouter()

WINDOW_MINUTES = 30
MIN_PUBLIC_COUNT = 3


def _ensure_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS learner_activity_aggregates ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "bucket_key TEXT NOT NULL, "
        "label TEXT NOT NULL, "
        "latitude REAL NOT NULL, "
        "longitude REAL NOT NULL, "
        "active_count INTEGER NOT NULL DEFAULT 0, "
        "observed_at TEXT NOT NULL DEFAULT (datetime('now')), "
        "source TEXT NOT NULL DEFAULT 'aggregate'"
        ")"
    )


@router.get("/activity/globe")
def globe_activity() -> dict[str, Any]:
    """Return only coarse, already-aggregated activity that is safe to display publicly.

    This endpoint intentionally does not derive geography from IP addresses and it does
    not accept client-side location pings. A deployment may populate
    learner_activity_aggregates from a trusted, privacy-reviewed telemetry pipeline.
    Buckets below MIN_PUBLIC_COUNT are never returned.
    """
    with connect() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT bucket_key, label, latitude, longitude, active_count, observed_at "
            "FROM learner_activity_aggregates "
            "WHERE active_count >= ? "
            "AND datetime(observed_at) >= datetime('now', ?) "
            "ORDER BY active_count DESC, label ASC LIMIT 24",
            (MIN_PUBLIC_COUNT, f"-{WINDOW_MINUTES} minutes"),
        ).fetchall()

    locations = [
        {
            "bucket_key": row["bucket_key"],
            "label": row["label"],
            "lat": float(row["latitude"]),
            "lon": float(row["longitude"]),
            "count": int(row["active_count"]),
            "observed_at": row["observed_at"],
        }
        for row in rows
    ]
    active_total = sum(item["count"] for item in locations)
    return {
        "window_minutes": WINDOW_MINUTES,
        "minimum_public_count": MIN_PUBLIC_COUNT,
        "active_total": active_total,
        "locations": locations,
        "mode": "live" if locations else "fallback",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "privacy": "coarse aggregated activity only; no precise individual location is returned",
    }
