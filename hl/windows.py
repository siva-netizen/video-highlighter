"""Stage 5: merge transcript + energy into scoring windows."""

from __future__ import annotations

import json
from pathlib import Path


def build_windows(
    segments: list[dict],
    energy: list[dict],
    *,
    window_seconds: float = 20.0,
    hop_seconds: float = 10.0,
) -> list[dict]:
    if not segments:
        return []

    end_time = max(s["end"] for s in segments)
    windows: list[dict] = []
    t = 0.0
    wid = 0
    while t < end_time:
        w_end = min(t + window_seconds, end_time)
        texts = [
            s["text"]
            for s in segments
            if s["end"] > t and s["start"] < w_end
        ]
        zs = [
            e["z"]
            for e in energy
            if t <= e["second"] < w_end
        ]
        peak = max(zs) if zs else 0.0
        windows.append(
            {
                "id": wid,
                "start": t,
                "end": w_end,
                "energy_peak": round(peak, 3),
                "text": " ".join(texts).strip(),
            }
        )
        wid += 1
        t += hop_seconds

    return windows


def save_windows(windows: list[dict], out_json: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(windows, indent=2))
