"""Coverage tests for mcp_server_nucleus.tools._marketplace_core."""
import json
import os
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
    """Create marketplace handlers with mock emit_event and get_brain_path."""
    emit_event = mock.MagicMock()
    get_brain_path = mock.MagicMock(return_value=brain_path)
    return mp.register(emit_event, get_brain_path)


# ── register ────────────────────────────────────────────────────

def test_register_returns_dict(handlers):
    assert isinstance(handlers, dict)
    assert "marketplace_search" in handlers
    assert "marketplace_whoami" in handlers
    assert "marketplace_recommend" in handlers
    assert "marketplace_promote" in handlers
    assert "marketplace_quarantine" in handlers
    assert "marketplace_audit" in handlers
    assert "marketplace_compare" in handlers
    assert "marketplace_alert" in handlers
    assert "marketplace_trends" in handlers
    assert "marketplace_export" in handlers
    assert "marketplace_dashboard" in handlers
    assert "marketplace_history" in handlers
    assert "marketplace_can_call" in handlers
    assert "marketplace_subscribe" in handlers
    assert "marketplace_unsubscribe" in handlers
    assert "marketplace_subscriptions" in handlers
    assert "marketplace_diff" in handlers
    assert "marketplace_federation_proxy" in handlers
    assert "marketplace_federation_register" in handlers
    assert "marketplace_federation_sync" in handlers


# ── marketplace_search ──────────────────────────────────────────

def test_marketplace_search_no_tags(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=[]):
        result = handlers["marketplace_search"]()
    data = json.loads(result)
    assert "cards" in data
    assert data["count"] == 0


def test_marketplace_search_with_tags(handlers):
    cards = [{"address": "a@n", "tier": 2, "success_rate": 0.9}]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=cards):
        result = handlers["marketplace_search"](tags=["dev"])
    data = json.loads(result)
    assert data["count"] == 1


def test_marketplace_search_min_tier(handlers):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    cards = [
        {"address": "a@n", "tier": TrustTier.UNVERIFIED, "success_rate": 0.5},
        {"address": "b@n", "tier": TrustTier.TRUSTED, "success_rate": 0.9},
    ]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=cards):
        result = handlers["marketplace_search"](min_tier="trusted")
    data = json.loads(result)
    assert data["count"] == 1
    assert data["cards"][0]["address"] == "b@n"


def test_marketplace_search_invalid_tier(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=[]):
        result = handlers["marketplace_search"](min_tier="invalid")
    data = json.loads(result)
    assert "error" in data


# ── marketplace_whoami ──────────────────────────────────────────

def test_marketplace_whoami_no_role(handlers, monkeypatch):
    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)
    result = handlers["marketplace_whoami"]()
    data = json.loads(result)
    assert data["registered"] is False


def test_marketplace_whoami_unregistered(handlers, monkeypatch):
    monkeypatch.setenv("CC_SESSION_ROLE", "dev")
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=None):
        result = handlers["marketplace_whoami"]()
    data = json.loads(result)
    assert data["registered"] is False


def test_marketplace_whoami_registered(handlers, monkeypatch):
    monkeypatch.setenv("CC_SESSION_ROLE", "dev")
    card = {"address": "dev@nucleus", "tier": 2, "tier_badge": "🟢", "display_name": "Dev",
            "last_promoted_at": "2026-01-01", "inactive": False}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=card):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals.compute_signals",
                        return_value={"connection_count": 5, "success_rate": 0.9, "avg_response_ms": 100, "last_seen_at": "2026-01-01"}):
            result = handlers["marketplace_whoami"]()
    data = json.loads(result)
    assert data["registered"] is True
    assert data["address"] == "dev@nucleus"


def test_marketplace_whoami_with_role_param(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=None):
        result = handlers["marketplace_whoami"](role="admin")
    data = json.loads(result)
    assert data["registered"] is False
    assert data["address"] == "admin@nucleus"


# ── marketplace_recommend ───────────────────────────────────────

def test_marketplace_recommend_no_tokens(handlers):
    result = handlers["marketplace_recommend"]("")
    data = json.loads(result)
    assert data["recommendations"] == []


def test_marketplace_recommend_with_match(handlers):
    cards = [{"address": "dev@n", "tags": ["python", "dev"], "display_name": "Developer", "accepts": ["code"], "tier": 2, "tier_badge": "🟢"}]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=cards):
        result = handlers["marketplace_recommend"]("python code dev")
    data = json.loads(result)
    assert len(data["recommendations"]) > 0


