"""Pipeline progress stages for job governance UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

ProgressFn = Callable[[str, str, int], None]


@dataclass(frozen=True)
class PipelineStage:
    id: str
    label: str
    weight: int


PIPELINE_STAGES: tuple[PipelineStage, ...] = (
    PipelineStage("audio", "Extracting audio (ffmpeg)", 5),
    PipelineStage("transcribe", "Transcribing commentary (Groq Whisper)", 28),
    PipelineStage("energy", "Measuring audio energy", 4),
    PipelineStage("shots", "Detecting shot boundaries (CV-1)", 14),
    PipelineStage("windows", "Building transcript windows", 3),
    PipelineStage("agent", "Agent scoring highlights (router + skills)", 26),
    PipelineStage("keyframes", "Scoring keyframes (CV-2)", 12),
    PipelineStage("dedup", "Removing duplicate replays (CV-3)", 3),
    PipelineStage("render", "Rendering highlight video", 5),
)

_CUMULATIVE: list[tuple[str, int]] = []
_acc = 0
for s in PIPELINE_STAGES:
    _acc += s.weight
    _CUMULATIVE.append((s.id, _acc))


def pct_at_stage_start(stage_id: str) -> int:
    for sid, cum in _CUMULATIVE:
        if sid == stage_id:
            for s in PIPELINE_STAGES:
                if s.id == stage_id:
                    return cum - s.weight
            break
    return 0


def pct_at_stage_end(stage_id: str) -> int:
    for sid, cum in _CUMULATIVE:
        if sid == stage_id:
            return cum
    return 100


def estimate_completion_iso(started_at_iso: str, progress_pct: int) -> str | None:
    if progress_pct < 3:
        return None
    try:
        started = datetime.fromisoformat(started_at_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    now = datetime.now(UTC)
    elapsed = (now - started).total_seconds()
    if elapsed <= 0:
        return None
    total = elapsed * 100.0 / progress_pct
    remaining = max(0.0, total - elapsed)
    return (now + timedelta(seconds=remaining)).isoformat()
