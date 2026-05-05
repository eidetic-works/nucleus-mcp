"""Tests for legacy `claude_code` bucket intercept.

Background: cc-tb's relay (relay_20260502_165946_b5b63145) addressed
`to: "claude_code"` instead of `to: "claude_code_main"`, violating
feedback_relay_post_to_field_uses_role_bucket HARD RULE.

This test verifies that the `_coerce_legacy_bucket_target()` intercept in
relay_post() transparently redirects writes destined for the legacy bucket to
the canonical `claude_code_main` bucket and emits a WARNING for observability.
Mirrors the R6.1-v2 sender-coercion test shape (test_relay_post_sender_required.py).
"""

import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.relay_ops import (
    _coerce_legacy_bucket_target,
    relay_post,
)


@pytest.fixture(autouse=True)
def _isolated_brain(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv("NUCLEUS_RELAY_INFER_SENDER", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_STRICT", raising=False)


# ── Unit tests for the helper ─────────────────────────────────────

class TestCoerceLegacyBucketTargetHelper:
    """Direct unit tests for _coerce_legacy_bucket_target()."""

    def test_legacy_bucket_coerced_to_main(self, caplog):
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            result = _coerce_legacy_bucket_target("claude_code")
        assert result == "claude_code_main"

    def test_non_legacy_bucket_unchanged(self):
        assert _coerce_legacy_bucket_target("claude_code_main") == "claude_code_main"
        assert _coerce_legacy_bucket_target("claude_code_peer") == "claude_code_peer"
        assert _coerce_legacy_bucket_target("cowork") == "cowork"
        assert _coerce_legacy_bucket_target("windsurf") == "windsurf"

    def test_coercion_emits_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            _coerce_legacy_bucket_target("claude_code")
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) >= 1, "coercion must emit at least one WARNING"
        msg = warnings[0].getMessage()
        assert "claude_code" in msg
        assert "claude_code_main" in msg

    def test_coercion_warning_includes_session_id(self, caplog):
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            _coerce_legacy_bucket_target("claude_code", from_session_id="ses_abc123")
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        msg = warnings[0].getMessage()
        assert "ses_abc123" in msg

    def test_no_warning_on_canonical_bucket(self, caplog):
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            _coerce_legacy_bucket_target("claude_code_main")
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert warnings == []


# ── Integration test: relay_post() end-to-end ─────────────────────

class TestRelayPostLegacyBucketIntercept:
    """Verify the intercept is wired into relay_post() at the bucket-path
    construction stage: message lands in claude_code_main/ and a WARNING fires.
    """

    def test_legacy_to_field_lands_in_main_bucket(self, tmp_path):
        """Core assertion: relay_post(to='claude_code') writes file to
        .brain/relay/claude_code_main/, not .brain/relay/claude_code/.
        """
        result = relay_post(
            to="claude_code",
            subject="cc-tb reply regression test",
            body=json.dumps({"note": "legacy bucket regression"}),
            sender="cowork",
            from_session_id="ses_tb_test",
        )
        assert result["sent"] is True
        # `to` field in return value must reflect coerced bucket
        assert result["to"] == "claude_code_main"
        # The file must exist under claude_code_main/, not claude_code/
        brain = Path(result["path"]).parts
        assert "claude_code_main" in brain, (
            f"Expected message in claude_code_main/ bucket; path was: {result['path']}"
        )
        legacy_dir = tmp_path / "relay" / "claude_code"
        assert not any(legacy_dir.glob("*.json")), (
            "No files should land in the legacy claude_code/ bucket"
        )

    def test_legacy_to_field_emits_warning_in_relay_post(self, caplog):
        """relay_post(to='claude_code') must emit a WARNING for observability."""
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            relay_post(
                to="claude_code",
                subject="observability check",
                body="{}",
                sender="cowork",
            )
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) >= 1, "legacy bucket intercept must emit a WARNING"
        msg = warnings[0].getMessage()
        assert "claude_code_main" in msg

    def test_canonical_to_field_no_warning(self, caplog):
        """relay_post(to='claude_code_main') must not trigger any WARNING
        (happy path stays silent).
        """
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            relay_post(
                to="claude_code_main",
                subject="canonical bucket check",
                body="{}",
                sender="cowork",
            )
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert warnings == [], "canonical bucket must produce no coercion warnings"
