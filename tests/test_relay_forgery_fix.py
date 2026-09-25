"""Regression test for high_relay_forgery: HMAC sender authentication.

Before the fix, FS-mode relay had no sender validation — any process could
write a JSON file to the relay inbox claiming to be any sender. The fix signs
each message with an HMAC using the sender's relay token
(~/.tb/relay_token_<role>). On read, the signature is validated; invalid
signatures are flagged with sender_hmac_valid=False.

This test verifies:
1. Messages are signed on post when a token exists
2. Forged messages (wrong signature) are flagged on read
3. Legacy messages (no signature) are accepted (backward compat)
4. Messages without a token file are accepted (graceful degradation)
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    """Create a fresh isolated brain directory with relay setup.

    Forces FS mode (unsets NUCLEUS_RELAY_URL so relay_post writes to disk,
    not HTTP transport).
    """
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    (brain / "ledger").mkdir(exist_ok=True)
    (brain / "engrams").mkdir(exist_ok=True)
    (brain / "sessions").mkdir(exist_ok=True)
    (brain / "relay").mkdir(exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    # Force FS mode — unset HTTP transport env vars
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)
    yield brain


@pytest.fixture
def fake_token_dir(tmp_path, monkeypatch):
    """Create a fake ~/.tb directory with relay tokens for test senders.

    Token files use canonical names (underscores, not hyphens) because
    relay_post canonicalizes the sender before signing.
    """
    # Create .tb directory inside tmp_path (which will be patched as home)
    tb_dir = tmp_path / ".tb"
    tb_dir.mkdir(exist_ok=True)
    # Token files use canonical (underscore) names — relay_post canonicalizes
    # "test-sender" → "test_sender" before calling _sign_relay_message
    (tb_dir / "relay_token_test_sender").write_text("secret-token-for-test-sender")
    (tb_dir / "relay_token_coordinator").write_text("secret-token-for-coordinator")
    # Patch Path.home() so _get_relay_token_for_sender finds our fake tokens
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tb_dir


class TestRelayForgeryFix:
    """Tests for high_relay_forgery fix: HMAC sender authentication."""

    def test_message_is_signed_on_post(self, brain_path, fake_token_dir):
        """When a sender has a relay token, the message must be signed."""
        from mcp_server_nucleus.runtime.relay.core import relay_post, relay_inbox

        relay_post(
            to="test-recipient",
            subject="Signed message",
            body="Test body",
            sender="test-sender",
        )

        # Canonical recipient name (hyphens → underscores)
        result = relay_inbox(recipient="test_recipient", unread_only=False)
        assert result["count"] == 1
        msg = result["messages"][0]
        assert "sender_hmac" in msg, "Message must be signed when token exists"
        assert msg["sender_hmac"] is not None
        assert msg["sender_hmac_valid"] is True, "Valid signature must pass verification"

    def test_forged_message_is_flagged(self, brain_path, fake_token_dir):
        """A message with a tampered signature must be flagged as invalid."""
        from mcp_server_nucleus.runtime.relay.core import (
            relay_post, relay_inbox, _get_relay_dir,
        )

        relay_post(
            to="test-recipient",
            subject="Original subject",
            body="Test body",
            sender="test-sender",
        )

        # Tamper with the message: change the subject but keep the old signature
        relay_dir = _get_relay_dir("test_recipient")
        msg_files = list(relay_dir.glob("*.json"))
        assert len(msg_files) == 1
        msg = json.loads(msg_files[0].read_text())
        original_sig = msg["sender_hmac"]
        msg["subject"] = "TAMPERED SUBJECT"
        msg["sender_hmac"] = original_sig  # Keep old signature (now invalid)
        msg_files[0].write_text(json.dumps(msg, indent=2))

        result = relay_inbox(recipient="test_recipient", unread_only=False)
        msg_read = result["messages"][0]
        assert msg_read["sender_hmac_valid"] is False, (
            "Tampered message must be flagged as invalid"
        )

    def test_legacy_message_without_signature_accepted(self, brain_path, fake_token_dir):
        """Messages without sender_hmac (legacy/pre-fix) must be accepted."""
        from mcp_server_nucleus.runtime.relay.core import relay_inbox, _get_relay_dir

        # Write a legacy message directly (no sender_hmac field)
        relay_dir = _get_relay_dir("test_recipient")
        relay_dir.mkdir(parents=True, exist_ok=True)
        legacy_msg = {
            "id": "relay_20260101_000000_legacy001",
            "from": "test-sender",
            "to": "test-recipient",
            "subject": "Legacy message",
            "body": "Old message without signature",
            "created_at": "2026-01-01T00:00:00Z",
            "read": False,
            "read_at": None,
            "read_by": None,
            "read_by_sessions": {},
        }
        msg_path = relay_dir / "20260101_000000_relay_20260101_000000_legacy001.json"
        msg_path.write_text(json.dumps(legacy_msg, indent=2))

        result = relay_inbox(recipient="test_recipient", unread_only=False)
        assert result["count"] == 1
        msg = result["messages"][0]
        assert msg["sender_hmac_valid"] is True, (
            "Legacy messages without signature must be accepted"
        )

    def test_message_without_token_file_accepted(self, brain_path, tmp_path, monkeypatch):
        """When no token file exists for the sender, message is accepted (graceful)."""
        # Point home to a dir with NO token files
        empty_home = tmp_path / "empty_home"
        empty_home.mkdir(exist_ok=True)
        monkeypatch.setattr(Path, "home", lambda: empty_home)

        from mcp_server_nucleus.runtime.relay.core import relay_post, relay_inbox

        relay_post(
            to="test-recipient",
            subject="No token message",
            body="Test body",
            sender="unknown-sender",
        )

        result = relay_inbox(recipient="test_recipient", unread_only=False)
        assert result["count"] == 1
        msg = result["messages"][0]
        # No token → no signature → accepted (graceful degradation)
        assert "sender_hmac" not in msg or msg["sender_hmac"] is None
        assert msg["sender_hmac_valid"] is True, (
            "Messages without token file must be accepted (graceful)"
        )

    def test_signature_covers_identity_fields(self, brain_path, fake_token_dir):
        """The HMAC must cover id, sender, recipient, subject, created_at."""
        from mcp_server_nucleus.runtime.relay.core import _sign_relay_message

        message = {
            "id": "test-msg-001",
            "to": "test-recipient",
            "subject": "Test subject",
            "created_at": "2026-01-01T00:00:00Z",
        }
        # Use canonical (underscore) sender name — matches token file
        sig1 = _sign_relay_message(message, "test_sender")
        assert sig1 is not None

        # Changing any covered field should produce a different signature
        message2 = dict(message)
        message2["subject"] = "Different subject"
        sig2 = _sign_relay_message(message2, "test_sender")
        assert sig1 != sig2, "Subject change must produce different signature"

        message3 = dict(message)
        message3["to"] = "different-recipient"
        sig3 = _sign_relay_message(message3, "test_sender")
        assert sig1 != sig3, "Recipient change must produce different signature"

    def test_different_senders_have_different_signatures(self, brain_path, fake_token_dir):
        """Different senders (different tokens) must produce different signatures."""
        from mcp_server_nucleus.runtime.relay.core import _sign_relay_message

        message = {
            "id": "test-msg-001",
            "to": "test-recipient",
            "subject": "Test subject",
            "created_at": "2026-01-01T00:00:00Z",
        }
        # Use canonical (underscore) sender names — matches token files
        sig_sender1 = _sign_relay_message(message, "test_sender")
        sig_sender2 = _sign_relay_message(message, "coordinator")
        assert sig_sender1 != sig_sender2, (
            "Different senders must produce different signatures"
        )
