"""
Nucleus Firestore Bridge
========================
Bridges the Local Brain (CLI) with the Cloud Brain (Orchestrator) via Firestore.

Logic:
- When an event is emitted locally, we push it to the 'nucleus-events' collection.
- This allows the Cloud Orchestrator to see local events (like "Task Added").

Location: mcp_server_nucleus/runtime/firestore_bridge.py
"""

import logging
from typing import Dict, Any

try:
    from google.cloud import firestore
    HAS_FIRESTORE = True
except ImportError:
    HAS_FIRESTORE = False

logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "gen-lang-client-0894185576"
COLLECTION_NAME = "nucleus-events"

class FirestoreBridge:
    def __init__(self, project_id: str = PROJECT_ID):
        self.project_id = project_id
        self.client = None
        self.enabled = False
        
        # Only enable if we have the library and credentials (or can get them)
        if HAS_FIRESTORE:
            try:
                # This will use Application Default Credentials (gcloud auth application-default login)
                self.client = firestore.Client(project=project_id)
                self.enabled = True
            except Exception as e:
                logger.debug(f"Firestore Bridge disabled (no creds): {e}")
                
    def push_event(self, event: Dict[str, Any]) -> bool:
        """Push a local event to the cloud."""
        if not self.enabled or not self.client:
            return False
            
        try:
            # key by event_id for idempotency
            event_id = event.get("event_id")
            if not event_id:
                return False
                
            doc_ref = self.client.collection(COLLECTION_NAME).document(event_id)
            doc_ref.set(event)
            return True
        except Exception as e:
            logger.warning(f"Failed to push event to cloud: {e}")
            return False

    def list_cloud_tasks(self, limit: int = 50) -> list:
        """Fetch tasks from the cloud 'nucleus-tasks' collection."""
        if not self.enabled or not self.client:
            return []
            
        try:
            # We assume cloud tasks are in 'nucleus-tasks'
            # Ordered by priority (asc) and created_at (desc)
            docs = self.client.collection("nucleus-tasks") \
                .order_by("priority", direction=firestore.Query.ASCENDING) \
                .limit(limit) \
                .stream()
                
            tasks = []
            for doc in docs:
                t = doc.to_dict()
                t["source"] = "cloud" # Mark as cloud source
                tasks.append(t)
            return tasks
        except Exception as e:
            logger.warning(f"Failed to list cloud tasks: {e}")
            return []

# Singleton instance
_bridge = None

def get_bridge() -> FirestoreBridge:
    global _bridge
    if _bridge is None:
        _bridge = FirestoreBridge()
    return _bridge
