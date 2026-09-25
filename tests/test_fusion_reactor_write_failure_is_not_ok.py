"""A failed engram write must not be reported as a written engram.

fusion_reactor guarded both of its engram writes with `except Exception` and,
on falling through, appended {"status": "ok"} and incremented
meta.engrams_written.

`_brain_write_engram_impl` NEVER RAISES. Its top-level handler returns
make_response(False, error=...) instead. Verified, not assumed: calling it with
an invalid key returns '{"success": false, ... "error": "Security Violation:
..."}' and raises nothing.

So the except was unreachable and every failed write was counted as a success.
That is the failure this repo exists to catch, in the code that writes the
memories the rest of the system reasons from: the reactor reported
engrams_written > 0 for engrams that were never stored.
"""

import json

from mcp_server_nucleus.runtime.god_combos.fusion_reactor import (
    _engram_write_succeeded,
)


def test_a_success_response_counts_as_written():
    ok, why = _engram_write_succeeded(json.dumps({"success": True, "data": {}}))
    assert ok is True and why == ""


def test_a_failure_response_does_NOT_count_as_written():
    """THE BUG: this exact shape was previously counted as ok."""
    resp = json.dumps({"success": False, "data": None,
                       "error": "Security Violation: Key must be at least 2 characters"})
    ok, why = _engram_write_succeeded(resp)
    assert ok is False
    assert "Security Violation" in why


def test_the_real_writer_returns_rather_than_raises():
    """CONTROL, and the premise of the whole fix. If _brain_write_engram_impl
    ever starts RAISING on bad input, the original `except Exception` becomes
    live and this response check is belt-and-braces rather than the only
    guard -- worth knowing, not worth silently assuming."""
    from mcp_server_nucleus.runtime.engram_ops import _brain_write_engram_impl
    result = _brain_write_engram_impl(key="x", value="v", context="bogus", intensity=5)
    assert isinstance(result, str), "writer raised; the premise changed"
    assert json.loads(result)["success"] is False


def test_an_unparseable_response_is_a_FAILURE_not_a_success():
    """OPPOSED: an answer nobody can read is not a yes. Defaulting the other way
    would rebuild the original bug behind a parser."""
    ok, why = _engram_write_succeeded("not json at all")
    assert ok is False and "unparseable" in why


def test_an_unexpected_type_is_a_failure():
    assert _engram_write_succeeded(None)[0] is False
    assert _engram_write_succeeded(42)[0] is False


def test_a_dict_response_also_works():
    """The writer returns a JSON string today; a dict is the obvious future
    shape and must not silently read as failure."""
    assert _engram_write_succeeded({"success": True})[0] is True


def test_both_write_sites_check_the_response():
    """The mechanism is only useful where it is CALLED. Both sites previously
    relied on an unreachable except."""
    import inspect
    from mcp_server_nucleus.runtime.god_combos import fusion_reactor
    src = inspect.getsource(fusion_reactor)
    assert src.count("_engram_write_succeeded(_write_result)") == 2
    assert src.count("_write_result = _brain_write_engram_impl(") == 2
