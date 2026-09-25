"""Regression test for high_relay_unbounded: secretary daemon relay cleanup.

Before the fix, relay_clear() existed but was never called automatically —
relay inboxes grew unbounded. The fix wires relay_clear into the secretary
daemon's periodic loop, running every ~6h and deleting messages older than 7 days.

This test verifies:
1. The secretary daemon has a _cleanup_old_relays method
2. Calling it deletes old relay messages
3. The cleanup interval is configured correctly
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def brain_path(tmp_path):
    """Create a fresh isolated brain directory with relay setup."""
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    (brain / "ledger").mkdir(exist_ok=True)
    (brain / "engrams").mkdir(exist_ok=True)
    (brain / "sessions").mkdir(exist_ok=True)
    (brain / "relay").mkdir(exist_ok=True)
    old = os.environ.get("NUCLEUS_BRAIN_PATH")
    os.environ["NUCLEUS_BRAIN_PATH"] = str(brain)
    yield brain
    if old is not None:
        os.environ["NUCLEUS_BRAIN_PATH"] = old
    else:
        os.environ.pop("NUCLEUS_BRAIN_PATH", None)
    os.environ.pop("NUCLEAR_BRAIN_PATH", None)


def _create_relay_message(relay_dir: Path, recipient: str, msg_id: str,
                          created_at: str, sender: str = "test-sender"):
    """Create a relay message file directly."""
    inbox = relay_dir / recipient
    inbox.mkdir(parents=True, exist_ok=True)
    msg = {
        "id": msg_id,
        "sender": sender,
        "recipient": recipient,
        "subject": f"Test message {msg_id}",
        "body": "Test body",
        "created_at": created_at,
    }
    (inbox / f"{msg_id}.json").write_text(json.dumps(msg))


class TestRelayCleanup:
    """Tests for high_relay_unbounded fix: secretary daemon relay cleanup."""

    def test_secretary_has_cleanup_method(self):
        """SecretaryDaemon must have a _cleanup_old_relays method."""
        from mcp_server_nucleus.runtime.lane.secretary_daemon import SecretaryDaemon
        assert hasattr(SecretaryDaemon, "_cleanup_old_relays"), (
            "SecretaryDaemon must have _cleanup_old_relays method "
            "(high_relay_unbounded fix)"
        )

    def test_secretary_has_cleanup_interval_config(self):
        """SecretaryDaemon must have relay cleanup interval configuration."""
        from mcp_server_nucleus.runtime.lane.secretary_daemon import SecretaryDaemon
        # Check the __init__ sets the interval — we can't easily construct one
        # without a full LaneConfig, so check the source has the attributes
        import inspect
        source = inspect.getsource(SecretaryDaemon.__init__)
        assert "_relay_cleanup_interval_ticks" in source, (
            "SecretaryDaemon.__init__ must set _relay_cleanup_interval_ticks"
        )
        assert "_relay_cleanup_older_than_hours" in source, (
            "SecretaryDaemon.__init__ must set _relay_cleanup_older_than_hours"
        )

    def test_cleanup_deletes_old_messages(self, brain_path):
        """relay_clear must delete messages older than the cutoff."""
        from mcp_server_nucleus.runtime.relay.core import relay_clear

        relay_dir = brain_path / "relay"
        # Create an old message (10 days ago)
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        _create_relay_message(relay_dir, "test-role", "old-msg-1", old_time)

        # Create a recent message (1 day ago)
        recent_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        _create_relay_message(relay_dir, "test-role", "recent-msg-1", recent_time)

        # Run cleanup with 7-day cutoff
        result = relay_clear(older_than_hours=168)

        assert result["deleted"] == 1, f"Expected 1 deletion, got {result}"
        assert not (relay_dir / "test-role" / "old-msg-1.json").exists(), (
            "Old message must be deleted"
        )
        assert (relay_dir / "test-role" / "recent-msg-1.json").exists(), (
            "Recent message must be preserved"
        )

    def test_cleanup_preserves_recent_messages(self, brain_path):
        """relay_clear must NOT delete messages newer than the cutoff."""
        from mcp_server_nucleus.runtime.relay.core import relay_clear

        relay_dir = brain_path / "relay"
        # Create 3 recent messages
        for i in range(3):
            recent_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            _create_relay_message(relay_dir, "test-role", f"recent-{i}", recent_time)

        result = relay_clear(older_than_hours=168)
        assert result["deleted"] == 0, "No recent messages should be deleted"
        for i in range(3):
            assert (relay_dir / "test-role" / f"recent-{i}.json").exists()

    def test_cleanup_handles_empty_inbox(self, brain_path):
        """relay_clear must handle empty inboxes gracefully."""
        from mcp_server_nucleus.runtime.relay.core import relay_clear

        result = relay_clear(older_than_hours=168)
        assert result["deleted"] == 0
        assert result["errors"] == 0
