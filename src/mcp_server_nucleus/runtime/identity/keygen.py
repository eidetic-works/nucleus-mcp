import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple, Optional, Dict

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger("KEY_MANAGER")

class KeyPair(NamedTuple):
    key_id: str
    private_key_pem: str
    public_key_pem: str

class KeyManager:
    """
    Manages Ed25519 Key Generation, Verification, and Persistence for Nucleus.
    """
    def __init__(self, brain_path: Optional[Path] = None):
        """
        Args:
            brain_path: Optional root path for key storage. If None, runs in stateless mode.
        """
        if not HAS_CRYPTO:
            raise ImportError("cryptography module is required. Install with: pip install cryptography")
        
        self.brain_path = brain_path
        if self.brain_path:
            self.keystore_path = self.brain_path / "ledger" / "keystore.json"
            self.keystore_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_keystore(self) -> Dict[str, Dict[str, str]]:
        if not self.brain_path or not self.keystore_path.exists():
            return {}
        try:
            return json.loads(self.keystore_path.read_text())
        except Exception:
            return {}

    def _save_keystore(self, store: Dict):
        if self.brain_path:
            # We don't have locking here yet, assume single user or add locking later
            # Ideally use update_brain_file or lock
            self.keystore_path.write_text(json.dumps(store, indent=2))

    def generate_key(self, alias: Optional[str] = None) -> str:
        """
        Generates, Persists, and returns Key ID.
        Args:
            alias: Optional human readable alias (e.g. 'publisher_main')
        """
        kp = self.generate_keypair()
        
        if self.brain_path:
            store = self._load_keystore()
            store[kp.key_id] = {
                "private_key_pem": kp.private_key_pem,
                "public_key_pem": kp.public_key_pem,
                "alias": alias,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            if alias:
                # Also index by alias for convenience? 
                # Or just search. Let's just store by ID for now.
                pass
            self._save_keystore(store)
            
        return kp.key_id

    def get_key_pair(self, key_id: str) -> Optional[KeyPair]:
        """Retrieve key pair from disk by ID."""
        if not self.brain_path:
            return None
        
        store = self._load_keystore()
        if key_id in store:
            data = store[key_id]
            return KeyPair(
                key_id=key_id,
                private_key_pem=data["private_key_pem"],
                public_key_pem=data["public_key_pem"]
            )
        return None

    def generate_keypair(self) -> KeyPair:
        """Generates a new Ed25519 keypair and returns PEM strings (Stateless)."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Serialize Private Key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize Public Key
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Generate Key ID (Fingerprint of Public Key)
        public_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        key_id = hashlib.sha256(public_der).hexdigest()
        
        return KeyPair(
            key_id=key_id,
            private_key_pem=private_pem.decode('utf-8'),
            public_key_pem=public_pem.decode('utf-8')
        )

    def sign(self, private_key_pem: str, data: bytes) -> bytes:
        """Signs data with private key PEM. Returns raw bytes signature."""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None
        )
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Invalid Key Type. Expected Ed25519PrivateKey.")
            
        return private_key.sign(data)

    def verify(self, public_key_pem: str, signature: bytes, data: bytes) -> bool:
        """Verifies signature with public key PEM. Returns True if valid."""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8')
            )
            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                raise ValueError("Invalid Key Type. Expected Ed25519PublicKey.")
                
            public_key.verify(signature, data)
            return True
        except Exception as e:
            logger.warning(f"Verification Failed: {e}")
            return False
