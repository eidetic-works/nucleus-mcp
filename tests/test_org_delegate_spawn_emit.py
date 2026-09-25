"""Tests for spawn_prep / spawn_close two-phase API in org_delegate.

Per cost-consult convergence 2026-05-02 — the API wraps assemble_prompt with
agent_spawn / agent_return event emission so /delegate skill (and other
delegation callsites) get cost-telemetry without per-callsite emit boilerplate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def tmp_brain(monkeypatch, tmp_path):
    brain = tmp_path / ".brain"
    (brain / "ledger").mkdir(parents=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    # Force re-import so module-level path resolvers honor the env override
    evicted = {
        name: mod
        for name, mod in sys.modules.items()
        if name.startswith("mcp_server_nucleus.runtime.")
    }
    for name in evicted:
        del sys.modules[name]
    yield brain
    # Restore evicted modules and re-point parent-package attrs; without this,
    # later test files hold stale module objects (OLD/NEW identity split)
    sys.modules.update(evicted)
    for name, mod in evicted.items():
        parent_name, _, attr = name.rpartition(".")
        parent = sys.modules.get(parent_name)
        if parent is not None:
            setattr(parent, attr, mod)


@pytest.fixture
def tmp_charters(tmp_path):
    charters = tmp_path / "charters"
    charters.mkdir()
    (charters / "sonnet_helper_peer.md").write_text(
        "---\nname: sonnet_helper_peer\n---\n\nExecute peer-lane briefs decisively.\n"
    )
    return charters


def _events(brain: Path) -> list[dict]:
    path = brain / "ledger" / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_spawn_prep_emits_agent_spawn_and_returns_prompt_and_id(tmp_brain, tmp_charters):
    from mcp_server_nucleus.runtime import org_delegate

    prompt, spawn_id = org_delegate.spawn_prep(
        role="sonnet_helper_peer",
        brief="ship a 30-LOC fix to scripts/foo.py",
        model="sonnet",
        parent="claude_code_peer",
        charters_dir=tmp_charters,
    )

    assert spawn_id.startswith("spawn_")
    assert "Charter: sonnet_helper_peer" in prompt
    assert "ship a 30-LOC fix" in prompt

    events = _events(tmp_brain)
    spawn_events = [e for e in events if e["type"] == "agent_spawn"]
    assert len(spawn_events) == 1
    e = spawn_events[0]
    assert e["emitter"] == "claude_code_peer"
    assert e["data"]["spawn_id"] == spawn_id
    assert e["data"]["role"] == "sonnet_helper_peer"
    assert e["data"]["model"] == "sonnet"
    assert e["data"]["parent"] == "claude_code_peer"
    assert e["data"]["prompt_chars"] == len(prompt)


def test_spawn_close_emits_paired_agent_return_with_duration(tmp_brain, tmp_charters):
    from mcp_server_nucleus.runtime import org_delegate

    _, spawn_id = org_delegate.spawn_prep(
        role="sonnet_helper_peer",
        brief="b",
        model="sonnet",
        parent="claude_code_peer",
        charters_dir=tmp_charters,
    )
    result = org_delegate.spawn_close(spawn_id, "ok done.")

    assert result["spawn_id"] == spawn_id
    assert result["response_chars"] == len("ok done.")
    assert result["success"] is True
    assert result["orphan"] is False
    assert result["duration_ms"] is not None and result["duration_ms"] >= 0

    events = _events(tmp_brain)
    return_events = [e for e in events if e["type"] == "agent_return"]
    assert len(return_events) == 1
    re = return_events[0]
    assert re["data"]["spawn_id"] == spawn_id
    assert re["data"]["parent"] == "claude_code_peer"
    assert re["data"]["orphan"] is False


def test_spawn_close_orphan_emits_with_orphan_flag(tmp_brain):
    """spawn_close called without prior spawn_prep emits an orphan-flagged
    agent_return so audit_token_cost.py can detect gap rather than silently
    dropping the close."""
    from mcp_server_nucleus.runtime import org_delegate

    result = org_delegate.spawn_close("spawn_does_not_exist_999", "x")

    assert result["orphan"] is True
    assert result["duration_ms"] is None
    assert result["spawn_id"] == "spawn_does_not_exist_999"

    events = _events(tmp_brain)
    return_events = [e for e in events if e["type"] == "agent_return"]
    assert len(return_events) == 1
    assert return_events[0]["data"]["orphan"] is True
    assert return_events[0]["emitter"] == "unknown"


def test_assemble_prompt_unchanged_no_events_emitted(tmp_brain, tmp_charters):
    """The original assemble_prompt API must NOT emit events — backwards-compat
    for callers who emit themselves."""
    from mcp_server_nucleus.runtime import org_delegate

    prompt, metadata = org_delegate.assemble_prompt(
        role="sonnet_helper_peer", brief="x", charters_dir=tmp_charters,
    )
    assert "Charter:" in prompt
    assert metadata["role"] == "sonnet_helper_peer"

    events = _events(tmp_brain)
    assert len([e for e in events if e["type"] in ("agent_spawn", "agent_return")]) == 0
