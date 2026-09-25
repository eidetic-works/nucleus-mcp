"""Per ADR-0033 v3 §C: `recall_activity` MCP wrapper composes tags correctly,
normalizes the role alias, returns the expected dict shape.
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
    return brain


def _write_history(brain: Path, records: list[dict]) -> None:
    path = brain / "engrams" / "history.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _record(value: str, *, key: str = "k", context: str = "activity",
            timestamp: str = "2026-05-30T10:00:00+00:00") -> dict:
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
            "source_agent": "nucleus-wedge",
            "op_type": "ADD",
            "timestamp": timestamp,
            "deleted": False,
            "signature": None,
        },
    }


def test_recall_activity_returns_expected_shape(fake_brain) -> None:
    from nucleus_wedge.memories import recall_activity

    _write_history(fake_brain, [
        _record("ship report 1", key="a",
                context="activity [#role:coordinator,domain:tb-endpoint]"),
    ])
    out = recall_activity(role="coordinator", domain="tb-endpoint", since="365d", limit=5)
    assert set(out.keys()) == {"role", "domain", "since", "results"}
    assert out["role"] == "coordinator"
    assert out["domain"] == "tb-endpoint"
    assert out["since"] == "365d"
    assert len(out["results"]) == 1
    assert out["results"][0]["text"] == "ship report 1"


def test_recall_activity_normalizes_role_alias(fake_brain) -> None:
    from nucleus_wedge.memories import recall_activity

    _write_history(fake_brain, [
        _record("main work", key="a",
                context="activity [#role:coordinator,domain:tb-endpoint]"),
        _record("peer work", key="b",
                context="activity [#role:worker,domain:audit]"),
    ])
    # `cc_main` alias must canonicalize to `coordinator` and return the matching engram.
    out = recall_activity(role="cc_main", since="365d", limit=5)
    assert out["role"] == "coordinator"
    texts = [r["text"] for r in out["results"]]
    assert texts == ["main work"]


def test_recall_activity_no_domain_returns_all_for_role(fake_brain) -> None:
    from nucleus_wedge.memories import recall_activity

    _write_history(fake_brain, [
        _record("a", key="a",
                context="activity [#role:coordinator,domain:tb-endpoint]"),
        _record("b", key="b",
                context="activity [#role:coordinator,domain:audit]"),
        _record("c", key="c",
                context="activity [#role:worker,domain:tb-endpoint]"),
    ])
    out = recall_activity(role="coordinator", domain=None, since="365d", limit=10)
    texts = sorted(r["text"] for r in out["results"])
    assert texts == ["a", "b"]
