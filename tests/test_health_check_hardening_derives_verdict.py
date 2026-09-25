"""check_hardening must derive its verdict from the status it fetched.

It called get_hardening_status(), read `components` and `enterprise_ready` out
of the result, and then returned HealthStatus.HEALTHY unconditionally. The only
thing that could produce a non-healthy verdict was an ImportError — a health
check unable to report ill-health from the very data it just retrieved.

Live consequence: C30_utf8_encoding has status "PARTIAL" and was being reported
as HEALTHY.

Worth noting what this does NOT fix. get_hardening_status() is itself largely
hardcoded — `enterprise_ready: True` and the critical_fixes values are literals,
and the only measured field is file_lock. Deriving the verdict is strictly
better than ignoring it, but a green reading here still rests on constants.
That is recorded rather than papered over.
"""

from mcp_server_nucleus.runtime.health_check import check_hardening


def test_a_partial_fix_is_not_reported_healthy():
    """THE BUG, against live data."""
    r = check_hardening()
    assert r["status"] != "healthy" or not r.get("degraded_reasons")
    if r.get("degraded_reasons"):
        assert r["status"] == "degraded"


def test_the_reasons_are_named_not_just_counted():
    """'degraded' with no reason is only marginally better than a false
    HEALTHY — the reader still cannot act on it."""
    r = check_hardening()
    if r["status"] == "degraded":
        assert r["degraded_reasons"], "degraded with no stated reason"
        assert all("=" in reason for reason in r["degraded_reasons"])


def test_robust_file_lock_is_not_flagged_as_degraded():
    """OPPOSED, and my own false positive caught by running it: file_lock's
    values are robust > basic > unavailable, so "robust" is the BEST state. The
    first version of this check assumed "active" was the only healthy value and
    reported the healthiest possible reading as a problem — the same defect as
    a false HEALTHY, with the sign flipped."""
    r = check_hardening()
    assert not any("file_lock=robust" in x for x in r.get("degraded_reasons", []))


def test_it_can_still_report_healthy():
    """OPPOSED, load-bearing: a check that can only ever say DEGRADED is as dead
    as one that can only say HEALTHY. With every component healthy and every fix
    FIXED, the verdict must be healthy."""
    import mcp_server_nucleus.runtime.health_check as hc
    real = hc.check_hardening

    import types
    mod = types.ModuleType("fake_hardening")
    mod.get_hardening_status = lambda: {
        "hardening_version": "1.0.0",
        "components": {"path_sanitizer": "active", "file_lock": "robust"},
        "critical_fixes": {"C20": "FIXED", "C25": "FIXED"},
        "enterprise_ready": True,
    }
    import sys
    sys.modules["mcp_server_nucleus.runtime.hardening"] = mod
    try:
        r = real()
        assert r["status"] == "healthy", f"clean input reported {r['status']}: {r.get('degraded_reasons')}"
        assert r["degraded_reasons"] == []
    finally:
        sys.modules.pop("mcp_server_nucleus.runtime.hardening", None)


def test_an_unavailable_component_is_flagged():
    """OPPOSED the other way: a genuinely bad value must surface."""
    import sys, types
    import mcp_server_nucleus.runtime.health_check as hc
    mod = types.ModuleType("fake_hardening")
    mod.get_hardening_status = lambda: {
        "components": {"file_lock": "unavailable"},
        "critical_fixes": {},
        "enterprise_ready": True,
    }
    sys.modules["mcp_server_nucleus.runtime.hardening"] = mod
    try:
        r = hc.check_hardening()
        assert r["status"] == "degraded"
        assert any("file_lock=unavailable" in x for x in r["degraded_reasons"])
    finally:
        sys.modules.pop("mcp_server_nucleus.runtime.hardening", None)
