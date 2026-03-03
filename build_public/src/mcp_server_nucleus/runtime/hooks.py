
"""
Strategic Hooks for Nucleus Daemon.
The "Billion Dollar Extensions" for Network Effects, Identity, and Scale.

Strategic Role:
- Turn the Daemon into a Platform (App Store).
- Turn the Daemon into a Global Node (Insight Exchange).
- Deepen Host Integration (Intimacy).
"""

import json
import logging
import time
import uuid
import hashlib
from typing import List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# --- CRYPTO UPGRADE (Phase 60: Gates Fix) ---
try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)

# --- 1. The App Store Hook (AgentManifest) ---
@dataclass
class AgentManifest:
    """Schema for a Tradeable Agent (The App Store Unit)."""
    id: str
    name: str
    version: str
    author_did: str # Decentralized ID of creator
    capabilities: List[str]
    lifecycle_state: str = "active" # active, archived, tombstone
    price_per_invocation_usd: float = 0.0
    hash: str = ""
    signature: str = ""

    def sign(self, identity_key: 'IdentityKey'):
        """Sign the manifest to prove authorship."""
        # Canonicalize the data
        payload = f"{self.id}:{self.version}:{self.author_did}:{self.lifecycle_state}"
        self.signature = identity_key.sign_message(payload)
        self.hash = hashlib.sha256(payload.encode()).hexdigest()

# --- 2. The Insight Hook (InsightExchange) ---
@dataclass
class InsightPacket:
    """Schema for Tradeable Information (The Data Unit)."""
    topic: str
    content_hash: str
    value_score: float
    source_did: str
    timestamp: float
    proof: Optional[str] = None # ZK Proof of validity (Future)

class InsightExchange:
    """Protocol for trading Insights between Daemons."""
    def __init__(self, brain_path: Path):
        self.ledger_path = brain_path / "network" / "insights.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def offer_insight(self, topic: str, content: str, value: float) -> InsightPacket:
        """Create an offer to sell info."""
        packet = InsightPacket(
            topic=topic,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            value_score=value,
            source_did="self", # In real impl, use IdentityKey
            timestamp=time.time()
        )
        # Log offers
        with open(self.ledger_path, "a") as f:
            f.write(json.dumps(asdict(packet)) + "\n")
        return packet

# --- 3. The Grid Hook (RemoteExecutionProtocol) ---
class RemoteExecutionProtocol:
    """Interface for offloading work to the Cloud (The Grid)."""
    def __init__(self, brain_path: Path):
        self.config_path = brain_path / "network" / "grid_config.json"
        
    def dispatch_container(self, image: str, cmd: List[str], max_budget_usd: float) -> str:
        """
        Stub: Dispatch a Docker container to a Grid Node (e.g. Cloud Run).
        Returns: Execution ID.
        """
        logger.info(f"🌩️ GRID DISPATCH: {image} (Budget: ${max_budget_usd})")
        # In real impl, this calls Google Cloud Run API or a P2P compute market
        return f"grid_exec_{uuid.uuid4()}"

# --- 4. The Host Hook (HostIntimacy) ---
class HostIntimacy:
    """
    Permission-aware OS Access. 
    Managing the "Deep Binding" to the user's life (Files, Calendar, etc).
    """
    def __init__(self):
        self.permissions = {
            "filesystem": "read-write",
            "geolocation": "denied",
            "clipboard": "ask",
            "biometrics": "unavailable"
        }
        
    def check_permission(self, capability: str) -> bool:
        """Centralized permission check."""
        return self.permissions.get(capability, "denied") in ["allowed", "read-write", "ask"]

