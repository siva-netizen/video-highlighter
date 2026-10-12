"""End-to-end orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from hl.agent import run_agent
from hl.audio import audio_energy_zscore, extract_audio
from hl.dedup import dedup_moments
from hl.keyframes import score_clip_keyframes
from hl.event_sink import emit
from hl.progress import ProgressFn, pct_at_stage_end, pct_at_stage_start
from hl.render import render_highlights
from hl.shot_previews import export_shot_thumbnails
from hl.shots import detect_shots
from hl.snap import picks_to_clips
from hl.transcribe import transcribe
from hl.windows import build_windows, save_windows


def _score_keyframes(
    video_path: Path,
    clips: list[dict],
    keyframes_root: Path,
    work_dir: Path,
    on_progress: ProgressFn | None,
) -> list[dict]:
    moments: list[dict] = []
    kf_start = pct_at_stage_start("keyframes")
    kf_end = pct_at_stage_end("keyframes")
    for i, c in enumerate(clips):
        if clips:
            sub = kf_start + int((i / len(clips)) * (kf_end - kf_start))
            _report(on_progress, "keyframes", f"Keyframe scoring clip {i + 1}/{len(clips)}", sub)
        existing = c.get("keyframes")
        if existing:
            moments.append(c)
            continue
        kfs = score_clip_keyframes(
            video_path,
            c["clip"]["start"],
            c["clip"]["end"],
            out_dir=keyframes_root / str(c["window_id"]),
            path_base=work_dir,
        )
        moments.append({**c, "keyframes": kfs})
    _report(on_progress, "keyframes", "Keyframes scored", kf_end)
    return moments


def _report(progress: ProgressFn | None, stage: str, message: str, pct: int) -> None:
    emit("stage", message, stage, {"progress_pct": pct})
    if progress:
        progress(stage, message, pct)


def run_pipeline(
    video_path: Path,
    *,
    work_dir: Path,
    target_seconds: int = 120,
    skill: str = "auto",
    out_video: Path | None = None,
    on_progress: ProgressFn | None = None,
) -> dict:
    work_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem

    audio_path = work_dir / f"{stem}_audio.flac"
    _report(on_progress, "audio", "Extracting audio (ffmpeg)", pct_at_stage_start("audio"))
    if not audio_path.is_file():
        extract_audio(video_path, audio_path)
    _report(on_progress, "audio", "Audio extracted", pct_at_stage_end("audio"))

    transcript_path = work_dir / f"{stem}_transcript.json"
    _report(on_progress, "transcribe", "Transcribing commentary (Groq Whisper)", pct_at_stage_start("transcribe"))
    segments = transcribe(audio_path, transcript_path)
    _report(on_progress, "transcribe", "Transcript ready", pct_at_stage_end("transcribe"))

    energy_path = work_dir / f"{stem}_energy.json"
    _report(on_progress, "energy", "Measuring audio energy", pct_at_stage_start("energy"))
    if energy_path.is_file():
        energy = json.loads(energy_path.read_text())
    else:
        energy = audio_energy_zscore(audio_path, energy_path)
    _report(on_progress, "energy", "Energy curve computed", pct_at_stage_end("energy"))

    shots_path = work_dir / f"{stem}_shots.json"
    _report(on_progress, "shots", "Detecting shot boundaries (CV-1)", pct_at_stage_start("shots"))
    shots = detect_shots(video_path, shots_path)
    thumbs_index = work_dir / "shot_thumbs" / "index.json"
    if not thumbs_index.is_file() and shots:
        export_shot_thumbnails(video_path, shots, work_dir / "shot_thumbs")
    _report(on_progress, "shots", "Shots detected", pct_at_stage_end("shots"))

    windows_path = work_dir / f"{stem}_windows.json"
    _report(on_progress, "windows", "Building transcript windows", pct_at_stage_start("windows"))
    if windows_path.is_file():
        windows = json.loads(windows_path.read_text())
    else:
        windows = build_windows(segments, energy)
        save_windows(windows, windows_path)
    _report(on_progress, "windows", "Windows ready", pct_at_stage_end("windows"))

    plan_path = work_dir / f"{stem}_plan.json"
    keyframes_root = work_dir / "keyframes"
    moments: list[dict] = []

    if plan_path.is_file():
        plan_cached = json.loads(plan_path.read_text())
        cached_moments = list(plan_cached.get("moments") or [])
        skill_used = plan_cached.get("skill", skill)
        if cached_moments and all(m.get("keyframes") for m in cached_moments):
            moments = cached_moments
            _report(
                on_progress,
                "agent",
                f"Reusing saved plan ({skill_used})",
                pct_at_stage_end("agent"),
            )
            _report(on_progress, "keyframes", "Keyframes already on disk", pct_at_stage_end("keyframes"))
            agent_out = {"skill": skill_used}
        elif cached_moments:
            _report(
                on_progress,
                "agent",
                f"Resuming saved plan ({skill_used})",
                pct_at_stage_end("agent"),
            )
            agent_out = {"skill": skill_used}
            moments = _score_keyframes(
                video_path,
                cached_moments,
                keyframes_root,
                work_dir,
                on_progress,
            )
        else:
            _report(on_progress, "agent", "Agent scoring highlights (router + skills)", pct_at_stage_start("agent"))
            agent_out = run_agent(windows, skill_name=skill, target_seconds=target_seconds)
            clips = picks_to_clips(agent_out["picks"], windows, shots)
            _report(on_progress, "agent", f"Agent selected skill: {agent_out['skill']}", pct_at_stage_end("agent"))
            moments = _score_keyframes(
                video_path,
                clips,
                keyframes_root,
                work_dir,
                on_progress,
            )
    else:
        _report(on_progress, "agent", "Agent scoring highlights (router + skills)", pct_at_stage_start("agent"))
        agent_out = run_agent(windows, skill_name=skill, target_seconds=target_seconds)
        clips = picks_to_clips(agent_out["picks"], windows, shots)
        _report(on_progress, "agent", f"Agent selected skill: {agent_out['skill']}", pct_at_stage_end("agent"))
        moments = _score_keyframes(
            video_path,
            clips,
            keyframes_root,
            work_dir,
            on_progress,
        )

    _report(on_progress, "dedup", "Removing duplicate replays (CV-3)", pct_at_stage_start("dedup"))
    moments = dedup_moments(moments, work_dir=work_dir)
    _report(on_progress, "dedup", "Dedup complete", pct_at_stage_end("dedup"))

    plan = {
        "skill": agent_out["skill"],
        "target_seconds": target_seconds,
        "moments": moments,
    }
    plan_path.write_text(json.dumps(plan, indent=2))

    _report(on_progress, "render", "Rendering highlight video", pct_at_stage_start("render"))
    out = out_video or work_dir / "highlights.mp4"
    if not out.is_file() or out.stat().st_size == 0:
        render_highlights(video_path, moments, out)
    _report(on_progress, "render", "Render complete", pct_at_stage_end("render"))

    summary_path = work_dir / "summary.md"
    summary_path.write_text(
        _summary_md(video_path, plan, out),
    )

    _report(on_progress, "done", "Highlight package ready", 100)

    return {"plan_path": plan_path, "video_path": out, "summary_path": summary_path}


def _summary_md(video: Path, plan: dict, out: Path) -> str:
    lines = [
        f"# Highlight summary",
        "",
        f"- Source: `{video.name}`",
        f"- Skill: **{plan.get('skill')}**",
        f"- Target: {plan.get('target_seconds')}s",
        f"- Moments: {len(plan.get('moments', []))}",
        f"- Output: `{out.name}`",
        "",
        "## Moments",
    ]
    for m in plan.get("moments", []):
        clip = m["clip"]
        lines.append(
            f"- **{m.get('label', '?')}** ({clip['start']:.1f}s–{clip['end']:.1f}s): "
            f"{m.get('reason', '')}"
        )
    return "\n".join(lines) + "\n"
