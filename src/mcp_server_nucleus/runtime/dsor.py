import json
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from .common import get_brain_path

class DecisionEntry:
    """Represents a single entry in the Decision System of Record (DSoR)."""
    def __init__(
        self,
        decision_id: str,
        intent: str,
        reasoning: str,
        context_hash: str,
        confidence: float = 1.0,
        deterministic_anchor: str = "NONE",
        audit_status: str = "PENDING",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None
    ):
        self.decision_id = decision_id
        self.intent = intent
        self.reasoning = reasoning
        self.context_hash = context_hash
        self.confidence = confidence
        self.deterministic_anchor = deterministic_anchor
        self.audit_status = audit_status
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "intent": self.intent,
            "reasoning": self.reasoning,
            "context_hash": self.context_hash,
            "confidence": self.confidence,
            "deterministic_anchor": self.deterministic_anchor,
            "audit_status": self.audit_status,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

class DecisionLedger:
    """Append-only ledger for capture decision provenance."""
    
    def __init__(self, brain_path: Optional[Path] = None):
        self.brain_path = brain_path or get_brain_path()
        self.ledger_dir = self.brain_path / "ledger" / "decisions"
        self.ledger_file = self.ledger_dir / "decisions.jsonl"
        self.ledger_dir.mkdir(parents=True, exist_ok=True)

    def record_decision(
        self,
        intent: str,
        reasoning: str,
        context_hash: str,
        confidence: float = 1.0,
        deterministic_anchor: str = "NONE",
        audit_status: str = "PENDING",
        metadata: Optional[Dict[str, Any]] = None
    ) -> DecisionEntry:
        """Record a new decision to the ledger."""
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"
        entry = DecisionEntry(
            decision_id=decision_id,
            intent=intent,
            reasoning=reasoning,
            context_hash=context_hash,
            confidence=confidence,
            deterministic_anchor=deterministic_anchor,
            audit_status=audit_status,
            metadata=metadata
        )
        
        # Append to JSONL
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
            
        return entry

    def update_audit_status(self, decision_id: str, status: str, auditor_notes: Optional[str] = None) -> bool:
        """Update the audit status of an existing decision."""
        if not self.ledger_file.exists():
            return False
            
        updated_entries = []
        found = False
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data["decision_id"] == decision_id:
                    data["audit_status"] = status
                    if auditor_notes:
                        data.setdefault("metadata", {})["auditor_notes"] = auditor_notes
                    found = True
                updated_entries.append(data)
        
        if found:
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                for entry in updated_entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return found

    def get_decision(self, decision_id: str) -> Optional[DecisionEntry]:
        """Retrieve a decision by ID."""
        if not self.ledger_file.exists():
            return None
            
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data["decision_id"] == decision_id:
                    return DecisionEntry(**data)
        return None

    def list_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent decisions."""
        if not self.ledger_file.exists():
            return []
            
        entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                entries.append(json.loads(line))
        
        return entries[-limit:]

    def list_all(self) -> List[Dict[str, Any]]:
        """List all decisions in the ledger."""
        if not self.ledger_file.exists():
            return []
            
        entries = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                entries.append(json.loads(line))
        
        return entries
class EngramVault:
    """Session-scoped ephemeral memory (The Vault) for active swarms."""
    def __init__(self, session_id: str, brain_path: Optional[Path] = None):
        self.session_id = session_id
        self.brain_path = brain_path or get_brain_path()
        self.vault_dir = self.brain_path / "session" / session_id
        self.vault_file = self.vault_dir / "vault.jsonl"
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def deposit(self, key: str, value: str, source_agent: str, metadata: Optional[Dict[str, Any]] = None):
        """Store an ephemeral engram in the vault."""
        entry = {
            "key": key,
            "value": value,
            "source_agent": source_agent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        with open(self.vault_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def list_all(self) -> List[Dict[str, Any]]:
        """List all ephemeral engrams in the vault."""
        if not self.vault_file.exists():
            return []
        entries = []
        with open(self.vault_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries

class SessionStateManager:
    """Manages persistence for Coordinator stats and session progress."""
    def __init__(self, session_id: str, brain_path: Optional[Path] = None):
        self.session_id = session_id
        self.brain_path = brain_path or get_brain_path()
        self.state_file = self.brain_path / "session" / session_id / "state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def save_state(self, stats: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Persist current coordinator stats and metadata."""
        state = {
            "session_id": self.session_id,
            "stats": stats,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load persisted session state."""
        if not self.state_file.exists():
            return None
        try:
            return json.loads(self.state_file.read_text())
        except Exception:
            return None
