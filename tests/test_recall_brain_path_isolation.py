"""Regression test: brain_path_arg isolation in _do_recall_query.

Repro: ``_do_recall_query(brain_path_arg=<fresh empty temp brain>)`` returned
rows from the operator's global CC memory corpus instead of 0. Root cause:
``build_auto_memory_index`` ignored an explicitly-provided ``brain_path`` and
fell back to ``default_auto_memory_root()`` (CWD-based), cross-contaminating
an isolated brain with the global auto-memory corpus.

Fix: when ``brain_path`` is explicitly provided (and ``memory_root`` is not),
``build_auto_memory_index`` scopes the auto-memory root to
``<brain>/auto_memory`` instead of the CWD-based global root.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _make_brain(root: Path) -> Path:
    """Create a fresh empty brain under *root* and return its path."""
    brain = root / ".brain"
    (brain / "engrams").mkdir(parents=True)
    (brain / "engrams" / "history.jsonl").write_text("", encoding="utf-8")
    return brain


def _write_global_auto_memory(global_root: Path) -> None:
    """Populate *global_root* with a markdown auto-memory file."""
    global_root.mkdir(parents=True, exist_ok=True)
    (global_root / "leaked_feedback.md").write_text(
        "---\n"
        "type: feedback\n"
        "name: leaked\n"
        "description: should not appear in isolated brain\n"
        "---\n"
        "\n"
        "This row lives in the operator global corpus and must NOT leak\n"
        "into a fresh empty brain passed via brain_path_arg.\n",
        encoding="utf-8",
    )


def test_fresh_empty_brain_returns_zero_rows(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    """A fresh empty temp brain passed via brain_path_arg must return 0 rows,
    even when the operator's global auto-memory corpus has content.

    Before the fix, ``build_auto_memory_index`` ignored ``brain_path`` and
    read from ``default_auto_memory_root()`` (CWD-based global CC memory),
    so the isolated brain returned rows it should never have seen.
    """
    from nucleus_wedge.memories import default_auto_memory_root
    from nucleus_wedge.recall_cmd import _do_recall_query

    # Fresh empty brain — no history, no auto_memory subdir.
    brain = _make_brain(tmp_path / "isolated")

    # Simulate the operator's global CC memory corpus having content.
    global_root = tmp_path / "global_auto_memory"
    _write_global_auto_memory(global_root)
    monkeypatch.setattr(
        "nucleus_wedge.memories.default_auto_memory_root", lambda: global_root
    )
    assert global_root.exists(), "test setup: global corpus must exist"

    # Query with the explicit isolated brain path. The query term matches the
    # leaked auto-memory text, so any cross-contamination is visible.
    rows = _do_recall_query(
        query="leaked",
        limit=5,
        kind=None,
        tags=None,
        since=None,
        source_filter=None,
        brain_path_arg=str(brain),
    )

    assert rows == [], (
        f"brain_path isolation broken: fresh empty brain returned {len(rows)} "
        f"rows from the global auto-memory corpus"
    )


def test_brain_scoped_auto_memory_still_read(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-memory files placed under ``<brain>/auto_memory/`` ARE read when
    ``brain_path_arg`` is explicit — the fix scopes, it does not disable.

    This guards against an over-broad fix that drops auto-memory entirely on
    the explicit-brain path.
    """
    from nucleus_wedge.memories import default_auto_memory_root
    from nucleus_wedge.recall_cmd import _do_recall_query

    brain = _make_brain(tmp_path / "scoped")

    # Global corpus with content that must NOT leak.
    global_root = tmp_path / "global_auto_memory"
    _write_global_auto_memory(global_root)
    monkeypatch.setattr(
        "nucleus_wedge.memories.default_auto_memory_root", lambda: global_root
    )

    # Brain-scoped auto-memory that SHOULD be read.
    scoped_dir = brain / "auto_memory"
    scoped_dir.mkdir(parents=True, exist_ok=True)
    (scoped_dir / "scoped_note.md").write_text(
        "---\n"
        "type: feedback\n"
        "name: scoped\n"
        "description: should appear because it lives in the brain\n"
        "---\n"
        "\n"
        "This row lives inside the brain and must appear in recall.\n",
        encoding="utf-8",
    )

    rows = _do_recall_query(
        query="scoped",
        limit=5,
        kind=None,
        tags=None,
        since=None,
        source_filter=None,
        brain_path_arg=str(brain),
    )

    texts = [r.get("text", "") for r in rows]
    assert any("scoped" in t for t in texts), (
        f"brain-scoped auto-memory not read: rows={texts}"
    )
    # Global corpus must still not leak.
    assert not any("leaked" in t for t in texts), (
        f"global auto-memory leaked into scoped brain: rows={texts}"
    )


def test_no_brain_path_uses_global_auto_memory(tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """When ``brain_path_arg`` is None, the legacy ``default_auto_memory_root()``
    behavior is preserved — the fix must not change the default path.

    This guards the backward-compat contract: normal operation (no explicit
    brain path) still reads the CWD-based global CC memory corpus.
    """
    from nucleus_wedge import memories as mem_mod
    from nucleus_wedge.recall_cmd import _do_recall_query

    # Use the conftest-provided NUCLEUS_BRAIN_PATH brain (autouse fixture sets it).
    brain_env = Path(__import__("os").environ["NUCLEUS_BRAIN_PATH"])
    (brain_env / "engrams").mkdir(parents=True, exist_ok=True)
    (brain_env / "engrams" / "history.jsonl").write_text("", encoding="utf-8")

    # Point default_auto_memory_root at a temp dir with content.
    global_root = tmp_path / "global_auto_memory"
    _write_global_auto_memory(global_root)
    monkeypatch.setattr(
        "nucleus_wedge.memories.default_auto_memory_root", lambda: global_root
    )

    rows = _do_recall_query(
        query="leaked",
        limit=5,
        kind=None,
        tags=None,
        since=None,
        source_filter=None,
        brain_path_arg=None,
    )

    texts = [r.get("text", "") for r in rows]
    assert any("leaked" in t for t in texts), (
        f"default path lost global auto-memory: rows={texts}"
    )
