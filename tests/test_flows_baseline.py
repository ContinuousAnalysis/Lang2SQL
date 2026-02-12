import pytest

from lang2sql.core.context import RunContext
from lang2sql.core.base import BaseFlow
from lang2sql.core.exceptions import ContractError
from lang2sql.flows.baseline import BaselineFlow


def test_requires_at_least_one_step():
    with pytest.raises(ValueError):
        BaselineFlow(steps=[])


def test_run_query_sets_inputs_query():
    def step(run: RunContext) -> RunContext:
        run.sql = "SELECT 1;"
        return run

    flow = BaselineFlow(steps=[step])
    out = flow.run_query("지난달 매출")

    assert out.inputs["query"] == "지난달 매출"
    assert out.query == "지난달 매출"
    assert out.sql == "SELECT 1;"


def test_ctx_mutate_style_step_mutates_and_returns_same_context():
    def step(run: RunContext) -> RunContext:
        run.metadata["x"] = 1
        return run

    flow = BaselineFlow(steps=[step])
    run = RunContext(query="q")
    out = flow.run(run)

    assert out is run
    assert out.metadata["x"] == 1


def test_functional_style_step_can_return_new_context():
    def step(run: RunContext) -> RunContext:
        new = RunContext(query=run.query)
        new.sql = "SELECT 2;"
        return new

    flow = BaselineFlow(steps=[step])
    run = RunContext(query="q")
    out = flow.run(run)

    assert out is not run
    assert out.query == "q"
    assert out.sql == "SELECT 2;"


def test_invalid_step_return_type_raises_contract_error():
    def bad_step(run: RunContext):
        return 123  # invalid

    flow = BaselineFlow(steps=[bad_step])
    with pytest.raises(ContractError):
        flow.run(RunContext(query="q"))


def test_step_order_is_preserved():
    def s1(run: RunContext) -> RunContext:
        run.push_meta("order", "s1")
        return run

    def s2(run: RunContext) -> RunContext:
        run.push_meta("order", "s2")
        return run

    def s3(run: RunContext) -> RunContext:
        run.push_meta("order", "s3")
        return run

    flow = BaselineFlow(steps=[s1, s2, s3])
    out = flow.run(RunContext(query="q"))

    assert out.get_meta_list("order") == ["s1", "s2", "s3"]


def test_user_can_override_pipeline_by_composing_flows_without_private_api():
    def default_step(run: RunContext) -> RunContext:
        run.push_meta("order", "default")
        return run

    def override_step(run: RunContext) -> RunContext:
        run.push_meta("order", "override")
        return run

    flow_default = BaselineFlow(steps=[default_step])
    flow_override = BaselineFlow(steps=[override_step])

    out_default = flow_default(RunContext(query="q"))
    assert out_default.get_meta_list("order") == ["default"]

    class CustomFlow(BaseFlow):
        def run(self, run: RunContext) -> RunContext:
            # Explicitly choose override pipeline
            return flow_override(run)

    out = CustomFlow().run(RunContext(query="q"))
    assert out.get_meta_list("order") == ["override"]


# -------------------------
# 1) Advanced: retry patterns (NO private API)
# -------------------------

def test_custom_flow_fallback_then_revalidate_makes_validation_ok():
    def gen_bad(run: RunContext) -> RunContext:
        run.sql = "DROP TABLE users;"
        return run

    class _V:
        def __init__(self, ok: bool):
            self.ok = ok

    def validate(run: RunContext) -> RunContext:
        ok = "drop " not in run.sql.lower()
        run.validation = _V(ok)
        return run

    pipeline = BaselineFlow(steps=[gen_bad, validate])  # gen -> validate

    class FixThenRevalidateFlow(BaseFlow):
        def run(self, run: RunContext) -> RunContext:
            pipeline(run)
            if run.validation.ok:
                return run

            run.sql = "SELECT 1;"
            validate(run)  # explicit re-validate
            return run

    out = FixThenRevalidateFlow().run(RunContext(query="q"))
    assert out.sql == "SELECT 1;"
    assert out.validation.ok is True


def test_custom_flow_retry_regenerates_sql_until_valid():
    def gen_with_attempt(run: RunContext) -> RunContext:
        attempt = int(run.metadata.get("attempt", 0))
        run.metadata["attempt"] = attempt + 1

        if attempt == 0:
            run.sql = "DROP TABLE users;"
        else:
            run.sql = "SELECT 1;"
        return run

    class _V:
        def __init__(self, ok: bool):
            self.ok = ok

    def validate(run: RunContext) -> RunContext:
        ok = "drop " not in run.sql.lower()
        run.validation = _V(ok)
        return run

    class RegenerateRetryFlow(BaseFlow):
        def run(self, run: RunContext) -> RunContext:
            for _ in range(3):
                gen_with_attempt(run)
                validate(run)
                if run.validation.ok:
                    return run
            return run

    out = RegenerateRetryFlow().run(RunContext(query="q"))
    assert out.sql == "SELECT 1;"
    assert out.validation.ok is True
    assert out.metadata["attempt"] >= 2


# -------------------------
# 2) Composition: flow as a step (subflow)
# -------------------------

def test_subflow_can_be_used_as_a_step_and_mutates_same_context():
    def a1(run: RunContext) -> RunContext:
        run.push_meta("trace", "a1")
        return run

    def a2(run: RunContext) -> RunContext:
        run.sql = "SELECT 42;"
        run.push_meta("trace", "a2")
        return run

    flow_a = BaselineFlow(steps=[a1, a2])

    def b1(run: RunContext) -> RunContext:
        run.push_meta("trace", "b1")
        return run

    def b2(run: RunContext) -> RunContext:
        run.push_meta("trace", "b2")
        return run

    flow_b = BaselineFlow(steps=[b1, flow_a, b2])

    run = RunContext(query="q")
    out = flow_b.run(run)

    assert out is run
    assert out.get_meta_list("trace") == ["b1", "a1", "a2", "b2"]
    assert out.sql == "SELECT 42;"


def test_subflow_can_be_conditionally_invoked_in_custom_flow():
    def a1(run: RunContext) -> RunContext:
        run.push_meta("trace", "a1")
        return run

    def a2(run: RunContext) -> RunContext:
        run.push_meta("trace", "a2")
        return run

    flow_a = BaselineFlow(steps=[a1, a2])

    def b1(run: RunContext) -> RunContext:
        run.push_meta("trace", "b1")
        return run

    def b2(run: RunContext) -> RunContext:
        run.push_meta("trace", "b2")
        return run

    class ConditionalFlow(BaseFlow):
        def run(self, run: RunContext) -> RunContext:
            b1(run)
            if "use_a" in run.query:
                flow_a(run)
            b2(run)
            return run

    out1 = ConditionalFlow().run(RunContext(query="nope"))
    assert out1.get_meta_list("trace") == ["b1", "b2"]

    out2 = ConditionalFlow().run(RunContext(query="please use_a"))
    assert out2.get_meta_list("trace") == ["b1", "a1", "a2", "b2"]

def test_none_return_raises_contract_error():
    def bad_none(run: RunContext):
        run.sql = "SELECT 1;"
        return None  # forgot return run

    flow = BaselineFlow(steps=[bad_none])
    with pytest.raises(ContractError) as ei:
        flow.run(RunContext(query="q"))

    assert "Did you forget" in str(ei.value) or "return run" in str(ei.value)


    