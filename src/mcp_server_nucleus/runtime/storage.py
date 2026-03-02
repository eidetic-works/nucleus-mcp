
import os
from pathlib import Path
from typing import Union
import logging

# Configuration
STORAGE_TYPE = os.environ.get("NUCLEUS_STORAGE_TYPE", "local")  # local | firestore
FIRESTORE_COLLECTION = "nucleus_brain"

# Singleton Firestore Client
_firestore_client = None


try:
    from google.cloud import firestore
except ImportError:
    firestore = None

def get_firestore_client():
    global _firestore_client
    if _firestore_client is None:
        if firestore is None:
            logging.error("google-cloud-firestore not installed.")
            raise ImportError("google-cloud-firestore module not found")
        try:
            _firestore_client = firestore.Client()
        except Exception as e:
            logging.error(f"Failed to initialize Firestore: {e}")
            raise
    return _firestore_client

def _path_to_id(path: Union[str, Path]) -> str:
    """Convert a file path to a Firestore Document ID."""
    # We strip the brain root if possible to make IDs cleaner, 
    # but for now, just replacing slashes is enough uniqueness.
    # e.g., "commitments/ledger.json" -> "commitments__ledger.json"
    p = str(path)
    # If path is absolute, try to make it relative to brain root?
    # Actually, simplistic approach: replace / with __
    return p.strip("/").replace("/", "__").replace(".", "_")

def read_brain_file(path: Union[str, Path]) -> str:
    """Read a file from Brain (Local or Firestore)."""
    if STORAGE_TYPE == "firestore":
        db = get_firestore_client()
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(_path_to_id(path))
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get("content", "")
        else:
            raise FileNotFoundError(f"Firestore document {doc_ref.id} not found")
    else:
        # Local Mode
        p = Path(path)
        return p.read_text()

def write_brain_file(path: Union[str, Path], content: str) -> None:
    """Write content to Brain (Local or Firestore)."""
    if STORAGE_TYPE == "firestore":
        db = get_firestore_client()
        doc_id = _path_to_id(path)
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(doc_id)
        
        doc_ref.set({
            "content": content,
            "path": str(path),
            "updated_at": firestore.SERVER_TIMESTAMP 
        }, merge=True)
    else:
        # Local Mode
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

def brain_file_exists(path: Union[str, Path]) -> bool:
    """Check if file exists in Brain."""
    if STORAGE_TYPE == "firestore":
        db = get_firestore_client()
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(_path_to_id(path))
        return doc_ref.get().exists
    else:
        return Path(path).exists()
