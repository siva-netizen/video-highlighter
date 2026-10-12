"""Stage 10: ffmpeg cut + concat with original audio."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def _cut_clip(video: Path, start: float, end: float, dest: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-to",
        str(end),
        "-i",
        str(video),
        "-c",
        "copy",
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

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    list_path.unlink(missing_ok=True)
    return out_mp4
