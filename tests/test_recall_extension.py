"""Per ADR-0033 v3 §A: structured filters (kind / tags / since), empty-query
allowed when at least one filter is present, full backward compat with the
legacy query-only call.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture
def fake_brain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "engrams" / "history.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    # Isolate auto-memory: point to empty tmp dir so build_auto_memory_index
    # doesn't pick up real ~/.claude/projects/<slug>/memory/*.md files
    empty_mem = tmp_path / "empty_auto_memory"
    empty_mem.mkdir()
    monkeypatch.setattr(
        "nucleus_wedge.memories.default_auto_memory_root", lambda: empty_mem
    )
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


def test_kind_filter_returns_only_matching(fake_brain, capsys) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [
        _record("shipped PR 123", key="a",
                context="activity [#role:main,domain:tb-endpoint]"),
        _record("a regular note", key="b", context="note"),
        _record("another activity", key="c",
                context="activity [#role:peer,domain:audit]"),
    ])

    rc = do_recall(query="", limit=10, kind="activity")
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    texts = sorted(r["text"] for r in payload)
    assert texts == ["another activity", "shipped PR 123"]


def test_tags_filter_substring_match(fake_brain, capsys) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [
        _record("main work", key="a",
                context="activity [#role:main,domain:tb-endpoint]"),
        _record("peer work", key="b",
                context="activity [#role:peer,domain:audit]"),
        _record("main audit", key="c",
                context="activity [#role:main,domain:audit]"),
    ])

    rc = do_recall(query="", limit=10, kind="activity", tags=["role:main"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    texts = sorted(r["text"] for r in payload)
    assert texts == ["main audit", "main work"]


def test_multiple_tags_compose_with_and(fake_brain, capsys) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [
        _record("main endpoint", key="a",
                context="activity [#role:main,domain:tb-endpoint]"),
        _record("peer endpoint", key="b",
                context="activity [#role:peer,domain:tb-endpoint]"),
        _record("main audit", key="c",
                context="activity [#role:main,domain:audit]"),
    ])

    rc = do_recall(
        query="", limit=10, kind="activity",
        tags=["role:main", "domain:tb-endpoint"],
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    texts = [r["text"] for r in payload]
    assert texts == ["main endpoint"]


def test_since_filter_relative_window(fake_brain, capsys) -> None:
    from nucleus_wedge.recall_cmd import do_recall
    from nucleus_wedge.memories import _parse_since

    now = datetime.now(timezone.utc)
    _write_history(fake_brain, [
        _record("recent", key="a", context="activity [#role:main]",
                timestamp=(now - timedelta(hours=2)).isoformat()),
        _record("ancient", key="b", context="activity [#role:main]",
                timestamp=(now - timedelta(days=400)).isoformat()),
    ])

    since = _parse_since("30d")
    rc = do_recall(query="", limit=10, kind="activity", since=since)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    texts = [r["text"] for r in payload]
    assert texts == ["recent"]


def test_empty_query_without_filter_errors(fake_brain, capsys) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    rc = do_recall(query="   ", limit=5)
    assert rc == 2
    err = capsys.readouterr().err
    assert "non-empty" in err


def test_empty_query_with_structured_filter_ok(fake_brain, capsys) -> None:
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [
        _record("the engram", key="a", context="activity [#role:main]"),
    ])
    rc = do_recall(query="", limit=5, kind="activity")
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1


def test_backward_compat_query_only_still_works(fake_brain, capsys) -> None:
    """Legacy positional call signature must stay green."""
    from nucleus_wedge.recall_cmd import do_recall

    _write_history(fake_brain, [
        _record("alpha beta gamma"),
        _record("beta only", key="b"),
    ])
    rc = do_recall("beta", limit=5, source_filter=None, brain_path_arg=None)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    texts = sorted(r["text"] for r in payload)
    assert texts == ["alpha beta gamma", "beta only"]
