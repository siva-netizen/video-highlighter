"""Load sport skill playbooks from skills/*.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from hl.config import SKILLS_DIR


@dataclass
class Skill:
    name: str
    description: str = ""
    pre_roll: float = 6.0
    post_roll: float = 6.0
    keywords: list[str] = field(default_factory=list)
    body: str = ""


def list_skills(skills_dir: Path | None = None) -> list[str]:
    root = skills_dir or SKILLS_DIR
    return sorted(p.stem for p in root.glob("*.md"))


def load_skill(name: str, skills_dir: Path | None = None) -> Skill:
    root = skills_dir or SKILLS_DIR
    path = root / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {path}")

    text = path.read_text()
    if text.startswith("---"):
        _, front, body = text.split("---", 2)
        meta = yaml.safe_load(front) or {}
    else:
        meta, body = {}, text

    return Skill(
        name=meta.get("name", name),
        description=meta.get("description", ""),
        pre_roll=float(meta.get("pre_roll", 6)),
        post_roll=float(meta.get("post_roll", 6)),
        keywords=list(meta.get("keywords") or []),
        body=body.strip(),
    )
