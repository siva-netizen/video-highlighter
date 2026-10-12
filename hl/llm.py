"""Groq chat completions with Gemini OpenAI-compat fallback on HTTP 429."""

from __future__ import annotations

import time
from typing import Any

from groq import APIStatusError, Groq, RateLimitError
from openai import OpenAI

from hl.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_OPENAI_BASE,
    require_groq_key,
)
from hl.event_sink import emit

GROQ_429_RETRIES = 2
GROQ_429_BACKOFF_SEC = 4.0


def _is_rate_limit(exc: BaseException) -> bool:
    code = getattr(exc, "status_code", None)
    if code == 429:
        return True
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "too many requests" in text


def _is_gemini_tool_history_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "thought_signature" in text or "function call is missing" in text


def plain_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gemini must never see assistant/tool turns from Groq tool loops."""
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role not in ("system", "user"):
            continue
        if m.get("tool_calls"):
            continue
        content = m.get("content")
        if content is None and role == "user":
            continue
        out.append({"role": role, "content": content or ""})
    if not out:
        raise RuntimeError("No system/user messages for LLM fallback")
    return out


def _gemini_client() -> OpenAI | None:
    if not GEMINI_API_KEY:
        return None
    return OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_OPENAI_BASE)


def _groq_create(kwargs: dict[str, Any]) -> Any:
    groq = Groq(api_key=require_groq_key())
    last: BaseException | None = None
    for attempt in range(GROQ_429_RETRIES):
        try:
            return groq.chat.completions.create(**kwargs)
        except (RateLimitError, APIStatusError) as exc:
            last = exc
            if not _is_rate_limit(exc) or attempt + 1 >= GROQ_429_RETRIES:
                raise
            emit(
                "system",
                "Groq rate limit (429)",
                f"retry in {GROQ_429_BACKOFF_SEC:.0f}s",
                {"attempt": attempt + 1},
            )
            time.sleep(GROQ_429_BACKOFF_SEC)
        except Exception as exc:
            if _is_rate_limit(exc) and attempt + 1 < GROQ_429_RETRIES:
                last = exc
                time.sleep(GROQ_429_BACKOFF_SEC)
                continue
            raise
    if last:
        raise last
    raise RuntimeError("Groq request failed")


def _gemini_create(
    messages: list[dict[str, Any]],
    *,
    purpose: str,
    response_format: dict[str, str] | None = None,
) -> Any:
    gemini = _gemini_client()
    if not gemini:
        raise RuntimeError(
            "Groq returned 429 (rate limit). Set GEMINI_API_KEY and GEMINI_MODEL for fallback."
        )
    plain = plain_messages(messages)
    emit(
        "system",
        "Gemini fallback",
        f"{purpose} · plain messages only (no tools)",
        {"model": GEMINI_MODEL, "message_count": len(plain)},
    )
    gkwargs: dict[str, Any] = {"model": GEMINI_MODEL, "messages": plain}
    if response_format is not None:
        gkwargs["response_format"] = response_format
    try:
        return gemini.chat.completions.create(**gkwargs)
    except Exception as exc:
        if response_format is not None and _is_gemini_tool_history_error(exc):
            raise
        if response_format is not None:
            emit("system", "Gemini JSON mode failed", str(exc)[:200], {})
            gkwargs.pop("response_format", None)
            return gemini.chat.completions.create(**gkwargs)
        raise


def chat_completions_create(
    *,
    groq_model: str,
    messages: list[dict[str, Any]],
    purpose: str,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = "auto",
    response_format: dict[str, str] | None = None,
) -> Any:
    """Call Groq; on 429 retry then Gemini (never tools / never tool-turn history)."""
    kwargs: dict[str, Any] = {"model": groq_model, "messages": messages}
    if tools is not None:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice or "auto"
    if response_format is not None:
        kwargs["response_format"] = response_format

    try:
        return _groq_create(kwargs)
    except (RateLimitError, APIStatusError) as exc:
        if not _is_rate_limit(exc):
            raise
    except Exception as exc:
        if not _is_rate_limit(exc):
            raise

    emit(
        "system",
        "Groq rate limit (429)",
        f"{purpose} · trying Gemini",
        {"groq_model": groq_model},
    )

    fmt = response_format
    if tools is not None:
        fmt = {"type": "json_object"}
    resp = _gemini_create(messages, purpose=purpose, response_format=fmt)
    emit(
        "agent",
        f"{purpose} via Gemini (fallback)",
        GEMINI_MODEL,
        {"after_groq_429": True, "json_only": tools is not None},
    )
    return resp


def chat_completions_json(
    *,
    groq_model: str,
    messages: list[dict[str, Any]],
    purpose: str,
) -> Any:
    """Groq JSON completion without tools; same Gemini fallback rules."""
    return chat_completions_create(
        groq_model=groq_model,
        messages=messages,
        purpose=purpose,
        tools=None,
        response_format={"type": "json_object"},
    )
