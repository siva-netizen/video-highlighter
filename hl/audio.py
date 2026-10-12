"""Stage 1 & 3: ffmpeg audio extract and per-second energy."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np


def extract_audio(video_path: Path, out_flac: Path) -> Path:
    out_flac.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(out_flac),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_flac


def audio_energy_zscore(audio_path: Path, out_json: Path) -> list[dict]:
    """Per-second RMS loudness with z-score (requires ffmpeg + numpy)."""
    cmd = [
        "ffmpeg",
        "-i",
        str(audio_path),
        "-f",
        "f32le",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True)
    samples = np.frombuffer(proc.stdout, dtype=np.float32)
    sr = 16000
    seconds = len(samples) // sr
    rms = []
    for i in range(seconds):
        chunk = samples[i * sr : (i + 1) * sr]
        rms.append(float(np.sqrt(np.mean(chunk**2)) + 1e-12))
    arr = np.array(rms)
    z = (arr - arr.mean()) / (arr.std() + 1e-12)
    series = [{"second": i, "rms": rms[i], "z": float(z[i])} for i in range(len(rms))]
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(series, indent=2))
    return series
