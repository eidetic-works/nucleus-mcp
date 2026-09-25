"""Tests for runtime.health_sidecar + tools._retry."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import health_sidecar as hs
from mcp_server_nucleus.tools import _retry


# ---------------------------------------------------------------------------
# State API
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_state():
    with hs._state_lock:
        hs._state.update({
            "started_at": None,
            "last_heartbeat_at": None,
            "last_tool_call_at": None,
            "pid": None,
            "sessions": [],
            "version": None,
            "status": "unknown",
        })
    yield


def test_mark_started_populates_state():
    hs.mark_started(pid=1234, version="test-1.0")
    s = hs.snapshot()
    assert s["pid"] == 1234
    assert s["version"] == "test-1.0"
    assert s["status"] == "healthy"
    assert s["started_at"] is not None


def test_mark_tool_call_updates_timestamp():
    hs.mark_started(pid=1, version="x")
    hs.mark_tool_call()
    s = hs.snapshot()
    assert s["last_tool_call_at"] is not None


def test_mark_sessions():
    hs.mark_session_active("sess-1")
    hs.mark_session_active("sess-2")
    hs.mark_session_active("sess-1")  # idempotent
    assert hs.snapshot()["sessions"] == ["sess-1", "sess-2"]
    hs.mark_session_closed("sess-1")
    assert hs.snapshot()["sessions"] == ["sess-2"]


# ---------------------------------------------------------------------------
# Sidecar lifecycle — UDS (acceptance criterion: 0600 mode)
# ---------------------------------------------------------------------------


@pytest.fixture
def sidecar_paths(tmp_path):
    """macOS AF_UNIX paths must be <= 104 chars. Use /tmp/nuc-<pid>/<name>."""
    import tempfile
    import uuid
    # Keep total path short: /tmp/nuc-<12hex>/h.sock
    short_dir = Path(tempfile.gettempdir()) / f"nuc-{uuid.uuid4().hex[:8]}"
    brain = tmp_path / ".brain"
    brain.mkdir(parents=True, exist_ok=True)
    yield {"socket_dir": short_dir, "brain_path": brain}
    # Cleanup
    try:
        for p in short_dir.iterdir():
            p.unlink()
        short_dir.rmdir()
    except (OSError, FileNotFoundError):
        pass


def _make_sidecar(paths):
    return hs.HealthSidecar(socket_dir=paths["socket_dir"], socket_file="h.sock")


def test_sidecar_uds_mode_is_0600(sidecar_paths):
    """Acceptance criterion: socket permissions must be owner rw only."""
    sc = _make_sidecar(sidecar_paths)
    sc.start(sidecar_paths["brain_path"])
    try:
        mode = sc.socket_mode()
        assert mode == hs.SOCKET_MODE
        assert mode == 0o600
    finally:
        sc.stop()


def test_sidecar_health_endpoint_returns_snapshot(sidecar_paths):
    sc = _make_sidecar(sidecar_paths)
    sc.start(sidecar_paths["brain_path"])
    try:
        time.sleep(0.05)
        result = hs.query("/health", socket_path=sc.socket_path, timeout=2.0)
        assert result.get("status") in {"healthy", "stale"}
        assert "pid" in result
        assert result["pid"] == os.getpid()
    finally:
        sc.stop()


def test_sidecar_sessions_endpoint(sidecar_paths):
    sc = _make_sidecar(sidecar_paths)
    sc.start(sidecar_paths["brain_path"])
    hs.mark_session_active("sess-abc")
    try:
        time.sleep(0.05)
        result = hs.query("/sessions", socket_path=sc.socket_path, timeout=2.0)
        assert "sess-abc" in result.get("sessions", [])
    finally:
        sc.stop()


def test_sidecar_unknown_endpoint_returns_404(sidecar_paths):
    sc = _make_sidecar(sidecar_paths)
    sc.start(sidecar_paths["brain_path"])
    try:
        time.sleep(0.05)
        result = hs.query("/does-not-exist", socket_path=sc.socket_path, timeout=2.0)
        assert result.get("error_type") == "not_found"
    finally:
        sc.stop()


def test_sidecar_stop_removes_socket(sidecar_paths):
    sc = _make_sidecar(sidecar_paths)
    sc.start(sidecar_paths["brain_path"])
    path = sc.socket_path
    assert path.exists()
    sc.stop()
    assert not path.exists()


def test_query_when_socket_missing_returns_transport_closed(tmp_path):
    missing = tmp_path / "nonexistent.sock"
    result = hs.query("/health", socket_path=missing, timeout=0.5)
    assert result["error_type"] == "transport_closed"
    assert "recovery_hint" in result


# ---------------------------------------------------------------------------
# Heartbeat staleness bound (acceptance criterion)
# ---------------------------------------------------------------------------


def test_is_heartbeat_stale_detects_missing():
    assert hs._is_heartbeat_stale({}) is True
    assert hs._is_heartbeat_stale({"last_heartbeat_at": "bogus"}) is True


def test_is_heartbeat_stale_detects_old():
    # 10 seconds old — way past 2x interval (4s)
    from datetime import datetime, timezone, timedelta
    old = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
    assert hs._is_heartbeat_stale({"last_heartbeat_at": old}) is True


def test_is_heartbeat_fresh_is_not_stale():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    assert hs._is_heartbeat_stale({"last_heartbeat_at": now}) is False


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def _success_envelope() -> str:
    return json.dumps({"ok": True, "data": {"x": 1}, "error": None, "brain_id": "b", "session_id": "s", "schema_version": "2", "warnings": []})


def _transport_closed_envelope() -> str:
    return json.dumps({"ok": False, "data": None, "error": {"error_type": "transport_closed", "recovery_hint": "restart"}, "brain_id": "b", "session_id": "s", "schema_version": "2", "warnings": []})


def _handler_error_envelope() -> str:
    return json.dumps({"ok": False, "data": None, "error": {"error_type": "handler_error", "recovery_hint": "check"}, "brain_id": "b", "session_id": "s", "schema_version": "2", "warnings": []})


def test_retry_returns_success_immediately():
    calls = []

    def fn():
        calls.append(1)
        return _success_envelope()

    result = _retry.with_retry(fn)
    assert len(calls) == 1
    assert json.loads(result)["ok"] is True


def test_retry_retries_on_transport_closed():
    calls = []

    def fn():
        calls.append(1)
        if len(calls) == 1:
            return _transport_closed_envelope()
        return _success_envelope()

    result = _retry.with_retry(fn, initial_backoff=0.001)
    assert len(calls) == 2
    assert json.loads(result)["ok"] is True


def test_retry_does_not_retry_on_handler_error():
    calls = []

    def fn():
        calls.append(1)
        return _handler_error_envelope()

    result = _retry.with_retry(fn, initial_backoff=0.001)
    assert len(calls) == 1
    assert json.loads(result)["error"]["error_type"] == "handler_error"


def test_retry_gives_up_after_max_retries():
    calls = []

    def fn():
        calls.append(1)
        return _transport_closed_envelope()

    result = _retry.with_retry(fn, max_retries=2, initial_backoff=0.001)
    assert len(calls) == 3  # 1 initial + 2 retries
    assert json.loads(result)["ok"] is False


def test_retry_on_dict_payload_not_string():
    """Retry helper should handle raw dict responses too."""
    calls = []

    def fn():
        calls.append(1)
        return {
            "ok": False,
            "error": {"error_type": "transport_closed", "recovery_hint": "x"},
        }

    result = _retry.with_retry(fn, max_retries=1, initial_backoff=0.001)
    assert len(calls) == 2
