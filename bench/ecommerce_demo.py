#!/usr/bin/env python3
"""E-commerce demo — Lang2SQL v4.1 headline value, no Discord and no real DB.

Run:  .venv/bin/python bench/ecommerce_demo.py

This is the study-group demo. It exercises the *real* V1 code paths
(``ContextConcierge`` + scope resolver + the canned Postgres explorer + the
offline ``FakeLLM``) to show three things end-to-end without a token or a live
database:

  Section 1 — define three e-commerce metrics in a channel and read them back.
  Section 2 — ★④ semantic federation: the *same* term ``active_user`` carries
              two different definitions in #marketing vs #finance, with no
              conflict. Each channel resolves its own effective layer.
  Section 3 — ★① safety pipeline: DROP / INSERT are blocked fail-closed while a
              plain SELECT passes.

Everything printed is produced by running the shipped modules, not hard-coded.
"""

from __future__ import annotations

import asyncio

from lang2sql.core.identity import Identity
from lang2sql.core.ports.safety import SafetyContext, Verdict
from lang2sql.harness.loop import agent_loop
from lang2sql.safety.pipeline import SafetyPipeline
from lang2sql.semantic.types import Metric
from lang2sql.tenancy.concierge import ContextConcierge
from lang2sql.tenancy.scope_resolver import ScopeResolver

# Stable IDs for the demo guild and its two channels.
GUILD = "acme-shop"
CH_MARKETING = "marketing"
CH_FINANCE = "finance"


def _hr(title: str) -> None:
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


def _marketing_identity() -> Identity:
    return Identity(user_id="dana", guild_id=GUILD, channel_id=CH_MARKETING)


def _finance_identity() -> Identity:
    return Identity(user_id="evan", guild_id=GUILD, channel_id=CH_FINANCE)


async def section_0_harness(concierge: ContextConcierge) -> None:
    """Drive one full agent turn through the assembled harness (offline).

    This is the *wiring* proof, not an intelligence proof: ``ContextConcierge``
    picks the offline FakeLLM (no OPENAI_API_KEY), starts a session, and wires
    the canned Postgres explorer + six tools into a ``HarnessContext`` that
    ``agent_loop`` drives LLM → tool → LLM to a final answer. No network, no
    real database.

    The FakeLLM is a deterministic stub: it blindly calls the first tool
    (``run_sql``) with placeholder args, so its turn ends up *demonstrating the
    safety gate* rather than answering the question. With OPENAI_API_KEY set,
    the same loop calls gpt-4.1-mini instead — zero other code changes.
    """
    _hr("SECTION 0 — assembled harness runs one turn (ContextConcierge + FakeLLM)")

    ident = _marketing_identity()
    ctx = await concierge.build_context(ident)
    print(f"LLM in use:  {type(ctx.llm).__name__}   (offline, no key required)")
    print(f"Explorer:    {type(ctx.explorer).__name__}   (canned orders/users tables)")
    print(f"Tools wired: {', '.join(s.name for s in ctx.tools.specs())}\n")

    final = await agent_loop(ctx, "How many orders do we have?")
    print("user>  How many orders do we have?")
    print(f"loop>  {final}")
    print("\n  The loop completed a real LLM→tool→LLM cycle. The stub's blind")
    print("  run_sql call was caught by the safety gate, which is exactly the")
    print("  ★① behaviour Section 3 isolates.")


async def section_1_define_metrics(resolver: ScopeResolver) -> None:
    """Define three e-commerce metrics in #marketing and read them back."""
    _hr("SECTION 1 — define three metrics (★① business-context learning)")

    ident = _marketing_identity()
    scope = ident.default_write_scope()  # current channel by default
    print(f"Writing to default scope for this channel: {scope}\n")

    metrics = [
        Metric("total_revenue", "SUM(orders.amount) WHERE status != 'cancelled'"),
        Metric("aov", "total_revenue / COUNT(DISTINCT orders.id)"),
        Metric("paid_orders", "COUNT(*) FROM orders WHERE status = 'paid'"),
    ]
    for m in metrics:
        await resolver.define(scope, m)
        print(f"  defined {m.name:>14}  =  {m.definition}")

    layer = await resolver.effective_layer(ident)
    print(f"\nEffective layer for #{CH_MARKETING} now holds "
          f"{len(layer.entries)} definition(s):")
    print(layer.render())


