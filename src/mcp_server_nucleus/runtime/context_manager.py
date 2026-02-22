"""
v0.6.0 DSoR: Context Manager

Provides stateless hashing of the current world-state for decision provenance.
This module enables verification of state before/after agent turns to ensure
integrity and detect unauthorized mutations.

Part of the Decision System of Record (DSoR) initiative.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


def get_brain_path() -> Path:
    """Get the brain path from environment."""
    return Path(os.getenv("NUCLEAR_BRAIN_PATH", "/Users/nucleus-os/ai-mvp-backend/.brain"))


@dataclass
class ContextSnapshot:
    """
    Immutable snapshot of world-state at a point in time.
    Used for before/after comparisons in agent turns.
    """
    snapshot_id: str
    timestamp: str
    state_hash: str
    component_hashes: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextSnapshot":
        return cls(**data)


@dataclass
class StateVerificationResult:
    """Result of comparing two context snapshots."""
    is_valid: bool
    before_hash: str
    after_hash: str
    mutations_detected: List[str] = field(default_factory=list)
    drift_components: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    verification_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ContextManager:
    """
    v0.6.0 DSoR: Manages context state hashing and verification.
    
    Provides:
    1. Stateless hashing of current world-state
    2. Before/after verification for agent turns
    3. Drift detection for unauthorized mutations
    """
    
    def __init__(self, brain_path: Optional[Path] = None):
        self.brain_path = brain_path or get_brain_path()
        self._snapshot_counter = 0
    
    def _hash_file(self, file_path: Path) -> Optional[str]:
        """Compute SHA-256 hash of a file's contents."""
        try:
            if file_path.exists() and file_path.is_file():
                content = file_path.read_bytes()
                return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            pass
        return None
    
    def _hash_dict(self, data: Dict[str, Any]) -> str:
        """Compute deterministic hash of a dictionary."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
    
    def _collect_ledger_state(self) -> Dict[str, Any]:
        """Collect state from the ledger directory."""
        ledger_path = self.brain_path / "ledger"
        state = {
            "engrams_hash": None,
            "events_hash": None,
            "tasks_hash": None,
            "decisions_hash": None,
        }
        
        if ledger_path.exists():
            # Hash key ledger files
            engrams_file = ledger_path / "engrams.jsonl"
            events_file = ledger_path / "events.jsonl"
            tasks_file = ledger_path / "tasks.json"
            decisions_dir = ledger_path / "decisions"
            
            state["engrams_hash"] = self._hash_file(engrams_file)
            state["events_hash"] = self._hash_file(events_file)
            state["tasks_hash"] = self._hash_file(tasks_file)
            
            if decisions_dir.exists():
                decisions_file = decisions_dir / "decisions.jsonl"
                state["decisions_hash"] = self._hash_file(decisions_file)
        
        return state
    
    def _collect_slots_state(self) -> Dict[str, Any]:
        """Collect state from the slots directory."""
        slots_path = self.brain_path / "slots"
        state = {"registry_hash": None, "slot_count": 0}
        
        if slots_path.exists():
            registry_file = slots_path / "registry.json"
            state["registry_hash"] = self._hash_file(registry_file)
            state["slot_count"] = len(list(slots_path.glob("slot_*.json")))
        
        return state
    
    def _collect_mounts_state(self) -> Dict[str, Any]:
        """Collect state from mounted servers."""
        mounts_file = self.brain_path / "ledger" / "mounts.json"
        state = {"mounts_hash": None, "mount_count": 0}
        
        if mounts_file.exists():
            state["mounts_hash"] = self._hash_file(mounts_file)
            try:
                with open(mounts_file) as f:
                    mounts = json.load(f)
                    state["mount_count"] = len(mounts.get("servers", []))
            except Exception:
                pass
        
        return state
    
    def compute_world_state_hash(self, include_docs: bool = False, 
                                  recent_events: Optional[List[str]] = None) -> Tuple[str, Dict[str, str]]:
        """
        Compute a comprehensive hash of the current world-state.
        
        Args:
            include_docs: Whether to include document checksums
            recent_events: Optional list of recent event strings to include
            
        Returns:
            Tuple of (overall_hash, component_hashes)
        """
        components = {}
        
        # 1. Ledger state
        ledger_state = self._collect_ledger_state()
        components["ledger"] = self._hash_dict(ledger_state)
        
        # 2. Slots state
        slots_state = self._collect_slots_state()
        components["slots"] = self._hash_dict(slots_state)
        
        # 3. Mounts state
        mounts_state = self._collect_mounts_state()
        components["mounts"] = self._hash_dict(mounts_state)
        
        # 4. Recent events (if provided)
        if recent_events:
            events_blob = json.dumps(recent_events[-10:], sort_keys=True)
            components["recent_events"] = hashlib.sha256(events_blob.encode()).hexdigest()[:16]
        
        # 5. Optional: Include docs checksums
        if include_docs:
            docs_path = self.brain_path / "artifacts"
            if docs_path.exists():
                doc_hashes = []
                for md_file in docs_path.rglob("*.md"):
                    h = self._hash_file(md_file)
                    if h:
                        doc_hashes.append(f"{md_file.name}:{h}")
                if doc_hashes:
                    components["docs"] = hashlib.sha256(
                        "|".join(sorted(doc_hashes)).encode()
                    ).hexdigest()[:16]
        
        # Compute overall hash from components
        overall = self._hash_dict(components)
        
        return overall, components
    
    def take_snapshot(self, include_docs: bool = False,
                      recent_events: Optional[List[str]] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> ContextSnapshot:
        """
        Take an immutable snapshot of the current world-state.
        
        Args:
            include_docs: Whether to include document checksums
            recent_events: Optional list of recent event strings
            metadata: Optional metadata to attach to snapshot
            
        Returns:
            ContextSnapshot instance
        """
        self._snapshot_counter += 1
        state_hash, component_hashes = self.compute_world_state_hash(
            include_docs=include_docs,
            recent_events=recent_events
        )
        
        snapshot = ContextSnapshot(
            snapshot_id=f"snap-{self._snapshot_counter:06d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            state_hash=state_hash,
            component_hashes=component_hashes,
            metadata=metadata or {}
        )
        
        return snapshot
    
    def verify_state_integrity(self, before: ContextSnapshot, 
                                after: ContextSnapshot,
                                allowed_mutations: Optional[List[str]] = None) -> StateVerificationResult:
        """
        Verify state integrity by comparing before/after snapshots.
        
        Args:
            before: Snapshot taken before agent turn
            after: Snapshot taken after agent turn
            allowed_mutations: List of component names that are allowed to change
            
        Returns:
            StateVerificationResult with drift analysis
        """
        allowed = set(allowed_mutations or [])
        mutations = []
        drift_components = {}
        
        # Compare component hashes
        all_components = set(before.component_hashes.keys()) | set(after.component_hashes.keys())
        
        for component in all_components:
            before_hash = before.component_hashes.get(component)
            after_hash = after.component_hashes.get(component)
            
            if before_hash != after_hash:
                mutations.append(component)
                drift_components[component] = (before_hash or "none", after_hash or "none")
        
        # Check if mutations are within allowed set
        unauthorized_mutations = [m for m in mutations if m not in allowed]
        is_valid = len(unauthorized_mutations) == 0
        
        return StateVerificationResult(
            is_valid=is_valid,
            before_hash=before.state_hash,
            after_hash=after.state_hash,
            mutations_detected=mutations,
            drift_components=drift_components
        )
    
    def persist_snapshot(self, snapshot: ContextSnapshot) -> Path:
        """
        Persist a snapshot to the ledger for audit purposes.
        
        Args:
            snapshot: The snapshot to persist
            
        Returns:
            Path to the persisted snapshot file
        """
        snapshots_dir = self.brain_path / "ledger" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        snapshot_file = snapshots_dir / f"{snapshot.snapshot_id}.json"
        snapshot_file.write_text(json.dumps(snapshot.to_dict(), indent=2))
        
        return snapshot_file
    
    def load_snapshot(self, snapshot_id: str) -> Optional[ContextSnapshot]:
        """
        Load a previously persisted snapshot.
        
        Args:
            snapshot_id: The ID of the snapshot to load
            
        Returns:
            ContextSnapshot if found, None otherwise
        """
        snapshots_dir = self.brain_path / "ledger" / "snapshots"
        snapshot_file = snapshots_dir / f"{snapshot_id}.json"
        
        if snapshot_file.exists():
            try:
                data = json.loads(snapshot_file.read_text())
                return ContextSnapshot.from_dict(data)
            except Exception:
                pass
        
        return None


# Singleton instance for convenience
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get or create the singleton ContextManager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


def compute_context_hash(recent_events: Optional[List[str]] = None) -> str:
    """
    Convenience function to compute the current context hash.
    
    Args:
        recent_events: Optional list of recent event strings
        
    Returns:
        SHA-256 hash (truncated to 16 chars) of current world-state
    """
    cm = get_context_manager()
    state_hash, _ = cm.compute_world_state_hash(recent_events=recent_events)
    return state_hash


def verify_turn_integrity(before_hash: str, after_hash: str,
                          allowed_drift: float = 0.0) -> bool:
    """
    Simple verification that state hasn't drifted unexpectedly.
    
    Args:
        before_hash: Hash from before agent turn
        after_hash: Hash from after agent turn
        allowed_drift: Currently unused, reserved for fuzzy matching
        
    Returns:
        True if hashes match (no drift), False otherwise
    """
    return before_hash == after_hash
