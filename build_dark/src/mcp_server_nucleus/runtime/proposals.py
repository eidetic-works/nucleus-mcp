
"""
ProposalOps: Deep Thought & Ratification Engine.
Allows the Daemon to "Think before it Acts" for high-stakes decisions.

Strategic Role:
- Generates "Strategic Briefings" (Option A vs B).
- Handles "Ratification" (User Approval) for Unshackled actions.
- Updates Trust Scores based on successful outcomes.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# Re-use our locking mechanism for safety
from .locking import get_lock

@dataclass
class Proposal:
    id: str
    title: str
    description: str
    options: List[Dict[str, str]] # [{"id": "A", "desc": "Do X"}, {"id": "B", "desc": "Do Y"}]
    risk_level: str # "low", "medium", "high", "critical"
    created_at: str
    status: str = "pending" # pending, ratified, rejected, executed
    ratified_option_id: Optional[str] = None
    
class ProposalOps:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.proposals_dir = brain_path / "ledger" / "proposals"
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_proposal(self, title: str, description: str, options: List[Dict], risk_level: str = "medium") -> Proposal:
        """Create a new decision proposal"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pid = f"prop_{timestamp}"
        
        proposal = Proposal(
            id=pid,
            title=title,
            description=description,
            options=options,
            risk_level=risk_level,
            created_at=datetime.now().isoformat()
        )
        
        self._save_proposal(proposal)
        return proposal
        
    def _save_proposal(self, proposal: Proposal):
        """Save proposal atomically"""
        file_path = self.proposals_dir / f"{proposal.id}.json"
        
        with get_lock("proposals", self.brain_path).section():
            with open(file_path, 'w') as f:
                json.dump(asdict(proposal), f, indent=2)
                
    def get_pending_proposals(self) -> List[Proposal]:
        """List all pending proposals"""
        pending = []
        # No lock needed for simple list unless we want strict consistency
        if not self.proposals_dir.exists():
            return []
            
        for f in self.proposals_dir.glob("prop_*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("status") == "pending":
                    pending.append(Proposal(**data))
            except Exception:
                pass
        return pending

    def ratify_proposal(self, proposal_id: str, option_id: str) -> bool:
        """User validates a proposal"""
        with get_lock("proposals", self.brain_path).section():
            file_path = self.proposals_dir / f"{proposal_id}.json"
            if not file_path.exists():
                return False
                
            data = json.loads(file_path.read_text())
            if data["status"] != "pending":
                return False
                
            # Verify option exists
            if not any(opt["id"] == option_id for opt in data["options"]):
                return False
                
            data["status"] = "ratified"
            data["ratified_option_id"] = option_id
            data["ratified_at"] = datetime.now().isoformat()
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            return True