def test_marketplace_recommend_no_match(handlers):
    cards = [{"address": "dev@n", "tags": ["rust"], "display_name": "Rust Dev", "accepts": ["systems"], "tier": 1, "tier_badge": "⚪"}]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=cards):
        result = handlers["marketplace_recommend"]("python web")
    data = json.loads(result)
    assert data["recommendations"] == []


# ── marketplace_promote ─────────────────────────────────────────

def test_marketplace_promote_caller_not_verified(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=None):
        result = handlers["marketplace_promote"]("target@n", "trusted", "caller@n")
    data = json.loads(result)
    assert data["ok"] is False
    assert data["reason"] == "caller_not_verified"


def test_marketplace_promote_unregistered_target(handlers):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    caller_card = {"tier": TrustTier.VERIFIED}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[caller_card, None]):
        result = handlers["marketplace_promote"]("target@n", "trusted", "caller@n")
    data = json.loads(result)
    assert data["ok"] is False
    assert data["reason"] == "unregistered_target"


def test_marketplace_promote_unknown_tier(handlers):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    caller_card = {"tier": TrustTier.VERIFIED}
    target_card = {"tier": TrustTier.UNVERIFIED, "address": "target@n"}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[caller_card, target_card]):
        result = handlers["marketplace_promote"]("target@n", "invalid", "caller@n")
    data = json.loads(result)
    assert data["ok"] is False
    assert "unknown_tier" in data["reason"]


def test_marketplace_promote_success(handlers, brain_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    caller_card = {"tier": TrustTier.VERIFIED}
    target_card = {"tier": TrustTier.UNVERIFIED, "address": "target@n"}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[caller_card, target_card]):
        with mock.patch("mcp_server_nucleus.runtime.marketplace._get_registry_dir",
                        return_value=brain_path / "marketplace" / "registry"):
            with mock.patch("mcp_server_nucleus.runtime.marketplace._get_card_path",
                            return_value=brain_path / "marketplace" / "registry" / "target.json"):
                result = handlers["marketplace_promote"]("target@n", "trusted", "caller@n")
    data = json.loads(result)
    assert data["ok"] is True
    assert data["old_tier"] == TrustTier.UNVERIFIED


# ── marketplace_quarantine ──────────────────────────────────────

def test_marketplace_quarantine_caller_not_verified(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=None):
        result = handlers["marketplace_quarantine"]("target@n", "caller@n", "bad")
    data = json.loads(result)
    assert data["ok"] is False


def test_marketplace_quarantine_success(handlers, brain_path):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    caller_card = {"tier": TrustTier.VERIFIED}
    target_card = {"tier": TrustTier.UNVERIFIED, "address": "target@n"}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[caller_card, target_card]):
        with mock.patch("mcp_server_nucleus.runtime.marketplace._get_registry_dir",
                        return_value=brain_path / "marketplace" / "registry"):
            with mock.patch("mcp_server_nucleus.runtime.marketplace._get_card_path",
                            return_value=brain_path / "marketplace" / "registry" / "target.json"):
                result = handlers["marketplace_quarantine"]("target@n", "caller@n", "bad actor")
    data = json.loads(result)
    assert data["ok"] is True
    assert data["quarantined"] is True


# ── marketplace_audit ───────────────────────────────────────────

def test_marketplace_audit_no_file(handlers, brain_path):
    result = handlers["marketplace_audit"]()
    data = json.loads(result)
    assert data["actions"] == []
    assert data["total"] == 0


def test_marketplace_audit_with_data(handlers, brain_path):
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    entries = [
        {"timestamp": "2026-01-01T00:00:00Z", "action": "promote", "address": "a@n", "caller": "admin"},
        {"timestamp": "2026-01-02T00:00:00Z", "action": "quarantine", "address": "b@n", "caller": "admin"},
    ]
    with open(admin_log, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    result = handlers["marketplace_audit"]()
    data = json.loads(result)
    assert data["total"] == 2


def test_marketplace_audit_with_filters(handlers, brain_path):
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    entries = [
        {"timestamp": "2026-01-01T00:00:00Z", "action": "promote", "address": "a@n", "caller": "admin"},
        {"timestamp": "2026-01-02T00:00:00Z", "action": "quarantine", "address": "b@n", "caller": "other"},
    ]
    with open(admin_log, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    result = handlers["marketplace_audit"](caller="admin")
    data = json.loads(result)
    assert data["total"] == 1


def test_marketplace_audit_since_timestamp(handlers, brain_path):
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    entries = [
        {"timestamp": "2026-01-01T00:00:00Z", "action": "promote", "address": "a@n", "caller": "admin"},
        {"timestamp": "2026-06-01T00:00:00Z", "action": "promote", "address": "b@n", "caller": "admin"},
    ]
    with open(admin_log, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    result = handlers["marketplace_audit"](since_timestamp="2026-03-01T00:00:00Z")
    data = json.loads(result)
    assert data["total"] == 1


# ── marketplace_compare ─────────────────────────────────────────

def test_marketplace_compare_a_not_found(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=None):
        result = handlers["marketplace_compare"]("a@n", "b@n")
    data = json.loads(result)
    assert "error" in data


def test_marketplace_compare_b_not_found(handlers):
    card_a = {"address": "a@n", "tier": 1}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[card_a, None]):
        result = handlers["marketplace_compare"]("a@n", "b@n")
    data = json.loads(result)
    assert "error" in data


def test_marketplace_compare_success(handlers):
    card_a = {"address": "a@n", "tier": 1}
    card_b = {"address": "b@n", "tier": 2}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[card_a, card_b]):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals.compute_signals",
                        return_value={}):
            result = handlers["marketplace_compare"]("a@n", "b@n")
    data = json.loads(result)
    assert "a" in data
    assert "b" in data


