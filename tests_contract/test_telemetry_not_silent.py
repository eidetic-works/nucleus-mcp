"""Telemetry that fails to emit must say so (QG-4).

`tools/orchestration.py` wrapped every `_emit_event` call in an inline
`try: ... except Exception: pass` — 27 of them — in a file containing no logging
of any kind. A telemetry bus that had quietly stopped accepting writes was
indistinguishable from a quiet system: `brain://events` and `brain://changes`
simply had gaps, and nothing anywhere recorded that a write had been attempted
and lost.

The swallow itself is correct and stays: telemetry must not break the operation
that emitted it. What was wrong is that it was silent. `tools/_dispatch.py`
already logs handler exceptions, so the two halves of the tool path disagreed
about whether a failure is worth mentioning.

    PYTHONPATH=src python3 -m pytest tests_contract -q
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

MODULE = SRC / "mcp_server_nucleus" / "tools" / "orchestration.py"

pytestmark = pytest.mark.skipif(not MODULE.exists(), reason="module not in this export")


@pytest.fixture(scope="module")
def tree():
    return ast.parse(MODULE.read_text(encoding="utf-8"))


def _calls_named(node, prefix):
    return [
        n for n in ast.walk(node)
        if isinstance(n, ast.Call) and getattr(n.func, "id", "").startswith(prefix)
    ]


def test_no_emit_call_sits_in_a_silent_pass_block(tree):
    """The pattern the finding is about, stated directly."""
    offenders = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Try) and len(node.handlers) == 1
                and len(node.handlers[0].body) == 1
                and isinstance(node.handlers[0].body[0], ast.Pass)):
            for call in _calls_named(node, "_emit_event"):
                offenders.append(call.lineno)
    assert not offenders, (
        f"telemetry emitted at line(s) {offenders} can fail with no log, no "
        "metric and no trace — a gap in brain:// looks exactly like a quiet system"
    )


def test_the_module_logs_at_all(tree):
    """It contained no logging of any kind, which is what made this invisible."""
    source = MODULE.read_text(encoding="utf-8")
    assert "logging.getLogger" in source, "the module still has no logger"


def test_the_helper_absorbs_the_exception(tree):
    """Telemetry must not break the operation that emitted it."""
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_emit_telemetry"
    )
    tries = [n for n in ast.walk(fn) if isinstance(n, ast.Try)]
    assert tries, "_emit_telemetry does not guard the emit; a failure now propagates"
    assert any(
        getattr(h.type, "id", None) == "Exception" for t in tries for h in t.handlers
    )


def test_the_helper_logs_rather_than_passing(tree):
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_emit_telemetry"
    )
    body = ast.unparse(fn)
    assert "logger.warning" in body or "logger.exception" in body, (
        "_emit_telemetry swallows the failure without recording it, which is the "
        "defect it was introduced to fix"
    )
    assert "exc_info" in body, "the log line carries no traceback, so it names no cause"


def test_the_helper_names_the_event_that_was_lost(tree):
    """A log line saying only 'telemetry failed' does not help anyone."""
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_emit_telemetry"
    )
    call = next(
        n for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and getattr(getattr(n.func, "attr", None), "__str__", lambda: "")() in ("warning", "exception")
    )
    assert any(isinstance(a, ast.Name) and a.id == "event" for a in call.args), (
        "the log line does not include which event was dropped"
    )


def test_every_emit_site_goes_through_the_helper(tree):
    """Three sites are deliberately excluded — see the assertion message."""
    direct = [
        c.lineno for c in _calls_named(tree, "_emit_event")
        # The helper's own pass-through call is the one legitimate direct use.
    ]
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_emit_telemetry"
    )
    inside_helper = {c.lineno for c in _calls_named(fn, "_emit_event")}
    remaining = sorted(set(direct) - inside_helper)
    assert len(remaining) <= 2, (
        f"more direct _emit_event calls than the two known exceptions: {remaining}. "
        "Those two sit inside handlers that return an error to the caller, so their "
        "failure is surfaced rather than swallowed; anything else should use the helper."
    )


def test_the_dispatch_layer_still_logs_its_own_failures():
    """The asymmetry this finding named: dispatch logged, telemetry did not."""
    dispatch = SRC / "mcp_server_nucleus" / "tools" / "_dispatch.py"
    if not dispatch.exists():
        pytest.skip("_dispatch.py not in this export")
    assert "log.exception" in dispatch.read_text(encoding="utf-8")
