"""Job artifact manifest (disk-backed, no DB)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def job_work_dir(job_dir: Path) -> Path:
    return job_dir / "work"


def manifest_path(job_dir: Path) -> Path:
    return job_dir / "artifacts.json"


def _glob_one(work: Path, pattern: str) -> Path | None:
    hits = list(work.glob(pattern))
    return hits[0] if hits else None


def scan_artifacts(job_dir: Path) -> dict[str, Any]:
    """Build manifest from files on disk."""
    work = job_work_dir(job_dir)
    shots = _glob_one(work, "*_shots.json")
    plan = _glob_one(work, "*_plan.json")
    transcript = _glob_one(work, "*_transcript.json")
    summary = work / "summary.md"
    if not summary.exists():
        summary = job_dir / "work" / "summary.md"
    video = job_dir / "highlights.mp4"

    keyframes: list[dict[str, Any]] = []
    kf_root = work / "keyframes"
    if kf_root.is_dir():
        for img in sorted(kf_root.rglob("*.jpg")):
            rel = img.relative_to(work).as_posix()
            keyframes.append(
                {
                    "path": rel,
                    "window_id": img.parent.name,
                }
            )

    moments_count = 0
    dedup_removed = 0
    skill = None
    if plan and plan.exists():
        data = json.loads(plan.read_text())
        moments_count = len(data.get("moments") or [])
        skill = data.get("skill")

    manifest: dict[str, Any] = {
        "updated_at": datetime.now(UTC).isoformat(),
        "storage": "local_disk",
        "paths": {
            "job_dir": str(job_dir),
            "work_dir": str(work),
            "video": str(video) if video.exists() else None,
        },
        "artifacts": {
            "video": {
                "ready": video.exists(),
                "url": "/api/jobs/{job_id}/video",
            },
            "cv1_shots": {
                "ready": shots is not None and shots.exists(),
                "path": shots.name if shots else None,
                "count": _count_json_list(shots),
                "preview_count": len(list((work / "shot_thumbs").glob("*.jpg")))
                if (work / "shot_thumbs").is_dir()
                else 0,
            },
            "cv2_keyframes": {
                "ready": len(keyframes) > 0,
                "count": len(keyframes),
                "items": keyframes[:48],
            },
            "plan": {
                "ready": plan is not None and plan.exists(),
                "moments": moments_count,
                "skill": skill,
            },
            "transcript": {
                "ready": bool(transcript and transcript.exists()),
                "segments": _count_json_list(transcript),
            },
            "summary": {
                "ready": summary.exists(),
            },
            "cv3_dedup": {
                "ready": plan is not None and plan.exists(),
                "note": "Deduped moments reflected in plan.json",
            },
        },
    }
    return manifest


def _count_json_list(path: Path | None) -> int:
    if not path or not path.exists():
        return 0
    try:
        data = json.loads(path.read_text())
        return len(data) if isinstance(data, list) else 0
    except json.JSONDecodeError:
        return 0


def write_manifest(job_dir: Path) -> dict[str, Any]:
    manifest = scan_artifacts(job_dir)
    manifest_path(job_dir).write_text(json.dumps(manifest, indent=2))
    return manifest


def load_manifest(job_dir: Path, job_id: str) -> dict[str, Any]:
    path = manifest_path(job_dir)
    if path.exists():
        manifest = json.loads(path.read_text())
    else:
        manifest = scan_artifacts(job_dir)
    return _inject_job_urls(manifest, job_id)


def _inject_job_urls(manifest: dict[str, Any], job_id: str) -> dict[str, Any]:
    arts = manifest.get("artifacts") or {}
    if arts.get("video", {}).get("ready"):
        arts["video"]["url"] = f"/api/jobs/{job_id}/video"
    kf = arts.get("cv2_keyframes") or {}
    for item in kf.get("items") or []:
        p = item.get("path", "")
        item["url"] = f"/api/jobs/{job_id}/artifact-file?path={p}"
    return manifest


def safe_work_path(work: Path, rel: str) -> Path:
    """Resolve path under work/; block traversal."""
    rel = rel.lstrip("/").replace("\\", "/")
    if ".." in rel.split("/"):
        raise ValueError("invalid path")
    full = (work / rel).resolve()
    if not str(full).startswith(str(work.resolve())):
        raise ValueError("invalid path")
    return full