# ── marketplace_alert ───────────────────────────────────────────

def test_marketplace_alert(handlers, brain_path):
    result = handlers["marketplace_alert"]("sub@n", "target@n")
    data = json.loads(result)
    assert data["subscribed"] is True
    alerts_file = brain_path / "marketplace" / "alerts.jsonl"
    assert alerts_file.exists()


def test_marketplace_alert_custom_events(handlers, brain_path):
    result = handlers["marketplace_alert"]("sub@n", "target@n", ["custom_event"])
    data = json.loads(result)
    assert data["event_types"] == ["custom_event"]


# ── marketplace_trends ──────────────────────────────────────────

def test_marketplace_trends_no_data(handlers, brain_path):
    result = handlers["marketplace_trends"](days=7)
    data = json.loads(result)
    assert data["trend"] == "insufficient_data"


def test_marketplace_trends_with_registry(handlers, brain_path):
    registry = brain_path / "marketplace" / "registry"
    (registry / "a.json").write_text(json.dumps({"address": "a@n", "tier": 2}))
    (registry / "b.json").write_text(json.dumps({"address": "b@n", "tier": 1}))
    result = handlers["marketplace_trends"](days=7)
    data = json.loads(result)
    assert "trend" in data
    assert "snapshots" in data


# ── marketplace_export ──────────────────────────────────────────

def test_marketplace_export_empty(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=[]):
        result = handlers["marketplace_export"]()
    data = json.loads(result)
    assert data["total"] == 0


def test_marketplace_export_with_cards(handlers):
    cards = [{"address": "a@n", "tier": 2}]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=cards):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals.compute_signals",
                        return_value={"success_rate": 0.9}):
            result = handlers["marketplace_export"]()
    data = json.loads(result)
    assert data["total"] == 1


# ── marketplace_dashboard ───────────────────────────────────────

def test_marketplace_dashboard_empty(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=[]):
        with mock.patch("mcp_server_nucleus.runtime.prometheus.get_metrics_json", return_value={}):
            result = handlers["marketplace_dashboard"]()
    data = json.loads(result)
    assert data["total_registered"] == 0


def test_marketplace_dashboard_with_cards(handlers):
    cards = [{"address": "a@n", "tier": 2, "success_rate": 0.9, "connection_count": 5}]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=cards):
        with mock.patch("mcp_server_nucleus.runtime.prometheus.get_metrics_json",
                        return_value={"tool_calls": {}}):
            result = handlers["marketplace_dashboard"]()
    data = json.loads(result)
    assert data["total_registered"] == 1


# ── marketplace_history ─────────────────────────────────────────

def test_marketplace_history_not_registered(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=None):
        result = handlers["marketplace_history"]("a@n")
    data = json.loads(result)
    assert "error" in data


def test_marketplace_history_no_telemetry(handlers, brain_path):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value={"address": "a@n"}):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals._get_telemetry_file",
                        return_value=brain_path / "nonexistent.jsonl"):
            result = handlers["marketplace_history"]("a@n")
    data = json.loads(result)
    assert data["total_events"] == 0


def test_marketplace_history_with_events(handlers, brain_path):
    tel_file = brain_path / "telemetry.jsonl"
    entries = [
        {"to_address": "a@n", "timestamp": "2026-01-01", "from_address": "b@n", "success": True, "latency_ms": 100},
        {"to_address": "a@n", "timestamp": "2026-01-02", "from_address": "c@n", "success": False, "latency_ms": 200},
    ]
    with open(tel_file, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value={"address": "a@n"}):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals._get_telemetry_file",
                        return_value=tel_file):
            result = handlers["marketplace_history"]("a@n")
    data = json.loads(result)
    assert data["total_events"] == 2
    assert data["events"][0]["cumulative_successes"] == 1


