"""Dual-source-on-read tests for EngramCache.search_dual.

Per Cowork directive d70e01bf: read-side fix for store divergence
(write-side projection lands in history.jsonl, read-side previously only
scanned ledger.jsonl). search_dual reads both, normalizes Store-shape
records to ledger shape, dedups by key (ledger-wins), tags every result
with a 'source' field.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / ".brain" / "engrams"
    b.mkdir(parents=True)
    return b


@pytest.fixture
def ledger_path(brain):
    return brain / "ledger.jsonl"


@pytest.fixture
def history_path(brain):
    return brain / "history.jsonl"


def _write_ledger(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _history_row(key: str, value: str, *, context: str = "Feature",
                 intensity: int = 5, source_agent: str = "auto_hook",
                 deleted: bool = False) -> dict:
    """Build a Store-shape history row matching real history.jsonl format."""
    ts = "2026-04-20T12:00:00.000000Z"
    return {
        "key": key,
        "op_type": "ADD",
        "timestamp": ts,
        "snapshot": {
            "key": key,
            "value": value,
            "context": context,
            "intensity": intensity,
            "version": 1,
            "source_agent": source_agent,
            "op_type": "ADD",
            "timestamp": ts,
            "deleted": deleted,
            "signature": None,
        },
    }


def _write_history(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


# ── _normalize_history_row (unit) ─────────────────────────────────────


def test_normalize_history_row_extracts_snapshot_fields():
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    row = _history_row("k1", "the value", context="Architecture", intensity=8)
    flat = EngramCache._normalize_history_row(row)
    assert flat["key"] == "k1"
    assert flat["value"] == "the value"
    assert flat["context"] == "Architecture"
    assert flat["intensity"] == 8
    assert flat["timestamp"] == "2026-04-20T12:00:00.000000Z"
    assert flat["source_agent"] == "auto_hook"


def test_normalize_history_row_drops_deleted():
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    row = _history_row("k1", "v", deleted=True)
    assert EngramCache._normalize_history_row(row) is None


def test_normalize_history_row_handles_missing_snapshot():
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    assert EngramCache._normalize_history_row({"key": "k1"}) is None
    assert EngramCache._normalize_history_row({"key": "k1", "snapshot": "bad"}) is None


def test_normalize_history_row_uses_outer_key_as_fallback():
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    row = {"key": "outer_key", "snapshot": {"value": "v", "context": "Feature",
                                             "intensity": 5}}
    flat = EngramCache._normalize_history_row(row)
    assert flat["key"] == "outer_key"


# ── search_dual (integration) ─────────────────────────────────────────


def test_search_dual_returns_only_ledger_when_history_empty(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "auth_login", "value": "OAuth flow", "context": "Feature", "intensity": 5},
    ])
    cache = EngramCache()
    matches, total = cache.search_dual(ledger_path, history_path, "auth")
    assert total == 1
    assert matches[0]["source"] == "ledger"
    assert matches[0]["key"] == "auth_login"


def test_search_dual_returns_only_history_when_ledger_empty(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_history(history_path, [
        _history_row("relay_projection_xyz", "auth audit topic discussed"),
    ])
    cache = EngramCache()
    matches, total = cache.search_dual(ledger_path, history_path, "auth")
    assert total == 1
    assert matches[0]["source"] == "history"
    assert matches[0]["key"] == "relay_projection_xyz"


def test_search_dual_merges_both_sources(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "k_ledger", "value": "the topic", "context": "Decision", "intensity": 7},
    ])
    _write_history(history_path, [
        _history_row("k_history", "topic in projection", intensity=4),
    ])
    cache = EngramCache()
    matches, total = cache.search_dual(ledger_path, history_path, "topic")
    assert total == 2
    sources = {m["source"] for m in matches}
    assert sources == {"ledger", "history"}


def test_search_dual_dedup_prefers_ledger_on_key_collision(ledger_path, history_path, caplog):
    import logging
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "shared_key", "value": "ledger version", "context": "Decision", "intensity": 9},
    ])
    _write_history(history_path, [
        _history_row("shared_key", "history version", intensity=4),
    ])
    cache = EngramCache()
    with caplog.at_level(logging.DEBUG, logger="nucleus.engram_cache"):
        matches, total = cache.search_dual(ledger_path, history_path, "version")
    assert total == 1
    assert matches[0]["value"] == "ledger version"
    assert matches[0]["source"] == "ledger"
    assert any("dedup" in r.message for r in caplog.records)


def test_search_dual_every_result_has_source_field(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "k1", "value": "match here", "context": "Feature", "intensity": 5},
        {"key": "k2", "value": "match again", "context": "Feature", "intensity": 5},
    ])
    _write_history(history_path, [
        _history_row("k3", "match in history"),
    ])
    cache = EngramCache()
    matches, _ = cache.search_dual(ledger_path, history_path, "match")
    assert len(matches) == 3
    for m in matches:
        assert m["source"] in ("ledger", "history")


def test_search_dual_preserves_match_in_field(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "auth", "value": "login flow", "context": "Feature", "intensity": 5},
    ])
    _write_history(history_path, [
        _history_row("relay_x", "auth projection"),
    ])
    cache = EngramCache()
    matches, _ = cache.search_dual(ledger_path, history_path, "auth")
    for m in matches:
        assert "_match_in" in m
        assert isinstance(m["_match_in"], list) and m["_match_in"]


def test_search_dual_case_sensitive(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "KEY1", "value": "Mixed Case", "context": "Feature", "intensity": 5},
    ])
    _write_history(history_path, [
        _history_row("key2", "lower case"),
    ])
    cache = EngramCache()
    cs_matches, _ = cache.search_dual(ledger_path, history_path, "Case", case_sensitive=True)
    assert len(cs_matches) == 1
    assert cs_matches[0]["key"] == "KEY1"

    ci_matches, _ = cache.search_dual(ledger_path, history_path, "case", case_sensitive=False)
    assert len(ci_matches) == 2


def test_search_dual_respects_limit(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": f"k{i}", "value": "match", "context": "Feature", "intensity": 5}
        for i in range(10)
    ])
    cache = EngramCache()
    matches, total = cache.search_dual(ledger_path, history_path, "match", limit=3)
    assert total == 10
    assert len(matches) == 3


def test_search_dual_handles_corrupted_history_lines(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    with history_path.open("w") as f:
        f.write(json.dumps(_history_row("k1", "good record")) + "\n")
        f.write("CORRUPTED LINE\n")
        f.write(json.dumps(_history_row("k2", "another good record")) + "\n")
    cache = EngramCache()
    matches, total = cache.search_dual(ledger_path, history_path, "good")
    assert total == 2


def test_search_dual_skips_deleted_history_records(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_history(history_path, [
        _history_row("alive", "still here"),
        _history_row("dead", "still here", deleted=True),
    ])
    cache = EngramCache()
    matches, total = cache.search_dual(ledger_path, history_path, "still here")
    assert total == 1
    assert matches[0]["key"] == "alive"


def test_search_dual_history_missing_file_is_safe(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "k1", "value": "v", "context": "Feature", "intensity": 5},
    ])
    cache = EngramCache()
    matches, total = cache.search_dual(ledger_path, history_path, "v")
    assert total == 1
    assert matches[0]["source"] == "ledger"


def test_search_dual_results_sorted_by_intensity_desc(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "low", "value": "match", "context": "Feature", "intensity": 2},
        {"key": "high", "value": "match", "context": "Feature", "intensity": 9},
    ])
    _write_history(history_path, [
        _history_row("mid", "match", intensity=5),
    ])
    cache = EngramCache()
    matches, _ = cache.search_dual(ledger_path, history_path, "match")
    intensities = [m.get("intensity") for m in matches]
    assert intensities == sorted(intensities, reverse=True)


# ── Cache invariants ─────────────────────────────────────────────────


def test_search_dual_independent_mtime_invalidation(ledger_path, history_path):
    """Changing ledger should not force a history reload, and vice-versa."""
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "k1", "value": "v", "context": "Feature", "intensity": 5},
    ])
    _write_history(history_path, [
        _history_row("h1", "v"),
    ])
    cache = EngramCache()
    cache.search_dual(ledger_path, history_path, "v")
    ledger_load_count_1 = cache.stats["load_count"]
    history_load_count_1 = cache.stats["history_load_count"]

    # Touch only ledger
    time.sleep(0.05)
    _write_ledger(ledger_path, [
        {"key": "k1", "value": "v", "context": "Feature", "intensity": 5},
        {"key": "k2", "value": "v", "context": "Feature", "intensity": 5},
    ])
    cache.search_dual(ledger_path, history_path, "v")
    assert cache.stats["load_count"] > ledger_load_count_1
    assert cache.stats["history_load_count"] == history_load_count_1

    # Touch only history
    time.sleep(0.05)
    _write_history(history_path, [
        _history_row("h1", "v"),
        _history_row("h2", "v"),
    ])
    ledger_load_count_2 = cache.stats["load_count"]
    cache.search_dual(ledger_path, history_path, "v")
    assert cache.stats["history_load_count"] > history_load_count_1
    assert cache.stats["load_count"] == ledger_load_count_2


def test_invalidate_clears_both_caches(ledger_path, history_path):
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [{"key": "k1", "value": "v", "context": "Feature", "intensity": 5}])
    _write_history(history_path, [_history_row("h1", "v")])
    cache = EngramCache()
    cache.search_dual(ledger_path, history_path, "v")
    cache.invalidate()
    cache.search_dual(ledger_path, history_path, "v")
    assert cache.stats["load_count"] >= 2
    assert cache.stats["history_load_count"] >= 2


# ── Existing single-source search regression ────────────────────────


def test_existing_search_unchanged_when_history_empty(ledger_path):
    """search() (single-source, ledger-only) must keep its prior contract."""
    from mcp_server_nucleus.runtime.engram_cache import EngramCache
    _write_ledger(ledger_path, [
        {"key": "k1", "value": "v1", "context": "Feature", "intensity": 5},
    ])
    cache = EngramCache()
    matches, total = cache.search(ledger_path, "v1")
    assert total == 1
    # 'source' field should NOT appear on legacy single-source path
    assert "source" not in matches[0]
