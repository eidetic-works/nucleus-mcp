"""
Gatekeeper: The Permission Broker.
Manages user consent ("CapabilityGrants") for sensitive operations.

Strategic Role:
- PERSISTENT: Remembers what the user allowed.
- GRANULAR: "Network: google.com" != "Network: *".
- INTERACTIVE: Bridges the gap between Agent Request and User Decision.
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel

logger = logging.getLogger("GATEKEEPER")

ACCESS_DENIED = False
ACCESS_GRANTED = True

class GrantRequest(BaseModel):
    agent_id: str
    capability: str
    params: Dict[str, Any] # e.g. {"domain": "google.com"} or {"path": "/tmp"}
    
    def fingerprint(self) -> str:
        """Unique hash for this request signature"""
        # Canonicalize params
        import json
        param_str = json.dumps(self.params, sort_keys=True)
        raw = f"{self.agent_id}|{self.capability}|{param_str}"
        return hashlib.sha256(raw.encode()).hexdigest()

class CapabilityGrant(BaseModel):
    request_fingerprint: str
    agent_id: str
    capability: str
    params: Dict[str, Any]
    granted_at: str # ISO Timestamp
    granted_by: str = "user"

class Gatekeeper:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.ledger_path = brain_path / "ledger" / "permissions.json"
        self._cache_grants: Dict[str, CapabilityGrant] = {}
        self._load_ledger()
        
    def _load_ledger(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if self.ledger_path.exists():
            try:
                data = json.loads(self.ledger_path.read_text())
                for item in data:
                    grant = CapabilityGrant(**item)
                    self._cache_grants[grant.request_fingerprint] = grant
            except Exception as e:
                logger.error(f"Failed to load permission ledger: {e}")
                
    def _save_ledger(self):
        data = [g.model_dump() for g in self._cache_grants.values()]
        self.ledger_path.write_text(json.dumps(data, indent=2))
        
    def check_permission(self, request: GrantRequest) -> bool:
        """
        Check if a grant exists for this specific request.
        """
        fp = request.fingerprint()
        if fp in self._cache_grants:
            return ACCESS_GRANTED
            
        # TODO: Implement wildcard support? 
        # For Phase 57, we do strict equality.
        
        return ACCESS_DENIED
        
    def grant_permission(self, request: GrantRequest):
        """
        Persist a new grant.
        """
        from datetime import datetime
        fp = request.fingerprint()
        
        grant = CapabilityGrant(
            request_fingerprint=fp,
            agent_id=request.agent_id,
            capability=request.capability,
            params=request.params,
            granted_at=datetime.now().isoformat()
        )
        
        self._cache_grants[fp] = grant
        self._save_ledger()
        logger.info(f"Granted permission: {request.agent_id} -> {request.capability} {request.params}")
        
    def revoke_permission(self, request: GrantRequest):
        """
        Revoke a grant.
        """
        fp = request.fingerprint()
        if fp in self._cache_grants:
            del self._cache_grants[fp]
            self._save_ledger()
            logger.info(f"Revoked permission: {request.agent_id}")
