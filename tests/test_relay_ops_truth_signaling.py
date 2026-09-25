"""relay_ops-level truth-in-signaling + force_fs guard — v0.2 read_inbox
bundle, items (a) and (c) at the relay_ops boundary.

Item (a): force_fs=True must bypass the HTTP swap-point in relay_post /
relay_inbox / relay_ack / relay_status (server-side self-recursion guard).
Tripwire: relay_transport functions are patched to raise.

Item (c): the HTTP-mode dicts returned by relay_inbox /
relay_context_sync now surface has_more / rate_limited / transport_error
so a rate-limited or failed read is distinguishable from a truly empty
inbox at every caller.
"""
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.relay_ops import (
    relay_ack,
    relay_context_sync,
    relay_inbox,
    relay_post,
    relay_status,
)
from mcp_server_nucleus.runtime.relay_transport import InboxResult

_READ_INBOX = "mcp_server_nucleus.runtime.relay_transport.read_inbox"
_POST_RELAY = "mcp_server_nucleus.runtime.relay_transport.post_relay"
_MARK_SEEN = "mcp_server_nucleus.runtime.relay_transport.mark_seen"


def _boom(*args, **kwargs):
    raise AssertionError("force_fs must not reach relay_transport")


@pytest.fixture
def brain(tmp_path, monkeypatch):
    b = tmp_path / "brain"
    b.mkdir()
    (b / "relay").mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    return b


@pytest.fixture
def http_env(monkeypatch):
    monkeypatch.setenv("NUCLEUS_RELAY_URL", "https://relay.example.com")
    monkeypatch.setenv("NUCLEUS_RELAY_BEARER", "test-bearer")


def _write_envelope(brain, recipient, n, read=False):
    inbox = brain / "relay" / recipient
    inbox.mkdir(parents=True, exist_ok=True)
    msg_id = f"relay_20260610_{n:06d}_{n:08x}"
    envelope = {
        "id": msg_id,
        "from": "test_sender",
        "to": recipient,
        "subject": f"msg {n}",
        "body": f"body {n}",
        "priority": "normal",
        "read": read,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    (inbox / f"20260610_{n:06d}_{msg_id}.json").write_text(
        json.dumps(envelope), encoding="utf-8"
    )
    return msg_id


# ── force_fs bypasses the HTTP swap-point (item a) ───────────────────────


def test_relay_inbox_force_fs_bypasses_http(brain, http_env):
    _write_envelope(brain, "cowork", 1)
    with patch(_READ_INBOX, side_effect=_boom):
        res = relay_inbox(recipient="cowork", force_fs=True)
    assert res["count"] == 1
    assert "transport" not in res, "FS path must not report transport=http"


def test_relay_post_force_fs_writes_fs(brain, http_env):
    with patch(_POST_RELAY, side_effect=_boom):
        res = relay_post(
            to="cowork",
            subject="s",
            body="b",
            sender="test_sender",
            force_fs=True,
        )
    files = list((brain / "relay" / "cowork").glob("*.json"))
    assert len(files) == 1
    assert res.get("id") or res.get("message_id")


def test_relay_ack_force_fs_acks_fs(brain, http_env):
    msg_id = _write_envelope(brain, "cowork", 2)
    with patch(_MARK_SEEN, side_effect=_boom):
        res = relay_ack(msg_id, recipient="cowork", force_fs=True)
    assert res["acknowledged"] is True


def test_relay_status_force_fs_returns_real_mailboxes(brain, http_env):
    _write_envelope(brain, "cowork", 3)
    res = relay_status(force_fs=True)
    assert res["mailboxes"]["cowork"]["total"] == 1
    # Sanity: without force_fs the v0.2 HTTP fan-out runs instead (get_status
    # patched so no real network); a dead server reports transport_error.
    with patch(
        "mcp_server_nucleus.runtime.relay_transport.get_status",
        return_value={"ok": False, "error": "transport_failure"},
    ):
        stub = relay_status()
    assert stub["mailboxes"] == {}
    assert stub["transport"] == "http"
    assert stub["transport_error"] is True


def test_relay_inbox_default_still_uses_http_swap(brain, http_env):
    """Regression guard: force_fs defaults False — plain clients with
    NUCLEUS_RELAY_URL set keep routing through relay_transport."""
    with patch(_READ_INBOX, return_value=InboxResult()) as mock_read:
        res = relay_inbox(recipient="cowork", limit=7)
    mock_read.assert_called_once_with("cowork", unread_only=True, limit=7)
    assert res["transport"] == "http"


# ── truth-in-signaling flags surfaced at relay_ops (item c) ──────────────


def test_relay_inbox_http_surfaces_flags(brain, http_env):
    inbox = InboxResult(
        [{"id": "m1"}], has_more=True, rate_limited=True, transport_error=False
    )
    with patch(_READ_INBOX, return_value=inbox):
        res = relay_inbox(recipient="cowork")
    assert res["count"] == 1
    assert res["has_more"] is True
    assert res["rate_limited"] is True
    assert res["transport_error"] is False


def test_relay_inbox_http_clean_flags_on_truly_empty(brain, http_env):
    with patch(_READ_INBOX, return_value=InboxResult()):
        res = relay_inbox(recipient="cowork")
    assert res["count"] == 0
    assert res["has_more"] is False
    assert res["rate_limited"] is False
    assert res["transport_error"] is False


def test_relay_inbox_http_transport_error_distinguishable_from_empty(brain, http_env):
    """The headline bug: rate-limited / failed reads used to come back as
    {"messages": [], "count": 0} — identical to an empty inbox."""
    failed = InboxResult(rate_limited=True, transport_error=True)
    with patch(_READ_INBOX, return_value=failed):
        res = relay_inbox(recipient="cowork")
    assert res["count"] == 0
    assert res["rate_limited"] is True
    assert res["transport_error"] is True


def test_relay_context_sync_http_surfaces_has_more(brain, http_env):
    inbox = InboxResult([{"id": "m1"}, {"id": "m2"}], has_more=True)
    with patch(_READ_INBOX, return_value=inbox) as mock_read:
        res = relay_context_sync(recipient="cowork")
    mock_read.assert_called_once_with("cowork", unread_only=False, limit=200)
    assert res["recent_history"] == [{"id": "m1"}, {"id": "m2"}]
    assert res["has_more"] is True
    assert res["transport_error"] is False