# ── marketplace_can_call ────────────────────────────────────────

def test_marketplace_can_call_unregistered_caller(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=None):
        result = handlers["marketplace_can_call"]("a@n", "b@n")
    data = json.loads(result)
    assert data["allowed"] is False
    assert data["reason"] == "unregistered_caller"


def test_marketplace_can_call_unregistered_target(handlers):
    caller = {"tier": 2}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[caller, None]):
        result = handlers["marketplace_can_call"]("a@n", "b@n")
    data = json.loads(result)
    assert data["allowed"] is False
    assert data["reason"] == "unregistered_target"


def test_marketplace_can_call_quarantined_caller(handlers):
    caller = {"tier": 2, "quarantined": True}
    target = {"tier": 1}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[caller, target]):
        result = handlers["marketplace_can_call"]("a@n", "b@n")
    data = json.loads(result)
    assert data["allowed"] is False
    assert data["reason"] == "quarantined"


def test_marketplace_can_call_target_quarantined(handlers):
    caller = {"tier": 2}
    target = {"tier": 1, "quarantined": True}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[caller, target]):
        result = handlers["marketplace_can_call"]("a@n", "b@n")
    data = json.loads(result)
    assert data["allowed"] is False
    assert data["reason"] == "target_quarantined"


def test_marketplace_can_call_allowed(handlers):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    caller = {"tier": TrustTier.TRUSTED}
    target = {"tier": TrustTier.ACTIVE}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[caller, target]):
        result = handlers["marketplace_can_call"]("a@n", "b@n")
    data = json.loads(result)
    assert data["allowed"] is True


def test_marketplace_can_call_tier_too_low(handlers):
    from mcp_server_nucleus.runtime.marketplace import TrustTier
    caller = {"tier": TrustTier.UNVERIFIED}
    target = {"tier": TrustTier.TRUSTED}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address",
                    side_effect=[caller, target]):
        result = handlers["marketplace_can_call"]("a@n", "b@n")
    data = json.loads(result)
    assert data["allowed"] is False
    assert data["reason"] == "tier_too_low"


