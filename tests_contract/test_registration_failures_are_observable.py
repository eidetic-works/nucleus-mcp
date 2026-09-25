"""A facade that fails to register must leave a signal something can read (CP-3).

`register_all` caught every registration failure, appended the module name to a
local list, and printed one line to stderr. Nothing else happened: no non-zero
exit, nothing an MCP caller could query, nothing a test could assert, and the
degraded-start summary was gated behind `NUCLEUS_DEBUG` so it did not appear on
a normal boot.

CP-5 lived in exactly that gap. The `grounding` facade returned a bare function
where every other facade returns `(name, func)` pairs; the bare except swallowed
it; the entire GROUND surface was missing from every boot for as long as that
was true, while CI printed the error on every run and nobody read it.

So the fix is not "stop catching" — a local user with a missing optional
dependency is better served by a degraded server than by no server. The fix is
that the failure has to be *legible*: in the log, on stderr unconditionally, and
in `get_registration_failures()` for doctor, health checks and tests.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

tools = pytest.importorskip("mcp_server_nucleus.tools")


class FakeMCP:
    """Enough surface for install_instrumentation and a facade register()."""

    def __init__(self):
        self.registered = []

    def tool(self, *a, **kw):
        def _decorator(fn):
            self.registered.append(getattr(fn, "__name__", "anon"))
            return fn
        return _decorator


def _module(name, register):
    mod = types.ModuleType(f"mcp_server_nucleus.tools.{name}")
    mod.register = register
    return mod


@pytest.fixture
def run_register(monkeypatch):
    """Drive register_all over a synthetic set of facade modules."""
    monkeypatch.setattr(tools, "install_instrumentation", lambda mcp: None, raising=False)
    monkeypatch.setattr(
        "mcp_server_nucleus.runtime.tool_instrumentation.install_instrumentation",
        lambda mcp: None,
    )

    def _run(modules):
        monkeypatch.setattr(tools, "_get_active_modules", lambda: modules)
        return tools.register_all(FakeMCP(), {})

    return _run


def _ok(name):
    return _module(name, lambda mcp, helpers: [(f"nucleus_{name}", lambda **kw: None)])


def _raises(name, exc):
    def register(mcp, helpers):
        raise exc
    return _module(name, register)


# --- the failure must be readable ------------------------------------------


def test_a_failing_facade_is_recorded(run_register):
    run_register([_ok("alpha"), _raises("beta", KeyError("missing helper"))])
    failures = tools.get_registration_failures()
    assert [f["module"] for f in failures] == ["beta"], (
        "a facade failed to register and left nothing any caller could query"
    )


def test_the_record_names_the_exception_type_and_message(run_register):
    run_register([_raises("beta", KeyError("emit_event"))])
    failure = tools.get_registration_failures()[0]
    assert failure["error_type"] == "KeyError"
    assert "emit_event" in failure["error"]


def test_the_cp5_shape_is_caught_and_recorded(run_register):
    """The actual CP-5 bug: a bare function where pairs were expected."""
    bad = _module("grounding", lambda mcp, helpers: (lambda **kw: None))
    run_register([bad])
    assert [f["module"] for f in tools.get_registration_failures()] == ["grounding"]


def test_a_clean_run_records_nothing(run_register):
    run_register([_ok("alpha"), _ok("gamma")])
    assert tools.get_registration_failures() == []


def test_a_later_clean_run_clears_an_earlier_failure(run_register):
    run_register([_raises("beta", RuntimeError("boom"))])
    assert tools.get_registration_failures()
    run_register([_ok("alpha")])
    assert tools.get_registration_failures() == [], (
        "a stale failure survived a successful re-registration"
    )


def test_the_record_cannot_be_cleared_by_a_caller(run_register):
    run_register([_raises("beta", RuntimeError("boom"))])
    got = tools.get_registration_failures()
    got.clear()
    got2 = tools.get_registration_failures()
    assert len(got2) == 1, "get_registration_failures handed out its own list"


def test_the_failure_is_logged_at_error(run_register, caplog):
    with caplog.at_level("ERROR", logger="nucleus.tools"):
        run_register([_raises("beta", RuntimeError("boom"))])
    assert any("beta" in r.getMessage() for r in caplog.records), (
        "nothing reached the log, so a deployment aggregating logs sees no failure"
    )


def test_the_degraded_summary_is_not_hidden_by_quiet_mode(run_register, capsys, monkeypatch):
    """It was gated behind NUCLEUS_DEBUG, so a normal boot never showed it."""
    monkeypatch.delenv("NUCLEUS_DEBUG", raising=False)
    monkeypatch.setattr(sys, "argv", ["nucleus", "--quiet"])
    run_register([_raises("beta", RuntimeError("boom"))])
    err = capsys.readouterr().err
    assert "degraded" in err and "beta" in err


# --- a working facade must still register ----------------------------------


def test_a_healthy_facade_still_reaches_the_parent_module(run_register):
    run_register([_ok("alpha")])
    import mcp_server_nucleus

    assert hasattr(mcp_server_nucleus, "nucleus_alpha"), (
        "the injection contract external callers depend on is broken"
    )


def test_one_failure_does_not_stop_the_others(run_register):
    run_register([_raises("beta", RuntimeError("boom")), _ok("delta")])
    import mcp_server_nucleus

    assert hasattr(mcp_server_nucleus, "nucleus_delta")


# --- strict mode -----------------------------------------------------------


def test_strict_mode_makes_a_failure_fatal(run_register, monkeypatch):
    monkeypatch.setenv("NUCLEUS_STRICT_REGISTRATION", "true")
    with pytest.raises(RuntimeError, match="beta"):
        run_register([_raises("beta", RuntimeError("boom"))])


def test_strict_mode_is_silent_on_a_clean_run(run_register, monkeypatch):
    monkeypatch.setenv("NUCLEUS_STRICT_REGISTRATION", "true")
    run_register([_ok("alpha")])
    assert tools.get_registration_failures() == []


def test_strict_mode_is_off_by_default(run_register, monkeypatch):
    """A missing optional dependency must not stop a local user booting."""
    monkeypatch.delenv("NUCLEUS_STRICT_REGISTRATION", raising=False)
    run_register([_raises("beta", RuntimeError("boom"))])
    assert tools.get_registration_failures()
