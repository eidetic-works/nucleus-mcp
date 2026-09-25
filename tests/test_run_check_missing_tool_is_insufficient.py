"""A verification tool that is not installed must not produce a PASS.

_run_check caught FileNotFoundError -- the tool binary is absent -- and returned
{"passed": True, "error": "tool not found, skipped"}. A check that never
executed counted toward the tier verdict as though the file had been verified.
Uninstall the linter and the tree goes green.

execution_verifier ALREADY had the honest value. `insufficient` is set around
L601 for permission errors, with the comment: "unknown coerced into a verdict.
INSUFFICIENT is the honest value, and it is excluded from the tier verdict
rather than blocking." But that scan only inspects signals where passed is
FALSE, so a branch claiming passed=True routed around the exact state introduced
to cover it.

Two bugs of the same shape in one file, one line apart in intent: this, and the
Tier-1 verdict where all([]) made an empty decidable-set report PASS.
"""

from mcp_server_nucleus.runtime.execution_verifier import _run_check


def test_a_missing_tool_is_not_a_pass():
    """THE BUG."""
    r = _run_check(["definitely-not-a-real-tool-xyz"], "faketool", "x.py")
    assert r["passed"] is False, "an uninstalled tool reported passed=True"


def test_a_missing_tool_is_marked_insufficient():
    """It must also not read as a FAILURE. The tool's absence says nothing about
    the file, which is what `insufficient` exists to express."""
    r = _run_check(["definitely-not-a-real-tool-xyz"], "faketool", "x.py")
    assert r.get("insufficient") is True
    assert r.get("state") == "INSUFFICIENT"


def test_the_error_says_it_was_not_verified():
    """A reader of this signal must not be able to mistake it for a verdict."""
    r = _run_check(["definitely-not-a-real-tool-xyz"], "faketool", "x.py")
    err = str(r.get("error", ""))
    assert "could not RUN" in err and "NOT verified" in err


def test_a_real_tool_that_succeeds_still_passes():
    """OPPOSED, load-bearing: marking everything insufficient would make the
    verifier incapable of ever confirming anything."""
    r = _run_check(["true"], "true-cmd", "x.py")
    assert r["passed"] is True
    assert not r.get("insufficient")


def test_a_real_tool_that_fails_still_fails():
    """OPPOSED: and must not swallow genuine failures into INSUFFICIENT."""
    r = _run_check(["false"], "false-cmd", "x.py")
    assert r["passed"] is False
    assert not r.get("insufficient"), "a real failure was excused as insufficient"


def test_insufficient_is_excluded_from_the_tier_verdict():
    """The consequence: the tier's decidable-set filter must drop it, so the
    signal neither passes nor fails the tier."""
    sigs = [
        {"passed": True, "insufficient": False},
        _run_check(["definitely-not-a-real-tool-xyz"], "faketool", "x.py"),
    ]
    decidable = [s for s in sigs if not s.get("insufficient")]
    assert len(decidable) == 1
    assert all(s["passed"] for s in decidable) is True