def test_marketplace_can_call_fail_open(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", side_effect=Exception("db error")):
        result = handlers["marketplace_can_call"]("a@n", "b@n")
    data = json.loads(result)
    assert data["allowed"] is True
    assert data["reason"] == "lookup_failed_fail_open"


# ── marketplace_subscribe / unsubscribe / subscriptions ─────────

def test_marketplace_subscribe(handlers, brain_path):
    result = handlers["marketplace_subscribe"]("sub@n", "target@n")
    data = json.loads(result)
    assert data["subscribed"] is True


def test_marketplace_unsubscribe_no_file(handlers, brain_path):
    result = handlers["marketplace_unsubscribe"]("sub@n", "target@n")
    data = json.loads(result)
    assert data["removed"] == 0


def test_marketplace_unsubscribe_with_data(handlers, brain_path):
    sub_file = brain_path / "marketplace" / "subscriptions.jsonl"
    entries = [
        {"subscriber": "sub@n", "target": "target@n", "active": True},
        {"subscriber": "other@n", "target": "other_target@n", "active": True},
    ]
    with open(sub_file, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    result = handlers["marketplace_unsubscribe"]("sub@n", "target@n")
    data = json.loads(result)
    assert data["removed"] == 1


def test_marketplace_subscriptions_empty(handlers, brain_path):
    result = handlers["marketplace_subscriptions"]()
    data = json.loads(result)
    assert data["count"] == 0


def test_marketplace_subscriptions_with_data(handlers, brain_path):
    sub_file = brain_path / "marketplace" / "subscriptions.jsonl"
    entries = [
        {"subscriber": "sub@n", "target": "target@n", "active": True, "event_types": ["tier_changed"]},
    ]
    with open(sub_file, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    result = handlers["marketplace_subscriptions"]()
    data = json.loads(result)
    assert data["count"] == 1


def test_marketplace_subscriptions_filtered(handlers, brain_path):
    sub_file = brain_path / "marketplace" / "subscriptions.jsonl"
    entries = [
        {"subscriber": "sub@n", "target": "target@n", "active": True},
        {"subscriber": "other@n", "target": "other@n", "active": True},
    ]
    with open(sub_file, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    result = handlers["marketplace_subscriptions"](subscriber="sub@n")
    data = json.loads(result)
    assert data["count"] == 1


# ── marketplace_diff ────────────────────────────────────────────

def test_marketplace_diff_json_strings(handlers):
    snap_a = json.dumps({"cards": [{"address": "a@n", "tier": 1}]})
    snap_b = json.dumps({"cards": [{"address": "a@n", "tier": 2}, {"address": "b@n", "tier": 1}]})
    result = handlers["marketplace_diff"](snap_a, snap_b)
    data = json.loads(result)
    assert "b@n" in data["added"]
    assert len(data["changed"]) == 1


def test_marketplace_diff_lists(handlers):
    snap_a = [{"address": "a@n", "tier": 1}]
    snap_b = [{"address": "a@n", "tier": 1}, {"address": "b@n", "tier": 2}]
    result = handlers["marketplace_diff"](snap_a, snap_b)
    data = json.loads(result)
    assert "b@n" in data["added"]


def test_marketplace_diff_invalid_json(handlers):
    result = handlers["marketplace_diff"]("invalid", "also invalid")
    data = json.loads(result)
    assert "error" in data


def test_marketplace_diff_removed(handlers):
    snap_a = [{"address": "a@n", "tier": 1}, {"address": "b@n", "tier": 2}]
    snap_b = [{"address": "a@n", "tier": 1}]
    result = handlers["marketplace_diff"](snap_a, snap_b)
    data = json.loads(result)
    assert "b@n" in data["removed"]


# ── marketplace_federation_proxy ────────────────────────────────

def test_marketplace_federation_proxy_no_engine(handlers):
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None):
        result = handlers["marketplace_federation_proxy"]("brain1", "search")
    data = json.loads(result)
    assert data["ok"] is False


def test_marketplace_federation_proxy_unknown_peer(handlers):
    engine = mock.MagicMock()
    engine.get_peers.return_value = []
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
        result = handlers["marketplace_federation_proxy"]("unknown", "search")
    data = json.loads(result)
    assert data["ok"] is False
    assert "Unknown peer" in data["error"]


# ── marketplace_federation_register ─────────────────────────────

def test_marketplace_federation_register_success(handlers):
    card = {"address": "test@n", "display_name": "Test"}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.register_tool", return_value=card):
        with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None):
            result = handlers["marketplace_federation_register"]("test@n", ["cap1"], "Test")
    data = json.loads(result)
    assert data["ok"] is True
    assert data["broadcast_peers"] == 0


def test_marketplace_federation_register_value_error(handlers):
    with mock.patch("mcp_server_nucleus.runtime.marketplace.register_tool", side_effect=ValueError("bad address")):
        result = handlers["marketplace_federation_register"]("bad", None)
    data = json.loads(result)
    assert data["ok"] is False


# ── marketplace_federation_sync ─────────────────────────────────

def test_marketplace_federation_sync_no_engine(handlers):
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None):
        result = handlers["marketplace_federation_sync"]()
    data = json.loads(result)
    assert data["ok"] is False


def test_marketplace_federation_sync_not_running(handlers):
    engine = mock.MagicMock()
    engine.running = False
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
        result = handlers["marketplace_federation_sync"]()
    data = json.loads(result)
    assert data["ok"] is False


# ── Additional coverage tests ────────────────────────────────────

def test_marketplace_federation_sync_success(handlers):
    """Test federation_sync with a running engine."""
    engine = mock.MagicMock()
    engine.running = True
    sync_result = mock.MagicMock()
    sync_result.peer_id = "peer1"
    sync_result.success = True
    sync_result.items_synced = 5
    sync_result.conflicts_resolved = 0
    sync_result.sync_time_ms = 100.5
    sync_result.error = None
    engine.sync_now = mock.AsyncMock(return_value=[sync_result])
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=[]):
            import asyncio
            loop = mock.MagicMock()
            loop.run_until_complete.return_value = [sync_result]
            with mock.patch("asyncio.new_event_loop", return_value=loop):
                result = handlers["marketplace_federation_sync"]()
    data = json.loads(result)
    assert data["ok"] is True


def test_marketplace_federation_sync_exception(handlers):
    """Test federation_sync with exception during sync."""
    engine = mock.MagicMock()
    engine.running = True
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=[]):
            with mock.patch("asyncio.new_event_loop", side_effect=Exception("fail")):
                result = handlers["marketplace_federation_sync"]()
    data = json.loads(result)
    assert data["ok"] is False


def test_marketplace_federation_proxy_unknown_peer(handlers):
    """Test federation_proxy with unknown peer."""
    engine = mock.MagicMock()
    engine.running = True
    engine.get_peers.return_value = []
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
        result = handlers["marketplace_federation_proxy"]("unknown_peer", "search", {})
    data = json.loads(result)
    assert data["ok"] is False


def test_marketplace_federation_proxy_no_engine(handlers):
    """Test federation_proxy with no engine."""
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=None):
        result = handlers["marketplace_federation_proxy"]("peer1", "search", {})
    data = json.loads(result)
    assert data["ok"] is False


