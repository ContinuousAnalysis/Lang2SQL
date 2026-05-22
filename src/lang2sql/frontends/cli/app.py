"""CLI frontend — the developer-facing driver of the harness.

Per v4.1 the CLI is a dev tool (Discord is the Phase 1 product frontend). It is
the simplest :class:`FrontendPort` consumer and the harness's first smoke test:
assemble a HarnessContext and run one turn through ``agent_loop``.

Run:  python -m lang2sql.frontends.cli.app "your question"
"""

from __future__ import annotations

import asyncio
import sys

from ...adapters.llm.fake import FakeLLM
from ...core.identity import Identity
from ...harness.context import HarnessContext
from ...harness.loop import agent_loop
from ...harness.session import Session
from ...harness.tool_registry import ToolRegistry
from ...tools.ping import Ping


def build_context(user_text: str) -> HarnessContext:
    """Assemble a minimal Week-1 context (FakeLLM + ping tool, no DB)."""
    identity = Identity(user_id="cli-user")
    return HarnessContext(
        identity=identity,
        llm=FakeLLM(),
        tools=ToolRegistry([Ping()]),
        session=Session(identity=identity),
    )


async def _run(user_text: str) -> str:
    ctx = build_context(user_text)
    return await agent_loop(ctx, user_text)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    user_text = " ".join(argv) or "ping the system"
    answer = asyncio.run(_run(user_text))
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