async def section_2_federation(resolver: ScopeResolver) -> None:
    """Same term, two channels, two definitions — no conflict (★④)."""
    _hr("SECTION 2 — semantic federation: one term, two definitions (★④)")

    # #marketing defines active_user one way ...
    mkt = _marketing_identity()
    await resolver.define(
        mkt.default_write_scope(),
        Metric("active_user", "user with a login event in the last 30 days"),
    )
    # ... and #finance defines the SAME name a different way.
    fin = _finance_identity()
    await resolver.define(
        fin.default_write_scope(),
        Metric("active_user", "user with an active paid subscription"),
    )

    print("Defined 'active_user' independently in two channels.\n")
    print("Now resolving the *effective* definition each channel sees")
    print("by walking its scope chain (most specific scope wins):\n")

    mkt_layer = await resolver.effective_layer(mkt)
    fin_layer = await resolver.effective_layer(fin)
    mkt_def = mkt_layer.lookup("active_user")
    fin_def = fin_layer.lookup("active_user")

    print(f"  #{CH_MARKETING:<10} active_user → {mkt_def.definition}")
    print(f"  #{CH_FINANCE:<10} active_user → {fin_def.definition}")

    assert mkt_def.definition != fin_def.definition
    print("\n  ✅ Same term, two live definitions, zero conflict.")
    print("     Each channel is its own branch in the federation tree;")
    print("     neither overwrote the other. (Wren's single MDL cannot do this.)")

    # Show the scope chain that produced the marketing answer.
    chain = " → ".join(str(s) for s in mkt.scope_chain())
    print(f"\n  #{CH_MARKETING} resolution order: {chain}")
    print("  Lookup stops at the first scope that defines the name (CHANNEL),")
    print("  so the GUILD/BUILTIN branches never get a chance to disagree.")


def section_3_safety(pipeline: SafetyPipeline) -> None:
    """DROP/INSERT blocked fail-closed; SELECT passes (★①)."""
    _hr("SECTION 3 — safety pipeline gates every query (★①)")

    layers = " → ".join(layer.name for layer in pipeline.layers)
    print(f"Pipeline layers in order: {layers}\n")

    cases = [
        ("DROP TABLE users", "must BLOCK"),
        ("INSERT INTO orders VALUES (99, 10.0, 'paid', now())", "must BLOCK"),
        ("WITH x AS (INSERT INTO t VALUES (1)) SELECT * FROM x", "must BLOCK (CTE)"),
        ("SELECT status, COUNT(*) FROM orders GROUP BY status", "must PASS"),
    ]
    ctx = SafetyContext()
    for sql, expectation in cases:
        decision = pipeline.evaluate(sql, ctx)
        passed = decision.verdict is Verdict.PASS
        mark = "✅ PASS " if passed else "🚫 BLOCK"
        reason = f"  ({decision.reason} @ {decision.layer})" if decision.reason else ""
        print(f"  {mark}  {expectation:<16}  {sql}{reason}")

    print("\n  Read-only is enforced before any SQL reaches the database:")
    print("  the whitelist layer is fail-closed, so anything it cannot prove")
    print("  is a single SELECT/WITH is rejected.")


async def main() -> None:
    print("Lang2SQL v4.1 — e-commerce demo (offline: FakeLLM, canned PG, in-memory)")

    # One shared resolver so federation state persists across sections 1 and 2.
    resolver = ScopeResolver()
    pipeline = SafetyPipeline()
    concierge = ContextConcierge()

    await section_0_harness(concierge)
    await section_1_define_metrics(resolver)
    await section_2_federation(resolver)
    section_3_safety(pipeline)

    _hr("DONE")
    print("Sections 1–2 exercise ★④ federation; section 3 exercises ★① safety.")
    print("No network, no token, no live database were used.")


if __name__ == "__main__":
    asyncio.run(main())
