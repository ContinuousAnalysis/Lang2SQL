from __future__ import annotations

from typing import Iterable, Protocol, Sequence

from ..core.base import BaseFlow
from ..core.context import RunContext
from ..core.exceptions import ContractError


class RunComponent(Protocol):
    """
    Protocol for a pipeline component.

    A component is a callable that takes a RunContext and must return a RunContext.
    This enforces a strict "RunContext in -> RunContext out" contract.

    Args:
        run: The current RunContext.

    Returns:
        A RunContext instance (usually the same object, mutated in-place).
    """

    def __call__(self, run: RunContext) -> RunContext: ...


class SequentialFlow(BaseFlow):
    """
    A minimal sequential pipeline runner (define-by-run style).

    This flow runs `steps` in order. Each step must follow the contract:
        RunContext -> RunContext

    Notes:
        - Steps may mutate `run` in-place and still must return `run`.
        - Returning None or a non-RunContext value is treated as a contract bug and fails fast.

    Args:
        steps: Ordered sequence of pipeline components.
        name: Optional name override for tracing/logging.
        hook: Optional TraceHook. If not provided, a NullHook is used by BaseFlow.

    Returns:
        The final RunContext after running all steps.
    """

    def __init__(
        self,
        *,
        steps: Sequence[RunComponent],
        name: str | None = None,
        hook=None,
    ) -> None:
        """
        Initialize the flow with an ordered list of steps.

        Args:
            steps: Ordered sequence of pipeline components. Must be non-empty.
            name: Optional name override.
            hook: Optional TraceHook used by BaseFlow for flow-level events.

        Raises:
            ValueError: If `steps` is empty.
        """
        super().__init__(name=name or "SequentialFlow", hook=hook)
        if not steps:
            raise ValueError("SequentialFlow requires at least one step.")
        self.steps: list[RunComponent] = list(steps)

    @staticmethod
    def _apply(step: RunComponent, run: RunContext) -> RunContext:
        """
        Apply a single step with strict contract validation.

        Args:
            step: A pipeline component (callable).
            run: The current RunContext.

        Returns:
            The RunContext returned by the step.

        Raises:
            ContractError: If the step returns None or a non-RunContext value.
        """
        out = step(run)

        if isinstance(out, RunContext):
            return out

        got = "None" if out is None else type(out).__name__
        raise ContractError(
            f"Component must return RunContext (got {got}). Did you forget `return run`?"
        )

    def _run_steps(
        self, run: RunContext, steps: Iterable[RunComponent] | None = None
    ) -> RunContext:
        """
        Run an iterable of steps sequentially.

        Args:
            run: The initial RunContext.
            steps: Optional override iterable of steps. If None, uses `self.steps`.

        Returns:
            The final RunContext after applying all steps.
        """
        it = self.steps if steps is None else steps
        for step in it:
            run = self._apply(step, run)
        return run

    def run(self, run: RunContext) -> RunContext:
        """
        Execute the flow on the given RunContext.

        Args:
            run: The initial RunContext.

        Returns:
            The final RunContext after running all configured steps.
        """
        return self._run_steps(run)

    def run_query(self, query: str) -> RunContext:
        """
        Beginner-friendly sugar API.

        Args:
            query: Natural language question / user query.

        Returns:
            A RunContext initialized with `query` and processed by the flow.
        """
        return super().run_query(query)


# Backward-compatible alias (optional).
# Keeping this alias means existing imports `from lang2sql.flows... import BaselineFlow`
# continue to work without changes.
BaselineFlow = SequentialFlow
