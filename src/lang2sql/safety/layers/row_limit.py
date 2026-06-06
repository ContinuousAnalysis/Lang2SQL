"""RowLimitLayer — automatically appends LIMIT to queries that lack one.

Returns PASS (not REWRITE) so the rewritten SQL flows into the next layer
(TimeoutLayer) and ctx.timeout_seconds still gets configured.
"""

from __future__ import annotations

import re

from ...core.ports.safety import SafetyContext, SafetyDecision, Verdict

_LIMIT_RE = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)


def _has_top_level_limit(sql: str) -> bool:
    """True if a LIMIT clause exists at parenthesis depth 0."""
    depth = 0
    for part in re.split(r"(\(|\))", sql):
        if part == "(":
            depth += 1
        elif part == ")":
            depth -= 1
        elif depth == 0 and _LIMIT_RE.search(part):
            return True
    return False


class RowLimitLayer:
    """Appends LIMIT when absent; leaves explicit LIMITs untouched."""

    @property
    def name(self) -> str:
        return "row_limit"

    def check(self, sql: str, ctx: SafetyContext) -> SafetyDecision:
        if _has_top_level_limit(sql):
            return SafetyDecision(verdict=Verdict.PASS, sql=sql, layer=self.name)
        limit = ctx.row_limit if ctx.row_limit and ctx.row_limit > 0 else 1000
        rewritten = sql.rstrip().rstrip(";") + f"\nLIMIT {limit}"
        return SafetyDecision(verdict=Verdict.PASS, sql=rewritten, layer=self.name)
