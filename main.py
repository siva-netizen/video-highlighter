#!/usr/bin/env python3
"""CLI entrypoint: python main.py video.mp4 --target 120"""

from __future__ import annotations

import argparse
from pathlib import Path

from hl.config import DEFAULT_WORK_DIR
from hl.pipeline import run_pipeline
from hl.skills import list_skills


def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic highlight maker")
    parser.add_argument("video", type=Path, help="Input video file (~30 min)")
    parser.add_argument("--target", type=int, default=120, help="Target highlight duration (seconds)")
    skill_names = list_skills()
    parser.add_argument(
        "--skill",
        default="auto",
        choices=["auto", *skill_names],
        help="Skill playbook from skills/*/SKILL.md (auto = LLM router over catalog)",
    )
    parser.add_argument("--out", type=Path, default=None, help="Output highlights.mp4 path")
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR, help="Cache directory")
    args = parser.parse_args()

    if not args.video.exists():
        raise SystemExit(f"Video not found: {args.video}")

    result = run_pipeline(
        args.video,
        work_dir=args.work_dir,
        target_seconds=args.target,
        skill=args.skill,
        out_video=args.out,
    )
    print(f"Wrote {result['video_path']}")
    print(f"Plan: {result['plan_path']}")
    print(f"Summary: {result['summary_path']}")


if __name__ == "__main__":
    main()
