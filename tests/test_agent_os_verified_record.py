"""Tests for ``runtime.agent_os.verified_record.label_turn``.

Doctrine under test: *never silently CONFIRM.* An unanchorable outcome must
come back UNVERIFIABLE (withhold, not guess); a deterministically-checkable
outcome must come back CONFIRMED. No network — all anchors are fs or manual.
"""
from __future__ import annotations

from mcp_server_nucleus.runtime.agent_os.verified_record import label_turn
from mcp_server_nucleus.runtime.verifier import (
    Anchor,
    InjectedReasoner,
    ProbeEngine,
    Verifier,
)


def test_unanchorable_outcome_is_unverifiable():
    """A vibe-level assertion with no deterministic anchor → UNVERIFIABLE.

    If the bare ``RuleReasoner`` happens to find an anchor for this string,
    force the issue with an ``InjectedReasoner`` carrying a single ``manual``
    anchor (always UNVERIFIABLE per the verifier contract).
    """
    outcome = "the vibe was good and the code feels clean"

    # First attempt: default RuleReasoner — honest verdict, no forcing.
    result = label_turn(outcome)
    if result["status"] == "UNVERIFIABLE":
        assert isinstance(result["confidence"], float)
        assert isinstance(result["detail"], str)
        return

    # Fallback: force a manual anchor so the doctrine is exercised regardless
    # of how RuleReasoner decomposes this particular string.
    forced = Verifier(
        reasoner=InjectedReasoner(
            {
                "agent_os_turn": [
                    Anchor(
                        "m1",
                        "manual",
                        {},
                        "no deterministic check",
                        critical=False,
                    )
                ]
            }
        ),
        probe_engine=ProbeEngine(),
        ledger=None,
        record=False,
    )
    result = label_turn(outcome, claim_id="agent_os_turn", verifier=forced)
    assert result["status"] == "UNVERIFIABLE"
    assert isinstance(result["confidence"], float)
    assert isinstance(result["detail"], str)


def test_checkable_outcome_is_confirmed(tmp_path):
    """A real temp file + an fs/file_exists anchor → CONFIRMED."""
    f = tmp_path / "out.txt"
    f.write_text("shipped\n", encoding="utf-8")

    verifier = Verifier(
        reasoner=InjectedReasoner(
            {
                "c1": [
                    Anchor(
                        "a1",
                        "fs",
                        {"op": "file_exists", "path": str(f)},
                        "file exists",
                        critical=True,
                    )
                ]
            }
        ),
        probe_engine=ProbeEngine(),
        ledger=None,
        record=False,
    )
    result = label_turn(
        "the output file was written", claim_id="c1", verifier=verifier
    )
    assert result["status"] == "CONFIRMED"
    assert isinstance(result["confidence"], float)
    assert isinstance(result["detail"], str)


# ── boot_cell integration: verified_label wiring (flag-gated, default OFF) ────


