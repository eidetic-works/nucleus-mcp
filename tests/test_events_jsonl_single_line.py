"""Regression test: brain ledger event writer must emit single-line JSON.

Defect (a): The brain ledger event writer that appends to
``.brain/ledger/events.jsonl`` must emit only single-line JSON —
``json.dumps(obj)`` without ``indent``.  Multi-line (indented) JSON
breaks the JSONL contract (one JSON object per line) and corrupts
every line-by-line reader in the substrate (event_stream.read_events,
event_ops._read_events, health_ops, prometheus, morning_brief, etc.).

This test exercises both writers that append to ``events.jsonl``:
  1. ``runtime/event_ops._emit_event``  — the primary event writer
  2. ``runtime/event_stream.emit_event`` — the agent-runtime event writer

Both must produce exactly one line per event, parseable as a single
JSON object, with no embedded newlines.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# --------------------------------------------------------------------------
# event_ops._emit_event
# --------------------------------------------------------------------------

def test_event_ops_emit_event_writes_single_line_json(tmp_path, monkeypatch):
    """_emit_event appends one parseable JSON line per event — no indent."""
    from mcp_server_nucleus.runtime import event_ops

    brain = tmp_path / "brain"
    (brain / "ledger").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

    event_ops._emit_event("test_event", "test_emitter", {"key": "val", "nested": {"a": 1}})

    events_file = brain / "ledger" / "events.jsonl"
    assert events_file.exists(), "events.jsonl was not created"

    lines = events_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1, f"expected exactly 1 line, got {len(lines)}"

    # The single line must parse as valid JSON
    obj = json.loads(lines[0])
    assert obj["type"] == "test_event"
    assert obj["emitter"] == "test_emitter"
    assert obj["data"]["key"] == "val"

    # No indentation — compact single-line JSON
    assert "  " not in lines[0], "line contains indentation (multi-line JSON)"
    assert "\n" not in lines[0].rstrip("\n"), "line contains embedded newline"


def test_event_ops_emit_event_multiple_events_each_one_line(tmp_path, monkeypatch):
    """Multiple events produce multiple lines, each a single JSON object."""
    from mcp_server_nucleus.runtime import event_ops

    brain = tmp_path / "brain"
    (brain / "ledger").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

    for i in range(5):
        event_ops._emit_event("test_event", f"emitter_{i}", {"idx": i})

    events_file = brain / "ledger" / "events.jsonl"
    lines = events_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5, f"expected 5 lines, got {len(lines)}"

    for i, line in enumerate(lines):
        obj = json.loads(line)  # must not raise
        assert obj["data"]["idx"] == i
        assert "  " not in line, f"line {i} contains indentation"


# --------------------------------------------------------------------------
# event_stream.emit_event
# --------------------------------------------------------------------------

def test_event_stream_emit_event_writes_single_line_json(tmp_path, monkeypatch):
    """event_stream.emit_event appends one parseable JSON line per event."""
    from mcp_server_nucleus.runtime import event_stream

    brain = tmp_path / "brain"
    events_path = event_stream.get_events_path(brain)
    events_path.parent.mkdir(parents=True, exist_ok=True)

    event_stream.emit_event(
        brain_path=brain,
        event_type="test_event",
        emitter="test_emitter",
        payload={"key": "val", "nested": {"a": 1}},
    )

    assert events_path.exists(), "events.jsonl was not created"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1, f"expected exactly 1 line, got {len(lines)}"

    obj = json.loads(lines[0])
    assert obj["event_type"] == "test_event"
    assert obj["payload"]["key"] == "val"

    # No indentation — compact single-line JSON
    assert "  " not in lines[0], "line contains indentation (multi-line JSON)"


# --------------------------------------------------------------------------
# Repair round-trip: _repair_events_jsonl preserves single-line format
# --------------------------------------------------------------------------

def test_repair_events_jsonl_preserves_single_line(tmp_path, monkeypatch):
    """_repair_events_jsonl rewrites with single-line JSON (no indent)."""
    from mcp_server_nucleus.runtime import event_ops

    brain = tmp_path / "brain"
    (brain / "ledger").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

    events_file = brain / "ledger" / "events.jsonl"
    # Seed with a valid single-line event
    event_ops._emit_event("seed", "test", {"a": 1})

    result = event_ops._repair_events_jsonl()
    assert result["status"] == "ok"

    lines = events_file.read_text(encoding="utf-8").splitlines()
    for line in lines:
        obj = json.loads(line)  # must parse
        assert "  " not in line, "repaired line contains indentation"
