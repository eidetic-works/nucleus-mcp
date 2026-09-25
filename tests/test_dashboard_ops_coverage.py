"""Coverage tests for mcp_server_nucleus.runtime.dashboard_ops."""
import sys
from unittest import mock

import pytest

from mcp_server_nucleus.runtime import dashboard_ops


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the dashboard engine singleton between tests."""
    dashboard_ops._dashboard_engine = None
    yield
    dashboard_ops._dashboard_engine = None


def test_get_dashboard_engine_not_available(monkeypatch):
    """_get_dashboard_engine returns None when nop_core cannot be imported."""
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "nop_core.dashboard":
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    result = dashboard_ops._get_dashboard_engine()
    assert result is None


def test_get_dashboard_engine_caches(monkeypatch):
    """_get_dashboard_engine caches the singleton."""
    fake_engine = mock.MagicMock()
    fake_module = mock.MagicMock()
    fake_module.DashboardEngine = mock.MagicMock(return_value=fake_engine)

    fake_orch = mock.MagicMock()
    fake_m = mock.MagicMock()
    fake_m.get_orch = mock.MagicMock(return_value=fake_orch)

    monkeypatch.setitem(sys.modules, "nop_core.dashboard", fake_module)
    monkeypatch.setattr(sys.modules["mcp_server_nucleus"], "get_orch", lambda: fake_orch)

    result1 = dashboard_ops._get_dashboard_engine()
    assert result1 is fake_engine
    # Second call should return cached
    result2 = dashboard_ops._get_dashboard_engine()
    assert result2 is fake_engine
    fake_module.DashboardEngine.assert_called_once()


def test_enhanced_dashboard_no_engine(monkeypatch):
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: None)
    result = dashboard_ops._brain_enhanced_dashboard_impl()
    assert "not available" in result


def test_enhanced_dashboard_success(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_engine.render.return_value = "dashboard output"
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_enhanced_dashboard_impl(
        detail_level="detailed", format="json", include_alerts=False, include_trends=True, category="cat"
    )
    assert result == "dashboard output"
    fake_engine.render.assert_called_once_with(
        detail_level="detailed", format="json", include_alerts=False, include_trends=True, category="cat"
    )


def test_enhanced_dashboard_exception(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_engine.render.side_effect = RuntimeError("boom")
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_enhanced_dashboard_impl()
    assert "Dashboard error" in result


def test_snapshot_no_engine(monkeypatch):
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: None)
    result = dashboard_ops._brain_snapshot_dashboard_impl()
    assert "not available" in result


def test_snapshot_success(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_snapshot = mock.MagicMock()
    fake_snapshot.id = "snap1"
    fake_snapshot.name = "My Snapshot"
    fake_snapshot.timestamp = "2026-01-01"
    fake_engine.create_snapshot.return_value = fake_snapshot
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_snapshot_dashboard_impl(name="test")
    assert "snap1" in result
    assert "My Snapshot" in result


def test_snapshot_exception(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_engine.create_snapshot.side_effect = RuntimeError("fail")
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_snapshot_dashboard_impl()
    assert "Snapshot error" in result


def test_list_snapshots_no_engine(monkeypatch):
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: None)
    result = dashboard_ops._brain_list_snapshots_impl()
    assert "not available" in result


def test_list_snapshots_empty(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_engine.list_snapshots.return_value = []
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_list_snapshots_impl()
    assert "No snapshots" in result


def test_list_snapshots_with_data(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_engine.list_snapshots.return_value = [
        {"id": "s1", "name": "Snap 1", "timestamp": "2026-01-01"},
        {"id": "s2", "name": "Snap 2", "timestamp": "2026-01-02"},
    ]
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_list_snapshots_impl()
    assert "s1" in result
    assert "Snap 1" in result
    assert "s2" in result


def test_list_snapshots_exception(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_engine.list_snapshots.side_effect = RuntimeError("err")
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_list_snapshots_impl()
    assert "List snapshots error" in result


def test_get_alerts_no_engine(monkeypatch):
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: None)
    result = dashboard_ops._brain_get_alerts_impl()
    assert "not available" in result


def test_get_alerts_empty(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_engine.get_alerts.return_value = []
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_get_alerts_impl()
    assert "No active alerts" in result


def test_get_alerts_with_data(monkeypatch):
    fake_engine = mock.MagicMock()
    alert1 = mock.MagicMock()
    alert1.level.value = "critical"
    alert1.message = "System down"
    alert1.metric = "cpu"
    alert1.value = 95
    alert1.threshold = 80
    alert2 = mock.MagicMock()
    alert2.level.value = "warning"
    alert2.message = "High memory"
    alert2.metric = "mem"
    alert2.value = 85
    alert2.threshold = 70
    fake_engine.get_alerts.return_value = [alert1, alert2]
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_get_alerts_impl()
    assert "System down" in result
    assert "High memory" in result


def test_get_alerts_exception(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_engine.get_alerts.side_effect = RuntimeError("err")
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_get_alerts_impl()
    assert "Alerts error" in result


def test_set_alert_threshold_no_engine(monkeypatch):
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: None)
    result = dashboard_ops._brain_set_alert_threshold_impl("cpu", "critical", 90)
    assert "not available" in result


def test_set_alert_threshold_success(monkeypatch):
    fake_engine = mock.MagicMock()
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_set_alert_threshold_impl("cpu", "critical", 90)
    assert "Threshold Set" in result
    assert "cpu" in result
    fake_engine.set_alert_threshold.assert_called_once_with("cpu", "critical", 90)


def test_set_alert_threshold_exception(monkeypatch):
    fake_engine = mock.MagicMock()
    fake_engine.set_alert_threshold.side_effect = RuntimeError("err")
    monkeypatch.setattr(dashboard_ops, "_get_dashboard_engine", lambda: fake_engine)
    result = dashboard_ops._brain_set_alert_threshold_impl("cpu", "critical", 90)
    assert "Threshold error" in result
