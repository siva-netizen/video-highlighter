"""Context-local event emitter for job activity streaming."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Callable

EventEmitter = Callable[[str, str, str, dict[str, Any] | None], None]

_sink: ContextVar[EventEmitter | None] = ContextVar("job_event_sink", default=None)


def set_event_sink(emitter: EventEmitter | None) -> Token:
    return _sink.set(emitter)


def reset_event_sink(token: Token) -> None:
    _sink.reset(token)


def emit(
    kind: str,
    title: str,
    detail: str = "",
    data: dict[str, Any] | None = None,
) -> None:
    fn = _sink.get()
    if fn:
        fn(kind, title, detail, data)
