"""Timeout layer — execution-config layer, never blocks.

This layer does not inspect the SQL for slow constructs (``pg_sleep`` etc.);
that is enforced at *run time* by the executor honoring ``ctx.timeout_seconds``.
Its only job is to guarantee a timeout is set on the context before execution.
"""

from __future__ import annotations

from ...core.ports.safety import (
    SafetyContext,
    SafetyDecision,
    Verdict,
)

_DEFAULT_TIMEOUT_SECONDS = 30


class TimeoutLayer:
    """Ensures ``ctx.timeout_seconds`` is set, then PASSes. ``SafetyLayerPort``."""

    def __init__(self, default_seconds: int = _DEFAULT_TIMEOUT_SECONDS) -> None:
        self._default_seconds = default_seconds

    @property
    def name(self) -> str:
        return "timeout"

    def check(self, sql: str, ctx: SafetyContext) -> SafetyDecision:
        # A non-positive (or unset) timeout would mean "no limit" downstream;
        # clamp it to the default so a slow query (case #7, pg_sleep) is bounded.
        if not ctx.timeout_seconds or ctx.timeout_seconds <= 0:
            ctx.timeout_seconds = self._default_seconds
        return SafetyDecision(verdict=Verdict.PASS, sql=sql, layer=self.name)
