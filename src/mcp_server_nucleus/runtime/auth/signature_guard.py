"""Cryptographic Task Signing and Verification Guard."""
import hashlib
import hmac
import os
import json
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional
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
        """Load — or MINT-AND-PERSIST — the same secret used by IPCAuthProvider.

        Mirrors ``IPCAuthProvider._load_or_create_secret`` (ipc_provider.py:116-128)
        byte-for-byte: ``secrets.token_bytes(32)`` in a ``0600`` ``secrets/`` dir.
        Whichever of IPCAuthProvider / SignatureGuard touches a brain first mints
        the ONE durable key; the other reads the identical bytes.

        The OLD behaviour returned an ephemeral ``os.urandom(32)`` WITHOUT
        persisting when the file was absent — so the signing process (executor)
        and the reading process (census) held different keys and EVERY verify
        failed. Persisting closes that hole: a signature written now verifies at a
        later, out-of-process capture.
        """
        secrets_dir = self.brain_path / "secrets"
        key_file = secrets_dir / ".ipc_secret"
        if key_file.exists():
            return key_file.read_bytes()
        secrets_dir.mkdir(parents=True, exist_ok=True)
        key = secrets.token_bytes(32)
        key_file.write_bytes(key)
        os.chmod(key_file, 0o600)
        return key

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

    # ── Cross-vendor dispatch signing (census crit-4 v2.1) ──────────────────
    #
    # Domain-separated from ``sign_dict``. The ``v1:dict:`` domain is SHARED with
    # handoff IntentTokens; reusing it would let a dispatch signature be replayed
    # as a handoff token (and vice-versa), and ``sign_dict`` signs whatever dict
    # it is handed rather than the EXACT named field set. ``v2:vdisp:`` binds the
    # signature to the exact ordered tuple below via COMPACT-JSON-ARRAY
    # canonicalization (not pipe-joins) — so a ref containing ``|`` or ``,``
    # cannot smear across fields (delimiter injection is impossible).

    @staticmethod
    def _vendor_dispatch_message(
        vendor: str,
        model: str,
        prompt_digest: str,
        artifact_refs: List[str],
        result_sha256: str,
        status: str,
        ts: int,
    ) -> str:
        """The canonical UTF-8 byte-string a dispatch signature covers.

        MUST stay byte-identical to the census script's stdlib recomputation
        (``scripts/census_v2.py::_vendor_dispatch_message``); a parity self-test
        asserts the two agree.
        """
        return "v2:vdisp:" + json.dumps(
            [
                vendor,
                model,
                prompt_digest,
                sorted(str(r) for r in artifact_refs),
                result_sha256,
                status,
                ts,
            ],
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def sign_vendor_dispatch(
        self,
        vendor: str,
        model: str,
        prompt_digest: str,
        artifact_refs: List[str],
        result_sha256: str,
        status: str,
        ts: int,
    ) -> str:
        """HMAC-sign a cross-vendor dispatch over its EXACT field set.

        Raises ``RuntimeError`` if the machine key is unavailable — this method
        NEVER emits the ``"unsigned-placeholder"`` fallback, because an
        un-verifiable placeholder in a census envelope would be worse than a
        missing signature. The single caller
        (``runtime/vendor_dispatch.py::_capture``) fault-isolates the raise and
        stamps ``dispatch_sig=null`` so the envelope fails closed AT THE CENSUS.
        """
        if not self._secret_key:
            raise RuntimeError("vendor-dispatch signing key unavailable")
        message = self._vendor_dispatch_message(
            vendor, model, prompt_digest, artifact_refs, result_sha256, status, ts
        )
        return self._compute_hmac(message)

    def verify_vendor_dispatch(
        self,
        vendor: str,
        model: str,
        prompt_digest: str,
        artifact_refs: List[str],
        result_sha256: str,
        status: str,
        ts: int,
        signature: str,
    ) -> bool:
        """Constant-time-verify a dispatch signature over its own field set."""
        if not signature or not self._secret_key:
            return False
        expected = self._compute_hmac(
            self._vendor_dispatch_message(
                vendor, model, prompt_digest, artifact_refs, result_sha256, status, ts
            )
        )
        return hmac.compare_digest(expected, signature)

# Singleton instance for high-frequency task operations
_guard: Optional[SignatureGuard] = None

def get_signature_guard(brain_path: Optional[Path] = None) -> SignatureGuard:
    global _guard
    if _guard is None:
        _guard = SignatureGuard(brain_path)
    return _guard
