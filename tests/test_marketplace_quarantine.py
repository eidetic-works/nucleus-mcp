"""Tests for marketplace_quarantine admin action and can_call quarantine gating.

These tests exercise the REAL ``_marketplace_quarantine`` and
``_marketplace_can_call`` closures produced by
``mcp_server_nucleus.tools._marketplace_core.register`` — not local
reimplementations. Broken production functions must fail these tests.
"""
import json
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.tools import _marketplace_core as mp


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    bp = tmp_path / ".brain"
    bp.mkdir()
    (bp / "marketplace").mkdir()
    (bp / "marketplace" / "registry").mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


@pytest.fixture
def handlers(brain_path):
    """Real marketplace handlers bound to an isolated brain_path."""
    emit_event = mock.MagicMock()
    get_brain_path = mock.MagicMock(return_value=brain_path)
    return mp.register(emit_event, get_brain_path)


def _register(address: str, tier: int, brain_path: Path):
    from mcp_server_nucleus.runtime.marketplace import register_tool
    register_tool({
        "address": address,
        "display_name": address.split("@")[0],
        "accepts": ["task"],
        "emits": ["result"],
        "tags": ["test"],
        "tier": tier,
    }, brain_path=brain_path)


def test_quarantine_verified_caller_succeeds(handlers, brain_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier, lookup_by_address
    _register("root@nucleus", TrustTier.VERIFIED, brain_path)
    _register("bad-actor@nucleus", TrustTier.ACTIVE, brain_path)
    result = handlers["marketplace_quarantine"]("bad-actor@nucleus", "root@nucleus")
    data = json.loads(result)
    assert data["ok"] is True
    card = lookup_by_address("bad-actor@nucleus", brain_path=brain_path)
    assert card["quarantined"] is True


def test_quarantine_blocks_can_call(handlers, brain_path):
    """Quarantined target → marketplace_can_call returns allowed=False, reason=target_quarantined."""
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("root@nucleus", TrustTier.VERIFIED, brain_path)
    _register("caller@nucleus", TrustTier.ACTIVE, brain_path)
    _register("bad-actor@nucleus", TrustTier.ACTIVE, brain_path)
    handlers["marketplace_quarantine"]("bad-actor@nucleus", "root@nucleus")
    result = handlers["marketplace_can_call"]("caller@nucleus", "bad-actor@nucleus")
    data = json.loads(result)
    assert data["allowed"] is False
    assert data["reason"] == "target_quarantined"


def test_quarantine_non_verified_caller_blocked(handlers, brain_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("lowcaller@nucleus", TrustTier.ACTIVE, brain_path)
    _register("target@nucleus", TrustTier.ACTIVE, brain_path)
    result = handlers["marketplace_quarantine"]("target@nucleus", "lowcaller@nucleus")
    data = json.loads(result)
    assert data["ok"] is False
    assert data["reason"] == "caller_not_verified"


def test_quarantine_audit_log_written(handlers, brain_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("root@nucleus", TrustTier.VERIFIED, brain_path)
    _register("suspect@nucleus", TrustTier.ACTIVE, brain_path)
    handlers["marketplace_quarantine"]("suspect@nucleus", "root@nucleus", reason="spam")
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    entries = [json.loads(l) for l in admin_log.read_text().strip().splitlines()]
    assert any(e["action"] == "quarantine" and e["address"] == "suspect@nucleus" for e in entries)
