"""Tools exposed to the highlight agent (Groq function calling)."""

from __future__ import annotations

import json
from typing import Any

from hl.skills import SkillCatalogEntry, catalog_as_prompt_lines, discover_skill_catalog, load_skill


class WindowTools:
    def __init__(self, windows: list[dict], picks: list[dict] | None = None):
        self.windows = {w["id"]: w for w in windows}
        self.picks = list(picks or [])

    def get_window(self, window_id: int) -> dict[str, Any]:
        if window_id not in self.windows:
            return {"error": f"unknown window_id {window_id}"}
        return self.windows[window_id]

    def get_neighbors(self, window_id: int, n: int = 2) -> list[dict]:
        ids = sorted(self.windows)
        if window_id not in ids:
            return []
        idx = ids.index(window_id)
        lo = max(0, idx - n)
        hi = min(len(ids), idx + n + 1)
        return [self.windows[i] for i in ids[lo:hi]]

    def list_picks(self) -> dict[str, Any]:
        by_id = self.windows
        total = 0.0
        for p in self.picks:
            w = by_id.get(p.get("window_id"))
            span = 15.0
            if w:
                span = (w["end"] - w["start"]) + float(p.get("pad_before", 6)) + float(
                    p.get("pad_after", 6)
                )
            total += span
        return {"picks": self.picks, "estimated_seconds": round(total, 1)}

    def check_overlap(self, window_ids: list[int]) -> dict[str, Any]:
        issues: list[str] = []
        selected = [self.windows[i] for i in window_ids if i in self.windows]
        selected.sort(key=lambda w: w["start"])
        for i in range(len(selected) - 1):
            a, b = selected[i], selected[i + 1]
            gap = b["start"] - a["end"]
            if gap < 20:
                issues.append(
                    f"Windows {a['id']} and {b['id']} are {gap:.1f}s apart (<20s)"
                )
            ta, tb = a.get("text", "")[:120], b.get("text", "")[:120]
            if ta and tb and ta == tb:
                issues.append(f"Windows {a['id']} and {b['id']} have duplicate text")
        return {"issues": issues}

    def set_picks(self, picks: list[dict]) -> dict[str, Any]:
        self.picks = picks
        return self.list_picks()


def groq_tool_definitions() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_window",
                "description": "Fetch one scoring window by id (start, end, text, energy_peak).",
                "parameters": {
                    "type": "object",
                    "properties": {"window_id": {"type": "integer"}},
                    "required": ["window_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_neighbors",
                "description": "Fetch n windows before and after window_id for context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "window_id": {"type": "integer"},
                        "n": {"type": "integer", "default": 2},
                    },
                    "required": ["window_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_picks",
                "description": "Return current highlight picks and estimated total duration.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_overlap",
                "description": "Report time proximity and duplicate-text issues for window ids.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "window_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                        }
                    },
                    "required": ["window_ids"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_available_skills",
                "description": (
                    "List installed highlight skills (name + description). "
                    "Use before loading a playbook."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "load_skill_playbook",
                "description": (
                    "Load full scoring instructions for a skill by name "
                    "(progressive disclosure level 2+3)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"skill_name": {"type": "string"}},
                    "required": ["skill_name"],
                },
            },
        },
    ]


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    window_tools: WindowTools,
    catalog: list[SkillCatalogEntry],
) -> Any:
    if name == "get_window":
        return window_tools.get_window(int(arguments["window_id"]))
    if name == "get_neighbors":
        return window_tools.get_neighbors(
            int(arguments["window_id"]), int(arguments.get("n", 2))
        )
    if name == "list_picks":
        return window_tools.list_picks()
    if name == "check_overlap":
        ids = arguments.get("window_ids") or []
        return window_tools.check_overlap([int(i) for i in ids])
    if name == "list_available_skills":
        return {
            "skills": [
                {"name": e.name, "description": e.description} for e in catalog
            ],
            "prompt": catalog_as_prompt_lines(catalog),
        }
    if name == "load_skill_playbook":
        skill_name = str(arguments["skill_name"])
        skill = load_skill(skill_name)
        return {
            "name": skill.name,
            "description": skill.description,
            "pre_roll": skill.pre_roll,
            "post_roll": skill.post_roll,
            "keywords": skill.keywords,
            "playbook": skill.body,
        }
    return {"error": f"unknown tool {name}"}


def parse_tool_arguments(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
