"""Tests for the checkpoint-optimized relay loader."""

import json
from pathlib import Path
import pytest

from mcp_server_nucleus.runtime.relay_ops import relay_context_sync


@pytest.fixture
def brain(tmp_path, monkeypatch):
    b = tmp_path / ".brain"
    (b / "relay" / "cowork").mkdir(parents=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    return b


def _write_msg(b: Path, filename: str, content: dict):
    target = b / "relay" / "cowork" / filename
    target.write_text(json.dumps(content), encoding="utf-8")


def test_relay_context_sync_slices_cycles(brain):
    """Test that context sync correctly slices by unique YYYYMMDD cycles."""
    # Write 4 messages across 4 distinct days
    msgs = [
        ("relay_20260421_120000_1111.json", {"from": "sys", "subject": "a"}),
        ("relay_20260422_120000_2222.json", {"from": "sys", "subject": "b"}),
        ("relay_20260423_120000_3333.json", {"from": "sys", "subject": "c"}),
        ("relay_20260424_120000_4444.json", {"from": "sys", "subject": "d"}),
        # Multiple in the same latest day
        ("relay_20260424_130000_5555.json", {"from": "sys", "subject": "e"}),
    ]
    for fn, c in msgs:
        _write_msg(brain, fn, c)

    res = relay_context_sync(recipient="cowork", max_cycles=2)
    
    # Should load only 20260424 and 20260423 (newest 2 days)
    # Total messages should be 3 (c, d, e)
    recent = res["recent_history"]
    assert len(recent) == 3
    assert res["cycles_loaded"] == 2
    subjects = {m["subject"] for m in recent}
    assert subjects == {"c", "d", "e"}
    assert "a" not in subjects
    assert "b" not in subjects


def test_relay_context_sync_extracts_active_decisions(brain):
    """Test that unread decisions/directives are extracted as active decisions."""
    # Write old messages but one is an active decision
    msgs = [
        ("relay_20260101_120000_old1.json", {"from": "sys", "subject": "ping", "read": False}),
        ("relay_20260102_120000_old2.json", {"from": "sys", "subject": "important decision needed", "read": False}),
        ("relay_20260103_120000_old3.json", {"from": "sys", "subject": "directive: do this", "read": True}), # Read, so not active
        ("relay_20260424_120000_new1.json", {"from": "sys", "subject": "ping"}),
    ]
    for fn, c in msgs:
        _write_msg(brain, fn, c)

    res = relay_context_sync(recipient="cowork", max_cycles=1)
    
    # max_cycles=1 means it will load 20260424 only in recent history.
    assert res["cycles_loaded"] == 1
    assert len(res["recent_history"]) == 1
    assert res["recent_history"][0]["subject"] == "ping"

    # However, active_decisions should grab 'important decision needed' despite it being outside the cycle limit.
    assert len(res["active_decisions"]) == 1
    assert res["active_decisions"][0]["subject"] == "important decision needed"
    # old3 was read, so it should not be included.
