"""Tests for cache key normalization in search_brain (fw-1786032960).

Verifies that the cache key normalizes the query string so minor
variations (trailing whitespace, case differences) hit the same cache
entry instead of causing cache misses.
"""
import sys
import pytest
from pathlib import Path

# providers/brain_rag.py lives at the repo root, not inside mcp-server-nucleus
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


class TestCacheKeyNormalization:
    def test_whitespace_normalized(self):
        """Trailing/leading whitespace does not change the cache key."""
        from providers.brain_rag import _cache_key
        bp = Path("/tmp/brain")
        k1 = _cache_key("fix the bug", bp, topk=5)
        k2 = _cache_key("  fix the bug  ", bp, topk=5)
        assert k1 == k2

    def test_case_normalized(self):
        """Case differences do not change the cache key."""
        from providers.brain_rag import _cache_key
        bp = Path("/tmp/brain")
        k1 = _cache_key("Fix The Bug", bp, topk=5)
        k2 = _cache_key("fix the bug", bp, topk=5)
        assert k1 == k2

    def test_truncation(self):
        """Queries longer than 200 chars are truncated to the same key."""
        from providers.brain_rag import _cache_key
        bp = Path("/tmp/brain")
        long_query = "a" * 300
        k1 = _cache_key(long_query, bp, topk=5)
        k2 = _cache_key("a" * 200, bp, topk=5)
        # Both should produce the same key because the query is truncated
        assert k1 == k2

    def test_different_queries_still_different(self):
        """Genuinely different queries still produce different keys."""
        from providers.brain_rag import _cache_key
        bp = Path("/tmp/brain")
        k1 = _cache_key("fix the bug", bp, topk=5)
        k2 = _cache_key("fix the feature", bp, topk=5)
        assert k1 != k2

    def test_different_topk_different_key(self):
        """Different topk values produce different keys."""
        from providers.brain_rag import _cache_key
        bp = Path("/tmp/brain")
        k1 = _cache_key("fix the bug", bp, topk=5)
        k2 = _cache_key("fix the bug", bp, topk=10)
        assert k1 != k2

    def test_different_session_different_key(self):
        """Different session IDs produce different keys (session boost matters)."""
        from providers.brain_rag import _cache_key
        bp = Path("/tmp/brain")
        k1 = _cache_key("fix the bug", bp, topk=5, session_id="sess1")
        k2 = _cache_key("fix the bug", bp, topk=5, session_id="sess2")
        assert k1 != k2
