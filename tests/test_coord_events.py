"""Tests for coord_events sidecar.

Per .brain/research/2026-04-28_tier_architecture/09_cloud_substrate_and_router_strategy.md
§5.4 implementation spec. Validates schema, append-only behavior, stitching
references, killswitch, and stats validation gate.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def tmp_brain(monkeypatch, tmp_path):
    """Point coord_events at a tmp brain dir so tests don't pollute real ledger."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEUS_COORD_EVENTS_DISABLED", raising=False)
    # Force re-import so module-level _DEFAULT_BRAIN_PATH doesn't shadow env
    if "mcp_server_nucleus.runtime.coord_events" in sys.modules:
        del sys.modules["mcp_server_nucleus.runtime.coord_events"]
    return brain


def _ledger_lines(brain: Path) -> list[dict]:
    path = brain / "ledger" / "coordination_events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_emit_writes_record_with_required_fields(tmp_brain):
    from mcp_server_nucleus.runtime import coord_events as ce
    eid = ce.emit(
        event_type="relay_fired",
        agent="claude_code_peer",
        session_id="sess-1",
        context_summary="firing test relay",
        available_options=[{"option_id": "A", "description": "x"}],
        chosen_option="A",
        reasoning_summary="only option that fits",
        tags=["test"],
    )
    assert eid.startswith("coord_")
    rows = _ledger_lines(tmp_brain)
    assert len(rows) == 1
    r = rows[0]
    for k in ("id", "timestamp", "event_type", "agent", "session_id",
              "context_summary", "available_options", "chosen_option",
              "reasoning_summary", "correction", "founder_verdict",
              "outcome_known_at", "outcome", "tags"):
        assert k in r, f"missing field: {k}"
    assert r["event_type"] == "relay_fired"
    assert r["chosen_option"] == "A"
    assert r["correction"] is None
    assert r["founder_verdict"] is None


def test_emit_unknown_event_type_raises(tmp_brain):
    from mcp_server_nucleus.runtime import coord_events as ce
    with pytest.raises(ValueError, match="unknown event_type"):
        ce.emit(event_type="not_a_real_type", agent="x", session_id="y", context_summary="z")


def test_killswitch_silently_skips(tmp_brain, monkeypatch):
    monkeypatch.setenv("NUCLEUS_COORD_EVENTS_DISABLED", "1")
    from mcp_server_nucleus.runtime import coord_events as ce
    eid = ce.emit(
        event_type="skill_picked",
        agent="claude_code_peer",
        session_id="sess-2",
        context_summary="skill match",
    )
    # Returns "" when disabled; ledger file never created
    assert eid == ""
    assert not (tmp_brain / "ledger" / "coordination_events.jsonl").exists()


def test_stitch_correction_references_original(tmp_brain):
    from mcp_server_nucleus.runtime import coord_events as ce
    original = ce.emit(
        event_type="skill_picked",
        agent="claude_code_main",
        session_id="sess-3",
        context_summary="picked skill X",
        chosen_option="skill_X",
    )
    correction_id = ce.stitch_correction(
        original,
        correction={"corrected_to": "skill_Y", "reason": "X was deprecated"},
    )
    rows = _ledger_lines(tmp_brain)
    assert len(rows) == 2
    assert rows[1]["event_type"] == "correction"
    assert rows[1]["stitches_to"] == original
    assert rows[1]["id"] == correction_id
    assert rows[1]["payload"]["corrected_to"] == "skill_Y"


def test_stitch_verdict_and_outcome(tmp_brain):
    from mcp_server_nucleus.runtime import coord_events as ce
    original = ce.emit(
        event_type="founder_override",
        agent="cowork",
        session_id="sess-4",
        context_summary="approval ask",
    )
    v_id = ce.stitch_verdict(original, verdict={"answer": "approve", "via": "telegram"})
    o_id = ce.stitch_outcome(original, outcome={"result": "shipped", "ts": "2026-05-01"})
    rows = _ledger_lines(tmp_brain)
    types = [r["event_type"] for r in rows]
    assert types == ["founder_override", "founder_verdict", "outcome"]
    assert rows[1]["stitches_to"] == original
    assert rows[2]["stitches_to"] == original
    assert v_id != o_id


def test_append_only_concurrent_writes(tmp_brain):
    """Multiple threads emit concurrently; all records land cleanly (no torn lines)."""
    import threading
    from mcp_server_nucleus.runtime import coord_events as ce

    def fire(n):
        for i in range(n):
            ce.emit(
                event_type="relay_fired",
                agent=f"agent-{i}",
                session_id=f"sess-{i}",
                context_summary="concurrent write test",
                tags=["concurrent"],
            )

    threads = [threading.Thread(target=fire, args=(20,)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    rows = _ledger_lines(tmp_brain)
    assert len(rows) == 80, f"expected 80 records, got {len(rows)}"
    # All event ids unique
    assert len({r["id"] for r in rows}) == 80


def test_stats_reports_validation_gate(tmp_brain):
    from mcp_server_nucleus.runtime import coord_events as ce
    # Empty ledger
    s = ce.stats()
    assert s["n_events"] == 0
    assert s["training_ready"] is False
    assert s["router_training_threshold"] == 5000

    # Add a few
    for i in range(3):
        ce.emit(event_type="relay_fired", agent="x", session_id=f"s{i}", context_summary="t")
    ce.emit(event_type="skill_picked", agent="x", session_id="s0", context_summary="t")
    s = ce.stats()
    assert s["n_events"] == 4
    assert s["n_by_type"] == {"relay_fired": 3, "skill_picked": 1}
    assert s["training_ready"] is False  # well below 5K threshold


def test_relay_processed_event_type_accepted(tmp_brain):
    """Receive-side event type fires + lands in ledger with matching message_id.

    Closes ack-latency loop for cross-trio observability dashboard
    (per .brain/research/2026-04-28_tier_architecture/15_coord_events_corpus_shape.md
    Gap 1). Substrate-level test — does NOT depend on relay_ops wiring;
    only verifies coord_events.emit accepts the new event_type.
    """
    from mcp_server_nucleus.runtime import coord_events as ce

    # Send-side event
    send_eid = ce.emit(
        event_type="relay_fired",
        agent="claude_code_main",
        session_id="sess-main",
        context_summary="relay to peer: hello",
        chosen_option="relay_msg_42",
    )
    assert send_eid.startswith("coord_")

    # Receive-side event with same chosen_option (the message_id)
    recv_eid = ce.emit(
        event_type="relay_processed",
        agent="claude_code_peer",
        session_id="sess-peer",
        context_summary="relay processed: hello",
        chosen_option="relay_msg_42",
        tags=["read_message"],
    )
    assert recv_eid.startswith("coord_")
    assert recv_eid != send_eid

    rows = _ledger_lines(tmp_brain)
    assert len(rows) == 2
    types = {r["event_type"] for r in rows}
    assert types == {"relay_fired", "relay_processed"}
    # Both events reference the same message_id — consumer can join for ack-latency
    msg_ids = {r["chosen_option"] for r in rows}
    assert msg_ids == {"relay_msg_42"}
