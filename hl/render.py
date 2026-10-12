"""Stage 10: ffmpeg cut + concat with original audio (A/V aligned)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

# Stream-copy + -ss before -i seeks video to keyframes while audio is sample-accurate → desync.
_VIDEO = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
_AUDIO = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
_SYNC = ["-reset_timestamps", "1", "-avoid_negative_ts", "make_zero"]


def _cut_clip(video: Path, start: float, end: float, dest: Path) -> None:
    duration = max(0.04, end - start)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        *_VIDEO,
        *_AUDIO,
        *_SYNC,
        "-movflags",
        "+faststart",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def render_highlights(
    video_path: Path,
    moments: list[dict],
    out_mp4: Path,
) -> Path:
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    clips_dir = out_mp4.parent / "clips"
    clips_dir.mkdir(exist_ok=True)

    clip_paths: list[Path] = []
    for i, m in enumerate(moments):
        clip = m["clip"]
        dest = clips_dir / f"clip_{i:03d}.mp4"
        _cut_clip(video_path, clip["start"], clip["end"], dest)
        clip_paths.append(dest)

    if not clip_paths:
        raise RuntimeError("No clips to render.")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lst:
        list_path = Path(lst.name)
        for p in clip_paths:
            lst.write(f"file '{p.resolve()}'\n")

    # Re-mux with encode so concat timestamps stay aligned (copy concat often offsets video vs audio).
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        *_VIDEO,
        *_AUDIO,
        "-vf",
        "setpts=PTS-STARTPTS",
        "-af",
        "asetpts=PTS-STARTPTS",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    list_path.unlink(missing_ok=True)
    return out_mp4
