"""CV-1: shot boundary detection via PySceneDetect."""

from __future__ import annotations

import json
from pathlib import Path

from scenedetect import ContentDetector, SceneManager, open_video

from hl.config import CONTENT_DETECTOR_THRESHOLD, MIN_SHOT_SECONDS


def detect_shots(video_path: Path, out_json: Path, *, force: bool = False) -> list[dict]:
    if out_json.exists() and not force:
        return json.loads(out_json.read_text())

    video = open_video(str(video_path))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=CONTENT_DETECTOR_THRESHOLD))
    manager.detect_scenes(video)
    scene_list = manager.get_scene_list()

    shots: list[dict] = []
    for i, (start, end) in enumerate(scene_list):
        s = start.get_seconds()
        e = end.get_seconds()
        if e - s < MIN_SHOT_SECONDS and shots:
            shots[-1]["end"] = e
            continue
        shots.append({"id": len(shots), "start": s, "end": e})

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(shots, indent=2))
    return shots
