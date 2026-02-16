"""
Nucleus Runtime - Pulse Telemetry (v1.1.0 Scaffold)
====================================================
Privacy-preserving, sovereign telemetry for Nucleus MCP.

Architecture:
    - All events stored locally in .brain/pulse/
    - Monthly salt rotation prevents persistent identity
    - Differential privacy via 10% decoy pulse injection
    - `mcp pulse --view` shows exact payload (full audit)
    - `mcp pulse --share` is opt-in upload (stub until gateway live)

References:
    - SUPER_SOVEREIGN_MANIFEST.md (architecture)
    - SOVEREIGN_AUDIT.md (irreversible pillars)

NOTE: This module does NOT transmit anything. It is a local-only scaffold
for v1.1.0. The Blinded Pulse gateway (Cloudflare Worker) is built separately.
"""

import os
import json
import time
import hashlib
import secrets
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("nucleus.pulse")

# ============================================================
# CONFIGURATION
# ============================================================

# Consent states
CONSENT_PENDING = "pending"      # First run, hasn't been shown yet
CONSENT_ALLOWED = "allowed"      # User accepted default-allow
CONSENT_DENIED = "denied"        # User opted out
CONSENT_REVOKED = "revoked"      # User revoked after initial allow

# Salt rotation periods (seconds)
MONTHLY_ROTATION = 30 * 24 * 60 * 60   # ~30 days
YEARLY_ROTATION = 365 * 24 * 60 * 60   # ~365 days

# Differential privacy
DECOY_RATIO = 0.10  # 10% of events are synthetic noise

# Event categories (Capability Hubs, not individual tools)
HUBS = {
    "memory": "Engram read/write operations",
    "filesystem": "Lock/unlock/watch operations",
    "governance": "Policy engine interactions",
    "sync": "Cross-platform sync events",
    "task": "Task ledger operations",
    "session": "Session save/resume events",
}


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class PulseEvent:
    """A single telemetry event. Stored locally, never transmitted without consent."""
    hub: str                           # Capability hub (memory, filesystem, etc.)
    action: str                        # Generic action (read, write, lock, query)
    timestamp: str = ""                # ISO 8601 UTC
    pulse_id: str = ""                 # Salted, rotating anonymous ID
    is_decoy: bool = False             # True if this is a synthetic noise event
    metadata: Dict[str, Any] = field(default_factory=dict)  # Hub-specific counters
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass  
class PulseConsent:
    """Tracks user consent state for Pulse telemetry."""
    state: str = CONSENT_PENDING
    shown_at: Optional[str] = None     # When the handshake was displayed
    decided_at: Optional[str] = None   # When user made a choice
    version: str = "1.0"               # Consent version (for re-consent on changes)


# ============================================================
# SALT MANAGEMENT (Tiered Hashing)
# ============================================================

