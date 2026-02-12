from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .exceptions import ContractError
from .context import RunContext
from .exceptions import ComponentError, Lang2SQLError
from .hooks import Event, NullHook, TraceHook, ms, now, summarize


class BaseComponent(ABC):
    """
    Base class for all components.

    Design goals:
    - Components are plain callables (define-by-run friendly).
    - No enforced global state schema.
    - Hooks provide observability without requiring a graph engine.
    """

    def __init__(self, name: Optional[str] = None, hook: Optional[TraceHook] = None) -> None:
        self.name: str = name or self.__class__.__name__
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

            if args and isinstance(args[0], RunContext) and not isinstance(out, RunContext):
                got = "None" if out is None else type(out).__name__
                raise ContractError(f"{self.name} must return RunContext (got {got}). Did you forget `return run`?")
            
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
            # Preserve domain-level errors (IntegrationMissingError, ValidationError, etc.).
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
            # Wrap non-domain errors into ComponentError.
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
            raise ComponentError(
                self.name,
                f"component failed ({type(e).__name__}: {e})",
                cause=e,
            ) from e

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class BaseFlow(ABC):
    """
    Base class for flows.

    Define-by-run:
    - Users write control-flow in pure Python (if/for/while).
    - We provide parts + presets, not a graph engine.
    """

    def __init__(self, name: Optional[str] = None, hook: Optional[TraceHook] = None) -> None:
        self.name: str = name or self.__class__.__name__
        self.hook: TraceHook = hook or NullHook()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        t0 = now()
        self.hook.on_event(Event(name="flow.run", component=self.name, phase="start", ts=t0))

        try:
            out = self.run(*args, **kwargs)
            t1 = now()
            self.hook.on_event(
                Event(
                    name="flow.run",
                    component=self.name,
                    phase="end",
                    ts=t1,
                    duration_ms=ms(t0, t1),
                )
            )
            return out

        except Lang2SQLError as e:
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
    
    def run_query(self, query: str) -> RunContext:
        """
        Convenience entrypoint.

        Creates a RunContext(query=...) and runs the flow.
        Intended for demos / quickstart.

        Args:
            query: Natural language question.

        Returns:
            RunContext after running this flow.
        """
        out = self.run(RunContext(query=query))
        if not isinstance(out, RunContext):
            got = "None" if out is None else type(out).__name__
            raise TypeError(f"{self.name}.run(run: RunContext) must return RunContext, got {got}")
        return out