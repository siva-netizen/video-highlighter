"""List and summarize jobs from disk (no database)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hl.checkpoint import job_can_resume
from hl.job_stale import job_looks_stale, reconcile_stale_job


def list_jobs(jobs_root: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    if not jobs_root.is_dir():
        return []

    entries: list[dict[str, Any]] = []
    for job_dir in jobs_root.iterdir():
        if not job_dir.is_dir():
            continue
        meta_path = job_dir / "job.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
            meta = reconcile_stale_job(meta)
        except json.JSONDecodeError:
            continue
        entry = {
            "id": meta.get("id", job_dir.name),
            "status": meta.get("status", "unknown"),
            "filename": meta.get("filename"),
            "target_seconds": meta.get("target_seconds"),
            "skill": meta.get("skill"),
            "progress_pct": meta.get("progress_pct", 0),
            "created_at": meta.get("created_at") or meta.get("started_at"),
            "started_at": meta.get("started_at"),
            "has_video": (job_dir / "highlights.mp4").exists(),
        }
        entry["can_resume"] = job_can_resume(job_dir, meta)
        entry["looks_stale"] = job_looks_stale(meta)
        entries.append(entry)

    entries.sort(key=lambda e: e.get("created_at") or e.get("started_at") or "", reverse=True)
    return entries[:limit]
