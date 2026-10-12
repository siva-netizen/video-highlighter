"""LLM agent: router, scorer, critic (LangGraph-ready stubs + Groq calls)."""

from __future__ import annotations

import json
from typing import Any, TypedDict

from groq import Groq

from hl.config import CRITIC_MAX_LOOPS, ROUTER_MODEL, SCORER_MODEL, require_groq_key
from hl.skills import Skill, load_skill


class AgentState(TypedDict, total=False):
    skill: str
    windows: list[dict]
    picks: list[dict]
    target_seconds: int
    iteration: int
    critic_feedback: str


def route_skill(transcript_sample: str, *, skill_hint: str = "auto") -> str:
    if skill_hint and skill_hint != "auto":
        return skill_hint

    client = Groq(api_key=require_groq_key())
    prompt = (
        "Pick one skill name for this sports commentary sample: "
        "cricket, football, or generic. Reply JSON: {\"skill\": \"...\"}\n\n"
        f"{transcript_sample[:4000]}"
    )
    resp = client.chat.completions.create(
        model=ROUTER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    return data.get("skill", "generic")


def score_windows(
    skill: Skill,
    windows: list[dict],
    target_seconds: int,
    critic_feedback: str = "",
) -> list[dict]:
    client = Groq(api_key=require_groq_key())
    payload = {
        "skill": skill.name,
        "playbook": skill.body,
        "keywords": skill.keywords,
        "pre_roll": skill.pre_roll,
        "post_roll": skill.post_roll,
        "target_seconds": target_seconds,
        "windows": windows,
        "critic_feedback": critic_feedback,
    }
    prompt = (
        "Score windows for a highlight reel. Return JSON: "
        '{"picks":[{"window_id":int,"score":1-10,"label":str,'
        '"pad_before":float,"pad_after":float,"reason":str}]}\n\n'
        + json.dumps(payload)[:120000]
    )
    resp = client.chat.completions.create(
        model=SCORER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    picks = data.get("picks") or []
    for p in picks:
        p.setdefault("pad_before", skill.pre_roll)
        p.setdefault("pad_after", skill.post_roll)
    return picks


def critic_check(
    picks: list[dict],
    windows: list[dict],
    target_seconds: int,
) -> tuple[bool, str]:
    """Mostly deterministic critic; returns (ok, feedback)."""
    if not picks:
        return False, "No picks returned; select at least 3 moments."

    by_id = {w["id"]: w for w in windows}
    est = 0.0
    for p in picks:
        w = by_id.get(p.get("window_id"))
        if not w:
            continue
        pad_b = float(p.get("pad_before", 6))
        pad_a = float(p.get("pad_after", 6))
        est += (w["end"] - w["start"]) + pad_b + pad_a

    if est < target_seconds * 0.85 or est > target_seconds * 1.15:
        return False, (
            f"Estimated duration {est:.0f}s outside ±15% of target {target_seconds}s."
        )

    sorted_picks = sorted(picks, key=lambda p: by_id.get(p["window_id"], {}).get("start", 0))
    for i in range(len(sorted_picks) - 1):
        a = by_id.get(sorted_picks[i]["window_id"], {})
        b = by_id.get(sorted_picks[i + 1]["window_id"], {})
        if a and b and b.get("start", 0) - a.get("end", 0) < 20:
            ta = a.get("text", "")[:80]
            tb = b.get("text", "")[:80]
            if ta and ta == tb:
                return False, "Two picks within 20s with similar text; diversify."

    return True, ""


def run_agent(
    windows: list[dict],
    *,
    skill_name: str = "auto",
    target_seconds: int = 120,
) -> dict[str, Any]:
    sample = " ".join(w["text"] for w in windows[:15])[:8000]
    resolved = route_skill(sample, skill_hint=skill_name)
    skill = load_skill(resolved if resolved in ("cricket", "football", "generic") else "generic")

    feedback = ""
    picks: list[dict] = []
    for iteration in range(CRITIC_MAX_LOOPS + 1):
        picks = score_windows(skill, windows, target_seconds, feedback)
        ok, feedback = critic_check(picks, windows, target_seconds)
        if ok or iteration >= CRITIC_MAX_LOOPS:
            break

    return {
        "skill": skill.name,
        "target_seconds": target_seconds,
        "picks": picks,
        "iteration": iteration,
        "critic_feedback": feedback if not ok else "",
    }
