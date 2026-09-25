"""Drift-guard tests for federation.py module-level _EVT_* constants.

Background (E7 follow-up, PR #351 cc-peer review):
    `runtime/federation.py` previously called `emit_event(EventTypes.FEDERATION_*,
    ...)` directly inside `if DSOR_AVAILABLE:` guards. The DSoR-unavailable
    fallback was simply "skip emission". The cc-peer review flagged the risk
    that any future fallback added with raw string literals (e.g.
    `'federation_peer_joined'`) could silently drift from the `EventTypes.*`
    constant strings in `event_stream.py`.

    The fix introduces module-level `_EVT_*` constants computed once at import:
        _EVT_PEER_JOINED = EventTypes.FEDERATION_PEER_JOINED if DSOR_AVAILABLE else "federation_peer_joined"

    Both branches resolve to the SAME identifier — so call sites only reference
    the module-level constant and drift becomes impossible.

This test asserts the equality holds. If anyone edits the EventTypes string
values, or adds a typo to a fallback literal, this test fails fast.
"""

import pytest


def test_evt_constants_match_eventtypes_and_literal_fallback():
    """_EVT_* constants must equal both the EventTypes.* string AND the literal
    fallback used in the DSOR_AVAILABLE=False branch."""
    try:
        from mcp_server_nucleus.runtime import federation as fed_mod
        from mcp_server_nucleus.runtime.event_stream import EventTypes
    except ImportError:
        pytest.skip("federation/event_stream modules not available")

    pairs = [
        ("_EVT_PEER_JOINED", "FEDERATION_PEER_JOINED", "federation_peer_joined"),
        ("_EVT_PEER_LEFT", "FEDERATION_PEER_LEFT", "federation_peer_left"),
        ("_EVT_PEER_SUSPECT", "FEDERATION_PEER_SUSPECT", "federation_peer_suspect"),
        ("_EVT_LEADER_ELECTED", "FEDERATION_LEADER_ELECTED", "federation_leader_elected"),
        ("_EVT_TASK_ROUTED", "FEDERATION_TASK_ROUTED", "federation_task_routed"),
        ("_EVT_STATE_SYNCED", "FEDERATION_STATE_SYNCED", "federation_state_synced"),
    ]

    for fed_attr, event_attr, literal in pairs:
        assert hasattr(fed_mod, fed_attr), (
            f"federation.py missing module-level constant {fed_attr}"
        )
        assert hasattr(EventTypes, event_attr), (
            f"EventTypes missing {event_attr} — fallback literal cannot stay in sync"
        )
        fed_value = getattr(fed_mod, fed_attr)
        evt_value = getattr(EventTypes, event_attr)
        assert fed_value == evt_value, (
            f"{fed_attr}={fed_value!r} drifted from EventTypes.{event_attr}={evt_value!r}"
        )
        assert fed_value == literal, (
            f"{fed_attr}={fed_value!r} drifted from literal fallback {literal!r}"
        )


def test_federation_call_sites_use_module_constants_not_eventtypes():
    """Verify federation.py emit_event call sites reference _EVT_* names, not
    repeat the `EventTypes.FOO if DSOR_AVAILABLE else "foo"` ternary inline.
    This is the structural guarantee that the DSOR_AVAILABLE=False branch
    cannot silently diverge from the DSOR_AVAILABLE=True branch.

    Two explicit exceptions are allowed (documented in federation.py):
      1. `record_decision(... event_type=EventTypes.FEDERATION_PEER_JOINED if
         DSOR_AVAILABLE else "federation_join", ...)` inside `join()` —
         the fallback string is intentionally distinct (federation_join, not
         federation_peer_joined) to distinguish the seeded-join action from
         a peer-acceptance callback.
      2. `_sync_event_type = _event_stream_mod.EventTypes.FEDERATION_STATE_SYNCED`
         inside `force_sync()` — runtime-resolved through the monkey-patchable
         module reference for test fixtures.
    """
    import inspect
    try:
        from mcp_server_nucleus.runtime import federation as fed_mod
    except ImportError:
        pytest.skip("federation module not available")

    src_lines = inspect.getsource(fed_mod).splitlines()
    offending = []
    for i, ln in enumerate(src_lines, start=1):
        if "EventTypes.FEDERATION_" not in ln:
            continue
        stripped = ln.strip()
        # Allowed: module-level _EVT_* declarations
        if stripped.startswith("_EVT_") and "EventTypes.FEDERATION_" in stripped:
            continue
        # Allowed: bespoke "federation_join" fallback (semantic difference)
        if '"federation_join"' in stripped:
            continue
        # Allowed: monkey-patchable module reference for sync test fixtures
        if "_event_stream_mod.EventTypes.FEDERATION_" in stripped:
            continue
        offending.append(f"  line {i}: {stripped}")

    assert not offending, (
        "federation.py still references EventTypes.FEDERATION_* outside the "
        "allow-list — call sites should use _EVT_* constants:\n"
        + "\n".join(offending)
    )
