#!/usr/bin/env python3
"""Validate Agent Skills layout under skills/ (Anthropic SKILL.md conventions)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED = {"anthropic", "claude"}
MAX_NAME = 64
MAX_DESC = 1024


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        raise ValueError("missing YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("unclosed frontmatter")
    import yaml

    data = yaml.safe_load(parts[1]) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data


def validate_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir.name}: missing SKILL.md"]

    meta = parse_frontmatter(skill_md.read_text())
    name = meta.get("name", "")
    desc = meta.get("description", "")

    if not name:
        errors.append(f"{skill_dir.name}: frontmatter missing name")
    elif len(name) > MAX_NAME:
        errors.append(f"{name}: name too long")
    elif not NAME_RE.match(name):
        errors.append(f"{name}: name must be kebab-case lowercase")
    elif name in RESERVED or any(r in name for r in RESERVED):
        errors.append(f"{name}: reserved word in name")
    elif name != skill_dir.name:
        errors.append(f"{name}: folder must match name field ({skill_dir.name})")

    if not desc:
        errors.append(f"{skill_dir.name}: missing description")
    elif len(desc) > MAX_DESC:
        errors.append(f"{skill_dir.name}: description over {MAX_DESC} chars")
    elif "<" in desc or ">" in desc:
        errors.append(f"{skill_dir.name}: description must not contain XML tags")

    if (skill_dir / "README.md").exists():
        errors.append(f"{skill_dir.name}: remove README.md (use SKILL.md / references/)")

    return errors


def main() -> int:
    all_errors: list[str] = []
    for path in sorted(SKILLS_ROOT.iterdir()):
        if not path.is_dir() or path.name == "scripts":
            continue
        all_errors.extend(validate_skill_dir(path))

    if all_errors:
        for e in all_errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print("OK: all skills valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
