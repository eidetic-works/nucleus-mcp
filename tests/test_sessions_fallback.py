"""Tests for v0.3.0 Layer 4 — mcp_server_nucleus.sessions.fallback.

Per .brain/specs/v030_full_client_emulator_oauth_path.md § Layer 4
+ cc-peer 2026-06-09T10:45Z verdict batch + op-assistant 03:50Z
Layer 3 NULL VERDICT (chain collapses to Layer 1 prearm + Layer 5).

Coverage:
- post_relay_to_role: chain orchestration, prearm best-effort, Layer 5
  load-bearing
- prearm failure NON-blocking when Layer 5 succeeds
- Layer 5 failure raises FallbackChainError
- prearm=False skips Layer 1 entirely
- prearm skipped silently when cookies missing/empty
- model + max_tokens passthrough
- Pseudonymity: bearer + relay body never logged (delegated to Layer 5)
- session_id + org_uuid truncated in logs
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from mcp_server_nucleus.sessions import fallback as fb


# ── Happy path: prearm + Layer 5 both succeed ──────────────────────────


def test_post_relay_to_role_happy_path():
    prearm_return = {
        "before": {}, "put_response": {}, "presence_response": {}, "after": {},
        "deltas": {"connection_status_changed": False},
    }
    wake_return = {
        "ok": True,
        "response": {"id": "msg_x", "stop_reason": "end_turn"},
        "tool_use_blocks": [],
        "wake_instruction": "ok",
    }
    with patch.object(fb, "prearm_session", return_value=prearm_return) as p, \
         patch.object(fb, "autonomous_wake_from_relay",
                      return_value=wake_return) as w:
        result = fb.post_relay_to_role(
            role="cc_tb",
            session_id="cse_abc123def456",
            org_uuid="903554b9-org",
            bearer="STUB-OAT",
            relay_subject="s",
            relay_body="b",
            cookies={"sessionKey": "STUB-SID"},
        )
    assert result["ok"] is True
    assert result["prearm_attempted"] is True
    assert result["prearm_ok"] is True
    assert result["prearm_error"] is None
    assert result["wake_response"] == wake_return
    assert result["wake_error"] is None
    p.assert_called_once()
    w.assert_called_once()


# ── Prearm failure NON-blocking when Layer 5 succeeds ──────────────────


def test_prearm_fail_does_not_abort_layer_5():
    """Layer 1 failure absorbed; Layer 5 still fires + chain reports ok."""
    wake_return = {
        "ok": True,
        "response": {"stop_reason": "end_turn"},
        "tool_use_blocks": [],
        "wake_instruction": "ok",
    }
    with patch.object(fb, "prearm_session",
                      side_effect=fb.SessionStateError("PUT rejected status=401")), \
         patch.object(fb, "autonomous_wake_from_relay",
                      return_value=wake_return):
        result = fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body="b",
            cookies={"sessionKey": "STUB-SID"},
        )
    assert result["ok"] is True
    assert result["prearm_attempted"] is True
    assert result["prearm_ok"] is False
    assert "PUT rejected" in result["prearm_error"]
    assert result["wake_error"] is None


# ── Layer 5 failure raises FallbackChainError ──────────────────────────


def test_layer_5_fail_raises_fallback_chain_error():
    with patch.object(fb, "prearm_session", return_value={"deltas": {}}), \
         patch.object(fb, "autonomous_wake_from_relay",
                      side_effect=fb.AutonomousWakeError("inference rejected status=429")):
        with pytest.raises(fb.FallbackChainError) as exc:
            fb.post_relay_to_role(
                role="cc_tb", session_id="cse_x", org_uuid="o",
                bearer="STUB-OAT", relay_subject="s", relay_body="b",
                cookies={"sessionKey": "STUB-SID"},
            )
    assert "Layer 5 inference failed" in str(exc.value)
    assert "cc_tb" in str(exc.value)


def test_layer_5_fail_after_successful_prearm_still_raises():
    """Even if prearm OK, Layer 5 failure is terminal for the chain."""
    with patch.object(fb, "prearm_session",
                      return_value={"deltas": {"worker_status_changed": True}}), \
         patch.object(fb, "autonomous_wake_from_relay",
                      side_effect=fb.AutonomousWakeError("transport timeout")):
        with pytest.raises(fb.FallbackChainError):
            fb.post_relay_to_role(
                role="cc_tb", session_id="cse_x", org_uuid="o",
                bearer="STUB-OAT", relay_subject="s", relay_body="b",
                cookies={"sessionKey": "STUB-SID"},
            )


# ── prearm=False skips Layer 1 entirely ────────────────────────────────


def test_prearm_false_skips_layer_1():
    with patch.object(fb, "prearm_session") as p, \
         patch.object(fb, "autonomous_wake_from_relay",
                      return_value={"ok": True, "response": {}, "tool_use_blocks": [],
                                    "wake_instruction": ""}):
        result = fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body="b",
            cookies={"sessionKey": "STUB-SID"},
            prearm=False,
        )
    p.assert_not_called()
    assert result["prearm_attempted"] is False
    assert result["prearm_ok"] is None
    assert result["ok"] is True


def test_prearm_skipped_silently_when_cookies_missing():
    with patch.object(fb, "prearm_session") as p, \
         patch.object(fb, "autonomous_wake_from_relay",
                      return_value={"ok": True, "response": {}, "tool_use_blocks": [],
                                    "wake_instruction": ""}):
        result = fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body="b",
            cookies=None,  # missing
            prearm=True,   # explicit prearm request but no cookies
        )
    p.assert_not_called()
    assert result["prearm_attempted"] is False
    assert result["ok"] is True


def test_prearm_skipped_silently_when_session_key_missing_in_cookies():
    with patch.object(fb, "prearm_session") as p, \
         patch.object(fb, "autonomous_wake_from_relay",
                      return_value={"ok": True, "response": {}, "tool_use_blocks": [],
                                    "wake_instruction": ""}):
        result = fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body="b",
            cookies={"cf_clearance": "cf"},  # no sessionKey
            prearm=True,
        )
    p.assert_not_called()
    assert result["prearm_attempted"] is False


# ── model + max_tokens passthrough ─────────────────────────────────────


def test_model_and_max_tokens_threaded_to_layer_5():
    captured = {}
    def _capture(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "response": {}, "tool_use_blocks": [],
                "wake_instruction": ""}
    with patch.object(fb, "autonomous_wake_from_relay", side_effect=_capture):
        fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body="b",
            prearm=False,
            model="claude-opus-4-7",
            max_tokens=8192,
        )
    assert captured["model"] == "claude-opus-4-7"
    assert captured["max_tokens"] == 8192


def test_model_and_max_tokens_omitted_when_none():
    """When caller doesn't specify, Layer 5 uses its defaults — kwargs not passed."""
    captured = {}
    def _capture(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "response": {}, "tool_use_blocks": [],
                "wake_instruction": ""}
    with patch.object(fb, "autonomous_wake_from_relay", side_effect=_capture):
        fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body="b",
            prearm=False,
        )
    assert "model" not in captured
    assert "max_tokens" not in captured


