"""FastAPI backend for the highlight maker web UI."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hl.event_sink import reset_event_sink, set_event_sink
from hl.job_events import append_event, read_events
from hl.progress import estimate_completion_iso

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from hl.artifacts import job_work_dir, load_manifest, safe_work_path, write_manifest
from hl.checkpoint import find_source_video, job_can_resume, resume_hint
from hl.config import DEFAULT_WORK_DIR
from hl.job_stale import job_looks_stale, reconcile_stale_job
from hl.shot_previews import export_shot_thumbnails, load_shot_thumbnail_index
from hl.jobs_registry import list_jobs
from hl.pipeline import run_pipeline
from hl.skills import discover_skill_catalog, list_skills

app = FastAPI(title="Highlight Maker API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:8800",
        "http://127.0.0.1:8800",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS_ROOT = DEFAULT_WORK_DIR / "jobs"


def _job_path(job_id: str) -> Path:
    return JOBS_ROOT / job_id


def _read_meta(job_id: str) -> dict[str, Any]:
    path = _job_path(job_id) / "job.json"
    if not path.exists():
        raise HTTPException(404, "Job not found")
    return json.loads(path.read_text())


def _write_meta(job_id: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(UTC).isoformat()
    path = _job_path(job_id) / "job.json"
    path.write_text(json.dumps(data, indent=2))


def _read_meta_fresh(job_id: str) -> dict[str, Any]:
    meta = _read_meta(job_id)
    fixed = reconcile_stale_job(meta)
    if fixed.get("status") != meta.get("status") or fixed.get("error") != meta.get("error"):
        _write_meta(job_id, fixed)
        return fixed
    return meta


def _apply_progress(job_id: str, stage: str, message: str, pct: int) -> None:
    meta = _read_meta(job_id)
    meta["status"] = "running"
    meta["stage"] = stage
    meta["progress_stage"] = stage
    meta["progress_message"] = message
    meta["progress_pct"] = min(100, max(0, pct))
    started = meta.get("started_at")
    if started:
        eta = estimate_completion_iso(started, meta["progress_pct"])
        if eta:
            meta["estimated_completion_at"] = eta
    _write_meta(job_id, meta)
    try:
        write_manifest(_job_path(job_id))
    except OSError:
        pass


def _run_job(
    job_id: str,
    video_path: Path,
    target: int,
    skill: str,
    *,
    resume: bool = False,
) -> None:
    job_dir = _job_path(job_id)
    work_dir = job_dir / "work"
    out_video = job_dir / "highlights.mp4"
    meta = _read_meta(job_id)
    try:
        meta["status"] = "running"
        meta["stage"] = "starting"
        if resume:
            meta.pop("error", None)
            meta["resumed_at"] = datetime.now(UTC).isoformat()
            meta["progress_message"] = resume_hint(work_dir, video_path.stem)
            if not meta.get("started_at"):
                meta["started_at"] = datetime.now(UTC).isoformat()
        else:
            meta["started_at"] = datetime.now(UTC).isoformat()
            meta["progress_pct"] = 0
            meta["progress_message"] = "Starting pipeline"
        meta["updated_at"] = datetime.now(UTC).isoformat()
        _write_meta(job_id, meta)

        def on_progress(stage: str, message: str, pct: int) -> None:
            _apply_progress(job_id, stage, message, pct)

        def on_event(kind: str, title: str, detail: str, data: dict | None) -> None:
            append_event(job_dir, kind=kind, title=title, detail=detail, data=data)

        token = set_event_sink(on_event)
        if resume:
            append_event(
                job_dir,
                kind="system",
                title="Session resumed",
                detail=meta.get("progress_message", "Continuing from disk artifacts"),
                data={"target_seconds": target, "skill": skill},
            )
        else:
            append_event(
                job_dir,
                kind="system",
                title="Job started",
                detail=video_path.name,
                data={"target_seconds": target, "skill": skill},
            )
        try:
            result = run_pipeline(
                video_path,
                work_dir=work_dir,
                target_seconds=target,
                skill=skill,
                out_video=out_video,
                on_progress=on_progress,
            )
        finally:
            reset_event_sink(token)
        meta = _read_meta(job_id)
        meta["status"] = "completed"
        meta["stage"] = "done"
        meta["progress_pct"] = 100
        meta["progress_message"] = "Complete"
        meta["result"] = {k: str(v) for k, v in result.items()}
        meta["video_url"] = f"/api/jobs/{job_id}/video"
        plan_path = Path(result["plan_path"])
        if plan_path.exists():
            meta["skill"] = json.loads(plan_path.read_text()).get("skill", skill)
        meta.pop("estimated_completion_at", None)
        _write_meta(job_id, meta)
        write_manifest(job_dir)
    except Exception as exc:  # noqa: BLE001 — surface to UI
        meta = _read_meta(job_id)
        meta["status"] = "failed"
        meta["error"] = str(exc)
        _write_meta(job_id, meta)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/skills")
def api_skills() -> list[dict[str, str]]:
    return [
        {"name": e.name, "description": e.description}
        for e in discover_skill_catalog()
    ]


@app.get("/api/skills/names")
def api_skill_names() -> list[str]:
    return list_skills()


@app.post("/api/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    target_seconds: int = Form(120),
    skill: str = Form("auto"),
) -> dict[str, str]:
    if target_seconds < 60 or target_seconds > 300:
        raise HTTPException(400, "target_seconds must be between 60 and 300 (5 min max)")
    skill = "auto"
    job_id = uuid.uuid4().hex[:12]
    job_dir = _job_path(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(video.filename or "upload.mp4").suffix or ".mp4"
    dest = job_dir / f"source{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(video.file, f)

    meta = {
        "id": job_id,
        "status": "queued",
        "stage": "queued",
        "filename": video.filename,
        "target_seconds": target_seconds,
        "skill": skill,
        "progress_pct": 0,
        "progress_message": "Queued — waiting for worker",
        "created_at": datetime.now(UTC).isoformat(),
    }
    _write_meta(job_id, meta)
    background_tasks.add_task(_run_job, job_id, dest, target_seconds, skill)
    return {"job_id": job_id}


@app.post("/api/jobs/{job_id}/resume")
def resume_job(job_id: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    job_dir = _job_path(job_id)
    if not job_dir.is_dir():
        raise HTTPException(404, "Job not found")
    meta = _read_meta_fresh(job_id)
    if meta.get("status") in ("running", "queued") and not job_looks_stale(meta):
        raise HTTPException(409, "Job is still running — wait a moment or refresh.")
    if meta.get("status") in ("running", "queued") and job_looks_stale(meta):
        meta["status"] = "failed"
        meta["stage"] = "interrupted"
        meta["error"] = (
            f"Worker stopped at {meta.get('progress_pct', 0)}%. "
            "Continuing from saved artifacts."
        )
        _write_meta(job_id, meta)
    if not job_can_resume(job_dir, meta):
        raise HTTPException(
            400,
            "Nothing to resume — upload a new video or this session already finished.",
        )
    source = find_source_video(job_dir)
    if not source:
        raise HTTPException(404, "Source video missing from session folder")
    target = int(meta.get("target_seconds") or 120)
    skill = str(meta.get("skill") or "auto")
    meta["status"] = "queued"
    meta["stage"] = "queued"
    meta["progress_message"] = "Queued — resuming from saved artifacts"
    meta.pop("error", None)
    _write_meta(job_id, meta)
    background_tasks.add_task(_run_job, job_id, source, target, skill, resume=True)
    return {
        "job_id": job_id,
        "status": "queued",
        "resume_hint": resume_hint(job_work_dir(job_dir), source.stem),
    }


@app.get("/api/jobs")
def list_all_jobs(limit: int = 40) -> dict[str, Any]:
    jobs = list_jobs(JOBS_ROOT, limit=min(limit, 100))
    return {"jobs": jobs, "storage": "local_disk", "root": str(JOBS_ROOT)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    meta = _read_meta_fresh(job_id)
    job_dir = _job_path(job_id)
    meta["can_resume"] = job_can_resume(job_dir, meta)
    meta["looks_stale"] = job_looks_stale(meta)
    if meta["can_resume"]:
        work = job_work_dir(job_dir)
        source = find_source_video(job_dir)
        if source:
            meta["resume_hint"] = resume_hint(work, source.stem)
    return meta


@app.get("/api/jobs/{job_id}/events")
def get_job_events(job_id: str, after: int = 0, full: bool = False) -> dict[str, Any]:
    job_dir = _job_path(job_id)
    if not job_dir.exists():
        raise HTTPException(404, "Job not found")
    if full:
        events, next_cursor = read_events(job_dir, after=0)
        while True:
            batch, next_cursor = read_events(job_dir, after=next_cursor)
            if not batch:
                break
            events.extend(batch)
        return {"events": events, "next": next_cursor}
    events, next_cursor = read_events(job_dir, after=after)
    return {"events": events, "next": next_cursor}


@app.get("/api/jobs/{job_id}/video")
def get_job_video(job_id: str) -> FileResponse:
    path = _job_path(job_id) / "highlights.mp4"
    if not path.exists():
        raise HTTPException(404, "Video not ready")
    return FileResponse(path, media_type="video/mp4", filename="highlights.mp4")


@app.get("/api/jobs/{job_id}/plan")
def get_job_plan(job_id: str) -> dict[str, Any]:
    work = _job_path(job_id) / "work"
    plans = list(work.glob("*_plan.json"))
    if not plans:
        raise HTTPException(404, "Plan not ready")
    return json.loads(plans[0].read_text())


@app.get("/api/jobs/{job_id}/artifacts")
def get_job_artifacts(job_id: str) -> dict[str, Any]:
    job_dir = _job_path(job_id)
    if not job_dir.exists():
        raise HTTPException(404, "Job not found")
    return load_manifest(job_dir, job_id)


@app.get("/api/jobs/{job_id}/artifacts/transcript")
def get_job_transcript(job_id: str) -> list[dict[str, Any]]:
    work = job_work_dir(_job_path(job_id))
    hits = list(work.glob("*_transcript.json"))
    if not hits:
        raise HTTPException(404, "Transcript not ready")
    return json.loads(hits[0].read_text())


@app.get("/api/jobs/{job_id}/artifacts/shots")
def get_job_shots(job_id: str) -> dict[str, Any]:
    job_dir = _job_path(job_id)
    work = job_work_dir(job_dir)
    shot_files = list(work.glob("*_shots.json"))
    if not shot_files:
        raise HTTPException(404, "Shots not ready")
    shots: list[dict[str, Any]] = json.loads(shot_files[0].read_text())

    thumbs = load_shot_thumbnail_index(work)
    if not thumbs:
        sources = list(job_dir.glob("source.*"))
        if sources:
            thumbs = export_shot_thumbnails(sources[0], shots, work / "shot_thumbs")

    previews = [
        {
            **t,
            "thumb_url": f"/api/jobs/{job_id}/artifact-file?path={t['path']}",
        }
        for t in thumbs
    ]
    return {"shots": shots, "previews": previews, "count": len(shots)}


@app.get("/api/jobs/{job_id}/summary")
def get_job_summary(job_id: str) -> dict[str, str]:
    work = job_work_dir(_job_path(job_id))
    path = work / "summary.md"
    if not path.exists():
        raise HTTPException(404, "Summary not ready")
    return {"markdown": path.read_text()}


@app.get("/api/jobs/{job_id}/artifact-file")
def get_artifact_file(job_id: str, path: str) -> FileResponse:
    job_dir = _job_path(job_id)
    work = job_work_dir(job_dir)
    try:
        file_path = safe_work_path(work, path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not file_path.is_file():
        raise HTTPException(404, "File not found")
    media = "application/octet-stream"
    if file_path.suffix.lower() in {".jpg", ".jpeg"}:
        media = "image/jpeg"
    elif file_path.suffix.lower() == ".json":
        media = "application/json"
    return FileResponse(file_path, media_type=media)
