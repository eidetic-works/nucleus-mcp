"""Tests for relay_wait and gemini_cli bucket registration."""
import json
import time
import pytest
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

def _write_relay(relay_dir: Path, relay_id: str, in_reply_to: str, sender: str = "windsurf") -> Path:
    relay_dir.mkdir(parents=True, exist_ok=True)
    msg = {
        "id": relay_id,
        "from": sender,
        "to": "windsurf",
        "in_reply_to": in_reply_to,
        "subject": f"Re: test reply {relay_id}",
        "body": "test reply body",
        "priority": "normal",
        "read": False,
        "created_at": "2026-05-04T00:00:00Z",
    }
    fpath = relay_dir / f"{relay_id}.json"
    fpath.write_text(json.dumps(msg, indent=2), encoding="utf-8")
    return fpath


# ── tests ─────────────────────────────────────────────────────────────────────

class TestRelayWait:
    def test_found_immediately(self, tmp_path, monkeypatch):
        """relay_wait returns found=True when reply already exists."""
        from mcp_server_nucleus.runtime import relay_ops

        relay_dir = tmp_path / "relay" / "windsurf"
        monkeypatch.setattr(relay_ops, "_get_relay_dir", lambda recipient=None: relay_dir)

        original_id = "relay_original_001"
        reply_id = "relay_reply_001"
        _write_relay(relay_dir, reply_id, in_reply_to=original_id)

        result = relay_ops.relay_wait(
            in_reply_to=original_id,
            recipient="windsurf",
            timeout_s=5,
            poll_interval_s=1,
        )

        assert result["found"] is True
        assert result["relay_id"] == reply_id
        assert result["subject"] == f"Re: test reply {reply_id}"
        assert result["waited_s"] == 0

    def test_timeout_when_no_reply(self, tmp_path, monkeypatch):
        """relay_wait returns timed_out=True when no reply arrives within timeout."""
        from mcp_server_nucleus.runtime import relay_ops

        relay_dir = tmp_path / "relay" / "windsurf"
        relay_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(relay_ops, "_get_relay_dir", lambda recipient=None: relay_dir)

        start = time.monotonic()
        result = relay_ops.relay_wait(
            in_reply_to="relay_nonexistent_999",
            recipient="windsurf",
            timeout_s=2,
            poll_interval_s=1,
        )
        elapsed = time.monotonic() - start

        assert result["found"] is False
        assert result["timed_out"] is True
        assert elapsed >= 2.0

    def test_reply_arrives_after_delay(self, tmp_path, monkeypatch):
        """relay_wait picks up a reply written after polling starts."""
        import threading
        from mcp_server_nucleus.runtime import relay_ops

        relay_dir = tmp_path / "relay" / "windsurf"
        relay_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(relay_ops, "_get_relay_dir", lambda recipient=None: relay_dir)

        original_id = "relay_original_delayed"
        reply_id = "relay_reply_delayed"

        def _write_after_delay():
            time.sleep(1.5)
            _write_relay(relay_dir, reply_id, in_reply_to=original_id)

        t = threading.Thread(target=_write_after_delay, daemon=True)
        t.start()

        result = relay_ops.relay_wait(
            in_reply_to=original_id,
            recipient="windsurf",
            timeout_s=10,
            poll_interval_s=1,
        )

        assert result["found"] is True
        assert result["relay_id"] == reply_id


class TestGeminiCliBucket:
    def test_gemini_cli_in_known_session_types(self):
        """gemini_cli must be a registered bucket in KNOWN_SESSION_TYPES."""
        from mcp_server_nucleus.runtime.relay_ops import KNOWN_SESSION_TYPES
        assert "gemini_cli" in KNOWN_SESSION_TYPES

    def test_gemini_cli_detected_via_env(self, monkeypatch):
        """GEMINI_CLI env var causes detect_session_type to return gemini_cli."""
        import os
        from mcp_server_nucleus.runtime import relay_ops

        monkeypatch.setenv("GEMINI_CLI", "1")
        monkeypatch.delenv("NUCLEUS_SESSION_TYPE", raising=False)
        monkeypatch.delenv("WINDSURF_SESSION", raising=False)
        monkeypatch.delenv("CURSOR_SESSION", raising=False)
        monkeypatch.delenv("ANTIGRAVITY_SESSION", raising=False)
        monkeypatch.delenv("CLAUDE_DESKTOP", raising=False)
        monkeypatch.delenv("VSCODE_PID", raising=False)
        monkeypatch.delenv("NUCLEUS_RELAY_INFER_SENDER", raising=False)

        detected = relay_ops._detect_session_type_raw()
        assert detected == "gemini_cli"