# ── discovery_context passthrough ──────────────────────────────────────


def test_discovery_context_threaded_to_layer_5():
    captured = {}
    def _capture(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "response": {}, "tool_use_blocks": [],
                "wake_instruction": ""}
    ctx = {"system_prompt": "you are cc-tb", "tools": [{"name": "x"}]}
    with patch.object(fb, "autonomous_wake_from_relay", side_effect=_capture):
        fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body="b",
            prearm=False,
            discovery_context=ctx,
        )
    assert captured["discovery_context"] == ctx


def test_history_limit_threaded_to_layer_5():
    captured = {}
    def _capture(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "response": {}, "tool_use_blocks": [],
                "wake_instruction": ""}
    with patch.object(fb, "autonomous_wake_from_relay", side_effect=_capture):
        fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body="b",
            prearm=False,
            history_limit=10,
        )
    assert captured["history_limit"] == 10


# ── Missing-arg guards ─────────────────────────────────────────────────


def test_raises_on_missing_role():
    with pytest.raises(fb.FallbackChainError):
        fb.post_relay_to_role(
            role="", session_id="cse_x", org_uuid="o",
            bearer="STUB", relay_subject="s", relay_body="b",
        )


def test_raises_on_missing_session_id():
    with pytest.raises(fb.FallbackChainError):
        fb.post_relay_to_role(
            role="cc_tb", session_id="", org_uuid="o",
            bearer="STUB", relay_subject="s", relay_body="b",
        )


def test_raises_on_missing_bearer():
    with pytest.raises(fb.FallbackChainError):
        fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="", relay_subject="s", relay_body="b",
        )


# ── Pseudonymity ───────────────────────────────────────────────────────


def test_bearer_never_logged_on_chain_success(caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.sessions_fallback")
    SECRET_BEARER = "STUB-OAT-fallback-secret-do-not-leak-xyz"
    with patch.object(fb, "autonomous_wake_from_relay",
                      return_value={"ok": True, "response": {}, "tool_use_blocks": [],
                                    "wake_instruction": ""}):
        fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer=SECRET_BEARER, relay_subject="s", relay_body="b",
            prearm=False,
        )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


def test_bearer_never_logged_on_layer_5_failure(caplog):
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.sessions_fallback")
    SECRET_BEARER = "STUB-OAT-fail-leak-xyz"
    with patch.object(fb, "autonomous_wake_from_relay",
                      side_effect=fb.AutonomousWakeError("fail")):
        with pytest.raises(fb.FallbackChainError):
            fb.post_relay_to_role(
                role="cc_tb", session_id="cse_x", org_uuid="o",
                bearer=SECRET_BEARER, relay_subject="s", relay_body="b",
                prearm=False,
            )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BEARER not in all_text


def test_relay_body_never_logged_at_layer_4(caplog):
    """Body content should not be logged at Layer 4 (Layer 5 also enforces)."""
    import logging
    caplog.set_level(logging.DEBUG, logger="nucleus.sessions_fallback")
    SECRET_BODY = "private operator content should not leak DEF-GHI-456"
    with patch.object(fb, "autonomous_wake_from_relay",
                      return_value={"ok": True, "response": {}, "tool_use_blocks": [],
                                    "wake_instruction": ""}):
        fb.post_relay_to_role(
            role="cc_tb", session_id="cse_x", org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body=SECRET_BODY,
            prearm=False,
        )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_BODY not in all_text


def test_session_id_truncated_in_logs(caplog):
    import logging
    caplog.set_level(logging.INFO, logger="nucleus.sessions_fallback")
    long_cse = "cse_AAAAAAAA_BBBBBBBB_CCCCCCCC_DDDDDDDD"
    with patch.object(fb, "autonomous_wake_from_relay",
                      return_value={"ok": True, "response": {}, "tool_use_blocks": [],
                                    "wake_instruction": ""}):
        fb.post_relay_to_role(
            role="cc_tb", session_id=long_cse, org_uuid="o",
            bearer="STUB-OAT", relay_subject="s", relay_body="b",
            prearm=False,
        )
    all_text = " ".join(r.getMessage() for r in caplog.records)
    assert long_cse[:12] in all_text
    assert long_cse not in all_text


# ── Module exports ─────────────────────────────────────────────────────


def test_all_exported():
    expected = {"FallbackChainError", "post_relay_to_role"}
    assert set(fb.__all__) == expected
