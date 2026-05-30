"""define_metric — scope-aware definition writer (★④ federation).

Writes one :class:`SemanticEntry` to a federation scope via the
:class:`ScopeResolverPort`. With no explicit scope it lands at the identity's
default write scope (current channel), so ``#marketing`` and ``#finance`` can
hold different definitions of the same name without conflict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core.ports.audit import AuditEvent
from ..core.identity import Scope, ScopeLevel
from ..core.types import ToolResult, ToolSpec
from ..semantic.types import SemanticEntry, SemanticKind

if TYPE_CHECKING:
    from ..harness.context import HarnessContext


class DefineMetric:
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="define_metric",
            description=(
                "Define a metric/dimension/rule for the current scope (channel by "
                "default). Later questions in this scope use this definition."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "definition": {"type": "string"},
                    "kind": {"type": "string", "enum": ["metric", "dimension", "rule"]},
                    "scope": {"type": "string", "enum": ["channel", "guild"],
                              "description": "where to store it; default channel"},
                },
                "required": ["name", "definition"],
            },
        )

    async def run(self, args: dict[str, Any], ctx: "HarnessContext") -> ToolResult:
        if ctx.scope_resolver is None:
            return ToolResult(call_id="", content="semantic layer unavailable", is_error=True)

        name = (args.get("name") or "").strip()
        definition = (args.get("definition") or "").strip()
        if not name or not definition:
            return ToolResult(call_id="", content="name and definition are required", is_error=True)

        kind = SemanticKind(args.get("kind", "metric"))
        scope = self._resolve_scope(args.get("scope"), ctx)
        entry = SemanticEntry(kind=kind, name=name, definition=definition,
                              created_by=ctx.identity.user_id)
        await ctx.scope_resolver.define(scope, entry)

        if ctx.audit is not None:
            await ctx.audit.record(
                AuditEvent(actor=ctx.identity.user_id, action="define_metric",
                           scope=str(scope), detail={"name": name, "kind": kind.value})
            )
        return ToolResult(call_id="", content=f"✅ {kind.value} '{name}' defined at {scope}.")

    @staticmethod
    def _resolve_scope(requested: str | None, ctx: "HarnessContext") -> Scope:
        if requested == "guild" and ctx.identity.guild_id:
            return Scope(ScopeLevel.GUILD, ctx.identity.guild_id)
        return ctx.identity.default_write_scope()