# --- 5. The Identity Hook (IdentityKey) ---
class IdentityKey:
    """
    Cryptographic Identity for the Sovereign Node (Ed25519).
    The "Soul" of the machine.
    """
    def __init__(self, brain_path: Path):
        self.key_dir = brain_path / "identity"
        self.key_dir.mkdir(parents=True, exist_ok=True)
        self.private_key_path = self.key_dir / "node.pem"
        self.public_key_path = self.key_dir / "node.pub"
        
        self.did = ""
        self._private_key = None
        self._load_or_create_identity()
        
    def _load_or_create_identity(self):
        if not CRYPTO_AVAILABLE:
            logger.warning("⚠️ 'cryptography' lib not found. Using UUID stub for Identity.")
            self.did = f"did:nucleus:stub:{uuid.uuid4()}"
            return

        if self.private_key_path.exists():
            try:
                with open(self.private_key_path, "rb") as f:
                    self._private_key = serialization.load_pem_private_key(
                        f.read(), password=None
                    )
                logger.info("🔑 Loaded existing IdentityKey.")
            except Exception as e:
                logger.error(f"❌ Failed to load IdentityKey: {e}. Generating new one.")
                self._generate_new_key()
        else:
            self._generate_new_key()

        # Derive Public Key and DID
        if self._private_key:
            public_key = self._private_key.public_key()
            pub_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            # DID format: did:nucleus:<hex_pub_key>
            self.did = f"did:nucleus:{pub_bytes.hex()}"
            
            # Save public key for strict reference
            with open(self.public_key_path, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

    def _generate_new_key(self):
        logger.info("✨ Generating new Ed25519 IdentityKey...")
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        
        # Save Private Key
        pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(self.private_key_path, "wb") as f:
            f.write(pem)

    def sign_message(self, message: str) -> str:
        """Sign a payload using Ed25519."""
        if not self._private_key:
            return f"stub_sig_{uuid.uuid4()}"
            
        points = message.encode("utf-8")
        signature = self._private_key.sign(points)
        return signature.hex()

    def verify_signature(self, message: str, signature_hex: str, did: str) -> bool:
        """Verify a signature against a DID (Public Key)."""
        if not CRYPTO_AVAILABLE or "stub" in did:
            return True # Fallback for dev/stub modes
            
        try:
            # Extract Public Key from DID
            if not did.startswith("did:nucleus:"):
                return False
            pub_key_hex = did.split(":")[-1]
            pub_key_bytes = bytes.fromhex(pub_key_hex)
            
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_key_bytes)
            
            signature_bytes = bytes.fromhex(signature_hex)
            public_key.verify(signature_bytes, message.encode("utf-8"))
            return True
        except Exception as e:
            logger.warning(f"⚠️ Signature Verification Failed: {e}")
            return False

# --- 6. The Pulse (AmbientTelemetry) ---
class AmbientTelemetry:
    """
    Writes status to a "Pulse File" for the HUD/Status Bar to read.
    Frequency: High (1s-5s).
    
    Security (V9 Patch): Uses IdentityKey to sign heartbeats, preventing IPC hijacking.
    """
    def __init__(self, brain_path: Path, identity: Optional['IdentityKey'] = None):
        self.pulse_file = brain_path / "pulse.json"
        self.identity = identity
        
    def beat(self, status: str, active_tasks: int, cpu_usage: float = 0.0):
        """Write the heartbeat with a cryptographic pulse signal."""
        timestamp = time.time()
        data = {
            "timestamp": timestamp,
            "status": status, # idle, busy, error, sleeping
            "tasks": active_tasks,
            "cpu": cpu_usage,
            "color": "green" if status == "idle" else "gold" if status == "busy" else "red"
        }
        
        # Add Trust Signal (Crypographic Pulse)
        if self.identity:
            payload = f"{timestamp}:{status}:{active_tasks}"
            data["pulse_sig"] = self.identity.sign_message(payload)
            data["did"] = self.identity.did

        # Atomic write
        try:
            temp_file = self.pulse_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(data))
            temp_file.replace(self.pulse_file)
        except Exception as e:
            logger.warning(f"Failed to pulse: {e}")
