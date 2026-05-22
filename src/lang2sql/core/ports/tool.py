"""Tool port — a single capability the agent can invoke.

Tools are ctx-aware: ``run`` receives the live :class:`HarnessContext` so a
tool can reach the explorer, semantic layer, safety pipeline, etc. without
globals. The harness advertises ``spec`` to the LLM and dispatches by ``name``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ..types import ToolResult, ToolSpec

if TYPE_CHECKING:  # avoid import cycle: harness imports core, not vice versa
    from ...harness.context import HarnessContext


@runtime_checkable
class ToolPort(Protocol):
    """One invocable capability (run_sql, explore_schema, define_metric, …)."""

    @property
    def spec(self) -> ToolSpec:
        """Name + description + JSON-Schema params advertised to the model."""
        ...

    async def run(self, args: dict[str, Any], ctx: "HarnessContext") -> ToolResult:
        """Execute with model-supplied ``args`` against the live context."""
        ...
