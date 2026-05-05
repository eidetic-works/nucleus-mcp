"""Tests for R6.1 — explicit-sender-required default contract.

Background: the MCP server process can't reliably distinguish which client
is calling it when multiple surfaces (Cowork, CC-main, CC-peer, Gemini,
Windsurf) share one stdio pipe. Silent coercion via detect_session_type()
produced cross-surface mis-attribution. R6.1 makes sender= required by
default; NUCLEUS_RELAY_INFER_SENDER=1 restores the legacy fallback opt-in.

R6.1-v2 (2026-04-24): the opt-in coercion path now emits a WARNING with
caller hint so mis-attribution is audible in logs. Silent on happy path,
audible on compat path, hard-fail on strict path.
"""

import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.relay_ops import relay_post


@pytest.fixture(autouse=True)
def _isolated_brain(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv("NUCLEUS_RELAY_INFER_SENDER", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_STRICT", raising=False)


class TestSenderRequiredDefault:
    def test_missing_sender_raises(self):
        with pytest.raises(ValueError, match="sender is required"):
            relay_post(to="cowork", subject="t", body="{}")

    def test_none_sender_raises(self):
        with pytest.raises(ValueError, match="sender is required"):
            relay_post(to="cowork", subject="t", body="{}", sender=None)

    def test_error_message_names_env_var(self):
        with pytest.raises(ValueError, match="NUCLEUS_RELAY_INFER_SENDER"):
            relay_post(to="cowork", subject="t", body="{}")

    def test_explicit_sender_passes(self):
        result = relay_post(
            to="cowork", subject="t", body="{}", sender="claude_code_peer"
        )
        assert result["sent"] is True
        assert result["from"] == "claude_code_peer"


class TestInferSenderOptIn:
    def test_env_var_enables_coercion(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
        # Force detector output via explicit override env var (avoids
        # cwd/process-tree heuristics polluting the test).
        monkeypatch.setenv("NUCLEUS_SESSION_TYPE", "cowork")
        result = relay_post(to="claude_code_peer", subject="t", body="{}")
        assert result["sent"] is True
        assert result["from"] == "cowork"

    def test_env_var_only_zero_one(self, monkeypatch):
        # Any value other than exactly "1" = disabled (strict boolean gate).
        monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "true")
        with pytest.raises(ValueError):
            relay_post(to="cowork", subject="t", body="{}")

    def test_explicit_wins_over_inference(self, monkeypatch):
        monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
        monkeypatch.setenv("NUCLEUS_SESSION_TYPE", "cowork")
        result = relay_post(
            to="cowork",
            subject="t",
            body="{}",
            sender="claude_code_main",
        )
        # Explicit sender passes through untouched even with inference on.
        assert result["from"] == "claude_code_main"


class TestCoercionWarning:
    """R6.1-v2 — opt-in coercion path must emit a WARNING with caller hint.

    Silent coercion produced the antigravity mis-attribution incident
    (relay_20260424_053832_0fd9d451). Even on opt-in, the fallback should
    now log so substrate-level drift is visible.
    """

    def test_coercion_emits_warning(self, monkeypatch, caplog):
        monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
        monkeypatch.setenv("NUCLEUS_SESSION_TYPE", "cowork")
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            result = relay_post(to="claude_code_peer", subject="t", body="{}")
        assert result["sent"] is True
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) >= 1, "coercion path must emit at least one WARNING"
        msg = warnings[0].getMessage()
        assert "sender coerced" in msg
        assert "NUCLEUS_RELAY_INFER_SENDER" in msg
        assert "cowork" in msg  # inferred sender value surfaces in the log

    def test_warning_carries_caller_hint(self, monkeypatch, caplog):
        monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
        monkeypatch.setenv("NUCLEUS_SESSION_TYPE", "cowork")
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            relay_post(to="claude_code_peer", subject="t", body="{}")
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        msg = warnings[0].getMessage()
        # Caller hint format: file:lineno:funcname — this test's file should
        # appear since it's the direct caller of relay_post.
        assert "Caller:" in msg
        assert "test_relay_post_sender_required.py" in msg

    def test_explicit_sender_emits_no_warning(self, monkeypatch, caplog):
        # Happy path (explicit sender) must stay silent — no stack
        # introspection, no log noise.
        monkeypatch.setenv("NUCLEUS_RELAY_INFER_SENDER", "1")
        monkeypatch.setenv("NUCLEUS_SESSION_TYPE", "cowork")
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            relay_post(
                to="cowork",
                subject="t",
                body="{}",
                sender="claude_code_peer",
            )
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert warnings == []

    def test_strict_mode_no_warning_on_rejection(self, monkeypatch, caplog):
        # Strict path (ValueError) must not log WARNING — the exception IS
        # the signal. Log noise on the reject path would double-count.
        with caplog.at_level(logging.WARNING, logger="nucleus.relay"):
            with pytest.raises(ValueError):
                relay_post(to="cowork", subject="t", body="{}")
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert warnings == []
