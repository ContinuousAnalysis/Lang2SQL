from __future__ import annotations

from typing import Iterable, Optional, Protocol, Sequence

from ..core.base import BaseFlow
from ..core.context import RunContext


class RunComponent(Protocol):
    """
    A pipeline step.

    Convention:
    - Prefer ctx-mutate style: return None and mutate `run` in-place.
    - For robustness, returning a RunContext is also accepted.
    """
    def __call__(self, run: RunContext) -> Optional[RunContext]: ...


class BaselineFlow(BaseFlow):
    """
    A minimal define-by-run pipeline runner.

    Default usage:
        flow = BaselineFlow(steps=[retriever, builder, generator, validator])
        run = flow.run_query("...")

    Advanced usage:
        class CustomFlow(BaselineFlow):
            def run(self, run: RunContext) -> RunContext:
                ...
    """

    def __init__(
        self,
        *,
        steps: Sequence[RunComponent],
        name: str | None = None,
        hook=None,
    ) -> None:
        super().__init__(name=name or "BaselineFlow", hook=hook)
        if not steps:
            raise ValueError("BaselineFlow requires at least one step.")
        self.steps: list[RunComponent] = list(steps)

    # ---- helpers for subclassing ----

    @staticmethod
    def _apply(step: RunComponent, run: RunContext) -> RunContext:
        """
        Apply a step to the RunContext.

        Contract:
        - Return None for ctx-mutate style.
        - Return RunContext for functional style.
        - Any other return type is considered a bug.
        """
        out = step(run)

        if out is None:
            return run

        if isinstance(out, RunContext):
            return out

        raise TypeError(
            f"Step must return None or RunContext, got {type(out).__name__}. "
            "If you want ctx-mutate style, do not return anything."
        )

    def _run_steps(self, run: RunContext, steps: Iterable[RunComponent] | None = None) -> RunContext:
        for step in (steps or self.steps):
            run = self._apply(step, run)
        return run

    # ---- BaseFlow API ----

    def run(self, run: RunContext) -> RunContext:
        return self._run_steps(run)

    def run_query(self, query: str) -> RunContext:
        # Beginner sugar API
        return self.run(RunContext(query=query))