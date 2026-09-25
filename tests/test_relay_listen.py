"""Tests for relay_listen — blocking end-of-turn wait primitive."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.relay_ops import relay_listen, _POLL_SIGNAL_FILENAME


def _write_relay(relay_dir: Path, relay_id: str, subject: str,
                 in_reply_to: str | None = None, read: bool = False,
                 context: dict | None = None) -> Path:
    relay_dir.mkdir(parents=True, exist_ok=True)
    path = relay_dir / f"{relay_id}.json"
    msg: dict = {
        "id": relay_id,
        "subject": subject,
        "from": "test_sender",
        "priority": "normal",
        "read": read,
    }
    if in_reply_to:
        msg["in_reply_to"] = in_reply_to
    if context:
        msg["context"] = context
    path.write_text(json.dumps(msg), encoding="utf-8")
    return path


@pytest.mark.timeout(120)
class TestRelayListen:
    def test_finds_new_relay_immediately(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf"
        _write_relay(relay_dir, "relay_existing_001", "Old message")
        _write_relay(relay_dir, "relay_new_002", "New task for you")

        # Pass old relay as known so only the new one surfaces — no threading race
        result = relay_listen("windsurf", window_s=5, poll_s=1,
                              known_ids=["relay_existing_001"])

        assert result["found"] is True
        assert result["relay"]["relay_id"] == "relay_new_002"
        assert result["relay"]["subject"] == "New task for you"
        assert result["waited_s"] >= 0

    def test_returns_call_again_on_timeout(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_timeout"
        relay_dir.mkdir(parents=True, exist_ok=True)

        result = relay_listen("windsurf_timeout", window_s=3, poll_s=1)

        assert result["found"] is False
        assert result["call_again"] is True
        assert "known_ids" in result
        assert "next_attempt" in result
        assert result["next_attempt"] == 2
        assert "hint" in result

    def test_known_ids_prevents_stale_relay_from_surfacing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_knownids"
        _write_relay(relay_dir, "relay_already_seen_abc", "Already processed")

        # Pass that relay as known so it won't surface
        result = relay_listen(
            "windsurf_knownids",
            window_s=3,
            poll_s=1,
            known_ids=["relay_already_seen_abc"],
        )
        assert result["found"] is False
        assert result["call_again"] is True

    def test_in_reply_to_filter_only_surfaces_matching_relay(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_filter"
        _write_relay(relay_dir, "relay_unrelated_xyz", "Unrelated task")
        _write_relay(relay_dir, "relay_reply_abc", "Re: your task",
                     in_reply_to="relay_original_task_001")

        # Pre-write both, pass unrelated as known — no threading race
        result = relay_listen(
            "windsurf_filter",
            window_s=5,
            poll_s=1,
            in_reply_to="relay_original_task_001",
            known_ids=["relay_unrelated_xyz"],
        )

        assert result["found"] is True
        assert result["relay"]["relay_id"] == "relay_reply_abc"
        assert result["relay"]["in_reply_to"] == "relay_original_task_001"

    def test_adaptive_interval_increases_with_attempt(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_adaptive"
        relay_dir.mkdir(parents=True, exist_ok=True)

        # attempt=3, poll_s=5 → effective_poll = min(5*3, 30) = 15
        # with window_s=2 it should timeout immediately (window < poll interval)
        result = relay_listen("windsurf_adaptive", window_s=2, poll_s=5, attempt=3)
        assert result["found"] is False
        assert result["next_attempt"] == 4
        # next_poll_s should be capped at 30
        assert result["next_poll_s"] <= 30

    def test_ignores_poll_signal_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_signal"
        relay_dir.mkdir(parents=True, exist_ok=True)
        # Write a POLL_SIGNAL.json — should never be returned as a relay
        (relay_dir / _POLL_SIGNAL_FILENAME).write_text(
            json.dumps({"running": True, "pending": []}), encoding="utf-8"
        )

        result = relay_listen("windsurf_signal", window_s=2, poll_s=1)
        assert result["found"] is False  # signal file not counted as relay

    def test_retry_chain_finds_relay_on_second_call(self, tmp_path, monkeypatch):
        """Simulate: first call times out, second call (with known_ids) finds relay."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_retry"
        relay_dir.mkdir(parents=True, exist_ok=True)

        # Write a pre-existing relay before first call
        _write_relay(relay_dir, "relay_preexisting_001", "Old message")

        # First call — times out, returns known_ids (which includes preexisting)
        r1 = relay_listen("windsurf_retry", window_s=2, poll_s=1, attempt=1)
        assert r1["found"] is False
        assert r1["call_again"] is True
        assert "relay_preexisting_001" in r1["known_ids"]

        # New relay arrives between calls (after first call returned)
        _write_relay(relay_dir, "relay_late_arrival_999", "Late task")

        # Second call with known_ids from first — finds only the new relay
        r2 = relay_listen(
            "windsurf_retry",
            window_s=30,
            poll_s=1,
            known_ids=r1["known_ids"],
            attempt=r1["next_attempt"],
        )
        assert r2["found"] is True
        assert r2["relay"]["relay_id"] == "relay_late_arrival_999"

    def test_returns_context_field_in_relay_summary(self, tmp_path, monkeypatch):
        """Test that relay_listen returns context field in relay summary."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_context"
        test_context = {"test": "value", "version": "1.0"}
        _write_relay(relay_dir, "relay_with_context_001", "Task with context",
                    context=test_context)

        # Pre-write + dummy known_ids to skip snapshot — no threading race
        result = relay_listen("windsurf_context", window_s=5, poll_s=1,
                              known_ids=["__dummy__"])

        assert result["found"] is True
        assert "context" in result["relay"]
        assert result["relay"]["context"] == test_context

    def test_is_convergence_true_when_context_convergence_set(self, tmp_path, monkeypatch):
        """Test that relay_listen returns is_convergence: true when context.convergence is true."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_convergence"
        convergence_context = {"convergence": True, "summary": "Plan complete"}
        _write_relay(relay_dir, "relay_convergence_001", "Done: Plan complete",
                    context=convergence_context)

        result = relay_listen("windsurf_convergence", window_s=5, poll_s=1,
                              known_ids=["__dummy__"])

        assert result["found"] is True
        assert "is_convergence" in result["relay"]
        assert result["relay"]["is_convergence"] is True

    def test_is_convergence_false_when_context_convergence_missing(self, tmp_path, monkeypatch):
        """Test that relay_listen returns is_convergence: false when context.convergence is not set."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_no_convergence"
        non_convergence_context = {"test": "value"}
        _write_relay(relay_dir, "relay_no_conv_001", "Regular task",
                    context=non_convergence_context)

        result = relay_listen("windsurf_no_convergence", window_s=5, poll_s=1,
                              known_ids=["__dummy__"])

        assert result["found"] is True
        assert "is_convergence" in result["relay"]
        assert result["relay"]["is_convergence"] is False

    def test_is_convergence_false_when_context_missing(self, tmp_path, monkeypatch):
        """Test that relay_listen returns is_convergence: false when context is entirely missing."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf_no_context"
        _write_relay(relay_dir, "relay_no_ctx_001", "Task without context")

        result = relay_listen("windsurf_no_context", window_s=5, poll_s=1,
                              known_ids=["__dummy__"])

        assert result["found"] is True
        assert "is_convergence" in result["relay"]
        assert result["relay"]["is_convergence"] is False
        assert "context" in result["relay"]
        assert result["relay"]["context"] == {}


