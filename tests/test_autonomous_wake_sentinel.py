"""Tests for v0.3.0 — sessions.autonomous_wake_sentinel.

Per cc-peer 2026-06-09T11:55Z SIGNOFF Q4 test floor:
- test_FallbackChainError_writes_sentinel_to_op_assistant_inbox
- test_sentinel_does_not_leak_bearer_or_body
- test_sentinel_filename_is_canonical_pattern
"""
from __future__ import annotations

import json

import pytest

from mcp_server_nucleus.sessions import autonomous_wake_sentinel as ws


# ── File creation + path shape ─────────────────────────────────────────


def test_sentinel_writes_to_op_assistant_inbox(tmp_path):
    brain = tmp_path / ".brain"
    path = ws.write_failure_sentinel(
        role="cc_tb",
        error_class_name="AutonomousWakeError",
        original_relay_filenames=["20260609T120000Z_main_test.json"],
        relay_subjects=["[TEST] subject"],
        brain_root=brain,
        timestamp="20260609T120000Z",
    )
    assert path.exists()
    assert path.parent == brain / "relay" / "claude_code_operator_assistant"


def test_sentinel_filename_is_canonical_pattern(tmp_path):
    path = ws.write_failure_sentinel(
        role="cc_tb",
        error_class_name="AutonomousWakeError",
        original_relay_filenames=[],
        relay_subjects=[],
        brain_root=tmp_path / ".brain",
        timestamp="20260609T120000Z",
    )
    assert path.name == (
        "20260609T120000Z_cc_tb_autonomous_wake_FAILED_role_cc_tb_err_AutonomousWakeError.json"
    )


def test_sentinel_json_shape_includes_required_keys(tmp_path):
    path = ws.write_failure_sentinel(
        role="cc_tb",
        error_class_name="FallbackChainError",
        original_relay_filenames=["a.json", "b.json"],
        relay_subjects=["s1", "s2"],
        brain_root=tmp_path / ".brain",
        timestamp="20260609T123456Z",
    )
    parsed = json.loads(path.read_text())
    assert parsed["schema"] == "relay/v1"
    assert parsed["from"] == "cc_tb"
    assert parsed["to"] == "claude_code_operator_assistant"
    assert parsed["priority"] == "high"
    body = parsed["body"]
    assert body["kind"] == "autonomous_wake_failure_sentinel"
    assert body["role"] == "cc_tb"
    assert body["error_class_name"] == "FallbackChainError"
    assert body["original_relay_filenames"] == ["a.json", "b.json"]
    assert body["truncated_subjects"] == ["s1", "s2"]


def test_sentinel_truncates_subjects_to_80_chars(tmp_path):
    long_subj = "A" * 500
    path = ws.write_failure_sentinel(
        role="cc_tb",
        error_class_name="FallbackChainError",
        original_relay_filenames=[],
        relay_subjects=[long_subj],
        brain_root=tmp_path / ".brain",
        timestamp="20260609T120000Z",
    )
    body = json.loads(path.read_text())["body"]
    assert len(body["truncated_subjects"][0]) == 80


def test_sentinel_ts_iso_normalized(tmp_path):
    path = ws.write_failure_sentinel(
        role="cc_tb",
        error_class_name="X",
        original_relay_filenames=[],
        relay_subjects=[],
        brain_root=tmp_path / ".brain",
        timestamp="20260609T120000Z",
    )
    parsed = json.loads(path.read_text())
    assert parsed["ts"] == "2026-06-09T12:00:00Z"


# ── Pseudonymity — sentinel does NOT leak bearer or body ──────────────


def test_sentinel_does_not_leak_bearer_or_body(tmp_path):
    """The sentinel writer must NEVER receive bearer or body. This test
    verifies that even if the caller had relay subjects + filenames, the
    written body has NO bearer/body fields."""
    SECRET_BEARER = "STUB-OAT-secret-bearer-do-not-leak"
    SECRET_BODY = "private body content that must never appear"
    path = ws.write_failure_sentinel(
        role="cc_tb",
        error_class_name="FallbackChainError",
        original_relay_filenames=[
            "20260609T120000Z_main_test.json",
        ],
        relay_subjects=["public-safe subject"],
        brain_root=tmp_path / ".brain",
        timestamp="20260609T120000Z",
    )
    raw = path.read_text()
    # bearer + body content NOT in sentinel
    assert SECRET_BEARER not in raw
    assert SECRET_BODY not in raw
    # Defensive: no bearer / body / cookie keys in body
    body = json.loads(raw)["body"]
    assert "bearer" not in body
    assert "body" not in body
    assert "cookies" not in body
    assert "wake_instruction" not in body


def test_sentinel_writes_atomically_via_tmp_rename(tmp_path, monkeypatch):
    from pathlib import Path
    seen_tmp = []
    orig_replace = Path.replace

    def _trace(self, target):
        if str(self).endswith(".tmp"):
            seen_tmp.append(str(self))
        return orig_replace(self, target)

    monkeypatch.setattr(Path, "replace", _trace)
    ws.write_failure_sentinel(
        role="cc_tb",
        error_class_name="X",
        original_relay_filenames=[],
        relay_subjects=[],
        brain_root=tmp_path / ".brain",
        timestamp="20260609T120000Z",
    )
    assert any(".tmp" in s for s in seen_tmp)


# ── Missing-arg guards ────────────────────────────────────────────────


def test_raises_on_empty_role(tmp_path):
    with pytest.raises(ValueError):
        ws.write_failure_sentinel(
            role="",
            error_class_name="X",
            original_relay_filenames=[],
            relay_subjects=[],
            brain_root=tmp_path,
        )


def test_raises_on_empty_error_class_name(tmp_path):
    with pytest.raises(ValueError):
        ws.write_failure_sentinel(
            role="cc_tb",
            error_class_name="",
            original_relay_filenames=[],
            relay_subjects=[],
            brain_root=tmp_path,
        )


def test_all_exported():
    assert set(ws.__all__) == {"write_failure_sentinel"}
