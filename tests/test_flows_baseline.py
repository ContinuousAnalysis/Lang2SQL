import pytest

from lang2sql.core.context import RunContext
from lang2sql.flows.baseline import BaselineFlow


def test_requires_at_least_one_step():
    with pytest.raises(ValueError):
        BaselineFlow(steps=[])


def test_run_query_sets_inputs_query():
    def step(run: RunContext):
        # no-op mutate style
        run.sql = "SELECT 1;"
        return None

    flow = BaselineFlow(steps=[step])
    out = flow.run_query("지난달 매출")

    assert out.inputs["query"] == "지난달 매출"
    assert out.query == "지난달 매출"
    assert out.sql == "SELECT 1;"


def test_ctx_mutate_style_step_returns_none_and_mutates():
    def step(run: RunContext):
        run.metadata["x"] = 1
        return None

    flow = BaselineFlow(steps=[step])
    run = RunContext(query="q")
    out = flow.run(run)

    assert out is run
    assert out.metadata["x"] == 1


def test_functional_style_step_can_return_new_context():
    def step(run: RunContext):
        new = RunContext(query=run.query)
        new.sql = "SELECT 2;"
        return new

    flow = BaselineFlow(steps=[step])
    run = RunContext(query="q")
    out = flow.run(run)

    assert out is not run
    assert out.query == "q"
    assert out.sql == "SELECT 2;"


def test_invalid_step_return_type_raises_typeerror():
    def bad_step(run: RunContext):
        return 123  # invalid

    flow = BaselineFlow(steps=[bad_step])
    with pytest.raises(TypeError):
        flow.run(RunContext(query="q"))


def test_step_order_is_preserved():
    def s1(run: RunContext):
        run.push_meta("order", "s1")
        return None

    def s2(run: RunContext):
        run.push_meta("order", "s2")
        return None

    def s3(run: RunContext):
        run.push_meta("order", "s3")
        return None

    flow = BaselineFlow(steps=[s1, s2, s3])
    out = flow.run(RunContext(query="q"))

    assert out.get_meta_list("order") == ["s1", "s2", "s3"]


def test_run_steps_can_override_steps_argument():
    def s1(run: RunContext):
        run.push_meta("order", "default")
        return None

    def s2(run: RunContext):
        run.push_meta("order", "override")
        return None

    flow = BaselineFlow(steps=[s1])
    out = flow._run_steps(RunContext(query="q"), steps=[s2])

    assert out.get_meta_list("order") == ["override"]