
import logging
import os
import time
from typing import List, Dict, Any
import sqlite3
import json
from pathlib import Path
from .llm_client import DualEngineLLM
from .storage import get_firestore_client, STORAGE_TYPE
from ..runtime.common import get_brain_path, open_hardened_sqlite

logger = logging.getLogger("nucleus.vector_store")

# --- Move 2 batch 5: flag-gated SoR read-model repoint ---------------------
# Self-contained env check (mirrors runtime/memory_pipeline.py::_sor_flag_on) so
# the flag-OFF path stays a byte-for-byte no-op and nothing from
# ``mcp_server_nucleus.memory`` is imported until the flag-ON branch. Under
# ``NUCLEUS_MEMORY_SOR`` the unified SoR (``MemoryFacade``) is authoritative for
# recall; this VectorStore degrades to a best-effort index sink + optional
# re-rank (LocalSQLiteStore local sink / Firestore KNN cloud re-rank — neither
# authoritative). Process-wide log-once latch so an additive SoR read/mirror
# failure degrades to the legacy vector path without log spam.
_SOR_FLAG = "NUCLEUS_MEMORY_SOR"
_SOR_TRUTHY = frozenset({"1", "true", "yes", "on"})
_sor_warned = False


def _sor_flag_on() -> bool:
    """True iff ``NUCLEUS_MEMORY_SOR`` is set truthy (default False)."""
    return os.environ.get(_SOR_FLAG, "").strip().lower() in _SOR_TRUTHY

class VectorStore:
    """
    Manages Vector Storage and Retrieval using Firestore and Gemini Embeddings.
    """
    def __init__(self):
        # We use a separate collection for memory vectors to avoid polluting the 'brain' file system
        self.collection_name = "nucleus_memory"
        self.enabled = STORAGE_TYPE == "firestore"
        
        if self.enabled:
            self.llm = DualEngineLLM(model_name="gemini-embedding-001")
        else:
            self.llm = None
            # Initialize Local SQLite Store for fallback
            self.local_store = LocalSQLiteStore(get_brain_path() / "memory.db")
            logger.info("🧠 VectorStore: Using Local SQLite fallback (No Amnesia).")

    def index(self, doc_id, text, metadata=None):
        """Best-effort index sink (Move 2 batch 5).

        Under the SoR read-model the unified ``MemoryFacade`` is authoritative
        for capture/recall; this method lets the facade push captured text into
        the vector index (Firestore KNN when enabled, else the LocalSQLiteStore
        local sink) for the optional re-rank stage. Purely additive and
        fault-isolated — any failure is swallowed so an index miss never breaks
        the authoritative SoR capture. Returns the sink doc id (or ``None``).
        """
        try:
            metadata = metadata or {}
            if getattr(self, "enabled", False) and getattr(self, "llm", None) is not None:
                embedding_resp = self.llm.embed_content(text, task_type="retrieval_document")
                vector = embedding_resp.get("embedding", [])
                if not vector:
                    return None
                db = get_firestore_client()
                doc_ref = db.collection(self.collection_name).document()
                payload = {"content": text, "metadata": metadata, "created_at": time.time()}
                try:
                    from google.cloud.firestore_v1.vector import Vector
                    payload["embedding_vector"] = Vector(vector)
                except ImportError:
                    pass
                doc_ref.set(payload)
                return doc_ref.id
            local = getattr(self, "local_store", None)
            if local is not None:
                return local.store(text, metadata)
        except Exception as exc:  # noqa: BLE001 — index sink is best-effort/additive
            logger.warning("VectorStore.index best-effort sink failed (ignored): %s", exc)
        return None

class LocalSQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with open_hardened_sqlite(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    metadata TEXT,
                    created_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content ON memories(content)")

    def store(self, content: str, metadata: Dict) -> str:
        import uuid
        doc_id = str(uuid.uuid4())
        with open_hardened_sqlite(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories (id, content, metadata, created_at) VALUES (?, ?, ?, ?)",
                (doc_id, content, json.dumps(metadata), time.time())
            )
        return doc_id

    def search(self, query: str, limit: int) -> List[Dict]:
        # Simplest possible keyword search for local fallback
        # In a real scenario, this would use FTS5 or local embeddings
        # NOTE for future-FTS5 migrator: if migrating from LIKE ? to FTS5
        # MATCH ?, apply the Bug #3 try-then-retry pattern. Literal-input
        # callers passing tokens FTS5 parses as syntax (e.g. `tb.py`,
        # `feat/foo`, anything containing `.` / `/` / `-`) raise
        # `fts5: syntax error`. Reference fix: eidetic-daemon
        # internal/store/store.go Search() (PR #77 / 3c3fa72) — try as-is,
        # retry once with phrase-quoting (`"..."` with `""`-escape doubling)
        # on FTS5 syntax error. FTS5's own error string is the discriminator;
        # context cancellation + other DB errors propagate unchanged.
        with open_hardened_sqlite(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit)
            )
            results = []
            for row in cursor:
                results.append({
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]),
                    "score": 1.0 # Exact keyword match proxy
                })
            return results

    def store_memory(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Embeds and stores a memory chunk. Returns the Document ID.

        Move 2 batch 5: flag-OFF (default) is byte-for-byte the legacy vector
        write (the local/Firestore index sink). Flag-ON additionally mirrors the
        capture into the unified SoR (authoritative), leaving this store as the
        best-effort index sink — dual-write, fault-isolated.
        """
        doc_id = self._store_memory_legacy(content, metadata)
        if _sor_flag_on():
            self._mirror_capture_to_sor(content, metadata)
        return doc_id

    def _mirror_capture_to_sor(self, content, metadata):
        """Best-effort dual-write of a vector-store capture into the unified SoR
        (Move 2 batch 5). The SoR (``MemoryFacade``) is authoritative; this
        vector store is the index sink. Fault-isolated: a mirror failure logs
        once and is swallowed — the legacy store write already succeeded."""
        global _sor_warned
        try:
            from mcp_server_nucleus.memory.facade import MemoryFacade

            brain = self.local_store.db_path.parent if getattr(self, "local_store", None) else None
            facade = MemoryFacade(brain_path=brain, enabled=True)
            facade.capture("memory", content, kind="memory", meta=metadata or {})
        except Exception as exc:  # noqa: BLE001 — SoR mirror is additive/best-effort
            if not _sor_warned:
                logger.warning("SoR memory capture mirror failed (ignored): %s", exc)
                _sor_warned = True

    def _store_memory_legacy(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Embeds and stores a memory chunk.
        Returns the Document ID.
        """
        if not self.enabled:
            metadata = metadata or {}
            doc_id = self.local_store.store(content, metadata)
            logger.info(f"🧠 [Local] Stored memory {doc_id}")
            return doc_id

        metadata = metadata or {}
        
        try:
            # Generate Embedding
            embedding_resp = self.llm.embed_content(content, task_type="retrieval_document")
            vector = embedding_resp.get('embedding', [])
            
            if not vector:
                raise ValueError("Failed to generate embedding")

            # Store in Firestore
            db = get_firestore_client()
            doc_ref = db.collection(self.collection_name).document()
            
            payload = {
                "content": content,
                "embedding": vector,  # Firestore supports Vector types? Or just list of floats.
                # Note: Pure Firestore vector search requires VectorValue. 
                # For MVP with `google-cloud-firestore` standard client, we store as raw list 
                # OR we need to use the specific Vector helper if available.
                # Assuming standard list for now, checking underlying support.
                # Wait, standard Firestore check:
                # To use KNN, we need `Vector` class from `google.cloud.firestore_v1.vector`.
                # Let's try to import it, or fallback.
                "metadata": metadata,
                "created_at": time.time()
            }
            
            # Helper for Vector type if available
            try:
                from google.cloud.firestore_v1.vector import Vector
                payload["embedding_vector"] = Vector(vector)
            except ImportError:
                 # Fallback/Older lib: Just store list, but search won't work efficiently without it.
                 pass

            doc_ref.set(payload)
            logger.info(f"🧠 Stored memory {doc_ref.id}")
            return doc_ref.id

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise

    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Semantic search for memories.

        Move 2 batch 5: flag-OFF (default) is byte-for-byte the legacy vector
        search (Firestore KNN when enabled, else LocalSQLiteStore). Flag-ON layers
        the unified SoR (``MemoryFacade.recall``, hybrid) on top additively — the
        vector store degrades to an optional re-rank sink; the SoR is authoritative.
        """
        legacy = self._search_memory_legacy(query, limit)
        if not _sor_flag_on():
            return legacy
        return self._merge_sor_search(query, limit, legacy)

    def _merge_sor_search(self, query, limit, legacy):
        """Union SoR (``MemoryFacade.recall`` hybrid) hits on top of the legacy
        vector result, dedup by content. Fault-isolated — a SoR read failure logs
        once and returns the legacy result unchanged (SoR read is purely additive
        so flag-ON recall is never worse than flag-OFF)."""
        global _sor_warned
        try:
            from mcp_server_nucleus.memory.facade import MemoryFacade

            brain = self.local_store.db_path.parent if getattr(self, "local_store", None) else None
            facade = MemoryFacade(brain_path=brain, enabled=True)
            hits = facade.recall(query=query or "", limit=max(int(limit) * 4, 40), mode="hybrid")
        except Exception as exc:  # noqa: BLE001 — additive read must not break search
            if not _sor_warned:
                logger.warning("SoR memory search read failed; legacy vector result only: %s", exc)
                _sor_warned = True
            return legacy
        merged = list(legacy)
        seen = {r.get("content") for r in legacy}
        for h in hits:
            text = h.get("text")
            if text in seen:
                continue
            seen.add(text)
            merged.append({
                "id": h.get("key") or h.get("id"),
                "content": text,
                "metadata": {
                    "category": h.get("kind"),
                    "tags": h.get("tags"),
                    "surface": h.get("surface"),
                    "source": h.get("source"),
                },
                "score": h.get("score", 0.0),
            })
        return merged[: max(1, int(limit))]

    def _search_memory_legacy(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Semantic search for memories.
        """
        if not self.enabled:
            return self.local_store.search(query, limit)

        try:
            # Embed Query
            embedding_resp = self.llm.embed_content(query, task_type="retrieval_query")
            query_vector = embedding_resp.get('embedding', [])
            
            if not query_vector:
                return []

            db = get_firestore_client()
            coll = db.collection(self.collection_name)
            
            # KNN Search
            # Requres `google-cloud-firestore>=2.14.0`
            from google.cloud.firestore_v1.vector import Vector
            from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

            # Execute Vector Search
            vector_query = coll.find_nearest(
                vector_field="embedding_vector",
                query_vector=Vector(query_vector),
                distance_measure=DistanceMeasure.COSINE,
                limit=limit
            )
            
            results = []
            docs = vector_query.get()
            for doc in docs:
                data = doc.to_dict()
                results.append({
                    "id": doc.id,
                    "content": data.get("content"),
                    "metadata": data.get("metadata"),
                    "score": 0.0 # Firestore doesn't return score easily in v1, implying raw sort
                })
                
            return results

        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []
