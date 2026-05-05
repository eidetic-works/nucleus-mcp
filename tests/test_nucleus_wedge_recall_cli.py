"""Recall CLI tests — SQLite-backed recall over memories.db.

Uses NUCLEUS_BRAIN_PATH monkeypatch fixture, mirroring the memories tests.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def fake_brain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "engrams" / "history.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    return brain


def _write_history(brain: Path, records: list[dict]) -> None:
    path = brain / "engrams" / "history.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")


def _record(value: str, *, key: str = "k", context: str = "note",
            source_agent: str = "nucleus-wedge",
            timestamp: str = "2026-04-20T10:00:00+00:00") -> dict:
    return {
        "key": key,
        "op_type": "ADD",
        "timestamp": timestamp,
        "snapshot": {
            "key": key,
            "value": value,
            "context": context,
            "intensity": 5,
            "version": 1,
            "source_agent": source_agent,
            "op_type": "ADD",
            "timestamp": timestamp,
            "deleted": False,
            "signature": None,
        },
    }


def test_recall_empty_query_returns_usage_error(fake_brain: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    rc = do_recall("   ", limit=5, source_filter=None, brain_path_arg=None)
    assert rc == 2
    err = capsys.readouterr().err
    assert "non-empty" in err


def test_recall_cold_start_builds_and_queries(fake_brain: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [
        _record("alpha beta gamma", timestamp="2026-04-19T10:00:00+00:00"),
        _record("beta only", timestamp="2026-04-20T10:00:00+00:00"),
    ])

    rc = do_recall("beta", limit=5, source_filter=None, brain_path_arg=None)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    texts = [row["text"] for row in payload]
    assert texts == ["beta only", "alpha beta gamma"]


def test_recall_is_case_insensitive(fake_brain: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [_record("Compounding Shape Anti-Pattern")])

    rc = do_recall("COMPOUNDING", limit=5, source_filter=None, brain_path_arg=None)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["text"] == "Compounding Shape Anti-Pattern"


def test_recall_matches_tags(fake_brain: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [
        _record("unrelated body", context="note [#sidecar-index]"),
        _record("other body", context="note"),
    ])

    rc = do_recall("sidecar", limit=5, source_filter=None, brain_path_arg=None)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["text"] for row in payload] == ["unrelated body"]


def test_recall_honors_limit(fake_brain: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [
        _record("match one", timestamp="2026-04-18T10:00:00+00:00"),
        _record("match two", timestamp="2026-04-19T10:00:00+00:00"),
        _record("match three", timestamp="2026-04-20T10:00:00+00:00"),
    ])

    rc = do_recall("match", limit=2, source_filter=None, brain_path_arg=None)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["text"] for row in payload] == ["match three", "match two"]


def test_recall_source_filter_isolates_auto_memory(fake_brain: Path, tmp_path: Path,
                                                    capsys: pytest.CaptureFixture[str]) -> None:
    from nucleus_wedge.memories import build_auto_memory_index, build_memories_index
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [_record("history says alpha")])
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    (mem_dir / "alpha.md").write_text(
        "---\nname: alpha\ntype: user\ndescription: alpha desc\n---\n\nauto memory alpha body\n",
        encoding="utf-8",
    )
    build_memories_index()
    build_auto_memory_index(memory_root=mem_dir)

    rc = do_recall("alpha", limit=5, source_filter="auto_memory", brain_path_arg=None)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    sources = {row["source"] for row in payload}
    assert sources == {"auto_memory"}


def test_recall_warm_path_does_not_rebuild(fake_brain: Path, monkeypatch: pytest.MonkeyPatch,
                                            capsys: pytest.CaptureFixture[str]) -> None:
    from nucleus_wedge import recall_cmd
    from nucleus_wedge.memories import build_memories_index

    _write_history(fake_brain, [_record("warmup row")])
    build_memories_index()

    calls: list[str] = []
    monkeypatch.setattr(recall_cmd, "build_memories_index",
                        lambda *a, **k: calls.append("history") or fake_brain / "memories.db")
    monkeypatch.setattr(recall_cmd, "build_auto_memory_index",
                        lambda *a, **k: calls.append("auto") or fake_brain / "memories.db")

    rc = recall_cmd.do_recall("warmup", limit=5, source_filter=None, brain_path_arg=None)
    assert rc == 0
    assert calls == []
    payload = json.loads(capsys.readouterr().out)
    assert [row["text"] for row in payload] == ["warmup row"]


def test_recall_no_match_returns_empty_list(fake_brain: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [_record("nothing to see here")])

    rc = do_recall("xyzzy", limit=5, source_filter=None, brain_path_arg=None)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == []


def test_cli_recall_subcommand_wires_through(fake_brain: Path,
                                              capsys: pytest.CaptureFixture[str]) -> None:
    from nucleus_wedge.__main__ import main

    _write_history(fake_brain, [_record("cli wiring verified")])

    rc = main(["recall", "--query", "wiring", "--limit", "3"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["text"] for row in payload] == ["cli wiring verified"]
