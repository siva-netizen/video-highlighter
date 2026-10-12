"""Anthropic-style skill discovery and progressive loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from hl.config import SKILLS_DIR


@dataclass
class SkillCatalogEntry:
    """Level 1: name + description only (router / system prompt)."""

    name: str
    description: str
    skill_md_path: Path


@dataclass
class Skill:
    """Level 2+: full instructions for scorer."""

    name: str
    description: str = ""
    pre_roll: float = 6.0
    post_roll: float = 6.0
    keywords: list[str] = field(default_factory=list)
    body: str = ""
    skill_dir: Path | None = None


def _skill_dirs(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.iterdir()
        if p.is_dir() and p.name != "scripts" and (p / "SKILL.md").exists()
    )


def discover_skill_catalog(skills_dir: Path | None = None) -> list[SkillCatalogEntry]:
    """Scan skills/*/SKILL.md; read YAML frontmatter only."""
    root = skills_dir or SKILLS_DIR
    catalog: list[SkillCatalogEntry] = []
    for skill_dir in _skill_dirs(root):
        path = skill_dir / "SKILL.md"
        meta, _ = _parse_skill_md(path)
        name = str(meta.get("name") or skill_dir.name)
        desc = str(meta.get("description") or "").strip()
        catalog.append(
            SkillCatalogEntry(name=name, description=desc, skill_md_path=path)
        )
    return catalog


def list_skills(skills_dir: Path | None = None) -> list[str]:
    return [e.name for e in discover_skill_catalog(skills_dir)]


def catalog_as_prompt_lines(catalog: list[SkillCatalogEntry]) -> str:
    lines = ["Available skills (pick exactly one by `name`):"]
    for e in catalog:
        lines.append(f"- name: {e.name}\n  description: {e.description}")
    return "\n".join(lines)


def _parse_skill_md(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    if not text.startswith("---"):
        return {}, text.strip()
    _, front, body = text.split("---", 2)
    meta = yaml.safe_load(front) or {}
    return meta, body.strip()


def _keywords_from_meta(meta: dict) -> list[str]:
    raw = meta.get("keywords")
    if raw is None and isinstance(meta.get("metadata"), dict):
        raw = meta["metadata"].get("keywords")
    if isinstance(raw, list):
        return [str(k) for k in raw]
    if isinstance(raw, str):
        return [k.strip() for k in raw.split(",") if k.strip()]
    return []


def _rolls_from_meta(meta: dict, key: str, default: float) -> float:
    if key in meta:
        return float(meta[key])
    md = meta.get("metadata") or {}
    if isinstance(md, dict) and key in md:
        return float(md[key])
    return default


def load_skill(
    name: str,
    skills_dir: Path | None = None,
    *,
    include_references: bool = True,
) -> Skill:
    """Level 2 load: SKILL.md body; level 3 optional references/scoring-playbook.md."""
    root = skills_dir or SKILLS_DIR
    skill_dir = root / name
    path = skill_dir / "SKILL.md"
    if not path.exists():
        legacy = root / f"{name}.md"
        if legacy.exists():
            path = legacy
            skill_dir = root
        else:
            catalog = discover_skill_catalog(root)
            by_name = {e.name: e for e in catalog}
            if name not in by_name:
                raise FileNotFoundError(
                    f"Skill {name!r} not found. Available: {list(by_name)}"
                )
            path = by_name[name].skill_md_path
            skill_dir = path.parent

    meta, body = _parse_skill_md(path)

    if include_references:
        ref = skill_dir / "references" / "scoring-playbook.md"
        if ref.exists():
            body = f"{body}\n\n## Detailed playbook\n\n{ref.read_text().strip()}"

    return Skill(
        name=str(meta.get("name", name)),
        description=str(meta.get("description", "")),
        pre_roll=_rolls_from_meta(meta, "pre_roll", 6.0),
        post_roll=_rolls_from_meta(meta, "post_roll", 6.0),
        keywords=_keywords_from_meta(meta),
        body=body,
        skill_dir=skill_dir,
    )


def resolve_skill_name(hint: str, catalog: list[SkillCatalogEntry]) -> str | None:
    """If hint is a known skill name, return it; else None (use router)."""
    names = {e.name for e in catalog}
    if hint and hint != "auto" and hint in names:
        return hint
    return None


def fallback_skill_name(catalog: list[SkillCatalogEntry], preferred: str = "generic") -> str:
    names = [e.name for e in catalog]
    if not names:
        raise RuntimeError(f"No skills found under {SKILLS_DIR}")
    if preferred in names:
        return preferred
    return names[0]
