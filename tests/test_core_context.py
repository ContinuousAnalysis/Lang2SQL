import pytest

from lang2sql.core.context import RunContext


def test_init_sets_query_and_metadata_kwargs():
    ctx = RunContext(query="hello", user_id="u1", trace_id="t1")
    assert ctx.inputs["query"] == "hello"
    assert ctx.metadata["user_id"] == "u1"
    assert ctx.metadata["trace_id"] == "t1"


def test_query_property_default_empty_string():
    ctx = RunContext()
    assert ctx.query == ""  # inputs에 query 없으면 ""


def test_query_setter_updates_inputs():
    ctx = RunContext()
    ctx.query = "select something"
    assert ctx.inputs["query"] == "select something"
    assert ctx.query == "select something"


def test_schema_property_initializes_dict_and_persists_reference():
    ctx = RunContext()
    s = ctx.schema
    assert isinstance(s, dict)
    assert ctx.artifacts["schema"] is s  # 같은 객체를 보장(참조 유지)

    s["selected"] = ["users", "orders"]
    assert ctx.artifacts["schema"]["selected"] == ["users", "orders"]


def test_schema_property_overwrites_non_dict_value():
    ctx = RunContext()
    ctx.artifacts["schema"] = ["not", "a", "dict"]
    s = ctx.schema
    assert isinstance(s, dict)
    assert ctx.artifacts["schema"] == {}  # dict가 아니면 {}로 교체됨


def test_sql_property_get_set():
    ctx = RunContext()
    assert ctx.sql == ""
    ctx.sql = "SELECT 1;"
    assert ctx.outputs["sql"] == "SELECT 1;"
    assert ctx.sql == "SELECT 1;"


def test_validation_property_get_set():
    ctx = RunContext()
    assert ctx.validation is None
    ctx.validation = {"ok": True, "warnings": []}
    assert ctx.outputs["validation"] == {"ok": True, "warnings": []}
    assert ctx.validation == {"ok": True, "warnings": []}


def test_push_meta_appends_to_list():
    ctx = RunContext()
    ctx.push_meta("events", {"name": "start"})
    ctx.push_meta("events", {"name": "end"})
    assert ctx.metadata["events"] == [{"name": "start"}, {"name": "end"}]


def test_push_meta_raises_when_existing_not_list():
    ctx = RunContext()
    ctx.metadata["events"] = {"name": "oops"}  # list가 아닌 값
    with pytest.raises(TypeError):
        ctx.push_meta("events", {"name": "start"})


def test_get_meta_list_returns_empty_when_missing():
    ctx = RunContext()
    assert ctx.get_meta_list("missing") == []


def test_get_meta_list_returns_list_or_wraps_scalar():
    ctx = RunContext()
    ctx.metadata["items"] = [1, 2, 3]
    assert ctx.get_meta_list("items") == [1, 2, 3]

    ctx.metadata["single"] = 42
    assert ctx.get_meta_list("single") == [42]