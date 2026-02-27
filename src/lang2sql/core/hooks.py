# lang2sql/core/hooks.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Optional, Literal
import time


@dataclass
class Event:
    name: str  # e.g., "component.run"
    component: str  # e.g., "KeywordTableRetriever"
    phase: Literal["start", "end", "error"]
    ts: float
    duration_ms: Optional[float] = None

    # human-friendly summaries (debug only)
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None

    # structured payload (for UI / filtering / tests)
    data: dict[str, Any] = field(default_factory=dict)


class TraceHook(Protocol):
    def on_event(self, event: Event) -> None: ...


class NullHook(TraceHook):
    def on_event(self, event: Event) -> None:
        return


class MemoryHook(TraceHook):
    def __init__(self) -> None:
        self.events: list[Event] = []

    def on_event(self, event: Event) -> None:
        self.events.append(event)

    def clear(self) -> None:
        self.events.clear()

    def snapshot(self) -> list[Event]:
        return list(self.events)


def now() -> float:
    return time.time()


def ms(start: float, end: float) -> float:
    return (end - start) * 1000.0


def summarize(x: Any, max_len: int = 240) -> str:
    try:
        s = repr(x)
    except Exception:
        s = f"<unreprable {type(x).__name__}>"
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s
