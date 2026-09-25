"""Regression test for the flywheel<->recall bridge.

flywheel.core.file_ticket writes failure tickets to
.brain/flywheel/pending_issues.jsonl, but nucleus_recall (wedge) reads only
memories.db/history.jsonl. Without a read-side bridge, flywheel-filed tickets
are invisible to the recall that gates every read.

This test files a real flywheel ticket, then recalls for its step text and
asserts the ticket surfaces in the results.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fake_brain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "engrams" / "history.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    # Isolate auto-memory so build_auto_memory_index doesn't pick up real
    # ~/.claude/projects/<slug>/memory/*.md files.
    empty_mem = tmp_path / "empty_auto_memory"
    empty_mem.mkdir()
    monkeypatch.setattr(
        "nucleus_wedge.memories.default_auto_memory_root", lambda: empty_mem
    )
    # Keep flywheel from shelling out to the real `gh` CLI under this test.
    monkeypatch.setenv("NUCLEUS_TEST", "1")
    return brain


def _file_ticket(brain: Path, step: str, error: str, phase: str = "",
                 fix_description: str = "") -> dict:
    """File a real flywheel ticket into the fake brain."""
    from mcp_server_nucleus.flywheel.core import Flywheel

    return Flywheel(brain_path=brain).file_ticket(
        step=step, error=error, phase=phase,
        fix_description=fix_description,
    )


def test_filed_ticket_surfaces_in_recall(fake_brain: Path, capsys) -> None:
    """File a ticket then recall for its step text -> the ticket must appear."""
    from nucleus_wedge.recall_cmd import do_recall

    step = "build_runner_scope_check"
    error = "scope enforcement failed for build_runner step 7"
    _file_ticket(fake_brain, step=step, error=error, phase="verify")

    rc = do_recall(query=step, limit=10, brain_path_arg=str(fake_brain))
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    texts = [r["text"] for r in payload]
    assert any(step in t for t in texts), (
        f"flywheel-filed ticket step text {step!r} not found in recall results; "
        f"got {texts}"
    )
    # The surfaced row should carry the flywheel source/kind.
    flywheel_rows = [r for r in payload if r.get("source") == "flywheel:pending_issues"]
    assert flywheel_rows, "no flywheel-source row surfaced in recall"
    row = flywheel_rows[0]
    assert row["kind"] == "flywheel_ticket"
    assert step in row["text"]
    assert error in row["text"]
    assert "open" in row["text"]  # no fix_description -> open


def test_filed_ticket_with_fix_marked_closed(fake_brain: Path, capsys) -> None:
    """A ticket with a fix_description surfaces as closed."""
    from nucleus_wedge.recall_cmd import do_recall

    step = "merge_gate_authorize"
    error = "merge gate rejected PR 42"
    _file_ticket(
        fake_brain, step=step, error=error, phase="merge",
        fix_description="Re-run with --strict after fixing the import.",
    )

    rc = do_recall(query=step, limit=10, brain_path_arg=str(fake_brain))
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    flywheel_rows = [r for r in payload if r.get("source") == "flywheel:pending_issues"]
    assert flywheel_rows
    assert "closed" in flywheel_rows[0]["text"]


def test_kind_filter_excludes_flywheel_rows(fake_brain: Path, capsys) -> None:
    """A recall asking for kind='activity' must not surface flywheel tickets."""
    from nucleus_wedge.recall_cmd import do_recall

    step = "should_not_appear_kind_filter"
    _file_ticket(fake_brain, step=step, error="boom", phase="verify")

    rc = do_recall(query=step, limit=10, kind="activity",
                   brain_path_arg=str(fake_brain))
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    sources = [r.get("source") for r in payload]
    assert "flywheel:pending_issues" not in sources


def test_no_flywheel_file_is_byte_identical(fake_brain: Path, capsys) -> None:
    """When no pending_issues.jsonl exists, recall behaves as before the bridge."""
    from nucleus_wedge.recall_cmd import do_recall

    # Write a plain history record so recall has something to return.
    hist = fake_brain / "engrams" / "history.jsonl"
    record = {
        "key": "k1", "op_type": "ADD",
        "timestamp": "2026-04-20T10:00:00+00:00",
        "snapshot": {
            "key": "k1", "value": "alpha beta gamma",
            "context": "note", "intensity": 5, "version": 1,
            "source_agent": "nucleus-wedge", "op_type": "ADD",
            "timestamp": "2026-04-20T10:00:00+00:00",
            "deleted": False, "signature": None,
        },
    }
    hist.write_text(json.dumps(record) + "\n", encoding="utf-8")

    rc = do_recall(query="alpha", limit=5, brain_path_arg=str(fake_brain))
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert "alpha beta gamma" in payload[0]["text"]
    assert payload[0]["source"].startswith("history.jsonl")