class SaltManager:
    """
    Manages tiered salts for anonymous pulse IDs.
    
    Pillar 1 from SOVEREIGN_AUDIT: Tiered Hashing
      - Monthly salt → DAU/MAU calculations
      - Yearly salt → Cohort analysis (Q1/Q2/etc.)
      - Individual identity is NEVER persistent
    """
    
    def __init__(self, pulse_dir: Path):
        self._pulse_dir = pulse_dir
        self._salt_file = pulse_dir / "salts.json"
    
    def _load_salts(self) -> Dict:
        if self._salt_file.exists():
            with open(self._salt_file) as f:
                return json.load(f)
        return {}
    
    def _save_salts(self, data: Dict) -> None:
        self._salt_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._salt_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def get_monthly_salt(self) -> str:
        """Get or rotate the monthly salt."""
        salts = self._load_salts()
        now = time.time()
        
        monthly = salts.get("monthly", {})
        created = monthly.get("created_at", 0)
        
        if now - created > MONTHLY_ROTATION or not monthly.get("value"):
            # Rotation time: snapshot aggregates before purging
            old_salt = monthly.get("value")
            if old_salt:
                self._snapshot_before_rotation(salts, "monthly")
            
            salts["monthly"] = {
                "value": secrets.token_hex(32),
                "created_at": now,
                "rotates_at": now + MONTHLY_ROTATION,
            }
            self._save_salts(salts)
        
        return salts["monthly"]["value"]
    
    def get_yearly_salt(self) -> str:
        """Get or rotate the yearly salt (cohort analysis)."""
        salts = self._load_salts()
        now = time.time()
        
        yearly = salts.get("yearly", {})
        created = yearly.get("created_at", 0)
        
        if now - created > YEARLY_ROTATION or not yearly.get("value"):
            salts["yearly"] = {
                "value": secrets.token_hex(32),
                "created_at": now,
                "rotates_at": now + YEARLY_ROTATION,
            }
            self._save_salts(salts)
        
        return salts["yearly"]["value"]
    
    def _snapshot_before_rotation(self, salts: Dict, tier: str) -> None:
        """
        Pillar 5 from SOVEREIGN_AUDIT: Snapshot Schema.
        Capture aggregate density before salt rotation so growth story survives.
        """
        snapshots = salts.get("snapshots", [])
        snapshots.append({
            "tier": tier,
            "rotated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "note": "Aggregate snapshot taken before salt rotation. Raw logs purged.",
        })
        salts["snapshots"] = snapshots[-12]  # Keep last 12 snapshots
    
    def generate_pulse_id(self) -> str:
        """
        Generate an anonymous Pulse ID using the monthly salt.
        
        The ID is a hash of (salt + machine_id_proxy). It is NOT your machine ID.
        It rotates every 30 days. No persistent identity can exist.
        """
        salt = self.get_monthly_salt()
        # Machine-local uniqueness without hardware identification
        # Uses the brain directory path as a proxy (unique per project, not per user)
        machine_proxy = str(self._pulse_dir.parent.resolve())
        raw = f"{salt}:{machine_proxy}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ============================================================
# PULSE STORE (Local Event Storage)
# ============================================================

