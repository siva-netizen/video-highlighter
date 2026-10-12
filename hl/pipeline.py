"""End-to-end orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from hl.agent import run_agent
from hl.audio import audio_energy_zscore, extract_audio
from hl.dedup import dedup_moments
from hl.keyframes import score_clip_keyframes
from hl.render import render_highlights
from hl.shots import detect_shots
from hl.snap import picks_to_clips
from hl.transcribe import transcribe
from hl.windows import build_windows, save_windows


def run_pipeline(
    video_path: Path,
    *,
    work_dir: Path,
    target_seconds: int = 120,
    skill: str = "auto",
    out_video: Path | None = None,
) -> dict:
    work_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem

    audio_path = work_dir / f"{stem}_audio.flac"
    extract_audio(video_path, audio_path)

    transcript_path = work_dir / f"{stem}_transcript.json"
    segments = transcribe(audio_path, transcript_path)

    energy_path = work_dir / f"{stem}_energy.json"
    energy = audio_energy_zscore(audio_path, energy_path)

    shots_path = work_dir / f"{stem}_shots.json"
    shots = detect_shots(video_path, shots_path)

    windows = build_windows(segments, energy)
    windows_path = work_dir / f"{stem}_windows.json"
    save_windows(windows, windows_path)

    agent_out = run_agent(windows, skill_name=skill, target_seconds=target_seconds)
    clips = picks_to_clips(agent_out["picks"], windows, shots)

    keyframes_root = work_dir / "keyframes"
    moments: list[dict] = []
    for c in clips:
        kfs = score_clip_keyframes(
            video_path,
            c["clip"]["start"],
            c["clip"]["end"],
            out_dir=keyframes_root / str(c["window_id"]),
            path_base=work_dir,
        )
        moments.append({**c, "keyframes": kfs})

    moments = dedup_moments(moments, work_dir=work_dir)

    plan = {
        "skill": agent_out["skill"],
        "target_seconds": target_seconds,
        "moments": moments,
    }
    plan_path = work_dir / f"{stem}_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2))

    out = out_video or work_dir / "highlights.mp4"
    render_highlights(video_path, moments, out)

    summary_path = work_dir / "summary.md"
    summary_path.write_text(
        _summary_md(video_path, plan, out),
    )

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
