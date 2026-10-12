"""Append-only job event log for Studio governance UI."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _events_path(job_dir: Path) -> Path:
    return job_dir / "events.jsonl"


def append_event(
    job_dir: Path,
    *,
    kind: str,
    title: str,
    detail: str = "",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    job_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(UTC).isoformat(),
        "kind": kind,
        "title": title,
        "detail": detail,
    }
    if data:
        row["data"] = _truncate_data(data)
    path = _events_path(job_dir)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _truncate_data(data: dict[str, Any], max_str: int = 1200) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, str) and len(v) > max_str:
            out[k] = v[:max_str] + "…"
        elif isinstance(v, list) and len(v) > 8:
            out[k] = v[:8]
            out[f"{k}_truncated"] = len(v)
        else:
            out[k] = v
    return out


def read_events(job_dir: Path, after: int = 0) -> tuple[list[dict], int]:
    path = _events_path(job_dir)
    if not path.exists():
        return [], after
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < after:
                continue
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows, after + len(rows)
