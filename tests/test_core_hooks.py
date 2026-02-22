from lang2sql.core.hooks import (
    Event,
    MemoryHook,
    NullHook,
    summarize,
    now,
    ms,
)


def test_memory_hook_collects_events():
    hook = MemoryHook()
    e1 = Event(name="x", component="c", phase="start", ts=123.0)
    e2 = Event(name="x", component="c", phase="end", ts=124.0, duration_ms=1.0)
    hook.on_event(e1)
    hook.on_event(e2)

    assert len(hook.events) == 2
    assert hook.events[0].phase == "start"
    assert hook.events[1].phase == "end"


def test_null_hook_does_not_crash():
    hook = NullHook()
    hook.on_event(
        Event(name="x", component="c", phase="start", ts=0.0)
    )  # should not raise


def test_summarize_truncates_long_repr():
    long = "a" * 1000
    s = summarize(long, max_len=50)
    assert len(s) <= 50
    assert s.endswith("...")


def test_now_and_ms_work():
    t0 = now()
    t1 = now()
    assert t1 >= t0
    d = ms(t0, t1)
    assert d >= 0.0


def test_memory_hook_clear_resets_events():
    hook = MemoryHook()
    hook.on_event(Event(name="x", component="c", phase="start", ts=0.0))
    assert len(hook.events) == 1
    hook.clear()
    assert len(hook.events) == 0


def test_memory_hook_snapshot_is_copy():
    hook = MemoryHook()
    hook.on_event(Event(name="x", component="c", phase="start", ts=0.0))

    snap = hook.snapshot()
    assert snap is not hook.events
    assert len(snap) == 1

    # mutate original after snapshot
    hook.on_event(Event(name="x", component="c", phase="end", ts=1.0))
    assert len(hook.events) == 2
    assert len(snap) == 1  # snapshot should not change


class BadRepr:
    def __repr__(self):
        raise RuntimeError("boom")


def test_summarize_handles_bad_repr():
    s = summarize(BadRepr(), max_len=50)
    assert "unreprable" in s
