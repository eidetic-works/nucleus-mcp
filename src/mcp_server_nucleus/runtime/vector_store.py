
import logging
import time
from typing import List, Dict, Any
from .llm_client import DualEngineLLM
from .storage import get_firestore_client, STORAGE_TYPE

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
            # Only initialize LLM if we are actually going to use it (requires API Key)
            self.llm = DualEngineLLM(model_name="text-embedding-004")
        else:
            self.llm = None
            logger.warning("⚠️ VectorStore disabled: NUCLEUS_STORAGE_TYPE is not 'firestore'.")

    def store_memory(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Embeds and stores a memory chunk.
        Returns the Document ID.
        """
        if not self.enabled:
            logger.info(f"Skipping memory storage (Local Mode): {content[:30]}...")
            return "local_mock_id"

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
            return [{"content": "Memory disabled in local mode", "score": 0.0}]

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
