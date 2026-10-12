"""Snap moment picks to shot boundaries (CV-1 post-processing)."""

from __future__ import annotations

from hl.config import MAX_CLIP_SECONDS, MIN_CLIP_SECONDS


def snap_moment(
    start: float,
    end: float,
    shots: list[dict],
    *,
    pad_before: float,
    pad_after: float,
) -> tuple[float, float]:
    want_start = start - pad_before
    want_end = end + pad_after

    clip_start = want_start
    for s in reversed(shots):
        if s["start"] <= want_start:
            clip_start = s["start"]
            break

    clip_end = want_end
    for s in shots:
        if s["end"] >= want_end:
            clip_end = s["end"]
            break

    length = clip_end - clip_start
    if length < MIN_CLIP_SECONDS:
        clip_end = clip_start + MIN_CLIP_SECONDS
    if length > MAX_CLIP_SECONDS:
        clip_end = clip_start + MAX_CLIP_SECONDS

    return clip_start, clip_end


def picks_to_clips(
    picks: list[dict],
    windows: list[dict],
    shots: list[dict],
) -> list[dict]:
    by_id = {w["id"]: w for w in windows}
    clips: list[dict] = []
    for p in picks:
        w = by_id.get(p["window_id"])
        if not w:
            continue
        cs, ce = snap_moment(
            w["start"],
            w["end"],
            shots,
            pad_before=float(p.get("pad_before", 6)),
            pad_after=float(p.get("pad_after", 6)),
        )
        clips.append(
            {
                "window_id": p["window_id"],
                "label": p.get("label", ""),
                "score": p.get("score", 0),
                "reason": p.get("reason", ""),
                "clip": {"start": cs, "end": ce},
            }
        )
    return clips