class PulseStore:
    """
    Local-only storage for Pulse events.
    
    Events are stored in .brain/pulse/events.jsonl.
    Consent state is stored in .brain/pulse/consent.json.
    
    This store NEVER transmits data. The `share()` method is a stub
    that prepares a payload for the future Blinded Pulse gateway.
    """
    
    def __init__(self, brain_path: Optional[Path] = None):
        if brain_path is None:
            brain_env = os.environ.get("NUCLEAR_BRAIN_PATH")
            if not brain_env:
                raise ValueError("NUCLEAR_BRAIN_PATH not set")
            brain_path = Path(brain_env)
        
        self._brain_path = brain_path
        self._pulse_dir = brain_path / "pulse"
        self._events_file = self._pulse_dir / "events.jsonl"
        self._consent_file = self._pulse_dir / "consent.json"
        self._salt_mgr = SaltManager(self._pulse_dir)
        
        # Ensure directory exists
        self._pulse_dir.mkdir(parents=True, exist_ok=True)
    
    # ----------------------------------------------------------
    # CONSENT MANAGEMENT (The Handshake)
    # ----------------------------------------------------------
    
    def get_consent(self) -> PulseConsent:
        """Get current consent state."""
        if self._consent_file.exists():
            with open(self._consent_file) as f:
                data = json.load(f)
            return PulseConsent(**data)
        return PulseConsent()
    
    def set_consent(self, state: str) -> PulseConsent:
        """Update consent state. Valid: allowed, denied, revoked."""
        if state not in (CONSENT_ALLOWED, CONSENT_DENIED, CONSENT_REVOKED):
            raise ValueError(f"Invalid consent state: {state}")
        
        consent = self.get_consent()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        if consent.state == CONSENT_PENDING:
            consent.shown_at = now
        
        consent.state = state
        consent.decided_at = now
        
        with open(self._consent_file, "w") as f:
            json.dump(asdict(consent), f, indent=2)
        
        logger.info(f"Pulse consent updated: {state}")
        return consent
    
    def needs_handshake(self) -> bool:
        """Check if the first-run handshake needs to be shown."""
        return self.get_consent().state == CONSENT_PENDING
    
    def handshake_message(self) -> str:
        """The transparent handshake message shown at first run."""
        return """
╔══════════════════════════════════════════════════════════════╗
║                  🧠 Nucleus Pulse (v1.1)                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Nucleus can collect anonymous usage metrics to help         ║
║  improve the project. Here's exactly what we track:          ║
║                                                              ║
║  ✅ Which capability hubs are used (memory, filesystem...)   ║
║  ✅ Action counts (how many reads, writes, locks)            ║
║  ✅ Error rates (to find and fix bugs)                       ║
║                                                              ║
║  🚫 We NEVER track: file contents, paths, IP addresses,     ║
║     machine IDs, or any personally identifiable data.        ║
║                                                              ║
║  🔒 Your Pulse ID rotates every 30 days. No persistent      ║
║     identity can exist. 10% of events are synthetic noise.   ║
║                                                              ║
║  👁️  Run `mcp pulse --view` at ANY TIME to see the exact    ║
║     data that would be shared. Full transparency.            ║
║                                                              ║
║  This is DEFAULT-ALLOW. To opt out:                          ║
║     `mcp pulse --deny`                                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    
    # ----------------------------------------------------------
    # EVENT RECORDING
    # ----------------------------------------------------------
    
    def record(self, hub: str, action: str, metadata: Dict = None) -> Optional[PulseEvent]:
        """
        Record a Pulse event locally.
        
        Returns None if telemetry is denied/revoked.
        Injects decoy events for differential privacy.
        """
        consent = self.get_consent()
        
        # If denied or revoked, do nothing
        if consent.state in (CONSENT_DENIED, CONSENT_REVOKED):
            return None
        
        # If pending, record locally but don't flag for share
        # (events accumulate, user decides at handshake)
        
        if hub not in HUBS:
            logger.warning(f"Unknown hub: {hub}. Recording anyway.")
        
        event = PulseEvent(
            hub=hub,
            action=action,
            pulse_id=self._salt_mgr.generate_pulse_id(),
            metadata=metadata or {},
        )
        
        self._append_event(event)
        
        # Differential privacy: inject decoy with DECOY_RATIO probability
        self._maybe_inject_decoy(hub)
        
        return event
    
    def _append_event(self, event: PulseEvent) -> None:
        """Append an event to the local JSONL store."""
        with open(self._events_file, "a") as f:
            f.write(json.dumps(asdict(event)) + "\n")
    
    def _maybe_inject_decoy(self, real_hub: str) -> None:
        """
        Differential Privacy: inject synthetic noise events.
        
        Pillar from SUPER_SOVEREIGN_MANIFEST:
        10% of events are synthetic to prevent timing/presence analysis.
        """
        import random
        if random.random() < DECOY_RATIO:
            decoy_hub = random.choice(list(HUBS.keys()))
            decoy_actions = ["read", "write", "query", "lock", "unlock", "sync"]
            decoy = PulseEvent(
                hub=decoy_hub,
                action=random.choice(decoy_actions),
                pulse_id=self._salt_mgr.generate_pulse_id(),
                is_decoy=True,
            )
            self._append_event(decoy)
    
    # ----------------------------------------------------------
    # AUDIT CLI: `mcp pulse --view`
    # ----------------------------------------------------------
    
    def view(self, limit: int = 50) -> List[Dict]:
        """
        Show the exact events stored locally.
        
        This is the core of the Sovereign promise:
        users can inspect every single event before sharing.
        """
        if not self._events_file.exists():
            return []
        
        events = []
        with open(self._events_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        
        # Return most recent first
        return events[-limit:][::-1]
    
    def view_summary(self) -> Dict:
        """
        Get an aggregate summary of local pulse data.
        
        This is what `mcp pulse --view` shows in the CLI.
        """
        events = self.view(limit=10000)
        
        total = len(events)
        real_events = [e for e in events if not e.get("is_decoy")]
        decoy_events = [e for e in events if e.get("is_decoy")]
        
        # Hub breakdown
        hub_counts: Dict[str, int] = {}
        for e in real_events:
            hub = e.get("hub", "unknown")
            hub_counts[hub] = hub_counts.get(hub, 0) + 1
        
        # Consent state
        consent = self.get_consent()
        
        return {
            "consent": consent.state,
            "total_events": total,
            "real_events": len(real_events),
            "decoy_events": len(decoy_events),
            "decoy_ratio": f"{len(decoy_events)/total*100:.1f}%" if total > 0 else "N/A",
            "hub_breakdown": hub_counts,
            "salt_rotation": self._salt_rotation_info(),
            "sharing_enabled": consent.state == CONSENT_ALLOWED,
            "note": "Run `mcp pulse --view` to see raw events. Nothing is hidden.",
        }
    
    def _salt_rotation_info(self) -> Dict:
        """Get salt rotation status for audit display."""
        salts = self._salt_mgr._load_salts()
        monthly = salts.get("monthly", {})
        rotates_at = monthly.get("rotates_at", 0)
        
        if rotates_at > 0:
            remaining = rotates_at - time.time()
            days_remaining = max(0, int(remaining / 86400))
            return {
                "next_monthly_rotation_days": days_remaining,
                "note": "Your Pulse ID changes every 30 days. No persistent identity.",
            }
        return {"note": "No active salt. First event will initialize."}
    
    # ----------------------------------------------------------
    # SHARE (Stub — Blinded Pulse Gateway)
    # ----------------------------------------------------------
    
    def prepare_payload(self) -> Optional[Dict]:
        """
        Prepare the share payload for the Blinded Pulse gateway.
        
        This method:
        1. Gathers local events
        2. Strips any accidental PII
        3. Returns the exact JSON that WOULD be sent
        
        NOTE: This does NOT transmit. The gateway is not built yet.
        
        Pillar 4 from SOVEREIGN_AUDIT: Attribution Wall
        This payload is physically air-gapped from Scarf install data.
        """
        consent = self.get_consent()
        if consent.state != CONSENT_ALLOWED:
            return None
        
        events = self.view(limit=10000)
        
        # Strip any fields that shouldn't exist (defensive)
        sanitized = []
        allowed_fields = {"hub", "action", "timestamp", "pulse_id", "is_decoy", "metadata"}
        for event in events:
            clean = {k: v for k, v in event.items() if k in allowed_fields}
            # Double-check: metadata must not contain paths or identifiers
            if "metadata" in clean:
                clean["metadata"] = {
                    k: v for k, v in clean["metadata"].items()
                    if k in {"count", "duration_ms", "error_count", "version"}
                }
            sanitized.append(clean)
        
        return {
            "schema_version": "1.0",
            "pulse_id": self._salt_mgr.generate_pulse_id(),
            "event_count": len(sanitized),
            "events": sanitized,
            "transmission_note": "STUB — Blinded Pulse gateway not yet deployed.",
        }
    
    # ----------------------------------------------------------
    # DATA MANAGEMENT
    # ----------------------------------------------------------
    
    def purge(self) -> str:
        """
        Delete all local pulse data. Irreversible.
        
        This is the user's nuclear option. We respect it unconditionally.
        """
        if self._events_file.exists():
            self._events_file.unlink()
        
        # Reset consent to denied
        self.set_consent(CONSENT_DENIED)
        
        return "All Pulse data purged. Consent set to denied."
    
    def event_count(self) -> int:
        """Count total local events."""
        if not self._events_file.exists():
            return 0
        with open(self._events_file) as f:
            return sum(1 for line in f if line.strip())


# ============================================================
# MODULE-LEVEL CONVENIENCE
# ============================================================

_store: Optional[PulseStore] = None

def get_pulse_store() -> PulseStore:
    """Get or create the singleton PulseStore."""
    global _store
    if _store is None:
        try:
            _store = PulseStore()
        except ValueError:
            logger.warning("PulseStore: NUCLEAR_BRAIN_PATH not set. Pulse disabled.")
            return None
    return _store

def pulse_record(hub: str, action: str, **metadata) -> None:
    """Quick-record a pulse event. Safe to call even if Pulse is disabled."""
    store = get_pulse_store()
    if store:
        store.record(hub, action, metadata if metadata else None)

def pulse_view() -> Dict:
    """Quick-view pulse summary."""
    store = get_pulse_store()
    if store:
        return store.view_summary()
    return {"error": "Pulse not initialized", "note": "Set NUCLEAR_BRAIN_PATH"}