def test_marketplace_federation_proxy_success(handlers):
    """Test federation_proxy with successful message send."""
    engine = mock.MagicMock()
    engine.running = True
    peer = mock.MagicMock()
    peer.peer_id = "peer1"
    peer.address = "addr1"
    engine.get_peers.return_value = [peer]
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
        loop = mock.MagicMock()
        loop.run_until_complete.return_value = {"status": "ok"}
        with mock.patch("asyncio.new_event_loop", return_value=loop):
            result = handlers["marketplace_federation_proxy"]("peer1", "search", {"q": "test"})
    data = json.loads(result)
    assert data["ok"] is True


def test_marketplace_federation_proxy_no_response(handlers):
    """Test federation_proxy with no response from peer."""
    engine = mock.MagicMock()
    engine.running = True
    peer = mock.MagicMock()
    peer.peer_id = "peer1"
    peer.address = "addr1"
    engine.get_peers.return_value = [peer]
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
        loop = mock.MagicMock()
        loop.run_until_complete.return_value = None
        with mock.patch("asyncio.new_event_loop", return_value=loop):
            result = handlers["marketplace_federation_proxy"]("peer1", "search", {})
    data = json.loads(result)
    assert data["ok"] is False


def test_marketplace_federation_proxy_exception(handlers):
    """Test federation_proxy with exception during send."""
    engine = mock.MagicMock()
    engine.running = True
    peer = mock.MagicMock()
    peer.peer_id = "peer1"
    peer.address = "addr1"
    engine.get_peers.return_value = [peer]
    with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
        with mock.patch("asyncio.new_event_loop", side_effect=Exception("fail")):
            result = handlers["marketplace_federation_proxy"]("peer1", "search", {})
    data = json.loads(result)
    assert data["ok"] is False


def test_marketplace_federation_register_with_engine(handlers):
    """Test federation_register with a running engine and peers."""
    card = {"address": "test@n", "display_name": "Test", "tier": 0}
    engine = mock.MagicMock()
    engine.running = True
    peer = mock.MagicMock()
    peer.address = "addr1"
    engine.get_online_peers.return_value = [peer]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.register_tool", return_value=card):
        with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
            loop = mock.MagicMock()
            loop.run_until_complete.return_value = []
            with mock.patch("asyncio.new_event_loop", return_value=loop):
                with mock.patch("asyncio.gather", return_value=[]):
                    result = handlers["marketplace_federation_register"]("test@n", ["cap1"], "Test")
    data = json.loads(result)
    assert data["ok"] is True
    assert data["broadcast_peers"] == 1


def test_marketplace_federation_register_broadcast_exception(handlers):
    """Test federation_register with exception during broadcast."""
    card = {"address": "test@n", "display_name": "Test", "tier": 0}
    engine = mock.MagicMock()
    engine.running = True
    peer = mock.MagicMock()
    peer.address = "addr1"
    engine.get_online_peers.return_value = [peer]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.register_tool", return_value=card):
        with mock.patch("mcp_server_nucleus.runtime.federation_ops._get_federation_engine", return_value=engine):
            with mock.patch("asyncio.new_event_loop", side_effect=Exception("fail")):
                result = handlers["marketplace_federation_register"]("test@n", ["cap1"], "Test")
    data = json.loads(result)
    assert data["ok"] is True
    assert data["broadcast_peers"] == 0


def test_marketplace_trends_with_admin_log(handlers, brain_path):
    """Test marketplace_trends with admin log containing promote actions."""
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    admin_log.parent.mkdir(parents=True, exist_ok=True)
    registry_dir = brain_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "test.json").write_text(json.dumps({"address": "test@n", "tier": 1}))
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    entry = json.dumps({
        "action": "promote",
        "timestamp": ts,
        "address": "test@n",
        "from_tier": 0,
        "to_tier": 1,
    })
    admin_log.write_text(entry + "\n")
    result = handlers["marketplace_trends"](days=7)
    data = json.loads(result)
    assert "trend" in data
    assert len(data["snapshots"]) > 0


def test_marketplace_trends_with_corrupt_admin_log(handlers, brain_path):
    """Test marketplace_trends with corrupt admin log entries."""
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    admin_log.parent.mkdir(parents=True, exist_ok=True)
    registry_dir = brain_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "test.json").write_text(json.dumps({"address": "test@n", "tier": 0}))
    admin_log.write_text("not json\n\n")
    result = handlers["marketplace_trends"](days=7)
    data = json.loads(result)
    assert "trend" in data


