"""Smoke test: the bench demo runs clean and shows its headline behaviours.

Guards the study-group demo against drift in the modules it exercises
(ContextConcierge, ScopeResolver, SafetyPipeline). Runs the demo's ``main()``
in-process and asserts the federation + safety claims it prints are real.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

_DEMO = Path(__file__).resolve().parent.parent / "bench" / "ecommerce_demo.py"


def _load_demo():
    spec = importlib.util.spec_from_file_location("ecommerce_demo", _DEMO)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_demo_runs_clean(capsys):
    demo = _load_demo()
    asyncio.run(demo.main())
    out = capsys.readouterr().out

    # ★④ federation: same term, two definitions, no conflict.
    assert "user with a login event in the last 30 days" in out
    assert "user with an active paid subscription" in out
    assert "zero conflict" in out

    # ★① safety: a mutating statement is blocked, a SELECT passes.
    assert "BLOCK" in out
    assert "PASS" in out


def test_demo_federation_resolves_distinct_definitions():
    """Reach into the demo's building blocks directly (no printing)."""
    demo = _load_demo()
    from lang2sql.semantic.types import Metric
    from lang2sql.tenancy.scope_resolver import ScopeResolver

    async def _run():
        resolver = ScopeResolver()
        mkt = demo._marketing_identity()
        fin = demo._finance_identity()
        await resolver.define(mkt.default_write_scope(), Metric("active_user", "30d login"))
        await resolver.define(fin.default_write_scope(), Metric("active_user", "paid sub"))
        mkt_layer = await resolver.effective_layer(mkt)
        fin_layer = await resolver.effective_layer(fin)
        return mkt_layer.lookup("active_user").definition, fin_layer.lookup("active_user").definition

    mkt_def, fin_def = asyncio.run(_run())
    assert mkt_def == "30d login"
    assert fin_def == "paid sub"
    assert mkt_def != fin_def
