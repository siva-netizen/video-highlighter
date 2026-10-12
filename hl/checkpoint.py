"""Detect whether a job can resume from on-disk artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hl.job_stale import job_looks_stale


def find_source_video(job_dir: Path) -> Path | None:
    for p in sorted(job_dir.glob("source.*")):
        if p.is_file():
            return p
    return None


def job_can_resume(job_dir: Path, meta: dict[str, Any]) -> bool:
    if not find_source_video(job_dir):
        return False
    if meta.get("status") in ("running", "queued"):
        return job_looks_stale(meta)
    if meta.get("status") == "completed" and (job_dir / "highlights.mp4").is_file():
        return False
    work = job_dir / "work"
    if not work.is_dir():
        return meta.get("status") == "failed"
    if meta.get("status") in ("failed", "interrupted"):
        return True
    if meta.get("status") == "completed":
        return not (job_dir / "highlights.mp4").is_file()
    return False


def resume_hint(work_dir: Path, stem: str) -> str:
    checks = [
        (f"{stem}_transcript.json", "transcript"),
        (f"{stem}_shots.json", "shots"),
        (f"{stem}_windows.json", "windows"),
        (f"{stem}_plan.json", "plan"),
    ]
    done = [label for name, label in checks if (work_dir / name).exists()]
    if not done:
        return "No cached stages — full pipeline"
    return "Reuse: " + ", ".join(done)
