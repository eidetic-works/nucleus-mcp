"""Coverage tests for mcp_server_nucleus.runtime.relay.pending."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.runtime.relay import pending as pending_mod


def test_is_shipped_artifact_relay_id():
    assert pending_mod._is_shipped_artifact("relay_20260601_120000_abc12345") is False


def test_is_shipped_artifact_normal():
    assert pending_mod._is_shipped_artifact("src/main.py") is True


def test_relay_consolidate_pending_http_mode(monkeypatch):
    """In HTTP mode, returns a stub response without touching FS."""
    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=True):
        result = pending_mod.relay_consolidate_pending()
    assert result["total_unread"] == 0
    assert result["transport"] == "http"
    assert result["mailboxes"] == {}


def test_relay_consolidate_pending_empty(monkeypatch, tmp_path):
    """FS mode with no messages returns empty pending."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    relay_dir.mkdir(parents=True)

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            result = pending_mod.relay_consolidate_pending()
    assert result["total_unread"] == 0
    assert result["mailboxes"] == {}
    assert (relay_dir / "pending.json").exists()


def test_relay_consolidate_pending_with_messages(monkeypatch, tmp_path):
    """FS mode with unread messages populates pending."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    inbox = relay_dir / "claude_code"
    inbox.mkdir(parents=True)

    # Create unread message
    msg = {
        "id": "relay_001",
        "from": "cowork",
        "subject": "test subject",
        "body": "hello",
        "priority": "high",
        "read": False,
        "created_at": "2026-01-01T00:00:00Z",
    }
    (inbox / "msg1.json").write_text(json.dumps(msg))

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            with mock.patch("mcp_server_nucleus.runtime.relay.paths._parse_relay_message", return_value=msg):
                result = pending_mod.relay_consolidate_pending()
    assert result["total_unread"] == 1
    assert "claude_code" in result["mailboxes"]
    assert len(result["urgent"]) == 1


def test_relay_consolidate_pending_read_messages_skipped(monkeypatch, tmp_path):
    """Read messages are not included in pending."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    inbox = relay_dir / "claude_code"
    inbox.mkdir(parents=True)

    msg = {"id": "r1", "read": True, "subject": "s", "from": "f", "priority": "normal"}
    (inbox / "msg1.json").write_text(json.dumps(msg))

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            with mock.patch("mcp_server_nucleus.runtime.relay.paths._parse_relay_message", return_value=msg):
                result = pending_mod.relay_consolidate_pending()
    assert result["total_unread"] == 0


def test_relay_consolidate_pending_skips_non_dirs(monkeypatch, tmp_path):
    """Non-directory entries in relay root are skipped."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    relay_dir.mkdir(parents=True)
    (relay_dir / "file.txt").write_text("not a dir")

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            result = pending_mod.relay_consolidate_pending()
    assert result["total_unread"] == 0


def test_relay_consolidate_pending_parse_exception(monkeypatch, tmp_path):
    """Parse exceptions are swallowed (continue)."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    inbox = relay_dir / "claude_code"
    inbox.mkdir(parents=True)
    (inbox / "bad.json").write_text("not json")

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            with mock.patch("mcp_server_nucleus.runtime.relay.paths._parse_relay_message", side_effect=Exception("parse fail")):
                result = pending_mod.relay_consolidate_pending()
    assert result["total_unread"] == 0


def test_relay_consolidate_pending_write_failure(monkeypatch, tmp_path):
    """Write failure is logged but doesn't raise."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    relay_dir.mkdir(parents=True)

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            with mock.patch("os.replace", side_effect=OSError("write fail")):
                result = pending_mod.relay_consolidate_pending()
    # Should still return the pending dict
    assert "total_unread" in result


def test_relay_read_pending_fresh(monkeypatch, tmp_path):
    """relay_read_pending consolidates when no pending.json exists."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    relay_dir.mkdir(parents=True)

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            result = pending_mod.relay_read_pending()
    assert "total_unread" in result


def test_relay_read_pending_fresh_file(monkeypatch, tmp_path):
    """relay_read_pending returns existing fresh pending.json."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    relay_dir.mkdir(parents=True)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data = {"updated_at": now, "total_unread": 5, "mailboxes": {}, "urgent": []}
    (relay_dir / "pending.json").write_text(json.dumps(data))

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            result = pending_mod.relay_read_pending()
    assert result["total_unread"] == 5


def test_relay_read_pending_stale_refreshes(monkeypatch, tmp_path):
    """relay_read_pending refreshes when pending.json is stale (>60s)."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    relay_dir.mkdir(parents=True)

    old_time = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat().replace("+00:00", "Z")
    data = {"updated_at": old_time, "total_unread": 99, "mailboxes": {}, "urgent": []}
    (relay_dir / "pending.json").write_text(json.dumps(data))

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            result = pending_mod.relay_read_pending()
    # Should have refreshed (total_unread should be 0, not 99)
    assert result["total_unread"] == 0


def test_relay_read_pending_corrupt_file(monkeypatch, tmp_path):
    """relay_read_pending handles corrupt pending.json by refreshing."""
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    relay_dir = tmp_path / "relay"
    relay_dir.mkdir(parents=True)
    (relay_dir / "pending.json").write_text("not valid json{{{")

    with mock.patch("mcp_server_nucleus.runtime.relay_transport.is_http_mode", return_value=False):
        with mock.patch("mcp_server_nucleus.runtime.relay.paths._get_relay_dir", return_value=relay_dir):
            result = pending_mod.relay_read_pending()
    assert "total_unread" in result
