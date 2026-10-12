"""Detect jobs stuck in running after worker loss."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

STALE_AFTER = timedelta(minutes=5)
STALE_RESUME_AFTER = timedelta(minutes=2)


def _parse_ts(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def job_looks_stale(meta: dict[str, Any]) -> bool:
    if meta.get("status") not in ("running", "queued"):
        return False
    ts = _parse_ts(meta.get("updated_at")) or _parse_ts(meta.get("started_at"))
    if not ts:
        return False
    return datetime.now(UTC) - ts > STALE_RESUME_AFTER


def reconcile_stale_job(meta: dict[str, Any]) -> dict[str, Any]:
    """If status is running/queued but heartbeat old, mark interrupted."""
    if meta.get("status") not in ("running", "queued"):
        return meta
    ts = _parse_ts(meta.get("updated_at")) or _parse_ts(meta.get("started_at"))
    if not ts:
        return meta
    if datetime.now(UTC) - ts <= STALE_AFTER:
        return meta
    pct = meta.get("progress_pct", 0)
    meta = dict(meta)
    meta["status"] = "failed"
    meta["error"] = (
        f"Job stalled at {pct}% (last update {ts.isoformat()}). "
        "Usually API/container restarted during agent or CV. Use Continue to resume from saved artifacts."
    )
    meta["stage"] = "interrupted"
    return meta
