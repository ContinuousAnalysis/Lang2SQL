import pytest

from lang2sql.core.context import RunContext
from lang2sql.flows.baseline import BaselineFlow


# -------------------------
# 1) Advanced: retry patterns
# -------------------------

def test_custom_flow_fallback_then_revalidate_makes_validation_ok():
    """
    Advanced (define-by-run):
    If generated SQL is invalid, apply a fallback fix and re-run validation.
    This demonstrates "fix & revalidate" style retry logic.
    """

    def gen_bad(run: RunContext):
        # Always generates a bad SQL
        run.sql = "DROP TABLE users;"
        return None

    class _V:
        def __init__(self, ok: bool):
            self.ok = ok

    def validate(run: RunContext):
        ok = "drop " not in run.sql.lower()
        run.validation = _V(ok)
        return None

    class FixThenRevalidateFlow(BaselineFlow):
        def run(self, run: RunContext) -> RunContext:
            # 1) try once (gen -> validate)
            run = self._run_steps(run)  # uses self.steps: [gen_bad, validate]
            if run.validation.ok:
                return run

            # 2) fallback fix
            run.sql = "SELECT 1;"

            # 3) IMPORTANT: re-validate after changing SQL
            run = self._run_steps(run, steps=[validate])
            return run

    flow = FixThenRevalidateFlow(steps=[gen_bad, validate])
    out = flow.run_query("q")

    assert out.sql == "SELECT 1;"
    assert out.validation.ok is True


def test_custom_flow_retry_regenerates_sql_until_valid():
    """
    Advanced (define-by-run):
    Retry generation+validation up to N times, where the generator can
    produce a different SQL depending on attempt count.

    This demonstrates "retry by re-generation" style.
    """

    def gen_with_attempt(run: RunContext):
        attempt = int(run.metadata.get("attempt", 0))
        run.metadata["attempt"] = attempt + 1

        # First attempt: bad SQL, subsequent attempts: good SQL
        if attempt == 0:
            run.sql = "DROP TABLE users;"
        else:
            run.sql = "SELECT 1;"
        return None

    class _V:
        def __init__(self, ok: bool):
            self.ok = ok

    def validate(run: RunContext):
        ok = "drop " not in run.sql.lower()
        run.validation = _V(ok)
        return None

    class RegenerateRetryFlow(BaselineFlow):
        def run(self, run: RunContext) -> RunContext:
            # retry up to 3 attempts
            for _ in range(3):
                run = self._run_steps(run)  # [gen_with_attempt, validate]
                if run.validation.ok:
                    return run
            return run

    flow = RegenerateRetryFlow(steps=[gen_with_attempt, validate])
    out = flow.run_query("q")

    assert out.sql == "SELECT 1;"
    assert out.validation.ok is True
    assert out.metadata["attempt"] >= 2  # at least 2 attempts happened


# -------------------------
# 2) Composition: flow as a step (subflow)
# -------------------------

def test_subflow_can_be_used_as_a_step_and_mutates_same_context():
    """
    Composition: a BaselineFlow instance is callable and returns RunContext,
    so it can be inserted as a step inside another flow.
    """

    # ---- subflow A: writes sql and records meta ----
    def a1(run: RunContext):
        run.push_meta("trace", "a1")
        return None

    def a2(run: RunContext):
        run.sql = "SELECT 42;"
        run.push_meta("trace", "a2")
        return None

    flow_a = BaselineFlow(steps=[a1, a2])

    # ---- flow B: b1 -> flow_a -> b2 ----
    def b1(run: RunContext):
        run.push_meta("trace", "b1")
        return None

    def b2(run: RunContext):
        run.push_meta("trace", "b2")
        return None

    flow_b = BaselineFlow(steps=[b1, flow_a, b2])

    run = RunContext(query="q")
    out = flow_b.run(run)

    # Same context object (ctx-mutate style all the way)
    assert out is run

    # subflow executed in the middle, so trace should reflect nested order
    assert out.get_meta_list("trace") == ["b1", "a1", "a2", "b2"]
    assert out.sql == "SELECT 42;"


def test_subflow_can_be_conditionally_invoked_in_custom_flow():
    """
    Advanced + composition:
    subclass flow and call a subflow only when condition matches.
    This demonstrates non-linear control-flow with reusable subflows.
    """

    def a1(run: RunContext):
        run.push_meta("trace", "a1")
        return None

    def a2(run: RunContext):
        run.push_meta("trace", "a2")
        return None

    flow_a = BaselineFlow(steps=[a1, a2])

    def b1(run: RunContext):
        run.push_meta("trace", "b1")
        return None

    def b2(run: RunContext):
        run.push_meta("trace", "b2")
        return None

    class ConditionalFlow(BaselineFlow):
        def __init__(self):
            super().__init__(steps=[b1, b2])

        def run(self, run: RunContext) -> RunContext:
            run = self._run_steps(run, steps=[b1])
            if "use_a" in run.query:
                run = flow_a(run)  # call subflow as a reusable block
            run = self._run_steps(run, steps=[b2])
            return run

    flow = ConditionalFlow()

    out1 = flow.run_query("nope")
    assert out1.get_meta_list("trace") == ["b1", "b2"]

    out2 = flow.run_query("please use_a")
    assert out2.get_meta_list("trace") == ["b1", "a1", "a2", "b2"]