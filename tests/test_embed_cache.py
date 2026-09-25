"""Tests for the embedding cache in _embed (fw-1786020758).

Verifies that repeated calls to _embed with the same text skip the
Ollama round-trip by returning the cached embedding.
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# providers/brain_rag.py lives at the repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


class TestEmbedCache:
    def test_repeated_call_hits_cache(self):
        """A second call with the same text does not call Ollama."""
        from providers.brain_rag import _embed, _EMBED_CACHE
        _EMBED_CACHE.clear()  # start fresh

        fake_embedding = [0.1, 0.2, 0.3]
        call_count = [0]

        def fake_urlopen(req, timeout=30):
            call_count[0] += 1
            resp = MagicMock()
            resp.read.return_value = '{"embeddings": [[0.1, 0.2, 0.3]]}'
            return resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            r1 = _embed("test query")
            r2 = _embed("test query")

        assert r1 == fake_embedding
        assert r2 == fake_embedding
        assert call_count[0] == 1  # Ollama called only once

    def test_different_queries_both_call_ollama(self):
        """Different texts produce different cache entries."""
        from providers.brain_rag import _embed, _EMBED_CACHE
        _EMBED_CACHE.clear()

        call_count = [0]
        def fake_urlopen(req, timeout=30):
            call_count[0] += 1
            resp = MagicMock()
            resp.read.return_value = '{"embeddings": [[0.1, 0.2, 0.3]]}'
            return resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _embed("query A")
            _embed("query B")

        assert call_count[0] == 2  # both called Ollama

    def test_cache_eviction_at_max(self):
        """Cache evicts oldest entry when at max capacity."""
        from providers.brain_rag import _embed, _EMBED_CACHE, _EMBED_CACHE_MAX
        _EMBED_CACHE.clear()

        def fake_urlopen(req, timeout=30):
            resp = MagicMock()
            resp.read.return_value = '{"embeddings": [[0.1]]}'
            return resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            for i in range(_EMBED_CACHE_MAX + 5):
                _embed(f"query_{i}")

        assert len(_EMBED_CACHE) <= _EMBED_CACHE_MAX

    def test_long_text_truncated_for_cache_key(self):
        """Text longer than 8000 chars is truncated for the cache key."""
        from providers.brain_rag import _embed, _EMBED_CACHE
        _EMBED_CACHE.clear()

        call_count = [0]
        def fake_urlopen(req, timeout=30):
            call_count[0] += 1
            resp = MagicMock()
            resp.read.return_value = '{"embeddings": [[0.1]]}'
            return resp

        long_text = "a" * 9000
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _embed(long_text)
            _embed(long_text[:8000])  # same cache key after truncation

        assert call_count[0] == 1  # second call hit cache
