"""LangGraph highlight agent: dynamic skill catalog, tool-using scorer, critic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from groq import Groq
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from hl.agent_tools import (
    WindowTools,
    execute_tool,
    groq_tool_definitions,
    parse_tool_arguments,
)
from hl.config import CRITIC_MAX_LOOPS, ROUTER_MODEL, SCORER_MODEL, require_groq_key
from hl.event_sink import emit
from hl.skills import (
    Skill,
    SkillCatalogEntry,
    catalog_as_prompt_lines,
    discover_skill_catalog,
    fallback_skill_name,
    load_skill,
    resolve_skill_name,
)


class AgentState(TypedDict, total=False):
    windows: list[dict]
    target_seconds: int
    skill_hint: str
    catalog: list[dict]
    skill_name: str
    skill: dict
    picks: list[dict]
    iteration: int
    critic_feedback: str
    critic_ok: bool


def _catalog_from_state(state: AgentState) -> list[SkillCatalogEntry]:
    raw = state.get("catalog") or []
    if raw:
        return [
            SkillCatalogEntry(
                name=e["name"],
                description=e["description"],
                skill_md_path=Path(e["skill_md_path"]),
            )
            for e in raw
        ]
    return discover_skill_catalog()


def _serialize_catalog(catalog: list[SkillCatalogEntry]) -> list[dict]:
    return [
        {
            "name": e.name,
            "description": e.description,
            "skill_md_path": str(e.skill_md_path),
        }
        for e in catalog
    ]


def _skill_from_state(state: AgentState) -> Skill:
    s = state["skill"]
    return Skill(
        name=s["name"],
        description=s.get("description", ""),
        pre_roll=float(s.get("pre_roll", 6)),
        post_roll=float(s.get("post_roll", 6)),
        keywords=list(s.get("keywords") or []),
        body=s["body"],
    )


def _skill_to_dict(skill: Skill) -> dict:
    return {
        "name": skill.name,
        "description": skill.description,
        "pre_roll": skill.pre_roll,
        "post_roll": skill.post_roll,
        "keywords": skill.keywords,
        "body": skill.body,
    }


def route_skill_with_catalog(
    transcript_sample: str,
    catalog: list[SkillCatalogEntry],
    *,
    skill_hint: str = "auto",
) -> str:
    forced = resolve_skill_name(skill_hint, catalog)
    if forced:
        emit("agent", "Skill pinned", forced, {"skill": forced})
        return forced

    client = Groq(api_key=require_groq_key())
    emit(
        "agent",
        "Router request",
        f"model={ROUTER_MODEL}",
        {"catalog": [{"name": e.name} for e in catalog], "sample_chars": len(transcript_sample)},
    )
    names = {e.name for e in catalog}
    prompt = (
        "Choose the best highlight skill for this transcript sample.\n"
        "Reply JSON only: {\"skill\": \"<name>\"}\n\n"
        f"{catalog_as_prompt_lines(catalog)}\n\n"
        f"Transcript sample:\n{transcript_sample[:6000]}"
    )
    resp = client.chat.completions.create(
        model=ROUTER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    chosen = str(data.get("skill", "")).strip()
    if chosen in names:
        emit("agent", "Router response", f"skill={chosen}", {"raw": data})
        return chosen
    fb = fallback_skill_name(catalog)
    emit("agent", "Router fallback", f"skill={fb}", {"raw": data})
    return fb


def trim_picks_by_score(
    picks: list[dict],
    windows: list[dict],
    target_seconds: int,
) -> list[dict]:
    if not picks:
        return picks
    by_id = {w["id"]: w for w in windows}

    def est_seconds(p: dict) -> float:
        w = by_id.get(p.get("window_id"))
        if not w:
            return 15.0
        return (
            (w["end"] - w["start"])
            + float(p.get("pad_before", 6))
            + float(p.get("pad_after", 6))
        )

    ranked = sorted(picks, key=lambda p: (-int(p.get("score", 0)), p.get("window_id", 0)))
    kept: list[dict] = []
    total = 0.0
    for p in ranked:
        need = est_seconds(p)
        if total + need <= target_seconds * 1.15:
            kept.append(p)
            total += need
    if not kept and ranked:
        kept = [ranked[0]]
    kept.sort(key=lambda p: by_id.get(p["window_id"], {}).get("start", 0))
    return kept


def score_windows_with_tools(
    skill: Skill,
    windows: list[dict],
    target_seconds: int,
    catalog: list[SkillCatalogEntry],
    critic_feedback: str = "",
    *,
    max_rounds: int = 16,
) -> list[dict]:
    client = Groq(api_key=require_groq_key())
    wt = WindowTools(windows)
    tools = groq_tool_definitions()

    window_summary = [
        {
            "id": w["id"],
            "start": w["start"],
            "end": w["end"],
            "energy_peak": w.get("energy_peak"),
            "text_preview": (w.get("text") or "")[:200],
        }
        for w in windows
    ]

    system = (
        "You are a highlight Scorer. Use tools to inspect windows before finalizing.\n"
        "When done, respond with JSON only (no markdown): "
        '{"picks":[{"window_id":int,"score":1-10,"label":str,'
        '"pad_before":float,"pad_after":float,"reason":str}]}\n'
        "Respect the loaded skill playbook and target duration."
    )
    user = {
        "active_skill": skill.name,
        "playbook": skill.body,
        "keywords": skill.keywords,
        "default_pre_roll": skill.pre_roll,
        "default_post_roll": skill.post_roll,
        "target_seconds": target_seconds,
        "critic_feedback": critic_feedback,
        "windows_index": window_summary,
    }
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user)[:100000]},
    ]
    emit(
        "agent",
        "Scorer request",
        f"model={SCORER_MODEL} · windows={len(windows)}",
        {"skill": skill.name, "target_seconds": target_seconds, "critic_feedback": critic_feedback},
    )

    for round_i in range(max_rounds):
        resp = client.chat.completions.create(
            model=SCORER_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )
            for tc in tool_calls:
                args = parse_tool_arguments(tc.function.arguments)
                emit(
                    "tool",
                    f"Tool call · {tc.function.name}",
                    tc.function.arguments or "{}",
                    {"round": round_i + 1},
                )
                result = execute_tool(tc.function.name, args, wt, catalog)
                emit(
                    "tool",
                    f"Tool result · {tc.function.name}",
                    json.dumps(result)[:500],
                    {"round": round_i + 1},
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result)[:50000],
                    }
                )
            continue

        content = (msg.content or "").strip()
        if not content:
            continue
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        data = json.loads(content)
        picks = data.get("picks") if isinstance(data, dict) else data
        if not isinstance(picks, list):
            continue
        for p in picks:
            p.setdefault("pad_before", skill.pre_roll)
            p.setdefault("pad_after", skill.post_roll)
        wt.set_picks(picks)
        emit(
            "agent",
            "Scorer response",
            f"{len(picks)} picks",
            {"picks": picks},
        )
        return picks

    raise RuntimeError("Scorer exceeded tool rounds without returning picks JSON")


def critic_check(
    picks: list[dict],
    windows: list[dict],
    target_seconds: int,
    skill: Skill,
) -> tuple[bool, str]:
    if not picks:
        return False, "No picks returned; select at least 3 moments."

    by_id = {w["id"]: w for w in windows}
    est = 0.0
    for p in picks:
        w = by_id.get(p.get("window_id"))
        if not w:
            continue
        est += (w["end"] - w["start"]) + float(p.get("pad_before", skill.pre_roll)) + float(
            p.get("pad_after", skill.post_roll)
        )

    if est < target_seconds * 0.85:
        return False, (
            f"Estimated duration {est:.0f}s below target {target_seconds}s; add higher-score moments."
        )
    if est > target_seconds * 1.15:
        return False, (
            f"Estimated duration {est:.0f}s above target {target_seconds}s; drop lowest-score picks."
        )

    sorted_picks = sorted(
        picks, key=lambda p: by_id.get(p["window_id"], {}).get("start", 0)
    )
    for i in range(len(sorted_picks) - 1):
        a = by_id.get(sorted_picks[i]["window_id"], {})
        b = by_id.get(sorted_picks[i + 1]["window_id"], {})
        if a and b and b.get("start", 0) - a.get("end", 0) < 20:
            ta, tb = a.get("text", "")[:80], b.get("text", "")[:80]
            if ta and ta == tb:
                return False, "Two picks within 20s with similar text; diversify."

    return True, ""


def _node_init_catalog(state: AgentState) -> AgentState:
    catalog = discover_skill_catalog()
    emit(
        "system",
        "Skills discovered",
        f"{len(catalog)} playbooks on disk",
        {"skills": [{"name": e.name, "description": e.description[:120]} for e in catalog]},
    )
    return {"catalog": _serialize_catalog(catalog), "iteration": state.get("iteration", 0)}


def _node_router(state: AgentState) -> AgentState:
    catalog = _catalog_from_state(state)
    windows = state["windows"]
    sample = " ".join(w["text"] for w in windows[:20])[:8000]
    skill_name = route_skill_with_catalog(
        sample, catalog, skill_hint=state.get("skill_hint", "auto")
    )
    skill = load_skill(skill_name)
    emit("agent", "Skill loaded", skill.name, {"description": skill.description[:200]})
    return {"skill_name": skill.name, "skill": _skill_to_dict(skill)}


def _node_scorer(state: AgentState) -> AgentState:
    catalog = _catalog_from_state(state)
    skill = _skill_from_state(state)
    picks = score_windows_with_tools(
        skill,
        state["windows"],
        state["target_seconds"],
        catalog,
        state.get("critic_feedback") or "",
    )
    return {"picks": picks}


def _node_critic(state: AgentState) -> AgentState:
    skill = _skill_from_state(state)
    ok, feedback = critic_check(
        state.get("picks") or [],
        state["windows"],
        state["target_seconds"],
        skill,
    )
    emit(
        "agent",
        "Critic check",
        "pass" if ok else feedback,
        {"iteration": int(state.get("iteration") or 0) + 1, "ok": ok},
    )
    return {
        "critic_ok": ok,
        "critic_feedback": feedback,
        "iteration": int(state.get("iteration") or 0) + 1,
    }


def _node_trim(state: AgentState) -> AgentState:
    picks = trim_picks_by_score(
        state.get("picks") or [],
        state["windows"],
        state["target_seconds"],
    )
    emit("agent", "Duration trim", f"{len(picks)} picks kept", {"count": len(picks)})
    return {"picks": picks}


def _after_critic(state: AgentState) -> Literal["scorer", "trim"]:
    if state.get("critic_ok"):
        return "trim"
    if int(state.get("iteration") or 0) > CRITIC_MAX_LOOPS:
        return "trim"
    return "scorer"


def build_highlight_graph():
    g = StateGraph(AgentState)
    g.add_node("init_catalog", _node_init_catalog)
    g.add_node("router", _node_router)
    g.add_node("scorer", _node_scorer)
    g.add_node("critic", _node_critic)
    g.add_node("trim", _node_trim)

    g.set_entry_point("init_catalog")
    g.add_edge("init_catalog", "router")
    g.add_edge("router", "scorer")
    g.add_edge("scorer", "critic")
    g.add_conditional_edges("critic", _after_critic, {"scorer": "scorer", "trim": "trim"})
    g.add_edge("trim", END)
    return g.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_highlight_graph()
    return _GRAPH


def run_agent(
    windows: list[dict],
    *,
    skill_name: str = "auto",
    target_seconds: int = 120,
) -> dict[str, Any]:
    graph = get_graph()
    final = graph.invoke(
        {
            "windows": windows,
            "target_seconds": target_seconds,
            "skill_hint": skill_name,
            "iteration": 0,
            "critic_feedback": "",
        }
    )
    return {
        "skill": final.get("skill_name", "generic"),
        "target_seconds": target_seconds,
        "picks": final.get("picks") or [],
        "iteration": final.get("iteration", 0),
        "critic_feedback": final.get("critic_feedback") or "",
        "catalog": final.get("catalog") or [],
    }
