"""explore_schema — let the agent discover tables/columns before writing SQL.

Read-only introspection through the :class:`ExplorerPort`. With no ``table``
arg it lists tables; with one it returns full column detail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core.types import ToolResult, ToolSpec

if TYPE_CHECKING:
    from ..harness.context import HarnessContext


class ExploreSchema:
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="explore_schema",
            description="List tables, or describe one table's columns. Call before writing SQL.",
            parameters={
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "table name to describe; omit to list all tables"},
                },
            },
        )

    async def run(self, args: dict[str, Any], ctx: "HarnessContext") -> ToolResult:
        if ctx.explorer is None:
            return ToolResult(call_id="", content="no DB connected (use /connect)", is_error=True)

        table = (args.get("table") or "").strip()
        if not table:
            tables = await ctx.explorer.list_tables()
            names = "\n".join(f"- {t.qualified}" for t in tables) or "(no tables)"
            return ToolResult(call_id="", content="Tables:\n" + names)

        t = await ctx.explorer.describe_table(table)
        cols = "\n".join(
            f"- {c.name}: {c.type}{'' if c.nullable else ' NOT NULL'}"
            f"{(' — ' + c.description) if c.description else ''}"
            for c in t.columns
        ) or "(no columns)"
        return ToolResult(call_id="", content=f"{t.qualified}\n{cols}")
