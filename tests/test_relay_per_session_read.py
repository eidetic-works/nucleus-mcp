"""Phase A3 — per-session read state for shared relay buckets.

Isolates read-state per session_id so peer sessions sharing a recipient bucket
(e.g., two Cowork sessions, two CC-peer sessions) don't hide each other's
messages. Legacy coarse-grained `read`/`read_by` fields stay — `relay_status`,
`pending.json`, and the morning brief still mean "any-session acked".
"""

import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def brain(tmp_path, monkeypatch):
    b = tmp_path / ".brain"
    (b / "relay").mkdir(parents=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    monkeypatch.setenv("NUCLEAR_BRAIN_PATH", str(b))
    return b


def _post(recipient="cowork", subject="hi", sender="claude_code_main"):
    from mcp_server_nucleus.runtime.relay_ops import relay_post
    return relay_post(
        to=recipient,
        subject=subject,
        body="{}",
        priority="normal",
        sender=sender,
    )


class TestReadBySessionsInit:
    def test_relay_post_initializes_empty_dict(self, brain):
        result = _post()
        path = brain / result["path"]
        msg = json.loads(path.read_text())
        assert msg["read_by_sessions"] == {}
        # Legacy fields preserved for back-compat
        assert msg["read"] is False
        assert msg["read_by"] is None


class TestPerSessionIsolation:
    """Two Cowork sessions share the bucket. One acking must NOT hide the
    message from the other."""

    def test_ack_by_session_a_does_not_hide_from_session_b(self, brain):
        from mcp_server_nucleus.runtime.relay_ops import relay_inbox, relay_ack

        posted = _post()
        mid = posted["message_id"]

        # Session A sees + acks
        inbox_a = relay_inbox(recipient="cowork", session_id="sess-A")
        assert inbox_a["count"] == 1
        relay_ack(mid, recipient="cowork", session_id="sess-A")

        # Session A no longer sees it
        inbox_a_after = relay_inbox(recipient="cowork", session_id="sess-A")
        assert inbox_a_after["count"] == 0

        # Session B still sees it (THE WHOLE POINT of Phase A3)
        inbox_b = relay_inbox(recipient="cowork", session_id="sess-B")
        assert inbox_b["count"] == 1
        assert inbox_b["messages"][0]["id"] == mid

    def test_ack_writes_only_acking_session_into_dict(self, brain):
        from mcp_server_nucleus.runtime.relay_ops import relay_ack

        posted = _post()
        mid = posted["message_id"]
        relay_ack(mid, recipient="cowork", session_id="sess-A")

        path = brain / posted["path"]
        msg = json.loads(path.read_text())
        assert list(msg["read_by_sessions"].keys()) == ["sess-A"]
        assert "sess-B" not in msg["read_by_sessions"]

    def test_both_sessions_ack_populates_both_entries(self, brain):
        from mcp_server_nucleus.runtime.relay_ops import relay_ack, relay_inbox

        posted = _post()
        mid = posted["message_id"]
        relay_ack(mid, recipient="cowork", session_id="sess-A")
        relay_ack(mid, recipient="cowork", session_id="sess-B")

        path = brain / posted["path"]
        msg = json.loads(path.read_text())
        assert set(msg["read_by_sessions"].keys()) == {"sess-A", "sess-B"}

        # Neither session sees it anymore
        assert relay_inbox(recipient="cowork", session_id="sess-A")["count"] == 0
        assert relay_inbox(recipient="cowork", session_id="sess-B")["count"] == 0


class TestBackCompat:
    """Legacy callers (no session_id) keep coarse-grained semantics."""

    def test_legacy_inbox_honors_read_flag(self, brain):
        from mcp_server_nucleus.runtime.relay_ops import relay_inbox, relay_ack

        posted = _post()
        mid = posted["message_id"]

        # Legacy call returns the message
        assert relay_inbox(recipient="cowork")["count"] == 1

        # Any ack (with or without session_id) flips legacy `read=True`
        relay_ack(mid, recipient="cowork", session_id="sess-A")

        # Legacy consumer (no session_id) no longer sees it
        assert relay_inbox(recipient="cowork")["count"] == 0

    def test_legacy_messages_without_field_treated_as_unread_for_everyone(self, brain):
        """A message posted before this patch lands has no read_by_sessions
        field. With per-session filter on, it must appear (no session has acked
        it)."""
        from mcp_server_nucleus.runtime.relay_ops import relay_inbox

        # Simulate pre-Phase-A3 file: no read_by_sessions field
        bucket = brain / "relay" / "cowork"
        bucket.mkdir(parents=True, exist_ok=True)
        legacy_msg = {
            "id": "relay_legacy_001",
            "from": "claude_code_main",
            "to": "cowork",
            "subject": "pre-A3",
            "body": "{}",
            "priority": "normal",
            "created_at": "2026-04-18T00:00:00Z",
            "read": False,
            "read_at": None,
            "read_by": None,
        }
        (bucket / "20260418_000000_relay_legacy_001.json").write_text(
            json.dumps(legacy_msg, indent=2)
        )

        # Per-session filter surfaces it for any session
        assert relay_inbox(recipient="cowork", session_id="sess-A")["count"] == 1
        assert relay_inbox(recipient="cowork", session_id="sess-Z")["count"] == 1


class TestAckMetadata:
    def test_ack_return_includes_session_id(self, brain):
        from mcp_server_nucleus.runtime.relay_ops import relay_ack

        posted = _post()
        result = relay_ack(posted["message_id"], recipient="cowork", session_id="sess-A")
        assert result["acknowledged"] is True
        assert result["session_id"] == "sess-A"
