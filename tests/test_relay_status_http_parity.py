"""core.relay_status HTTP fan-out — v0.2 Seq-2 relay_status parity.

Per spec §"Swap points" table: "http_mode: call GET /relay/{role}/status
per known role". Known roles = deduped CANONICAL_ROLE_TO_INBOX_DIR values,
so HTTP-mode status covers the exact same roles FS-mode would scan.

Covered here:
- fan-out hits every known canonical role exactly once, FS-compatible shape
- connection-level failure bails after ONE call (dead server ≠ one timeout
  per known role)
- per-role HTTP errors counted in status_errors, iteration continues
- force_fs=True self-recursion guard never reaches relay_transport
- FS-mode regression: URL unset → real FS scan, no "transport" key

relay_status's swap-point does a call-time function-body import from
relay_transport, so patching the relay_transport module attribute is
binding-faithful (same tripwire doctrine as test_relay_ops_truth_signaling).
"""
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime.relay_inbox_canonical import (
    CANONICAL_ROLE_TO_INBOX_DIR,
)
from mcp_server_nucleus.runtime.relay_ops import relay_status

_GET_STATUS = "mcp_server_nucleus.runtime.relay_transport.get_status"

EXPECTED_ROLES = sorted(set(CANONICAL_ROLE_TO_INBOX_DIR.values()))


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Host shells in this fleet export NUCLEUS_RELAY_URL/BEARER — scrub so
    each test opts in explicitly."""
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)


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


def _boom(*args, **kwargs):
    raise AssertionError("relay_status escaped to relay_transport.get_status")


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


# ── HTTP fan-out ─────────────────────────────────────────────────────────


def test_http_fan_out_covers_every_known_role(http_env):
    calls = []

    def _fake_get_status(role, **kwargs):
        calls.append(role)
        return {"ok": True, "role": role, "queue_depth": 2, "unread": 1}

    with patch(_GET_STATUS, side_effect=_fake_get_status):
        status = relay_status()

    assert calls == EXPECTED_ROLES
    assert status["transport"] == "http"
    assert sorted(status["mailboxes"]) == EXPECTED_ROLES
    for canonical in EXPECTED_ROLES:
        assert status["mailboxes"][canonical] == {
            "total": 2,
            "unread": 1,
            "latest_message_at": None,
        }
    assert status["total_messages"] == 2 * len(EXPECTED_ROLES)
    assert status["total_unread"] == len(EXPECTED_ROLES)
    assert "status_errors" not in status
    assert "transport_error" not in status


def test_dead_server_bails_fanout_after_one_call(http_env):
    calls = []

    def _dead_server(role, **kwargs):
        calls.append(role)
        return {"ok": False, "error": "transport_failure"}

    with patch(_GET_STATUS, side_effect=_dead_server):
        status = relay_status()

    assert len(calls) == 1, "dead server must cost ONE timeout, not one per role"
    assert status["transport_error"] is True
    assert status["mailboxes"] == {}
    assert status["total_messages"] == 0


def test_per_role_http_error_counts_and_continues(http_env):
    failing_role = EXPECTED_ROLES[0]

    def _one_bad_role(role, **kwargs):
        if role == failing_role:
            return {"ok": False, "error": 404}
        return {"ok": True, "queue_depth": 1, "unread": 0}

    with patch(_GET_STATUS, side_effect=_one_bad_role):
        status = relay_status()

    assert status["status_errors"] == 1
    assert failing_role not in status["mailboxes"]
    assert sorted(status["mailboxes"]) == EXPECTED_ROLES[1:]
    assert status["total_messages"] == len(EXPECTED_ROLES) - 1
    assert "transport_error" not in status


# ── force_fs self-recursion guard + FS regression ────────────────────────


def test_force_fs_never_reaches_transport(brain, http_env):
    _write_envelope(brain, "cowork", 1)
    with patch(_GET_STATUS, side_effect=_boom):
        status = relay_status(force_fs=True)
    assert "transport" not in status, "FS path must not report transport=http"
    assert status["mailboxes"]["cowork"]["total"] == 1
    assert status["mailboxes"]["cowork"]["latest_message_at"] is not None


def test_fs_mode_regression_when_url_unset(brain):
    _write_envelope(brain, "cowork", 2)
    _write_envelope(brain, "cowork", 3, read=True)
    with patch(_GET_STATUS, side_effect=_boom):
        status = relay_status()
    assert "transport" not in status
    assert status["mailboxes"]["cowork"]["total"] == 2
    assert status["mailboxes"]["cowork"]["unread"] == 1
    assert status["total_messages"] == 2
    assert status["total_unread"] == 1
