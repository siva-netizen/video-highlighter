"""CV-2: keyframe quality scoring."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _frame_ok(gray: np.ndarray) -> bool:
    mean_b = float(gray.mean())
    std_b = float(gray.std())
    if mean_b < 20 or mean_b > 235:
        return False
    if std_b < 15:
        return False
    return True


def score_clip_keyframes(
    video_path: Path,
    start: float,
    end: float,
    *,
    out_dir: Path,
    path_base: Path | None = None,
    max_frames: int = 3,
    sample_fps: float = 1.0,
) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    candidates: list[dict] = []
    prev_gray = None
    t = start
    idx = 0
    while t <= end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            t += 1.0 / sample_fps
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if not _frame_ok(gray):
            prev_gray = gray
            t += 1.0 / sample_fps
            continue
        sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        motion = 0.0
        if prev_gray is not None:
            motion = float(np.mean(np.abs(gray.astype(np.float32) - prev_gray.astype(np.float32))))
        candidates.append({"t": t, "sharpness": sharp, "motion": motion, "frame": frame})
        prev_gray = gray
        t += 1.0 / sample_fps
        idx += 1

    cap.release()
    if not candidates:
        return []

    sharp_vals = np.array([c["sharpness"] for c in candidates])
    mot_vals = np.array([c["motion"] for c in candidates])
    sn = (sharp_vals - sharp_vals.min()) / (float(np.ptp(sharp_vals)) + 1e-6)
    mn = (mot_vals - mot_vals.min()) / (float(np.ptp(mot_vals)) + 1e-6)
    for i, c in enumerate(candidates):
        c["score"] = float(sn[i] + mn[i])

    top = sorted(candidates, key=lambda c: c["score"], reverse=True)[:max_frames]
    results: list[dict] = []
    for i, c in enumerate(top):
        path = out_dir / f"{int(start)}_{i}.jpg"
        cv2.imwrite(str(path), c["frame"])
        rel_base = path_base or out_dir.parent
        results.append(
            {
                "t": c["t"],
                "sharpness": round(c["sharpness"], 2),
                "motion": round(c["motion"], 2),
                "path": str(path.relative_to(rel_base)),
            }
        )
    return results
