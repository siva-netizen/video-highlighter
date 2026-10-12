"""Stage 2: Groq Whisper with chunking and disk cache."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from groq import Groq

from hl.config import STT_MODEL, WHISPER_CHUNK_SECONDS, require_groq_key


def _duration_seconds(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(out.stdout.strip())


def _split_chunk(audio_path: Path, start: float, duration: float, dest: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-i",
        str(audio_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def transcribe(audio_path: Path, out_json: Path, *, force: bool = False) -> list[dict]:
    if out_json.exists() and not force:
        return json.loads(out_json.read_text())

    client = Groq(api_key=require_groq_key())
    duration = _duration_seconds(audio_path)
    segments: list[dict] = []
    offset = 0.0

    while offset < duration:
        chunk_len = min(WHISPER_CHUNK_SECONDS, duration - offset)
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as tmp:
            chunk_path = Path(tmp.name)
        try:
            _split_chunk(audio_path, offset, chunk_len, chunk_path)
            with chunk_path.open("rb") as f:
                resp = client.audio.transcriptions.create(
                    file=f,
                    model=STT_MODEL,
                    response_format="verbose_json",
                )
            raw = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)
            for seg in raw.get("segments") or []:
                segments.append(
                    {
                        "start": float(seg["start"]) + offset,
                        "end": float(seg["end"]) + offset,
                        "text": (seg.get("text") or "").strip(),
                    }
                )
        finally:
            chunk_path.unlink(missing_ok=True)
        offset += chunk_len

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(segments, indent=2))
    return segments
