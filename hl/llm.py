"""Groq chat completions with Gemini OpenAI-compat fallback on HTTP 429."""

from __future__ import annotations

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


def _is_rate_limit(exc: BaseException) -> bool:
    code = getattr(exc, "status_code", None)
    if code == 429:
        return True
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "too many requests" in text


def _gemini_client() -> OpenAI | None:
    if not GEMINI_API_KEY:
        return None
    return OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_OPENAI_BASE)


def chat_completions_create(
    *,
    groq_model: str,
    messages: list[dict[str, Any]],
    purpose: str,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = "auto",
    response_format: dict[str, str] | None = None,
) -> Any:
    """Call Groq; on 429 retry same request on Gemini if configured."""
    groq = Groq(api_key=require_groq_key())
    kwargs: dict[str, Any] = {"model": groq_model, "messages": messages}
    if tools is not None:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice or "auto"
    if response_format is not None:
        kwargs["response_format"] = response_format

    try:
        return groq.chat.completions.create(**kwargs)
    except (RateLimitError, APIStatusError) as exc:
        if not _is_rate_limit(exc):
            raise
        emit(
            "system",
            "Groq rate limit (429)",
            f"{purpose} · trying Gemini",
            {"groq_model": groq_model},
        )
    except Exception as exc:
        if not _is_rate_limit(exc):
            raise
        emit(
            "system",
            "Groq rate limit (429)",
            f"{purpose} · trying Gemini",
            {"groq_model": groq_model},
        )

    gemini = _gemini_client()
    if not gemini:
        raise RuntimeError(
            "Groq returned 429 (rate limit). Set GEMINI_API_KEY and GEMINI_MODEL for fallback."
        ) from None

    gkwargs: dict[str, Any] = {"model": GEMINI_MODEL, "messages": messages}
    if tools is not None:
        gkwargs["tools"] = tools
        gkwargs["tool_choice"] = tool_choice or "auto"
    if response_format is not None:
        gkwargs["response_format"] = response_format

    try:
        resp = gemini.chat.completions.create(**gkwargs)
        emit(
            "agent",
            f"{purpose} via Gemini (fallback)",
            GEMINI_MODEL,
            {"after_groq_429": True},
        )
        return resp
    except Exception as exc:
        if tools is None:
            raise exc

    # Scorer: Gemini may reject tools — one-shot JSON without tools
    emit(
        "system",
        "Gemini tool fallback",
        "JSON-only scorer (no tools)",
        {"model": GEMINI_MODEL},
    )
    plain = [m for m in messages if m.get("role") != "tool"]
    if plain and plain[0].get("role") == "system":
        plain[0] = {
            **plain[0],
            "content": plain[0]["content"]
            + "\nTools unavailable on fallback — use windows_index in the user message only.",
        }
    return gemini.chat.completions.create(
        model=GEMINI_MODEL,
        messages=plain,
        response_format={"type": "json_object"},
    )