def _http_msg(mid: str, subject: str = "s", in_reply_to: str | None = None,
              context: dict | None = None) -> dict:
    msg: dict = {"id": mid, "subject": subject, "from": "test_sender",
                 "priority": "normal"}
    if in_reply_to:
        msg["in_reply_to"] = in_reply_to
    if context is not None:
        msg["context"] = context
    return msg


_READ_INBOX = "mcp_server_nucleus.runtime.relay_transport.read_inbox"


class TestRelayListenHttpMode:
    """GAP-4: with NUCLEUS_RELAY_URL set, relay_listen must scan via
    relay_transport.read_inbox instead of globbing the local FS dir
    (which is empty/stale on an HTTP-flipped host)."""

    def test_finds_new_arrival_after_snapshot(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_URL", "http://relay.test.invalid")
        old = _http_msg("relay_old_http", "Old message")
        new = _http_msg("relay_new_http", "New task")
        # call 1 = snapshot, call 2 = first poll
        with patch(_READ_INBOX, side_effect=[[old], [old, new]]) as mock_read:
            result = relay_listen("windsurf", window_s=30, poll_s=1)

        assert result["found"] is True
        assert result["relay"]["relay_id"] == "relay_new_http"
        assert result["relay"]["subject"] == "New task"
        mock_read.assert_called_with("windsurf", unread_only=True, limit=200)

    def test_known_ids_prevents_stale_relay_from_surfacing(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_URL", "http://relay.test.invalid")
        with patch(_READ_INBOX, return_value=[_http_msg("relay_seen_http")]):
            result = relay_listen(
                "windsurf", window_s=1, poll_s=1, known_ids=["relay_seen_http"]
            )

        assert result["found"] is False
        assert result["call_again"] is True
        assert "relay_seen_http" in result["known_ids"]

    def test_in_reply_to_filter_only_surfaces_matching(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_URL", "http://relay.test.invalid")
        msgs = [
            _http_msg("relay_unrelated_http", "Unrelated"),
            _http_msg("relay_reply_http", "Re: task", in_reply_to="relay_orig_001"),
        ]
        with patch(_READ_INBOX, side_effect=[[], msgs]):
            result = relay_listen(
                "windsurf", window_s=30, poll_s=1, in_reply_to="relay_orig_001"
            )

        assert result["found"] is True
        assert result["relay"]["relay_id"] == "relay_reply_http"
        assert result["relay"]["in_reply_to"] == "relay_orig_001"

    def test_timeout_returns_snapshot_known_ids(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_URL", "http://relay.test.invalid")
        with patch(_READ_INBOX, return_value=[_http_msg("relay_preexisting_http")]):
            result = relay_listen("windsurf", window_s=1, poll_s=1)

        assert result["found"] is False
        assert result["call_again"] is True
        assert "relay_preexisting_http" in result["known_ids"]
        assert result["next_attempt"] == 2

    def test_is_convergence_from_context(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_URL", "http://relay.test.invalid")
        new = _http_msg("relay_conv_http", "Done", context={"convergence": True})
        with patch(_READ_INBOX, side_effect=[[], [new]]):
            result = relay_listen("windsurf", window_s=30, poll_s=1)

        assert result["found"] is True
        assert result["relay"]["is_convergence"] is True
        assert result["relay"]["context"] == {"convergence": True}

    def test_null_context_coerced_to_empty_dict(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_URL", "http://relay.test.invalid")
        new = dict(_http_msg("relay_null_ctx_http"), context=None)
        with patch(_READ_INBOX, side_effect=[[], [new]]):
            result = relay_listen("windsurf", window_s=30, poll_s=1)

        assert result["found"] is True
        assert result["relay"]["context"] == {}
        assert result["relay"]["is_convergence"] is False

    def test_http_mode_ignores_fs_files(self, tmp_path, monkeypatch):
        """A new relay sitting in the local FS dir must NOT surface in
        HTTP mode — the inbox of record is the relay service."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        relay_dir = tmp_path / "relay" / "windsurf"
        _write_relay(relay_dir, "relay_fs_only_001", "FS-only message")

        monkeypatch.setenv("NUCLEUS_RELAY_URL", "http://relay.test.invalid")
        with patch(_READ_INBOX, return_value=[]):
            result = relay_listen("windsurf", window_s=1, poll_s=1)

        assert result["found"] is False
        assert result["call_again"] is True

    def test_transport_error_degrades_to_timeout(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_URL", "http://relay.test.invalid")
        with patch(_READ_INBOX, side_effect=RuntimeError("transport down")):
            result = relay_listen("windsurf", window_s=1, poll_s=1)

        assert result["found"] is False
        assert result["call_again"] is True
