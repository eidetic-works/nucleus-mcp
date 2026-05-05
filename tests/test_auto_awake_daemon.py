"""Tests for auto_awake daemon (Sub-slice B, Tier 1 headless proxy)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "src")
)

from mcp_server_nucleus.runtime import auto_awake


def _write_envelope(
    bucket_dir: Path, relay_id: str, subject: str, body: str = "test body"
) -> Path:
    bucket_dir.mkdir(parents=True, exist_ok=True)
    path = bucket_dir / f"{relay_id}.json"
    payload = {
        "id": relay_id,
        "subject": subject,
        "body": body,
        "from": "test_sender",
        "to": bucket_dir.name,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def brain(tmp_path: Path) -> Path:
    """Isolated .brain/ root with relay/ + state/ scaffolded."""
    root = tmp_path / ".brain"
    (root / "relay").mkdir(parents=True)
    (root / "state").mkdir(parents=True)
    return root


def test_dispatch_happy_path(brain: Path) -> None:
    """Env-configured CLI gets invoked once; relay recorded with PID."""
    bucket_dir = brain / "relay" / "claude_code_main"
    _write_envelope(bucket_dir, "rl_happy_001", "[DIRECTIVE] kick the tires")

    targets = [("claude_code_main", "anthropic_claude_code", bucket_dir)]
    dedup = auto_awake._dedup_path(brain)

    with patch.dict(
        os.environ,
        {"NUCLEUS_AWAKE_CMD_ANTHROPIC_CLAUDE_CODE": "/bin/echo dispatched"},
    ):
        with patch.object(auto_awake.subprocess, "Popen") as popen_mock:
            popen_mock.return_value.pid = 4242
            popen_mock.return_value.stdin = None
            fired = auto_awake._poll_once(
                brain, targets, ("[DIRECTIVE]",), dedup
            )

    assert fired == 1
    popen_mock.assert_called_once()
    state = json.loads(dedup.read_text())
    entry = state["rl_happy_001"]
    assert entry["pid"] == 4242
    assert entry["bucket"] == "claude_code_main"
    assert "skipped" not in entry


def test_provider_missing_skip(brain: Path) -> None:
    """No env var for provider → relay recorded as no-cli-configured (no Popen)."""
    bucket_dir = brain / "relay" / "claude_code_main"
    _write_envelope(bucket_dir, "rl_skip_002", "[DIRECTIVE] no cli wired")

    targets = [("claude_code_main", "anthropic_claude_code", bucket_dir)]
    dedup = auto_awake._dedup_path(brain)

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("NUCLEUS_AWAKE_CMD_ANTHROPIC_CLAUDE_CODE", None)
        with patch.object(auto_awake.subprocess, "Popen") as popen_mock:
            fired = auto_awake._poll_once(
                brain, targets, ("[DIRECTIVE]",), dedup
            )

    assert fired == 0
    popen_mock.assert_not_called()
    state = json.loads(dedup.read_text())
    assert state["rl_skip_002"]["skipped"] == "no-cli-configured"


def test_dedup_prevents_redispatch(brain: Path) -> None:
    """Already-recorded relay_id is not re-dispatched on a second pass."""
    bucket_dir = brain / "relay" / "claude_code_main"
    _write_envelope(bucket_dir, "rl_dedup_003", "[DIRECTIVE] only once")

    targets = [("claude_code_main", "anthropic_claude_code", bucket_dir)]
    dedup = auto_awake._dedup_path(brain)

    with patch.dict(
        os.environ,
        {"NUCLEUS_AWAKE_CMD_ANTHROPIC_CLAUDE_CODE": "/bin/echo first"},
    ):
        with patch.object(auto_awake.subprocess, "Popen") as popen_mock:
            popen_mock.return_value.pid = 1
            popen_mock.return_value.stdin = None
            first = auto_awake._poll_once(
                brain, targets, ("[DIRECTIVE]",), dedup
            )
            second = auto_awake._poll_once(
                brain, targets, ("[DIRECTIVE]",), dedup
            )

    assert first == 1
    assert second == 0
    assert popen_mock.call_count == 1


def test_broken_envelope_silently_skipped(brain: Path) -> None:
    """Malformed JSON in inbox does not crash the poll pass."""
    bucket_dir = brain / "relay" / "claude_code_main"
    bucket_dir.mkdir(parents=True, exist_ok=True)
    (bucket_dir / "broken.json").write_text("{ not json", encoding="utf-8")
    _write_envelope(bucket_dir, "rl_after_broken", "[DIRECTIVE] still works")

    targets = [("claude_code_main", "anthropic_claude_code", bucket_dir)]
    dedup = auto_awake._dedup_path(brain)

    with patch.dict(
        os.environ,
        {"NUCLEUS_AWAKE_CMD_ANTHROPIC_CLAUDE_CODE": "/bin/echo ok"},
    ):
        with patch.object(auto_awake.subprocess, "Popen") as popen_mock:
            popen_mock.return_value.pid = 7
            popen_mock.return_value.stdin = None
            fired = auto_awake._poll_once(
                brain, targets, ("[DIRECTIVE]",), dedup
            )

    assert fired == 1
    state = json.loads(dedup.read_text())
    assert "rl_after_broken" in state
    assert "broken" not in state


def test_subject_prefix_filter(brain: Path) -> None:
    """Envelopes whose subject does not match a configured prefix are ignored."""
    bucket_dir = brain / "relay" / "claude_code_main"
    _write_envelope(bucket_dir, "rl_match_005", "[DIRECTIVE] do the thing")
    _write_envelope(bucket_dir, "rl_skip_006", "[INFO] do not trigger")

    targets = [("claude_code_main", "anthropic_claude_code", bucket_dir)]
    dedup = auto_awake._dedup_path(brain)

    with patch.dict(
        os.environ,
        {"NUCLEUS_AWAKE_CMD_ANTHROPIC_CLAUDE_CODE": "/bin/echo y"},
    ):
        with patch.object(auto_awake.subprocess, "Popen") as popen_mock:
            popen_mock.return_value.pid = 9
            popen_mock.return_value.stdin = None
            fired = auto_awake._poll_once(
                brain, targets, ("[DIRECTIVE]",), dedup
            )

    assert fired == 1
    state = json.loads(dedup.read_text())
    assert "rl_match_005" in state
    assert "rl_skip_006" not in state


def test_dedup_atomic_write_replaces_existing(brain: Path, tmp_path: Path) -> None:
    """`_write_dedup` must use tmp+replace so a partial write never lands."""
    dedup = brain / "state" / "auto_awake_dispatched.json"
    auto_awake._write_dedup(dedup, {"a": {"v": 1}})
    auto_awake._write_dedup(dedup, {"a": {"v": 1}, "b": {"v": 2}})

    state = json.loads(dedup.read_text())
    assert set(state.keys()) == {"a", "b"}
    siblings = list(dedup.parent.glob(f".{dedup.name}.tmp.*"))
    assert siblings == []
