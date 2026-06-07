"""define_metric — scope-aware definition writer (★④ federation).

Writes one definition to the KV-backed federation store via FedEntry.
With no explicit scope it lands at the identity's default write scope
(current channel), so #marketing and #finance can hold different definitions
of the same name without conflict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core.ports.audit import AuditEvent
from ..core.identity import Scope, ScopeLevel
from ..core.types import ToolResult, ToolSpec
from .semantic_federation import FedEntry, _kv_key

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
        if ctx.store is None:
            return ToolResult(call_id="", content="semantic layer unavailable", is_error=True)

        name = (args.get("name") or "").strip()
        definition = (args.get("definition") or "").strip()
        if not name or not definition:
            return ToolResult(call_id="", content="name and definition are required", is_error=True)

        kind = (args.get("kind") or "metric").strip()
        layer, entity = self._resolve_layer(args.get("scope"), ctx)
        kv_scope = ctx.identity.guild_id or f"dm:{ctx.identity.user_id}"

        entry = FedEntry(
            term=name,
            layer=layer,
            entity=entity,
            definition=definition,
            inferred=False,
        )
        ctx.store.kv_set(kv_scope, _kv_key(name, layer, entity), entry.to_json())

        if ctx.audit is not None:
            scope_obj = self._scope_obj(layer, entity, ctx)
            await ctx.audit.record(
                AuditEvent(actor=ctx.identity.user_id, action="define_metric",
                           scope=str(scope_obj), detail={"name": name, "kind": kind})
            )
        layer_label = "전사" if layer == "guild" else "채널"
        return ToolResult(call_id="", content=f"✅ {kind} '{name}' defined at {layer_label}.")

    @staticmethod
    def _resolve_layer(requested: str | None, ctx: "HarnessContext") -> tuple[str, str]:
        channel_id = ctx.identity.thread_id or ctx.identity.channel_id or ""
        if requested == "guild":
            return "guild", ""
        if channel_id:
            return "channel", channel_id
        # No channel context (e.g. DM) — store at guild level to remain visible
        return "guild", ""

    @staticmethod
    def _scope_obj(layer: str, entity: str, ctx: "HarnessContext") -> Scope:
        if layer == "guild" and ctx.identity.guild_id:
            return Scope(ScopeLevel.GUILD, ctx.identity.guild_id)
        return ctx.identity.default_write_scope()