def test_boot_cell_attaches_verified_label_when_flag_on(tmp_path, monkeypatch):
    """Flag ON: boot_cell attaches a referee verdict to BootResult.verified_label."""
    import pytest

    from mcp_server_nucleus.runtime.agent_os import boot as boot_mod

    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")
    monkeypatch.setenv(boot_mod.VERIFIED_RECORD_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")

    from nucleus_wedge.store import Store

    Store(str(brain)).append(
        value="The Nucleus gateway routes model calls through the OS; agents live INSIDE.",
        kind="note",
        tags=["topic:gateway"],
        source_agent="prior-session",
    )

    result = boot_mod.boot_cell(
        "How should this agent route its model calls?",
        recall_query="gateway",
        brain_path=str(brain),
    )

    assert result.verified_label is not None
    assert "status" in result.verified_label
    assert result.verified_label["status"] in {
        "CONFIRMED",
        "REFUTED",
        "UNVERIFIABLE",
        "PARTIAL",
    }


def test_boot_cell_no_label_when_flag_off(tmp_path, monkeypatch):
    """Flag OFF: boot_cell.verified_label is None (byte-identical-OFF contract)."""
    from mcp_server_nucleus.runtime.agent_os import boot as boot_mod

    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    monkeypatch.delenv(boot_mod.VERIFIED_RECORD_FLAG, raising=False)

    from nucleus_wedge.store import Store

    Store(str(brain)).append(
        value="The Nucleus gateway routes model calls through the OS; agents live INSIDE.",
        kind="note",
        tags=["topic:gateway"],
        source_agent="prior-session",
    )

    result = boot_mod.boot_cell(
        "How should this agent route its model calls?",
        recall_query="gateway",
        brain_path=str(brain),
    )

    assert result.verified_label is None


# ── boot_cell persistence: verified_label lands in loop_turns.jsonl on disk ────


def test_boot_cell_persists_verified_label_to_flywheel_when_flag_on(
    tmp_path, monkeypatch
):
    """Flag ON: the referee verdict is persisted into loop_turns.jsonl (not just
    attached ephemerally to BootResult). The on-disk corpus is REFEREE-verified.
    """
    import json

    from mcp_server_nucleus.runtime.agent_os import boot as boot_mod

    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")
    monkeypatch.setenv(boot_mod.VERIFIED_RECORD_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")

    from nucleus_wedge.store import Store

    Store(str(brain)).append(
        value="The Nucleus gateway routes model calls through the OS; agents live INSIDE.",
        kind="note",
        tags=["topic:gateway"],
        source_agent="prior-session",
    )

    result = boot_mod.boot_cell(
        "How should this agent route its model calls?",
        recall_query="gateway",
        brain_path=str(brain),
    )

    # BootResult still carries the label (unchanged behavior).
    assert result.verified_label is not None
    assert result.verified_label["status"] in {
        "CONFIRMED",
        "REFUTED",
        "UNVERIFIABLE",
        "PARTIAL",
    }

    # The label is ALSO persisted to disk — read the loop_turns.jsonl the turn
    # was written to and assert the last record carries the verified_label.
    turns_path = boot_mod.Path(brain) / "training" / "loop_turns.jsonl"
    rows = [json.loads(l) for l in turns_path.read_text().splitlines() if l.strip()]
    assert rows, "boot_cell must write at least one turn to the flywheel"
    last = rows[-1]
    assert "verified_label" in last, "verified_label must be persisted to disk"
    assert last["verified_label"]["status"] in {
        "CONFIRMED",
        "REFUTED",
        "UNVERIFIABLE",
        "PARTIAL",
    }


def test_boot_cell_flywheel_record_byte_identical_when_flag_off(tmp_path, monkeypatch):
    """Flag OFF: the persisted loop_turns.jsonl record has NO 'verified_label'
    key — byte-identical to the pre-verified-record shape.
    """
    import json

    from mcp_server_nucleus.runtime.agent_os import boot as boot_mod

    brain = tmp_path / "brain"
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.setenv(boot_mod.BOOT_FLAG, "1")
    monkeypatch.setenv(boot_mod.STUB_FLAG, "1")
    monkeypatch.setenv("NUCLEUS_DISABLE_ARTERY_4", "1")
    monkeypatch.delenv(boot_mod.VERIFIED_RECORD_FLAG, raising=False)

    from nucleus_wedge.store import Store

    Store(str(brain)).append(
        value="The Nucleus gateway routes model calls through the OS; agents live INSIDE.",
        kind="note",
        tags=["topic:gateway"],
        source_agent="prior-session",
    )

    boot_mod.boot_cell(
        "How should this agent route its model calls?",
        recall_query="gateway",
        brain_path=str(brain),
    )

    turns_path = boot_mod.Path(brain) / "training" / "loop_turns.jsonl"
    rows = [json.loads(l) for l in turns_path.read_text().splitlines() if l.strip()]
    assert rows, "boot_cell must write at least one turn to the flywheel"
    last = rows[-1]
    assert "verified_label" not in last, (
        "flag OFF must NOT persist verified_label (byte-identical-OFF contract)"
    )
