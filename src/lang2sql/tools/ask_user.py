"""ask_user — request a clarification from the human.

The agent calls this when a question is ambiguous. V1 returns the question as
the tool result; the frontend surfaces it and the user's reply arrives as the
next turn. (A suspend/resume round-trip is a v1.5 frontend concern; the loop
contract here is simply that the model gets its question echoed back so it
stops guessing.)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core.types import ToolResult, ToolSpec

if TYPE_CHECKING:
    from ..harness.context import HarnessContext


class AskUser:
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="ask_user",
            description="Ask the user a clarifying question when the request is ambiguous.",
            parameters={
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        )

    async def run(self, args: dict[str, Any], ctx: "HarnessContext") -> ToolResult:
        question = (args.get("question") or "").strip()
        if not question:
            return ToolResult(call_id="", content="no question provided", is_error=True)
        return ToolResult(call_id="", content=f"❓ Awaiting user: {question}")
