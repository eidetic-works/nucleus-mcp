"""Tests for relay_listen — blocking end-of-turn wait primitive."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

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


class TestRelayListen:
    def test_finds_new_relay_immediately(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
        relay_dir = tmp_path / "relay" / "windsurf"
        _write_relay(relay_dir, "relay_existing_001", "Old message")

        # Write new relay in a thread after 1s
        def _post():
            time.sleep(1)
            _write_relay(relay_dir, "relay_new_002", "New task for you")

        threading.Thread(target=_post, daemon=True).start()
        result = relay_listen("windsurf", window_s=10, poll_s=1)

        assert result["found"] is True
        assert result["relay"]["relay_id"] == "relay_new_002"
        assert result["relay"]["subject"] == "New task for you"
        assert result["waited_s"] >= 0

    def test_returns_call_again_on_timeout(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
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
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
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
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
        relay_dir = tmp_path / "relay" / "windsurf_filter"
        _write_relay(relay_dir, "relay_unrelated_xyz", "Unrelated task")

        # Write the matching reply after 1s
        def _post():
            time.sleep(1)
            _write_relay(relay_dir, "relay_reply_abc", "Re: your task",
                         in_reply_to="relay_original_task_001")

        threading.Thread(target=_post, daemon=True).start()
        result = relay_listen(
            "windsurf_filter",
            window_s=10,
            poll_s=1,
            in_reply_to="relay_original_task_001",
        )

        assert result["found"] is True
        assert result["relay"]["relay_id"] == "relay_reply_abc"
        assert result["relay"]["in_reply_to"] == "relay_original_task_001"

    def test_adaptive_interval_increases_with_attempt(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
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
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
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
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
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
            window_s=10,
            poll_s=1,
            known_ids=r1["known_ids"],
            attempt=r1["next_attempt"],
        )
        assert r2["found"] is True
        assert r2["relay"]["relay_id"] == "relay_late_arrival_999"

    def test_returns_context_field_in_relay_summary(self, tmp_path, monkeypatch):
        """Test that relay_listen returns context field in relay summary."""
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
        relay_dir = tmp_path / "relay" / "windsurf_context"
        test_context = {"test": "value", "version": "1.0"}

        def _post():
            time.sleep(1)
            _write_relay(relay_dir, "relay_with_context_001", "Task with context",
                        context=test_context)

        threading.Thread(target=_post, daemon=True).start()
        result = relay_listen("windsurf_context", window_s=10, poll_s=1)

        assert result["found"] is True
        assert "context" in result["relay"]
        assert result["relay"]["context"] == test_context

    def test_is_convergence_true_when_context_convergence_set(self, tmp_path, monkeypatch):
        """Test that relay_listen returns is_convergence: true when context.convergence is true."""
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
        relay_dir = tmp_path / "relay" / "windsurf_convergence"
        convergence_context = {"convergence": True, "summary": "Plan complete"}

        def _post():
            time.sleep(1)
            _write_relay(relay_dir, "relay_convergence_001", "Done: Plan complete",
                        context=convergence_context)

        threading.Thread(target=_post, daemon=True).start()
        result = relay_listen("windsurf_convergence", window_s=10, poll_s=1)

        assert result["found"] is True
        assert "is_convergence" in result["relay"]
        assert result["relay"]["is_convergence"] is True

    def test_is_convergence_false_when_context_convergence_missing(self, tmp_path, monkeypatch):
        """Test that relay_listen returns is_convergence: false when context.convergence is not set."""
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
        relay_dir = tmp_path / "relay" / "windsurf_no_convergence"
        non_convergence_context = {"test": "value"}

        def _post():
            time.sleep(1)
            _write_relay(relay_dir, "relay_no_conv_001", "Regular task",
                        context=non_convergence_context)

        threading.Thread(target=_post, daemon=True).start()
        result = relay_listen("windsurf_no_convergence", window_s=10, poll_s=1)

        assert result["found"] is True
        assert "is_convergence" in result["relay"]
        assert result["relay"]["is_convergence"] is False

    def test_is_convergence_false_when_context_missing(self, tmp_path, monkeypatch):
        """Test that relay_listen returns is_convergence: false when context is entirely missing."""
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.relay_ops.get_brain_path", lambda: tmp_path
        )
        relay_dir = tmp_path / "relay" / "windsurf_no_context"

        def _post():
            time.sleep(1)
            _write_relay(relay_dir, "relay_no_ctx_001", "Task without context")

        threading.Thread(target=_post, daemon=True).start()
        result = relay_listen("windsurf_no_context", window_s=10, poll_s=1)

        assert result["found"] is True
        assert "is_convergence" in result["relay"]
        assert result["relay"]["is_convergence"] is False
        assert "context" in result["relay"]
        assert result["relay"]["context"] == {}
