"""Tests for _resolve_inbox_dir per PR #1 CCR-inversion-for-relay-pickup.

Validates the bug fix: cc-tb's _resolve_inbox_dir now uses canonical map +
honors inbox_filter override.
"""
from __future__ import annotations
import pytest

from mcp_server_nucleus.runtime.relay_notify import _resolve_inbox_dir


def test_cc_tb_role_resolves_to_canonical_cc_tb_dir(tmp_path, monkeypatch):
    """LOAD-BEARING: closes the bug. cc-tb role -> .brain/relay/cc_tb/ path."""
    # Point get_brain_path to tmp_path/.brain
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)

    result = _resolve_inbox_dir(role="tb")
    assert result.name == "cc_tb", f"Expected 'cc_tb', got '{result.name}'"


def test_main_role_still_resolves_to_claude_code_main(tmp_path, monkeypatch):
    """Regression: main mapping unchanged."""
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)

    result = _resolve_inbox_dir(role="main")
    assert result.name == "claude_code_main"


def test_peer_role_still_resolves_to_claude_code_peer(tmp_path, monkeypatch):
    """Regression: peer mapping unchanged."""
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)

    result = _resolve_inbox_dir(role="peer")
    assert result.name == "claude_code_peer"


def test_inbox_filter_overrides_role_detection(tmp_path, monkeypatch):
    """PR #1 NEW capability: explicit inbox_filter bypasses role resolution."""
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("CC_SESSION_ROLE", "main")  # would normally map to claude_code_main

    # inbox_filter explicitly says "watch cc_tb instead"
    result = _resolve_inbox_dir(role="main", inbox_filter="cc_tb")
    assert result.name == "cc_tb"


def test_inbox_filter_overrides_env_var(tmp_path, monkeypatch):
    """inbox_filter wins over CC_SESSION_ROLE env var."""
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv("CC_SESSION_ROLE", "claude_code_main")

    result = _resolve_inbox_dir(inbox_filter="claude_code_peer")
    assert result.name == "claude_code_peer"


def test_inbox_filter_lowercases(tmp_path, monkeypatch):
    """inbox_filter is normalized to lowercase per canonical map."""
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

    result = _resolve_inbox_dir(inbox_filter="CC_TB")
    assert result.name == "cc_tb"


def test_legacy_claude_code_tb_role_maps_to_canonical_cc_tb(tmp_path, monkeypatch):
    """Legacy alias: claude_code_tb role -> canonical cc_tb dir."""
    brain = tmp_path / ".brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("CC_SESSION_ROLE", raising=False)

    result = _resolve_inbox_dir(role="claude_code_tb")
    assert result.name == "cc_tb"
