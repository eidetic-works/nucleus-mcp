
import logging
import time
from typing import List, Dict, Any
import sqlite3
import json
from pathlib import Path
from .llm_client import DualEngineLLM
from .storage import get_firestore_client, STORAGE_TYPE
from ..runtime.common import get_brain_path

logger = logging.getLogger("nucleus.vector_store")

class VectorStore:
    """
    Manages Vector Storage and Retrieval using Firestore and Gemini Embeddings.
    """
    def __init__(self):
        # We use a separate collection for memory vectors to avoid polluting the 'brain' file system
        self.collection_name = "nucleus_memory"
        self.enabled = STORAGE_TYPE == "firestore"
        
        if self.enabled:
            self.llm = DualEngineLLM(model_name="text-embedding-004")
        else:
            self.llm = None
            # Initialize Local SQLite Store for fallback
            self.local_store = LocalSQLiteStore(get_brain_path() / "memory.db")
            logger.info("🧠 VectorStore: Using Local SQLite fallback (No Amnesia).")

class LocalSQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories (id, content, metadata, created_at) VALUES (?, ?, ?, ?)",
                (doc_id, content, json.dumps(metadata), time.time())
            )
        return doc_id

    def search(self, query: str, limit: int) -> List[Dict]:
        # Simplest possible keyword search for local fallback
        # In a real scenario, this would use FTS5 or local embeddings
        with sqlite3.connect(self.db_path) as conn:
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
