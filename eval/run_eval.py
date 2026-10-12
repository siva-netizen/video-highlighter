#!/usr/bin/env python3
"""Ablation metrics: event recall/precision, mid-shot rate, keyframe stats."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def overlap(a_start: float, a_end: float, b_start: float, b_end: float, tol: float = 5.0) -> bool:
    return not (a_end + tol < b_start or a_start - tol > b_end)


def event_metrics(plan: dict, events: list[dict]) -> dict:
    moments = plan.get("moments", [])
    tp = 0
    for ev in events:
        for m in moments:
            c = m["clip"]
            if overlap(c["start"], c["end"], ev["start"], ev["end"]):
                tp += 1
                break
    precision = tp / len(moments) if moments else 0.0
    recall = tp / len(events) if events else 0.0
    return {"tp": tp, "precision": precision, "recall": recall}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, default=Path(__file__).parent / "ground_truth.json")
    parser.add_argument("--video-id", default="cricket_sample")
    args = parser.parse_args()

    gt = json.loads(args.ground_truth.read_text())
    video = next(v for v in gt["videos"] if v["id"] == args.video_id)
    plan = json.loads(args.plan.read_text())
    print(json.dumps(event_metrics(plan, video["events"]), indent=2))


if __name__ == "__main__":
    main()
