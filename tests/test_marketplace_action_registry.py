"""Atom A — registration meta-test (2026-05-05).

Parametrized test that mechanically kills #264/#266-class test-theater:
every marketplace_<X> action MUST be registered in the nucleus_sync
ROUTER (tools/sync.py) such that calling nucleus_sync("marketplace_<X>",
{...}) does NOT return {"error": "Unknown action ..."}.

A handler that lives only as a private helper inside a test file or source
file but is never wired into ROUTER will fail here. This is the structural
fix that makes self-attestation unnecessary: CI enforces registration.

Coverage: all marketplace actions currently documented in nucleus_sync
docstring + any discovered by scanning sync.py for _marketplace_* defs.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_brain(tmp_path: Path) -> Path:
    brain = tmp_path / ".brain"
    brain.mkdir(parents=True, exist_ok=True)
    return brain


async def _call(nucleus_sync, action: str, params: dict) -> dict:
    """Call nucleus_sync and always return a parsed dict."""
    raw = await nucleus_sync(action=action, params=params)
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": raw}
    return raw if isinstance(raw, dict) else {"_raw": raw}


def _is_unknown_action(result: dict) -> bool:
    """True iff the dispatcher returned the 'Unknown action' sentinel."""
    err = result.get("error", "")
    if isinstance(err, str) and "Unknown action" in err:
        return True
    # Also check nested envelope (when response is wrapped)
    data = result.get("data", {})
    if isinstance(data, dict):
        err2 = data.get("error", "")
        if isinstance(err2, str) and "Unknown action" in err2:
            return True
    return False


# ---------------------------------------------------------------------------
# Fixture — nucleus_sync callable with isolated brain
# ---------------------------------------------------------------------------

@pytest.fixture()
def nucleus_sync(tmp_path, monkeypatch):
    """Return a nucleus_sync callable bound to a fresh tmp brain."""
    brain = _make_brain(tmp_path)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

    # Import after env is set so get_brain_path() resolves correctly.
    from mcp_server_nucleus.tools.sync import register

    # Build a minimal mock MCP host that captures the registered tool.
    tools: dict = {}

    class _MockMCP:
        def tool(self, **kwargs):
            def decorator(fn):
                tools[fn.__name__] = fn
                return fn
            return decorator

    class _MockHelpers:
        def get(self, key, default=None):
            return default

        def __getitem__(self, key):
            import mcp_server_nucleus.runtime.common as _common
            _map = {
                "make_response": lambda success, data=None, error=None: (
                    json.dumps({"success": success, "data": data, "error": error})
                ),
                "emit_event": lambda *a, **kw: None,
                "get_brain_path": _common.get_brain_path,
            }
            return _map[key]

    register(_MockMCP(), _MockHelpers())
    fn = tools.get("nucleus_sync")
    assert fn is not None, "nucleus_sync was not registered by tools/sync.py register()"
    return fn


# ---------------------------------------------------------------------------
# Parametrized action list
# ---------------------------------------------------------------------------

# Canonical list discovered from tools/sync.py ROUTER + docstring (2026-05-05).
# When new marketplace_<X> atoms ship, add the action name here.
# The test will FAIL if the action is added here but not registered — which is
# exactly the signal we want.
MARKETPLACE_ACTIONS = [
    # Core read-only
    "marketplace_search",
    "marketplace_whoami",
    "marketplace_can_call",
    "marketplace_recommend",
    "marketplace_dashboard",
    "marketplace_history",
    "marketplace_export",
    # Admin mutations
    "marketplace_promote",
    "marketplace_quarantine",
    # Audit (Atom 2)
    "marketplace_audit",
    # Compare (Atom 3)
    "marketplace_compare",
    # Alerting (Atom 1)
    "marketplace_alert",
    # Trends (Atom 4)
    "marketplace_trends",
    # Snapshot ops (Atom B pre-approved)
    "marketplace_diff",
    # Subscription ops (Atom C pre-approved)
    "marketplace_subscribe",
    "marketplace_unsubscribe",
    "marketplace_subscriptions",
    # Federation Parallel-Chain primitives
    "marketplace_federation_proxy",
    "marketplace_federation_register",
    "marketplace_federation_sync",
]

# capability_registry_* actions (if any exist in sync.py)
CAPABILITY_REGISTRY_ACTIONS = [
    # Currently none in sync.py — placeholder for future atoms
]

# reputation_* actions (if any exist in sync.py)
REPUTATION_ACTIONS = [
    # Currently none in sync.py — placeholder for future atoms
]

# Combined list for parametrization
ALL_ACTIONS = MARKETPLACE_ACTIONS + CAPABILITY_REGISTRY_ACTIONS + REPUTATION_ACTIONS

# Minimal params that satisfy required positional args without triggering
# domain errors — we only care that the dispatcher ROUTES the call, not
# that the handler succeeds with these exact inputs.
_MIN_PARAMS: dict[str, dict] = {
    "marketplace_can_call": {"caller": "_test_caller", "target": "_test_target"},
    "marketplace_recommend": {"task": "_test"},
    "marketplace_history": {"address": "_test_addr"},
    "marketplace_promote": {"address": "_test_addr", "new_tier": "T1", "caller": "admin"},
    "marketplace_quarantine": {"address": "_test_addr"},
    "marketplace_audit": {},
    "marketplace_compare": {"a": "_test_addr_a", "b": "_test_addr_b"},
    "marketplace_alert": {"subscriber": "_test_sub", "target": "_test_target"},
    "marketplace_trends": {"days": 7},
    "marketplace_diff": {"snapshot_a": {"addresses": []}, "snapshot_b": {"addresses": []}},
    "marketplace_subscribe": {"subscriber": "_test_sub"},
    "marketplace_unsubscribe": {"subscriber": "_test_sub"},
    # Federation primitives — FederationEngine unavailable in test env, expect ok=False not Unknown action
    "marketplace_federation_proxy": {"target_brain": "_test_brain", "action": "marketplace_search"},
    "marketplace_federation_register": {"address": "test-brain@nucleus"},
    "marketplace_federation_sync": {},
}


@pytest.mark.parametrize("action", ALL_ACTIONS)
async def test_marketplace_action_is_registered(nucleus_sync, action):
    """Assert that nucleus_sync routes marketplace_<X> without 'Unknown action'.

    This is the #264/#266 theater killer: a private helper that was never
    wired into ROUTER will hit the dispatch fallback and return
    {"error": "Unknown action ..."}, failing this test immediately.
    """
    params = _MIN_PARAMS.get(action, {})
    result = await _call(nucleus_sync, action, params)
    assert not _is_unknown_action(result), (
        f"nucleus_sync(action='{action}') returned 'Unknown action' — "
        f"handler exists but is NOT registered in tools/sync.py ROUTER.\n"
        f"Full response: {json.dumps(result, indent=2, default=str)}"
    )
