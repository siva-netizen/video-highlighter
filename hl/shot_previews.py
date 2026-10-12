"""CV-1 preview frames: one thumbnail per detected shot."""

from __future__ import annotations

import json
from pathlib import Path

import cv2


def export_shot_thumbnails(
    video_path: Path,
    shots: list[dict],
    out_dir: Path,
    *,
    max_shots: int = 120,
) -> list[dict]:
    """Save JPG mid-frame per shot; return metadata list."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    index: list[dict] = []
    for shot in shots[:max_shots]:
        sid = int(shot["id"])
        start = float(shot["start"])
        end = float(shot["end"])
        t = start + (end - start) * 0.5
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        h, w = frame.shape[:2]
        if w > 480:
            scale = 480 / w
            frame = cv2.resize(frame, (480, int(h * scale)))
        dest = out_dir / f"{sid:04d}.jpg"
        cv2.imwrite(str(dest), frame)
        index.append(
            {
                "id": sid,
                "start": start,
                "end": end,
                "t": t,
                "path": f"shot_thumbs/{dest.name}",
            }
        )

    cap.release()
    (out_dir / "index.json").write_text(json.dumps(index, indent=2))
    return index


def load_shot_thumbnail_index(work_dir: Path) -> list[dict]:
    path = work_dir / "shot_thumbs" / "index.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())
