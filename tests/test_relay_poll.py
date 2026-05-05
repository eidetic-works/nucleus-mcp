"""Tests for relay_poll_start / relay_poll_stop / relay_poll_status."""
from __future__ import annotations

import json
import time
import threading
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.relay_ops import (
    relay_poll_start,
    relay_poll_stop,
    relay_poll_status,
    _poll_daemons,
    _poll_daemons_lock,
    _POLL_SIGNAL_FILENAME,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _clean_daemons(recipient: str):
    """Stop and remove any daemon for recipient (test teardown)."""
    relay_poll_stop(recipient)
    with _poll_daemons_lock:
        _poll_daemons.pop(recipient, None)


def _write_relay(relay_dir: Path, relay_id: str, subject: str, read: bool = False) -> Path:
    relay_dir.mkdir(parents=True, exist_ok=True)
    path = relay_dir / f"{relay_id}.json"
    path.write_text(json.dumps({
        "id": relay_id,
        "subject": subject,
        "from": "test_sender",
        "priority": "normal",
        "read": read,
    }), encoding="utf-8")
    return path


# ── tests ─────────────────────────────────────────────────────────────────────

class TestRelayPollStart:
    def test_starts_daemon_and_returns_started(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path",
            lambda: tmp_path,
        )
        recipient = "windsurf_poll_test_start"
        try:
            result = relay_poll_start(recipient, interval_s=2)
            assert result["status"] == "started"
            assert result["recipient"] == recipient
            assert result["interval_s"] == 2
            with _poll_daemons_lock:
                assert recipient in _poll_daemons
                assert _poll_daemons[recipient]._thread.is_alive()
        finally:
            _clean_daemons(recipient)

    def test_idempotent_when_already_running(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path",
            lambda: tmp_path,
        )
        recipient = "windsurf_poll_test_idem"
        try:
            relay_poll_start(recipient, interval_s=2)
            result2 = relay_poll_start(recipient, interval_s=5)
            assert result2["status"] == "already_running"
            assert result2["interval_s"] == 2  # original interval unchanged
        finally:
            _clean_daemons(recipient)


class TestRelayPollStop:
    def test_stops_running_daemon(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path",
            lambda: tmp_path,
        )
        recipient = "windsurf_poll_test_stop"
        relay_poll_start(recipient, interval_s=2)
        result = relay_poll_stop(recipient)
        assert result["status"] == "stopped"
        with _poll_daemons_lock:
            assert recipient not in _poll_daemons

    def test_stop_when_not_running(self):
        result = relay_poll_stop("nonexistent_bucket_xyz")
        assert result["status"] == "not_running"


class TestRelayPollStatus:
    def test_status_before_start_returns_not_running(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path",
            lambda: tmp_path,
        )
        result = relay_poll_status("windsurf_never_started")
        assert result["running"] is False
        assert result["pending"] == []
        assert "hint" in result

    def test_status_after_start_shows_running(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path",
            lambda: tmp_path,
        )
        recipient = "windsurf_poll_test_status"
        try:
            relay_poll_start(recipient, interval_s=1)
            time.sleep(1.5)  # allow at least one scan cycle
            result = relay_poll_status(recipient)
            assert result["running"] is True
            assert "checked_at" in result
            assert isinstance(result["pending"], list)
        finally:
            _clean_daemons(recipient)

    def test_status_surfaces_unread_relay(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path",
            lambda: tmp_path,
        )
        recipient = "windsurf_poll_test_surface"
        relay_dir = tmp_path / "relay" / recipient
        _write_relay(relay_dir, "relay_20260504_test_abc123", "Task: do something")

        try:
            relay_poll_start(recipient, interval_s=1)
            time.sleep(1.5)  # allow daemon to scan
            result = relay_poll_status(recipient)
            assert result["pending_count"] >= 1
            relay_ids = [m["relay_id"] for m in result["pending"]]
            assert "relay_20260504_test_abc123" in relay_ids
        finally:
            _clean_daemons(recipient)

    def test_status_excludes_read_relay(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path",
            lambda: tmp_path,
        )
        recipient = "windsurf_poll_test_read"
        relay_dir = tmp_path / "relay" / recipient
        _write_relay(relay_dir, "relay_already_read_xyz", "Old task", read=True)

        try:
            relay_poll_start(recipient, interval_s=1)
            time.sleep(1.5)
            result = relay_poll_status(recipient)
            relay_ids = [m["relay_id"] for m in result["pending"]]
            assert "relay_already_read_xyz" not in relay_ids
        finally:
            _clean_daemons(recipient)

    def test_signal_file_written_to_disk(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path",
            lambda: tmp_path,
        )
        recipient = "windsurf_poll_test_signal"
        try:
            relay_poll_start(recipient, interval_s=1)
            time.sleep(1.5)
            signal_path = tmp_path / "relay" / recipient / _POLL_SIGNAL_FILENAME
            assert signal_path.exists(), "POLL_SIGNAL.json should be written by daemon"
            data = json.loads(signal_path.read_text())
            assert data["running"] is True
            assert "checked_at" in data
        finally:
            _clean_daemons(recipient)
