"""Integration test for the ``nucleus`` wedge (remember/recall over engrams/history.jsonl).

Uses ``tmp_path`` to avoid touching the real repo ``.brain/`` substrate.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fake_brain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    brain = tmp_path / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "memory").mkdir(parents=True)
    (brain / "engrams" / "history.jsonl").write_text("", encoding="utf-8")
    (brain / "memory" / "engrams.json").write_text(
        json.dumps(
            [
                {
                    "key": "welcome_nucleus",
                    "value": "Nucleus is your sovereign Agent OS. It remembers what you decided across every AI tool you use.",
                    "context": "Feature",
                    "intensity": 8,
                    "timestamp": "2026-03-30T10:33:04.079346Z",
                    "source": "recipe:Founder OS",
                },
                {
                    "key": "workflow_founder",
                    "value": "Your daily loop: nucleus morning brief, work in any IDE, nucleus combo pulse end-of-day.",
                    "context": "Strategy",
                    "intensity": 9,
                    "timestamp": "2026-03-30T10:33:04.079346Z",
                    "source": "recipe:Founder OS",
                },
                {
                    "key": "quick_reference",
                    "value": "Top commands: nucleus morning-brief, nucleus combo pulse, nucleus engrams search, nucleus status.",
                    "context": "Feature",
                    "intensity": 7,
                    "timestamp": "2026-03-30T10:33:04.079346Z",
                    "source": "recipe:Founder OS",
                },
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
    return brain


def test_ensure_seeds_is_idempotent(fake_brain: Path) -> None:
    from nucleus_wedge.seed import SEED_KEYS, ensure_seeds
    from nucleus_wedge.store import Store

    first_write = ensure_seeds()
    assert sorted(first_write) == sorted(SEED_KEYS)

    store = Store()
    keys_after_first = store.keys_present()
    for k in SEED_KEYS:
        assert k in keys_after_first

    second_write = ensure_seeds()
    assert second_write == []

    rows_count = sum(1 for _ in store.rows())
    assert rows_count == len(SEED_KEYS)


def test_append_increments_row_count(fake_brain: Path) -> None:
    from nucleus_wedge.seed import ensure_seeds
    from nucleus_wedge.store import Store

    ensure_seeds()
    store = Store()
    before = sum(1 for _ in store.rows())

    result = store.append("remembered via MCP", kind="decision")
    assert result["key"]
    assert result["timestamp"]

    after = sum(1 for _ in store.rows())
    assert after == before + 1


def test_recall_morning_brief_surfaces_workflow_founder(fake_brain: Path) -> None:
    from nucleus_wedge import bm25
    from nucleus_wedge.seed import ensure_seeds
    from nucleus_wedge.store import Store

    ensure_seeds()
    results = bm25.search(Store(), query="morning brief", limit=3)
    top_keys = [r["key"] for r in results]
    assert "workflow_founder" in top_keys


def test_recall_engrams_search_surfaces_quick_reference(fake_brain: Path) -> None:
    from nucleus_wedge import bm25
    from nucleus_wedge.seed import ensure_seeds
    from nucleus_wedge.store import Store

    ensure_seeds()
    results = bm25.search(Store(), query="engrams search", limit=3)
    top_keys = [r["key"] for r in results]
    assert "quick_reference" in top_keys