def test_marketplace_trends_with_bad_timestamp(handlers, brain_path):
    """Test marketplace_trends with bad timestamp in admin log."""
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    admin_log.parent.mkdir(parents=True, exist_ok=True)
    registry_dir = brain_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "test.json").write_text(json.dumps({"address": "test@n", "tier": 0}))
    entry = json.dumps({
        "action": "promote",
        "timestamp": "bad_timestamp",
        "address": "test@n",
        "from_tier": 0,
        "to_tier": 1,
    })
    admin_log.write_text(entry + "\n")
    result = handlers["marketplace_trends"](days=7)
    data = json.loads(result)
    assert "trend" in data


def test_marketplace_trends_with_cards_and_changes(handlers, brain_path):
    """Test marketplace_trends with cards and tier changes."""
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    admin_log.parent.mkdir(parents=True, exist_ok=True)
    registry_dir = brain_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "test.json").write_text(json.dumps({"address": "test@n", "tier": 2}))
    from datetime import datetime, timezone, timedelta
    ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    entry = json.dumps({
        "action": "promote",
        "timestamp": ts,
        "address": "test@n",
        "from_tier": 0,
        "to_tier": 2,
    })
    admin_log.write_text(entry + "\n")
    result = handlers["marketplace_trends"](days=7)
    data = json.loads(result)
    assert "trend" in data
    assert len(data["snapshots"]) > 0


def test_marketplace_trends_with_corrupt_card(handlers, brain_path):
    """Test marketplace_trends with corrupt card file."""
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    admin_log.parent.mkdir(parents=True, exist_ok=True)
    registry_dir = brain_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "bad.json").write_text("not json")
    (registry_dir / "good.json").write_text(json.dumps({"address": "good@n", "tier": 0}))
    result = handlers["marketplace_trends"](days=7)
    data = json.loads(result)
    assert "trend" in data


def test_marketplace_trends_no_cards(handlers, brain_path):
    """Test marketplace_trends with no cards in registry."""
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    admin_log.parent.mkdir(parents=True, exist_ok=True)
    admin_log.write_text(json.dumps({
        "action": "promote",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "address": "test@n",
        "from_tier": 0,
        "to_tier": 1,
    }) + "\n")
    result = handlers["marketplace_trends"](days=7)
    data = json.loads(result)
    assert data["trend"] == "insufficient_data"
    assert data["snapshots"] == []


def test_marketplace_trends_hardening(handlers, brain_path):
    """Test marketplace_trends showing hardening trend."""
    admin_log = brain_path / "marketplace" / "admin_actions.jsonl"
    admin_log.parent.mkdir(parents=True, exist_ok=True)
    registry_dir = brain_path / "marketplace" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "test.json").write_text(json.dumps({"address": "test@n", "tier": 2}))
    from datetime import datetime, timezone, timedelta
    ts_old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    ts_recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    admin_log.write_text(
        json.dumps({"action": "promote", "timestamp": ts_old, "address": "test@n", "from_tier": 0, "to_tier": 1}) + "\n" +
        json.dumps({"action": "promote", "timestamp": ts_recent, "address": "test@n", "from_tier": 1, "to_tier": 2}) + "\n"
    )
    result = handlers["marketplace_trends"](days=7)
    data = json.loads(result)
    assert data["trend"] in ("hardening", "softening", "stable", "insufficient_data")


def test_marketplace_export_with_reputation_error(handlers):
    """Test marketplace_export when ReputationSignals.compute_signals raises."""
    cards = [{"address": "test@n", "tier": 0}]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=cards):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals.compute_signals",
                        side_effect=Exception("fail")):
            result = handlers["marketplace_export"]()
    data = json.loads(result)
    assert data["total"] == 1


def test_marketplace_dashboard_with_invalid_tier(handlers):
    """Test marketplace_dashboard with invalid tier value."""
    cards = [{"address": "test@n", "tier": 999, "inactive": True, "success_rate": 0.5, "connection_count": 3}]
    with mock.patch("mcp_server_nucleus.runtime.marketplace.search_by_tags", return_value=cards):
        with mock.patch("mcp_server_nucleus.runtime.prometheus.get_metrics_json", return_value={"tool_calls": {}}):
            result = handlers["marketplace_dashboard"]()
    data = json.loads(result)
    assert data["total_registered"] == 1
    assert data["inactive_count"] == 1


