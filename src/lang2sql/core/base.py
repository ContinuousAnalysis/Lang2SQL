from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .hooks import TraceHook, NullHook, Event, now, ms, summarize
from .exceptions import ComponentError, Lang2SQLError


class BaseComponent(ABC):
    """
    All components are callables.
    - No global state schema enforced.
    - Hooks provide observability without building a graph engine.
    """

    def __init__(self, name: Optional[str] = None, hook: Optional[TraceHook] = None) -> None:
        self.name = name or self.__class__.__name__
        self.hook: TraceHook = hook or NullHook()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        t0 = now()
        self.hook.on_event(
            Event(
                name="component.run",
                component=self.name,
                phase="start",
                ts=t0,
                input_summary=f"args={summarize(args)} kwargs={summarize(kwargs)}",
            )
        )

        try:
            out = self.run(*args, **kwargs)
            t1 = now()
            self.hook.on_event(
                Event(
                    name="component.run",
                    component=self.name,
                    phase="end",
                    ts=t1,
                    duration_ms=ms(t0, t1),
                    output_summary=summarize(out),
                )
            )
            return out

        except Lang2SQLError as e:
            # Preserve domain-level errors (IntegrationMissingError, ValidationError, etc.)
            t1 = now()
            self.hook.on_event(
                Event(
                    name="component.run",
                    component=self.name,
                    phase="error",
                    ts=t1,
                    duration_ms=ms(t0, t1),
                    error=f"{type(e).__name__}: {e}",
                )
            )
            raise

        except Exception as e:
            # Wrap unexpected errors for consistent UX
            t1 = now()
            self.hook.on_event(
                Event(
                    name="component.run",
                    component=self.name,
                    phase="error",
                    ts=t1,
                    duration_ms=ms(t0, t1),
                    error=f"{type(e).__name__}: {e}",
                )
            )
            raise ComponentError(self.name, f"{type(e).__name__}: {e}", cause=e) from e

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class BaseFlow(ABC):
    """
    Define-by-run:
    - Users control control-flow (if/while/for) directly in Python.
    - We provide parts + presets, not a graph engine.
    """

    def __init__(self, name: Optional[str] = None, hook: Optional[TraceHook] = None) -> None:
        self.name = name or self.__class__.__name__
        self.hook: TraceHook = hook or NullHook()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        t0 = now()
        self.hook.on_event(Event(name="flow.run", component=self.name, phase="start", ts=t0))

        try:
            out = self.run(*args, **kwargs)
            t1 = now()
            self.hook.on_event(
                Event(name="flow.run", component=self.name, phase="end", ts=t1, duration_ms=ms(t0, t1))
            )
            return out

        except Lang2SQLError as e:
            # Preserve domain-level errors
            t1 = now()
            self.hook.on_event(
                Event(
                    name="flow.run",
                    component=self.name,
                    phase="error",
                    ts=t1,
                    duration_ms=ms(t0, t1),
                    error=f"{type(e).__name__}: {e}",
                )
            )
            raise

        except Exception as e:
            t1 = now()
            self.hook.on_event(
                Event(
                    name="flow.run",
                    component=self.name,
                    phase="error",
                    ts=t1,
                    duration_ms=ms(t0, t1),
                    error=f"{type(e).__name__}: {e}",
                )
            )
            raise

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError