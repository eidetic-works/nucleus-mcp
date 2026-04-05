"""
Tests for Engram Cache — In-memory index with mtime invalidation
================================================================
"""

import json
import os
import time
import pytest
from pathlib import Path


@pytest.fixture
def brain_path(tmp_path):
    """Create a fresh isolated brain directory for each test."""
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    old = os.environ.get("NUCLEAR_BRAIN_PATH")
    os.environ["NUCLEAR_BRAIN_PATH"] = str(brain)
    yield brain
    if old is not None:
        os.environ["NUCLEAR_BRAIN_PATH"] = old
    else:
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)


@pytest.fixture
def ledger_path(brain_path):
    """Get the engram ledger path."""
    (brain_path / "engrams").mkdir(exist_ok=True)
    return brain_path / "engrams" / "ledger.jsonl"


def _write_ledger(path, engrams):
    with open(path, "w", encoding="utf-8") as f:
        for e in engrams:
            f.write(json.dumps(e) + "\n")


class TestEngramCache:
    def test_empty_ledger(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [])
        engrams, total = cache.query(ledger_path)
        assert total == 0
        assert engrams == []

    def test_query_loads_engrams(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "k1", "value": "v1", "context": "Feature", "intensity": 5},
            {"key": "k2", "value": "v2", "context": "Strategy", "intensity": 8},
        ])
        engrams, total = cache.query(ledger_path)
        assert total == 2

    def test_query_filters_by_context(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "k1", "value": "v1", "context": "Feature", "intensity": 5},
            {"key": "k2", "value": "v2", "context": "Strategy", "intensity": 8},
        ])
        engrams, total = cache.query(ledger_path, context="Feature")
        assert total == 1
        assert engrams[0]["key"] == "k1"

    def test_query_filters_by_intensity(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "low", "value": "v", "context": "Feature", "intensity": 3},
            {"key": "high", "value": "v", "context": "Feature", "intensity": 9},
        ])
        engrams, total = cache.query(ledger_path, min_intensity=5)
        assert total == 1
        assert engrams[0]["key"] == "high"

    def test_excludes_deleted_and_quarantined(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "good", "value": "v", "context": "Feature", "intensity": 5},
            {"key": "del", "value": "v", "context": "Feature", "intensity": 5, "deleted": True},
            {"key": "quar", "value": "v", "context": "Feature", "intensity": 5, "quarantined": True},
        ])
        engrams, total = cache.query(ledger_path)
        assert total == 1

    def test_cache_reuses_on_same_mtime(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "k1", "value": "v", "context": "Feature", "intensity": 5},
        ])
        cache.query(ledger_path)
        load_count_1 = cache.stats["load_count"]
        cache.query(ledger_path)  # Should use cache
        load_count_2 = cache.stats["load_count"]
        assert load_count_2 == load_count_1

    def test_cache_reloads_on_file_change(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "k1", "value": "v", "context": "Feature", "intensity": 5},
        ])
        cache.query(ledger_path)
        load_count_1 = cache.stats["load_count"]

        # Modify file (ensure different mtime)
        time.sleep(0.05)
        _write_ledger(ledger_path, [
            {"key": "k1", "value": "v", "context": "Feature", "intensity": 5},
            {"key": "k2", "value": "v", "context": "Feature", "intensity": 5},
        ])
        engrams, total = cache.query(ledger_path)
        assert total == 2
        assert cache.stats["load_count"] > load_count_1

    def test_invalidate_forces_reload(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "k1", "value": "v", "context": "Feature", "intensity": 5},
        ])
        cache.query(ledger_path)
        load_count_1 = cache.stats["load_count"]
        cache.invalidate()
        cache.query(ledger_path)
        assert cache.stats["load_count"] > load_count_1

    def test_search_matches_key_and_value(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "auth_module", "value": "handles login", "context": "Feature", "intensity": 5},
            {"key": "db_module", "value": "auth backend", "context": "Architecture", "intensity": 7},
        ])
        matches, total = cache.search(ledger_path, "auth")
        assert total == 2
        for m in matches:
            assert "_match_in" in m

    def test_search_case_sensitive(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "API_Gateway", "value": "v", "context": "Feature", "intensity": 5},
        ])
        matches, _ = cache.search(ledger_path, "api_gateway", case_sensitive=True)
        assert len(matches) == 0
        matches, _ = cache.search(ledger_path, "API_Gateway", case_sensitive=True)
        assert len(matches) == 1

    def test_get_by_key(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "target", "value": "found", "context": "Feature", "intensity": 5},
        ])
        result = cache.get_by_key(ledger_path, "target")
        assert result is not None
        assert result["value"] == "found"

    def test_get_by_key_not_found(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [])
        assert cache.get_by_key(ledger_path, "missing") is None

    def test_stats(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        _write_ledger(ledger_path, [
            {"key": "k1", "value": "v", "context": "Feature", "intensity": 5},
            {"key": "k2", "value": "v", "context": "Strategy", "intensity": 8},
        ])
        cache.query(ledger_path)
        stats = cache.stats
        assert stats["cached_engrams"] == 2
        assert stats["unique_keys"] == 2
        assert "feature" in stats["contexts"]
        assert "strategy" in stats["contexts"]

    def test_skips_corrupted_lines(self, ledger_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        with open(ledger_path, "w") as f:
            f.write('{"key":"good","value":"v","context":"Feature","intensity":5}\n')
            f.write('CORRUPTED\n')
            f.write('{"key":"also_good","value":"v","context":"Feature","intensity":5}\n')
        engrams, total = cache.query(ledger_path)
        assert total == 2

    def test_nonexistent_file(self, brain_path):
        from mcp_server_nucleus.runtime.engram_cache import EngramCache
        cache = EngramCache()
        fake_path = brain_path / "nonexistent" / "ledger.jsonl"
        engrams, total = cache.query(fake_path)
        assert total == 0

    def test_global_singleton(self):
        from mcp_server_nucleus.runtime.engram_cache import get_engram_cache
        c1 = get_engram_cache()
        c2 = get_engram_cache()
        assert c1 is c2
