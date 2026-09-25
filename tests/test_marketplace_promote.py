"""Tests for marketplace_promote admin action.

These tests exercise the REAL ``_marketplace_promote`` closure produced by
``mcp_server_nucleus.tools._marketplace_core.register`` — not a local
reimplementation. A broken production function must fail these tests.
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


def test_promote_verified_caller_succeeds(handlers, brain_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier, lookup_by_address
    _register("root@nucleus", TrustTier.VERIFIED, brain_path)
    _register("target@nucleus", TrustTier.UNVERIFIED, brain_path)
    result = handlers["marketplace_promote"]("target@nucleus", "trusted", "root@nucleus")
    data = json.loads(result)
    assert data["ok"] is True
    card = lookup_by_address("target@nucleus", brain_path=brain_path)
    assert card["tier"] == TrustTier.TRUSTED


def test_promote_non_verified_caller_blocked(handlers, brain_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("lowcaller@nucleus", TrustTier.ACTIVE, brain_path)
    _register("target@nucleus", TrustTier.UNVERIFIED, brain_path)
    result = handlers["marketplace_promote"]("target@nucleus", "trusted", "lowcaller@nucleus")
    data = json.loads(result)
    assert data["ok"] is False
    assert data["reason"] == "caller_not_verified"


def test_promote_audit_log_written(handlers, brain_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("root@nucleus", TrustTier.VERIFIED, brain_path)
    _register("agent@nucleus", TrustTier.UNVERIFIED, brain_path)
    handlers["marketplace_promote"]("agent@nucleus", "active", "root@nucleus")
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    assert admin_log.exists()
    entries = [json.loads(l) for l in admin_log.read_text().strip().splitlines()]
    assert any(e["action"] == "promote" and e["address"] == "agent@nucleus" for e in entries)


def test_promote_unregistered_target_blocked(handlers, brain_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    _register("root@nucleus", TrustTier.VERIFIED, brain_path)
    result = handlers["marketplace_promote"]("ghost@nucleus", "trusted", "root@nucleus")
    data = json.loads(result)
    assert data["ok"] is False
    assert data["reason"] == "unregistered_target"
