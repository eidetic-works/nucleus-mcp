"""
Coverage tests for mcp_server_nucleus.runtime.incident_ops.

Targets 90%+ line coverage. Uses tmp_path for filesystem, monkeypatch for
env vars, and mocks channels/sync_ops/telemetry_ops. No real
network/subprocess.
"""
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import incident_ops as iops
from mcp_server_nucleus.runtime.incident_ops import (
    IncidentManager,
    get_incident_manager,
    handle_alert,
)


# ──────────────────────────────────────────────────────────────────────
# Construction / setup
# ──────────────────────────────────────────────────────────────────────

def test_init_creates_incidents_dir(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    assert mgr.incidents_dir == brain / "incidents"
    assert mgr.incidents_dir.exists()
    assert "flush_cache" in mgr._healing_registry
    assert "force_sync" in mgr._healing_registry
    assert "restart_worker" in mgr._healing_registry


def test_init_defaults_brain_path(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    mgr = IncidentManager()
    assert mgr.brain_path == brain


# ──────────────────────────────────────────────────────────────────────
# Healers
# ──────────────────────────────────────────────────────────────────────

def test_healer_flush_cache_success(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    fake_mod = types.ModuleType("mcp_server_nucleus.runtime.telemetry_ops")
    fake_mod._invalidate_cache = MagicMock()
    with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.telemetry_ops": fake_mod}):
        result = mgr._healer_flush_cache()
    assert "SUCCESS" in result
    fake_mod._invalidate_cache.assert_called_once()


def test_healer_flush_cache_failure(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    fake_mod = types.ModuleType("mcp_server_nucleus.runtime.telemetry_ops")
    fake_mod._invalidate_cache = MagicMock(side_effect=RuntimeError("nope"))
    with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.telemetry_ops": fake_mod}):
        result = mgr._healer_flush_cache()
    assert "FAILED" in result


def test_healer_flush_cache_import_error(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    # Force ImportError by hiding the module
    with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.telemetry_ops": None}):
        result = mgr._healer_flush_cache()
    assert "FAILED" in result


def test_healer_force_sync_success(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    fake_mod = types.ModuleType("mcp_server_nucleus.runtime.sync_ops")
    fake_mod.perform_sync = MagicMock(return_value={"files_synced": ["a", "b"]})
    with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.sync_ops": fake_mod}):
        result = mgr._healer_force_sync()
    assert "SUCCESS" in result
    assert "2 files" in result
    fake_mod.perform_sync.assert_called_once_with(force=True, brain_path=brain)


def test_healer_force_sync_failure(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    fake_mod = types.ModuleType("mcp_server_nucleus.runtime.sync_ops")
    fake_mod.perform_sync = MagicMock(side_effect=RuntimeError("sync err"))
    with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.sync_ops": fake_mod}):
        result = mgr._healer_force_sync()
    assert "FAILED" in result


def test_healer_restart_worker(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    result = mgr._healer_restart_worker()
    assert "PENDING" in result


# ──────────────────────────────────────────────────────────────────────
# attempt_auto_heal
# ──────────────────────────────────────────────────────────────────────

def test_attempt_auto_heal_unknown(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    assert "UNKNOWN HEALER" in mgr.attempt_auto_heal("nope")


def test_attempt_auto_heal_known(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    result = mgr.attempt_auto_heal("restart_worker")
    assert "PENDING" in result


# ──────────────────────────────────────────────────────────────────────
# create_incident_artifact
# ──────────────────────────────────────────────────────────────────────

def test_create_incident_artifact(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    path = mgr.create_incident_artifact("Something broke", {"key": "val"}, severity="ERROR")
    assert path.exists()
    content = path.read_text()
    assert "Something broke" in content
    assert "ERROR" in content
    assert "OPEN" in content
    assert '"key": "val"' in content
    # month dir created
    assert path.parent == mgr.incidents_dir / path.parent.name


def test_create_incident_artifact_default_severity(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    path = mgr.create_incident_artifact("boom", {})
    content = path.read_text()
    assert "ERROR" in content


# ──────────────────────────────────────────────────────────────────────
# handle_alert
# ──────────────────────────────────────────────────────────────────────

def test_handle_alert_telemetry_domain(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    alert = {"domain": "telemetry", "rate_per_min": 10.0, "threshold_rate": 5.0}
    with patch.object(mgr, "_notify_incident") as mock_notify, \
         patch.object(mgr, "attempt_auto_heal", return_value="ok") as mock_heal:
        mgr.handle_alert(alert)
    mock_notify.assert_called_once()
    mock_heal.assert_called_once_with("flush_cache")


def test_handle_alert_sync_domain(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    alert = {"domain": "sync", "rate_per_min": 10.0, "threshold_rate": 5.0}
    with patch.object(mgr, "_notify_incident"), \
         patch.object(mgr, "attempt_auto_heal", return_value="ok") as mock_heal:
        mgr.handle_alert(alert)
    mock_heal.assert_called_once_with("force_sync")


def test_handle_alert_other_domain_no_heal(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    alert = {"domain": "llm", "rate_per_min": 10.0, "threshold_rate": 5.0}
    with patch.object(mgr, "_notify_incident"), \
         patch.object(mgr, "attempt_auto_heal") as mock_heal:
        mgr.handle_alert(alert)
    mock_heal.assert_not_called()


def test_handle_alert_defaults(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    alert = {}
    with patch.object(mgr, "_notify_incident"), \
         patch.object(mgr, "attempt_auto_heal") as mock_heal:
        mgr.handle_alert(alert)
    # UNKNOWN domain => no heal
    mock_heal.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# _notify_incident
# ──────────────────────────────────────────────────────────────────────

def test_notify_incident_success(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    fake_channels = types.ModuleType("mcp_server_nucleus.runtime.channels")
    router = MagicMock()
    router.notify.return_value = {"slack": True, "discord": False}
    fake_channels.get_channel_router = MagicMock(return_value=router)
    with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.channels": fake_channels}):
        mgr._notify_incident("summary", Path("INCIDENT-x.md"))
    router.notify.assert_called_once()


def test_notify_incident_no_channels(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    fake_channels = types.ModuleType("mcp_server_nucleus.runtime.channels")
    router = MagicMock()
    router.notify.return_value = {}
    fake_channels.get_channel_router = MagicMock(return_value=router)
    with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.channels": fake_channels}):
        mgr._notify_incident("summary", Path("INCIDENT-x.md"))


def test_notify_incident_all_false(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    fake_channels = types.ModuleType("mcp_server_nucleus.runtime.channels")
    router = MagicMock()
    router.notify.return_value = {"slack": False}
    fake_channels.get_channel_router = MagicMock(return_value=router)
    with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.channels": fake_channels}):
        mgr._notify_incident("summary", Path("INCIDENT-x.md"))


def test_notify_incident_exception_swallowed(tmp_path):
    brain = tmp_path / ".brain"
    brain.mkdir()
    mgr = IncidentManager(brain_path=brain)
    fake_channels = types.ModuleType("mcp_server_nucleus.runtime.channels")
    fake_channels.get_channel_router = MagicMock(side_effect=RuntimeError("no channels"))
    with patch.dict(sys.modules, {"mcp_server_nucleus.runtime.channels": fake_channels}):
        # should not raise
        mgr._notify_incident("summary", Path("INCIDENT-x.md"))


# ──────────────────────────────────────────────────────────────────────
# Singleton + facade
# ──────────────────────────────────────────────────────────────────────

def test_get_incident_manager_singleton(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    # reset singleton
    iops._manager = None
    m1 = get_incident_manager()
    m2 = get_incident_manager()
    assert m1 is m2
    # cleanup
    iops._manager = None


def test_handle_alert_facade(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    iops._manager = None
    with patch.object(IncidentManager, "handle_alert") as mock_h:
        handle_alert({"domain": "telemetry", "rate_per_min": 1.0, "threshold_rate": 0.5})
    mock_h.assert_called_once()
    iops._manager = None
