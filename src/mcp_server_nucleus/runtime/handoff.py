import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from .common import get_brain_path
from .auth.signature_guard import get_signature_guard

class HandoffToken:
    """A signed intent packet for transferring context between agents."""
    def __init__(
        self,
        session_id: str,
        source_agent: str,
        target_agent: str,
        intent: str,
        memory_pointer: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.handoff_id = f"hnd-{uuid.uuid4().hex[:12]}"
        self.session_id = session_id
        self.source_agent = source_agent
        self.target_agent = target_agent
        self.intent = intent
        self.memory_pointer = memory_pointer
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.metadata = metadata or {}
        
        # Sign the token for zero-shortcut enforcement
        guard = get_signature_guard()
        self.signature = guard.sign_dict(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "session_id": self.session_id,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "intent": self.intent,
            "memory_pointer": self.memory_pointer,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    def to_signed_json(self) -> str:
        data = self.to_dict()
        data["signature"] = self.signature
        return json.dumps(data, ensure_ascii=False)

class HandoffLedger:
    """Append-only record of agent transitions within a session."""
    def __init__(self, session_id: str, brain_path: Optional[Path] = None):
        self.session_id = session_id
        self.brain_path = brain_path or get_brain_path()
        self.ledger_file = self.brain_path / "session" / session_id / "handoffs.jsonl"
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)

    def record_handoff(self, token: HandoffToken):
        """Record a handoff token to the session ledger."""
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(token.to_signed_json() + "\n")

    def verify_and_load(self, handoff_json: str) -> Optional[Dict[str, Any]]:
        """Verify a JSON handoff token and return its data if valid."""
        try:
            data = json.loads(handoff_json)
            sig = data.pop("signature", None)
            if not sig:
                return None
            
            guard = get_signature_guard()
            if guard.verify_dict(data, sig):
                return data
            return None
        except Exception:
            return None

    def list_history(self) -> List[Dict[str, Any]]:
        """List all previous handoffs in this session."""
        if not self.ledger_file.exists():
            return []
        history = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        history.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return history
