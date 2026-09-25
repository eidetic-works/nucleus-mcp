"""A verification tier that checked nothing must not report PASS.

Why this exists: Tier 1's verdict was

    decidable = [s for s in t1_sigs if not s.get("insufficient")]
    if all(s["passed"] for s in decidable): tiers_passed.append(1)

`all([])` is True. So when EVERY signal came back insufficient -- nothing was
actually checked -- the tier was recorded as PASSED.

The history matters more than the bug. The `insufficient` state exists in this
file precisely to stop a check that could not RUN from being read as a failure:
py_compile under a chflags-locked directory cannot write __pycache__, and the
old all() read that as a syntax error and blocked commits over files it never
parsed. That was corrected. The correction introduced the opposite error one
line below, and this one is worse -- a false failure gets investigated, a false
pass does not.
"""

import pytest


def _verdict(signals):
    """Mirror of the shipped Tier-1 verdict, including the empty-set branch."""
    decidable = [s for s in signals if not s.get("insufficient")]
    if not decidable:
        return "skipped"
    return "passed" if all(s["passed"] for s in decidable) else "failed"


def test_all_signals_insufficient_is_not_a_pass():
    """THE BUG. Nothing was checked, so there is nothing to pass."""
    sigs = [{"passed": False, "insufficient": True},
            {"passed": False, "insufficient": True}]
    assert _verdict(sigs) == "skipped", (
        "a tier that could not run a single check reported PASS"
    )


def test_the_premise_all_over_empty_is_true():
    """CONTROL: the whole bug rests on this. If it ever stops holding, the fix
    is unnecessary and should be revisited rather than left as cargo."""
    assert all(x for x in []) is True


def test_a_genuine_pass_still_passes():
    """OPPOSED, load-bearing: routing the empty case to skipped must not make
    real passes unreachable. A tier that can never pass is equally dead."""
    assert _verdict([{"passed": True, "insufficient": False}]) == "passed"


def test_a_genuine_failure_still_fails():
    """OPPOSED: and must not swallow real failures."""
    assert _verdict([{"passed": False, "insufficient": False}]) == "failed"


def test_a_mix_ignores_the_insufficient_one():
    """The original correct behaviour is preserved: an insufficient signal is
    neither pass nor fail, it is excluded -- so one real pass alongside it is
    still a pass."""
    sigs = [{"passed": True, "insufficient": False},
            {"passed": False, "insufficient": True}]
    assert _verdict(sigs) == "passed"


def test_the_shipped_code_has_the_empty_guard():
    """The mirror above models the logic; this pins it to the real file so the
    model cannot drift from the code it claims to describe."""
    import inspect
    from mcp_server_nucleus.runtime import execution_verifier
    src = inspect.getsource(execution_verifier)
    assert "if not decidable:" in src, "the empty-decidable guard is gone"
    assert "all Tier-1 signals were insufficient" in src
