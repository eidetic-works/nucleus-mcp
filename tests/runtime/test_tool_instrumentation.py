"""Tests for runtime.tool_instrumentation (treatment sweep #002).

Covers:
- Wraps a callable and emits one JSONL line per invocation
- Preserves the wrapped function's return value
- Records duration in milliseconds
- Captures exception type and re-raises
- NUCLEUS_INSTRUMENT_DISABLED=1 short-circuits with zero overhead
- install_instrumentation() is idempotent
- NUCLEUS_INSTRUMENT_PATH overrides the JSONL directory
- Instrumentation never breaks a tool call even if the JSONL write fails
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import tool_instrumentation as ti


@pytest.fixture(autouse=True)
def _reset_cache():
    ti._JSONL_PATH_CACHE.clear()
    yield
    ti._JSONL_PATH_CACHE.clear()


@pytest.fixture
def instrument_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_INSTRUMENT_PATH", str(tmp_path))
    monkeypatch.delenv("NUCLEUS_INSTRUMENT_DISABLED", raising=False)
    yield tmp_path


def _read_jsonl(directory: Path) -> list[dict]:
    files = sorted(directory.glob("*.jsonl"))
    if not files:
        return []
    return [json.loads(line) for line in files[-1].read_text().splitlines() if line.strip()]


def test_instrument_emits_one_record_per_call(instrument_dir):
    @ti.instrument
    def add(a, b):
        return a + b

    assert add(2, 3) == 5

    records = _read_jsonl(instrument_dir)
    assert len(records) == 1
    rec = records[0]
    assert rec["tool"] == "add"
    assert "ts" in rec
    assert isinstance(rec["ms"], (int, float))
    assert rec["ms"] >= 0
    assert "error" not in rec


def test_instrument_preserves_return_value(instrument_dir):
    @ti.instrument
    def echo(x):
        return {"echoed": x, "length": len(x)}

    result = echo("hello")
    assert result == {"echoed": "hello", "length": 5}


def test_instrument_records_error_and_reraises(instrument_dir):
    @ti.instrument
    def boom():
        raise ValueError("kapow")

    with pytest.raises(ValueError, match="kapow"):
        boom()

    records = _read_jsonl(instrument_dir)
    assert len(records) == 1
    assert records[0]["error"] == "ValueError"
    assert records[0]["tool"] == "boom"


def test_instrument_disabled_returns_original_function(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_INSTRUMENT_DISABLED", "1")
    monkeypatch.setenv("NUCLEUS_INSTRUMENT_PATH", str(tmp_path))

    def naked():
        return "raw"

    wrapped = ti.instrument(naked)
    assert wrapped is naked  # exact identity; no wrapping overhead

    assert wrapped() == "raw"
    # Nothing written because instrumentation was off at decoration time.
    assert not list(tmp_path.glob("*.jsonl"))


def test_instrument_explicit_name_override(instrument_dir):
    def some_func():
        return None

    wrapped = ti.instrument(some_func, name="aliased")
    wrapped()

    records = _read_jsonl(instrument_dir)
    assert records[0]["tool"] == "aliased"


def test_session_hint_recorded_when_env_set(instrument_dir, monkeypatch):
    monkeypatch.setenv("CC_SESSION_ROLE", "operator_assistant")

    @ti.instrument
    def t():
        return 1

    t()
    records = _read_jsonl(instrument_dir)
    assert records[0]["session"] == "operator_assistant"


def test_session_hint_absent_when_env_unset(instrument_dir, monkeypatch):
    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)

    @ti.instrument
    def t():
        return 1

    t()
    records = _read_jsonl(instrument_dir)
    assert "session" not in records[0]


class _FakeMcp:
    """Mimics fastmcp's tool() calling patterns:
    - tool() / tool(name='x') / tool('x')           -> returns decorator
    - tool(fn) / tool(fn, name='x')                 -> direct-fn mode, returns FakeTool
    The second form is what fastmcp's partial(self.tool, ...) re-entry produces
    at every parenthesized @mcp.tool() registration (peer crack #7).
    """
    class FakeTool:
        def __init__(self, name, fn):
            self.name = name
            self.fn = fn
        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

    def __init__(self):
        self.registered = []

    def tool(self, *args, **kwargs):
        # Direct-fn mode (mimics fastmcp partial re-entry).
        if args and callable(args[0]) and not isinstance(args[0], str):
            fn = args[0]
            tool_name = kwargs.get("name") or fn.__name__
            ft = self.FakeTool(tool_name, fn)
            self.registered.append((tool_name, ft))
            return ft

        # Decorator mode.
        explicit_name = kwargs.get("name") or (args[0] if args and isinstance(args[0], str) else None)

        def decorator(func):
            tool_name = explicit_name or func.__name__
            ft = self.FakeTool(tool_name, func)
            self.registered.append((tool_name, ft))
            return ft

        return decorator


def test_install_instrumentation_wraps_tool_decorator(instrument_dir):
    mcp = _FakeMcp()
    ti.install_instrumentation(mcp)

    @mcp.tool()
    def my_tool(x):
        return x * 2

    assert my_tool(7) == 14

    records = _read_jsonl(instrument_dir)
    assert len(records) == 1
    assert records[0]["tool"] == "my_tool"


def test_install_instrumentation_is_idempotent(instrument_dir):
    mcp = _FakeMcp()
    ti.install_instrumentation(mcp)
    first = mcp.tool
    ti.install_instrumentation(mcp)
    second = mcp.tool
    assert first is second  # second call was a no-op


def test_install_instrumentation_respects_disabled_env(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_INSTRUMENT_DISABLED", "1")
    monkeypatch.setenv("NUCLEUS_INSTRUMENT_PATH", str(tmp_path))
    mcp = _FakeMcp()
    ti.install_instrumentation(mcp)
    # Sentinel never set because install took the early-exit path.
    assert not getattr(mcp, "_nucleus_instrumentation_installed", False)

    # And no instrumentation actually fires on a registered tool.
    @mcp.tool()
    def naked():
        return "raw"

    assert naked() == "raw"
    assert not list(tmp_path.glob("*.jsonl"))


def test_jsonl_write_failure_does_not_break_tool(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_INSTRUMENT_PATH", str(tmp_path / "nonexistent" / "deep"))
    monkeypatch.delenv("NUCLEUS_INSTRUMENT_DISABLED", raising=False)

    # The parent will be auto-created by _jsonl_dir; force a failure by
    # patching _emit's open call to raise.
    @ti.instrument
    def alive():
        return "still here"

    def boom_open(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "open", boom_open)

    # Must not raise; tool call must still succeed.
    assert alive() == "still here"


def test_mkdir_failure_does_not_break_tool(monkeypatch, tmp_path):
    """Peer crack #2: mkdir failure (e.g. read-only fs) must not raise."""
    monkeypatch.delenv("NUCLEUS_INSTRUMENT_DISABLED", raising=False)
    monkeypatch.setenv("NUCLEUS_INSTRUMENT_PATH", str(tmp_path / "deep" / "deeper"))

    def boom_mkdir(self, *a, **kw):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(Path, "mkdir", boom_mkdir)

    @ti.instrument
    def t():
        return "ok"

    assert t() == "ok"  # tool returns; instrumentation silently absorbed the failure


def test_async_handler_measures_actual_execution_time(instrument_dir):
    """Peer crack #3: sync wrapper on coroutine measures construction (~0ms)
    not execution. The async branch must await inside the timer."""
    import asyncio

    @ti.instrument
    async def slow_async():
        await asyncio.sleep(0.05)  # 50ms
        return "done"

    result = asyncio.run(slow_async())
    assert result == "done"

    records = _read_jsonl(instrument_dir)
    assert len(records) == 1
    assert records[0]["tool"] == "slow_async"
    # Sync wrapping would yield ~0ms (coroutine creation). Async wrapping
    # measures the sleep. Must be >= 40ms to allow scheduler jitter.
    assert records[0]["ms"] >= 40, f"async wrapper measuring only {records[0]['ms']}ms — likely sync-wrapped a coroutine"


def test_async_handler_error_recorded_and_reraised(instrument_dir):
    """Async branch must also capture exceptions and re-raise like sync."""
    import asyncio

    @ti.instrument
    async def async_boom():
        raise RuntimeError("async kapow")

    with pytest.raises(RuntimeError, match="async kapow"):
        asyncio.run(async_boom())

    records = _read_jsonl(instrument_dir)
    assert records[0]["error"] == "RuntimeError"


def test_typed_shape_passthrough_sync_wrap(instrument_dir):
    """Peer crack #1 + addendum: both sync and async wrappers must preserve
    typed signatures end-to-end so FastMCP's TypeAdapter doesn't degrade to
    untyped blob. Highest-blast-radius crack if it breaks."""
    import inspect

    def typed_tool(x: int, name: str = "default", tags: list[str] | None = None) -> dict:
        return {"x": x, "name": name, "tags": tags}

    wrapped = ti.instrument(typed_tool)

    orig_sig = inspect.signature(typed_tool)
    wrap_sig = inspect.signature(wrapped)
    assert str(wrap_sig) == str(orig_sig)
    assert wrapped.__annotations__ == typed_tool.__annotations__
    assert wrapped.__name__ == typed_tool.__name__
    assert wrapped.__doc__ == typed_tool.__doc__

    # Roundtrip a real call to confirm semantics unchanged.
    assert wrapped(1, name="hi", tags=["a", "b"]) == {"x": 1, "name": "hi", "tags": ["a", "b"]}


def test_typed_shape_passthrough_async_wrap(instrument_dir):
    """Peer addendum: async branch must ALSO preserve signature — there are
    two wrapper shapes to verify, not one."""
    import inspect

    async def typed_async_tool(x: int, name: str = "default") -> dict:
        return {"x": x, "name": name}

    wrapped = ti.instrument(typed_async_tool)

    assert inspect.iscoroutinefunction(wrapped), "async branch must preserve CO_COROUTINE flag"
    assert str(inspect.signature(wrapped)) == str(inspect.signature(typed_async_tool))
    assert wrapped.__annotations__ == typed_async_tool.__annotations__
    assert wrapped.__name__ == typed_async_tool.__name__


def test_install_picks_up_name_from_first_positional_arg(instrument_dir):
    """cc-main crack #1: FastMCP tool(name=...) also accepts positional;
    @mcp.tool('alias') was logging func.__name__ instead of 'alias'."""
    mcp = _FakeMcp()
    ti.install_instrumentation(mcp)

    @mcp.tool("aliased_via_positional")
    def real_name():
        return None

    real_name()

    records = _read_jsonl(instrument_dir)
    assert records[0]["tool"] == "aliased_via_positional"


def test_emit_fail_evicts_cache(instrument_dir, monkeypatch):
    """cc-main crack #2: cache eviction on emit failure so the next call
    re-mkdirs. Without this, a mid-day dir-deletion (e.g. fleet cleanup
    sweep) silently /dev/nulls every record until midnight rollover."""
    @ti.instrument
    def t():
        return None

    # First call lands cleanly + populates the cache.
    t()
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    assert today in ti._JSONL_PATH_CACHE

    # Patch open() to raise — simulates dir deletion or perms loss.
    orig_open = Path.open

    def boom_open(self, *a, **kw):
        raise OSError("file vanished")

    monkeypatch.setattr(Path, "open", boom_open)
    t()  # must not raise; failure absorbed.
    # Cache should have been evicted by the except branch.
    assert today not in ti._JSONL_PATH_CACHE

    # Restore open + verify next call re-mkdirs and writes successfully.
    monkeypatch.setattr(Path, "open", orig_open)
    t()
    assert today in ti._JSONL_PATH_CACHE


def test_sentinel_prevents_double_wrap(instrument_dir):
    """Peer crack #7 part 2: main-server chain traverses patched_tool twice
    per registration; without the idempotence sentinel the inner instrument()
    call would double-wrap, yielding two JSONL records per invocation."""
    @ti.instrument
    def my_tool():
        return "ok"

    # Wrapping the wrapper again must return the same object (no second wrap).
    twice = ti.instrument(my_tool)
    assert twice is my_tool

    # And a single call must emit exactly one record.
    my_tool()
    records = _read_jsonl(instrument_dir)
    assert len(records) == 1, f"expected 1 record after double-wrap-but-actually-single, got {len(records)}"
    assert records[0]["tool"] == "my_tool"


def test_direct_fn_pattern_forwards_to_original(instrument_dir):
    """Peer crack #7 part 1: when patched_tool receives a function as first
    positional (fastmcp partial re-entry pattern), it MUST forward
    original_tool's return value (FakeTool, simulating FunctionTool /
    CallableTool), NOT synthesize a wrapping_decorator."""
    mcp = _FakeMcp()
    ti.install_instrumentation(mcp)

    def real_fn():
        return "ok"

    # Invoke the direct-fn mode the way fastmcp's partial re-entry does.
    result = mcp.tool(real_fn)

    # MUST be the FakeTool, not a wrapping_decorator function.
    assert isinstance(result, _FakeMcp.FakeTool), (
        f"expected FakeTool from direct-fn pattern, got {type(result).__name__} "
        f"named {getattr(result, '__name__', '?')!r} — wrapping_decorator regression"
    )
    assert result.name == "real_fn"

    # The registered fn must be the instrumented wrapper (not the raw fn),
    # so calling it fires the JSONL record.
    result()
    records = _read_jsonl(instrument_dir)
    assert len(records) == 1
    assert records[0]["tool"] == "real_fn"


def test_decorator_pattern_via_fake_partial_reentry_returns_tool(instrument_dir):
    """End-to-end simulation of fastmcp's @mcp.tool() flow:
    - user code: @mcp.tool() -> calls patched_tool() -> returns wrapping_decorator
    - then wrapping_decorator(fn) calls decorator(instrumented_fn) which under
      real fastmcp re-enters self.tool(instrumented_fn) — our FakeMcp.tool's
      direct-fn branch simulates the same shape.
    The final decoration result must be FakeTool (or FunctionTool under real
    fastmcp), NOT wrapping_decorator (the pre-fix regression)."""
    mcp = _FakeMcp()
    ti.install_instrumentation(mcp)

    decorator = mcp.tool()
    # decorator here would be the FakeMcp's inner `decorator` closure,
    # via patched_tool's `original_tool(*args, **kwargs)`.

    def my_tool():
        return "ok"

    result = decorator(my_tool)

    assert isinstance(result, _FakeMcp.FakeTool), (
        f"decoration result regressed to {type(result).__name__}; expected FakeTool"
    )
    # Calling it MUST fire instrumentation exactly once.
    result()
    records = _read_jsonl(instrument_dir)
    assert len(records) == 1


def test_real_fastmcp_returns_tool_object(instrument_dir):
    """Peer crack #7 empirical recipe: with the real FastMCP, @mcp.tool()
    decoration must yield a FunctionTool-like object, not a junk
    wrapping_decorator function. This is the test that would have caught
    crack #7 in the original gate."""
    fastmcp = pytest.importorskip("fastmcp", minversion="2")
    FastMCP = fastmcp.FastMCP

    mcp = FastMCP(name="test-instrumentation")
    ti.install_instrumentation(mcp)

    @mcp.tool()
    def my_real_tool() -> str:
        return "ok"

    type_name = type(my_real_tool).__name__
    func_name = getattr(my_real_tool, "__name__", "<no-name>")
    assert type_name != "function" or func_name != "wrapping_decorator", (
        f"decoration regressed to {type_name} named {func_name!r}; "
        f"would mean patched_tool returned wrapping_decorator instead of forwarding "
        f"the FunctionTool from original_tool's partial re-entry"
    )


def test_override_path_dir_auto_created(monkeypatch, tmp_path):
    """Peer crack #6: NUCLEUS_INSTRUMENT_PATH pointing at a nonexistent dir
    must NOT silently become /dev/null — the dir gets mkdir'd."""
    target = tmp_path / "fresh" / "subdir"
    assert not target.exists()  # confirm starting state

    monkeypatch.delenv("NUCLEUS_INSTRUMENT_DISABLED", raising=False)
    monkeypatch.setenv("NUCLEUS_INSTRUMENT_PATH", str(target))

    @ti.instrument
    def t():
        return "ok"

    assert t() == "ok"
    assert target.exists()
    assert list(target.glob("*.jsonl")), "JSONL file should have been written to auto-created override dir"


def test_date_rollover_writes_to_new_file(instrument_dir, monkeypatch):
    """Peer crack #5: cache must key on date so midnight rollover starts
    a new file. Simulate by manually populating the cache for yesterday
    and verifying today's call ignores the stale entry."""
    @ti.instrument
    def t():
        return None

    # Force a stale 'yesterday' cache entry.
    ti._JSONL_PATH_CACHE["20991231"] = instrument_dir / "20991231.jsonl"
    (instrument_dir / "20991231.jsonl").write_text('{"stale":true}\n')

    t()
    # The today key must have been computed independently and written its own file.
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    today_file = instrument_dir / f"{today}.jsonl"
    assert today_file.exists()
    records = [json.loads(line) for line in today_file.read_text().splitlines()]
    assert records[0]["tool"] == "t"

    # Stale file untouched.
    stale = (instrument_dir / "20991231.jsonl").read_text()
    assert "stale" in stale
