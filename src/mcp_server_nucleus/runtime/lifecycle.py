"""
LifecycleManager: The Cardiologist.
Tracks the pulse of every agent and enforces the "Tombstone Protocol".

Strategic Role:
- MONITOR: Who is alive? Who is dead?
- CONTROL: Kill switch functionality.
- SECURITY: Once Tombstoned, NEVER Resurrect.
"""

import json
import logging
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
from .locking import get_lock

logger = logging.getLogger("LIFECYCLE")

class AgentState(str, Enum):
    ACTIVE = "active"
    STOPPED = "stopped"
    CRASHED = "crashed"
    TOMBSTONED = "tombstoned" # Permanently banned/killed

class LifecycleManager:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.ledger_path = brain_path / "ledger" / "lifecycle.json"
        
        # Ensure ledger dir exists
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_ledger(self) -> Dict[str, Dict[str, Any]]:
        with get_lock("lifecycle", self.brain_path).section():
            if self.ledger_path.exists():
                try:
                    return json.loads(self.ledger_path.read_text())
                except Exception:
                    pass
            return {}

    def _save_ledger(self, ledger: Dict):
        with get_lock("lifecycle", self.brain_path).section():
            self.ledger_path.write_text(json.dumps(ledger, indent=2))

    def register_agent(self, agent_id: str):
        """Register a new agent instance as ACTIVE."""
        ledger = self._load_ledger()
        
        # Check if already tombstoned
        if agent_id in ledger:
            if ledger[agent_id]["state"] == AgentState.TOMBSTONED:
                raise PermissionError(f"Cannot register Tombstoned agent: {agent_id}")
        
        ledger[agent_id] = {
            "state": AgentState.ACTIVE.value,
            "last_heartbeat": datetime.now().isoformat(),
            "reason": "Registered"
        }
        self._save_ledger(ledger)
        logger.info(f"❤️ Agent Registered: {agent_id}")

    def update_state(self, agent_id: str, new_state: AgentState, reason: str = ""):
        """Transition agent state."""
        ledger = self._load_ledger()
        
        if agent_id not in ledger:
            logger.warning(f"Attempted to update unknown agent: {agent_id}")
            return

        current_state = ledger[agent_id]["state"]

        # PROTOCOL: TOMBSTONE IS FINAL
        if current_state == AgentState.TOMBSTONED:
            if new_state != AgentState.TOMBSTONED:
                logger.error(f"🚫 BLOCKED RESURRECTION of {agent_id}")
                raise PermissionError(f"TOMBSTONE PROTOCOL: {agent_id} cannot be revived.")
            return # No-op if setting to tombstone again

        ledger[agent_id]["state"] = new_state.value
        ledger[agent_id]["reason"] = reason
        ledger[agent_id]["last_heartbeat"] = datetime.now().isoformat()
        
        self._save_ledger(ledger)
        logger.info(f"🔄 State Change: {agent_id} -> {new_state} ({reason})")

    def record_heartbeat(self, agent_id: str):
        """Update last_heartbeat timestamp."""
        ledger = self._load_ledger()
        if agent_id in ledger and ledger[agent_id]["state"] == AgentState.ACTIVE:
            ledger[agent_id]["last_heartbeat"] = datetime.now().isoformat()
            self._save_ledger(ledger)

    def tombstone_agent(self, agent_id: str, reason: str):
        """Permanently disable an agent."""
        self.update_state(agent_id, AgentState.TOMBSTONED, reason)

    def get_state(self, agent_id: str) -> AgentState:
        ledger = self._load_ledger()
        if agent_id not in ledger:
            return AgentState.STOPPED # Default assumption if unknown
        return AgentState(ledger[agent_id]["state"])

    def can_execute(self, agent_id: str) -> bool:
        """Check if agent is allowed to execute commands."""
        state = self.get_state(agent_id)
        if state == AgentState.TOMBSTONED:
            return False
        # We might allow STOPPED to restart, or CRASHED to restart.
        # But TOMBSTONED is hard no.
        return True

    def is_alive(self, agent_id: str, timeout_seconds: int = 60) -> bool:
        """Check if agent is Active and recent heartbeat."""
        ledger = self._load_ledger()
        if agent_id not in ledger:
            return False
            
        data = ledger[agent_id]
        if AgentState(data["state"]) != AgentState.ACTIVE:
            return False
            
        last_hb = datetime.fromisoformat(data["last_heartbeat"])
        if datetime.now() - last_hb > timedelta(seconds=timeout_seconds):
            return False
            
        return True