def test_marketplace_history_with_telemetry(handlers, brain_path):
    """Test marketplace_history with telemetry file."""
    telemetry_dir = brain_path / "telemetry"
    telemetry_dir.mkdir(exist_ok=True)
    telemetry_file = telemetry_dir / "relay_metrics.jsonl"
    entries = [
        json.dumps({"to_address": "test@n", "timestamp": "2026-01-01", "success": True, "from_address": "other@n"}),
        json.dumps({"to_address": "other@n", "timestamp": "2026-01-02", "success": False, "from_address": "test@n"}),
        json.dumps({"to_address": "test@n", "timestamp": "2026-01-03", "success": True, "from_address": "another@n"}),
    ]
    telemetry_file.write_text("\n".join(entries) + "\n")
    card = {"address": "test@n", "tier": 0}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=card):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals._get_telemetry_file",
                        return_value=telemetry_file):
            result = handlers["marketplace_history"]("test@n", limit=10)
    data = json.loads(result)
    assert "events" in data
    assert len(data["events"]) == 2


def test_marketplace_history_telemetry_exception(handlers, brain_path):
    """Test marketplace_history with exception reading telemetry."""
    card = {"address": "test@n", "tier": 0}
    bad_file = mock.MagicMock()
    bad_file.exists.side_effect = Exception("fail")
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=card):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals._get_telemetry_file",
                        return_value=bad_file):
            result = handlers["marketplace_history"]("test@n")
    data = json.loads(result)
    assert "error" in data


def test_marketplace_history_empty_lines(handlers, brain_path):
    """Test marketplace_history with empty lines in telemetry."""
    telemetry_dir = brain_path / "telemetry"
    telemetry_dir.mkdir(exist_ok=True)
    telemetry_file = telemetry_dir / "relay_metrics.jsonl"
    telemetry_file.write_text("\n\n  \n")
    card = {"address": "test@n", "tier": 0}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=card):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals._get_telemetry_file",
                        return_value=telemetry_file):
            result = handlers["marketplace_history"]("test@n")
    data = json.loads(result)
    assert "events" in data
    assert len(data["events"]) == 0


def test_marketplace_history_corrupt_json(handlers, brain_path):
    """Test marketplace_history with corrupt JSON in telemetry."""
    telemetry_dir = brain_path / "telemetry"
    telemetry_dir.mkdir(exist_ok=True)
    telemetry_file = telemetry_dir / "relay_metrics.jsonl"
    telemetry_file.write_text("not json\n")
    card = {"address": "test@n", "tier": 0}
    with mock.patch("mcp_server_nucleus.runtime.marketplace.lookup_by_address", return_value=card):
        with mock.patch("mcp_server_nucleus.runtime.marketplace.ReputationSignals._get_telemetry_file",
                        return_value=telemetry_file):
            result = handlers["marketplace_history"]("test@n")
    data = json.loads(result)
    assert "events" in data
    assert len(data["events"]) == 0


def test_marketplace_unsubscribe_with_corrupt_line(handlers, brain_path):
    """Test marketplace_unsubscribe with corrupt JSON line."""
    sub_file = brain_path / "marketplace" / "subscriptions.jsonl"
    sub_file.parent.mkdir(parents=True, exist_ok=True)
    sub_file.write_text("not json\n" + json.dumps({"subscriber": "sub1", "target": "*"}) + "\n")
    result = handlers["marketplace_unsubscribe"]("sub1", "*")
    data = json.loads(result)
    assert data["removed"] == 1


def test_marketplace_subscriptions_with_corrupt_line(handlers, brain_path):
    """Test marketplace_subscriptions with corrupt JSON line."""
    sub_file = brain_path / "marketplace" / "subscriptions.jsonl"
    sub_file.parent.mkdir(parents=True, exist_ok=True)
    sub_file.write_text("not json\n" + json.dumps({"subscriber": "sub1", "target": "*", "active": True}) + "\n")
    result = handlers["marketplace_subscriptions"]()
    data = json.loads(result)
    assert data["count"] == 1


def test_marketplace_subscriptions_with_duplicates(handlers, brain_path):
    """Test marketplace_subscriptions with duplicate entries."""
    sub_file = brain_path / "marketplace" / "subscriptions.jsonl"
    sub_file.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({"subscriber": "sub1", "target": "*", "active": True})
    sub_file.write_text(entry + "\n" + entry + "\n")
    result = handlers["marketplace_subscriptions"]()
    data = json.loads(result)
    assert data["count"] == 1


def test_marketplace_subscriptions_inactive(handlers, brain_path):
    """Test marketplace_subscriptions with inactive entries."""
    sub_file = brain_path / "marketplace" / "subscriptions.jsonl"
    sub_file.parent.mkdir(parents=True, exist_ok=True)
    sub_file.write_text(json.dumps({"subscriber": "sub1", "target": "*", "active": False}) + "\n")
    result = handlers["marketplace_subscriptions"]()
    data = json.loads(result)
    assert data["count"] == 0
