"""Cryptographic Task Signing and Verification Guard."""
import hashlib
import hmac
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from mcp_server_nucleus.runtime.common import get_brain_path

class SignatureGuard:
    """
    Handles cryptographic signing and verification for session integrity.
    Uses the Brain's private IPC secret.
    """
    
    def __init__(self, brain_path: Optional[Path] = None):
        self.brain_path = brain_path or get_brain_path()
        self._secret_key = self._load_secret()
        
    def _load_secret(self) -> bytes:
        """Load the same secret used by IPCAuthProvider."""
        key_file = self.brain_path / "secrets" / ".ipc_secret"
        if not key_file.exists():
            # Generate ephemeral secret if IPCAuthProvider hasn't created one yet
            import os
            return os.urandom(32)
        return key_file.read_bytes()

    def sign_payload(self, task_id: str, description: str) -> str:
        """Create a shorter, URL-safe HMAC signature for a task."""
        message = f"v1:{task_id}:{description}"
        return self._compute_hmac(message)

    def sign_dict(self, data: Dict[str, Any]) -> str:
        """Create a deterministic HMAC signature for a dictionary."""
        # Sort keys and remove existing signature for deterministic hashing
        payload = {k: v for k, v in data.items() if k != "signature"}
        message = f"v1:dict:{json.dumps(payload, sort_keys=True)}"
        return self._compute_hmac(message)

    def _compute_hmac(self, message: str) -> str:
        """Internal HMAC computation (32-character hex)."""
        if not self._secret_key:
            return "unsigned-placeholder"
        signature = hmac.new(
            self._secret_key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature[:32]

    def verify_dict(self, data: Dict[str, Any], signature: str) -> bool:
        """Verify the signature of a dictionary."""
        if not signature:
            return False
        expected = self.sign_dict(data)
        return hmac.compare_digest(expected, signature)

    def verify_payload(self, task_id: str, description: str, signature: str) -> bool:
        """Verify that a task was signed by a trusted internal source."""
        if not signature:
            return False
        expected = self.sign_payload(task_id, description)
        return hmac.compare_digest(expected, signature)

# Singleton instance for high-frequency task operations
_guard: Optional[SignatureGuard] = None

def get_signature_guard(brain_path: Optional[Path] = None) -> SignatureGuard:
    global _guard
    if _guard is None:
        _guard = SignatureGuard(brain_path)
    return _guard
