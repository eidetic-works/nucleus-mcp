"""Comprehensive tests for runtime/vector_store.py — VectorStore, LocalSQLiteStore."""
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.vector_store import LocalSQLiteStore, VectorStore


# ── LocalSQLiteStore ─────────────────────────────────────────────

class TestLocalSQLiteStore:
    def test_init_creates_db(self, tmp_path):
        db_path = tmp_path / "memory.db"
        store = LocalSQLiteStore(db_path)
        assert store.db_path == db_path
        assert db_path.exists()

    def test_init_idempotent(self, tmp_path):
        db_path = tmp_path / "memory.db"
        store1 = LocalSQLiteStore(db_path)
        store2 = LocalSQLiteStore(db_path)
        # Both should work without error
        assert store2.db_path == db_path

    def test_store_returns_id(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        doc_id = store.store("hello world", {"tag": "test"})
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0

    def test_store_persists_content(self, tmp_path):
        db_path = tmp_path / "memory.db"
        store = LocalSQLiteStore(db_path)
        doc_id = store.store("hello world", {"tag": "test"})
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (doc_id,)).fetchone()
            assert row["content"] == "hello world"
            assert json.loads(row["metadata"]) == {"tag": "test"}

    def test_store_multiple(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        id1 = store.store("content1", {"a": 1})
        id2 = store.store("content2", {"b": 2})
        assert id1 != id2

    def test_search_finds_matches(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.store("hello world", {"tag": "greeting"})
        store.store("goodbye world", {"tag": "farewell"})
        results = store.search("hello", limit=10)
        assert len(results) == 1
        assert results[0]["content"] == "hello world"
        assert results[0]["metadata"] == {"tag": "greeting"}
        assert results[0]["score"] == 1.0

    def test_search_no_matches(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.store("hello world", {"tag": "greeting"})
        results = store.search("nonexistent", limit=10)
        assert results == []

    def test_search_limit(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        for i in range(5):
            store.store(f"item_{i}", {"idx": i})
        results = store.search("item", limit=2)
        assert len(results) == 2

    def test_search_empty_db(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        results = store.search("anything", limit=10)
        assert results == []

    def test_search_partial_match(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.store("the quick brown fox", {"tag": "animal"})
        results = store.search("quick", limit=10)
        assert len(results) == 1

    def test_search_returns_id(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        doc_id = store.store("test content", {"k": "v"})
        results = store.search("test", limit=10)
        assert results[0]["id"] == doc_id


# ── VectorStore (local mode) ─────────────────────────────────────

class TestVectorStoreLocal:
    def test_init_local_mode(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_STORAGE_TYPE", "local")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        vs = VectorStore()
        assert vs.enabled is False
        assert vs.llm is None
        assert vs.local_store is not None
        assert vs.collection_name == "nucleus_memory"

    def test_init_local_creates_db(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_STORAGE_TYPE", "local")
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
        vs = VectorStore()
        assert (tmp_path / "memory.db").exists()


# ── LocalSQLiteStore.store_memory / search_memory ────────────────
# Note: store_memory and search_memory are defined on LocalSQLiteStore
# but reference VectorStore attributes (self.enabled, self.local_store).
# We test them by attaching the needed attributes.

class TestLocalSQLiteStoreMemory:
    def test_store_memory_local_mode(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        # Attach VectorStore-like attributes
        store.enabled = False
        store.local_store = store  # self-reference for local fallback
        doc_id = store.store_memory("test content", {"tag": "test"})
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0

    def test_store_memory_local_no_metadata(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = False
        store.local_store = store
        doc_id = store.store_memory("test content")
        assert isinstance(doc_id, str)

    def test_store_memory_local_none_metadata(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = False
        store.local_store = store
        doc_id = store.store_memory("test content", None)
        assert isinstance(doc_id, str)

    def test_search_memory_local(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = False
        store.local_store = store
        store.store_memory("hello world", {"tag": "greeting"})
        results = store.search_memory("hello", limit=5)
        assert len(results) == 1
        assert results[0]["content"] == "hello world"

    def test_search_memory_local_no_results(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = False
        store.local_store = store
        results = store.search_memory("nonexistent", limit=5)
        assert results == []

    def test_search_memory_local_default_limit(self, tmp_path):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = False
        store.local_store = store
        store.store_memory("test content", {})
        results = store.search_memory("test")
        assert len(results) == 1


# ── LocalSQLiteStore.store_memory / search_memory (firestore mode — mocked) ──

class TestStoreMemoryFirestore:
    def test_store_memory_firestore_success(self, tmp_path, monkeypatch):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = True
        store.collection_name = "nucleus_memory"
        mock_llm = MagicMock()
        mock_llm.embed_content.return_value = {"embedding": [0.1, 0.2, 0.3]}
        store.llm = mock_llm

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "firestore_doc_123"
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with patch("mcp_server_nucleus.runtime.vector_store.get_firestore_client", return_value=mock_db):
            doc_id = store.store_memory("test content", {"tag": "test"})
            assert doc_id == "firestore_doc_123"
            mock_llm.embed_content.assert_called_once()
            mock_doc_ref.set.assert_called_once()

    def test_store_memory_firestore_no_embedding(self, tmp_path, monkeypatch):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = True
        store.collection_name = "nucleus_memory"
        mock_llm = MagicMock()
        mock_llm.embed_content.return_value = {"embedding": []}
        store.llm = mock_llm

        with patch("mcp_server_nucleus.runtime.vector_store.get_firestore_client"):
            with pytest.raises(ValueError, match="Failed to generate embedding"):
                store.store_memory("test", {})

    def test_store_memory_firestore_exception(self, tmp_path, monkeypatch):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = True
        store.collection_name = "nucleus_memory"
        mock_llm = MagicMock()
        mock_llm.embed_content.side_effect = Exception("API error")
        store.llm = mock_llm

        with pytest.raises(Exception, match="API error"):
            store.store_memory("test", {})

    def test_search_memory_firestore_success(self, tmp_path, monkeypatch):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = True
        store.collection_name = "nucleus_memory"
        mock_llm = MagicMock()
        mock_llm.embed_content.return_value = {"embedding": [0.1, 0.2]}
        store.llm = mock_llm

        mock_doc = MagicMock()
        mock_doc.id = "doc1"
        mock_doc.to_dict.return_value = {
            "content": "hello",
            "metadata": {"tag": "test"},
        }
        mock_vector_query = MagicMock()
        mock_vector_query.get.return_value = [mock_doc]
        mock_collection = MagicMock()
        mock_collection.find_nearest.return_value = mock_vector_query
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with patch("mcp_server_nucleus.runtime.vector_store.get_firestore_client", return_value=mock_db):
            results = store.search_memory("hello", limit=5)
            assert len(results) == 1
            assert results[0]["content"] == "hello"
            assert results[0]["id"] == "doc1"

    def test_search_memory_firestore_no_embedding(self, tmp_path, monkeypatch):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = True
        store.collection_name = "nucleus_memory"
        mock_llm = MagicMock()
        mock_llm.embed_content.return_value = {"embedding": []}
        store.llm = mock_llm

        results = store.search_memory("hello")
        assert results == []

    def test_search_memory_firestore_exception(self, tmp_path, monkeypatch):
        store = LocalSQLiteStore(tmp_path / "memory.db")
        store.enabled = True
        store.collection_name = "nucleus_memory"
        mock_llm = MagicMock()
        mock_llm.embed_content.side_effect = Exception("search error")
        store.llm = mock_llm

        results = store.search_memory("hello")
        assert results == []


# ── Move 2 batch 5: SoR read-model repoint (flag-ON, STRICT) ─────
# These adapt the store to its flag-ON delegation contract. They are STRICT:
# a broken delegation (no SoR mirror on capture, no SoR union on search, or a
# no-op index sink) makes each assertion fail — there is no `or True` escape.

class TestVectorStoreSoRFlagOn:
    def _local_store(self, tmp_path):
        """A LocalSQLiteStore wired like the VectorStore local mode (self is the
        vector store: enabled=False, local_store=self) so store_memory /
        search_memory run their real bodies."""
        (tmp_path / ".brain").mkdir(parents=True, exist_ok=True)
        store = LocalSQLiteStore(tmp_path / ".brain" / "memory.db")
        store.enabled = False
        store.local_store = store
        return store

    def _sor_count(self, tmp_path):
        from mcp_server_nucleus.memory.sor import SorStore
        return SorStore(tmp_path / ".brain" / "engrams.db").count()

    def test_store_memory_flag_on_mirrors_to_sor(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "1")
        store = self._local_store(tmp_path)
        assert self._sor_count(tmp_path) == 0
        doc_id = store.store_memory("mirror me to the SoR", {"tag": "x"})
        assert isinstance(doc_id, str) and doc_id  # legacy index write still returns id
        # STRICT: the capture must have been mirrored into the authoritative SoR.
        assert self._sor_count(tmp_path) == 1

    def test_store_memory_flag_off_does_not_mirror(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "")
        store = self._local_store(tmp_path)
        store.store_memory("no mirror", {})
        # STRICT: flag-OFF is byte-for-byte legacy — the SoR db is never created.
        assert not (tmp_path / ".brain" / "engrams.db").exists()

    def test_search_memory_flag_on_unions_sor(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "1")
        store = self._local_store(tmp_path)
        # A doc only in the SoR (never written to the local memory.db sink).
        from mcp_server_nucleus.memory.facade import MemoryFacade
        MemoryFacade(brain_path=tmp_path / ".brain", enabled=True).capture(
            "memory", "sorexclusive alpha token", kind="note"
        )
        results = store.search_memory("sorexclusive", limit=5)
        contents = [r.get("content") for r in results]
        # STRICT: the SoR-only doc is surfaced only if search delegates to recall.
        assert any("sorexclusive alpha token" == c for c in contents), contents

    def test_search_memory_flag_off_ignores_sor(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "1")
        store = self._local_store(tmp_path)
        from mcp_server_nucleus.memory.facade import MemoryFacade
        MemoryFacade(brain_path=tmp_path / ".brain", enabled=True).capture(
            "memory", "sorexclusive beta token", kind="note"
        )
        monkeypatch.setenv("NUCLEUS_MEMORY_SOR", "")
        results = store.search_memory("sorexclusive", limit=5)
        # STRICT: flag-OFF must NOT reach the SoR — the local sink has no such doc.
        assert results == []

    def test_index_sink_writes_local(self, tmp_path, monkeypatch):
        # VectorStore.index best-effort sink -> local_store.store in local mode.
        (tmp_path / ".brain").mkdir(parents=True, exist_ok=True)
        vs = VectorStore.__new__(VectorStore)
        vs.enabled = False
        vs.llm = None
        vs.collection_name = "nucleus_memory"
        vs.local_store = LocalSQLiteStore(tmp_path / ".brain" / "memory.db")
        sink_id = vs.index("id-1", "indexed sink text", metadata={"k": "v"})
        assert isinstance(sink_id, str) and sink_id
        # STRICT: the text is retrievable from the local index the sink wrote to.
        hits = vs.local_store.search("indexed", limit=5)
        assert any("indexed sink text" == h["content"] for h in hits)

    def test_index_sink_best_effort_swallows_errors(self, tmp_path):
        vs = VectorStore.__new__(VectorStore)
        vs.enabled = False
        vs.llm = None
        vs.collection_name = "nucleus_memory"
        vs.local_store = None  # no sink -> index returns None, never raises
        assert vs.index("id", "text") is None
