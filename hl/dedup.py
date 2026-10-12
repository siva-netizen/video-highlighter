"""CV-3: perceptual hash + histogram duplicate removal."""

from __future__ import annotations

from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image


def _hist_corr(a: np.ndarray, b: np.ndarray) -> float:
    ha = cv2.calcHist([a], [0], None, [256], [0, 256])
    hb = cv2.calcHist([b], [0], None, [256], [0, 256])
    cv2.normalize(ha, ha)
    cv2.normalize(hb, hb)
    return float(cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL))


def dedup_moments(
    moments: list[dict],
    *,
    work_dir: Path | None = None,
    hamming_max: int = 8,
    hist_min: float = 0.95,
) -> list[dict]:
    kept: list[dict] = []
    hashes: list[imagehash.ImageHash] = []
    grays: list[np.ndarray] = []

    for m in moments:
        kfs = m.get("keyframes") or []
        if not kfs:
            kept.append(m)
            continue
        path = Path(kfs[0]["path"])
        if not path.is_absolute() and work_dir is not None:
            path = work_dir / path
        elif not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            kept.append(m)
            continue

        img = Image.open(path)
        h = imagehash.phash(img)
        gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        duplicate = False
        for i, (prev_h, prev_g) in enumerate(zip(hashes, grays)):
            if h - prev_h < hamming_max:
                duplicate = True
                break
            if gray is not None and prev_g is not None:
                if _hist_corr(gray, prev_g) > hist_min:
                    duplicate = True
                    break
        if duplicate:
            continue
        hashes.append(h)
        grays.append(gray if gray is not None else np.zeros((1, 1), dtype=np.uint8))
        kept.append(m)

    return kept
