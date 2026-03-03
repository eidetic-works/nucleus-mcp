"""
TeamManager: The Hive Mind.
Manages Shared Configuration and Trust Roots for the Team.

Strategic Role:
- SYNC: Ensures all agents on the team use the same Registry.
- TRUST: Distributes the Team Lead's public keys.
- POLICY: Enforces team-wide rules (e.g. "Signed Only").
"""

import json
import logging
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger("TEAM")

class TeamPolicy(BaseModel):
    require_signed: bool = True
    min_trust_level: str = "verified"

class TeamConfig(BaseModel):
    team_id: str
    name: str
    registry_url: Optional[str] = None
    trusted_keys: List[str] = []
    policy: TeamPolicy = Field(default_factory=TeamPolicy)

class TeamManager:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.config_path = brain_path / "config" / "team.json"
        
    def get_config(self) -> Optional[TeamConfig]:
        """Load and return the current team configuration."""
        if not self.config_path.exists():
            return None
            
        try:
            data = json.loads(self.config_path.read_text())
            return TeamConfig(**data)
        except Exception as e:
            logger.error(f"Failed to load team config: {e}")
            return None

    def get_trusted_roots(self) -> List[str]:
        """Return the list of trusted key fingerprints defined by the team."""
        config = self.get_config()
        if config:
            return config.trusted_keys
        return []
        
    def get_registry_url(self) -> Optional[str]:
        """Return the team's private registry URL if configured."""
        config = self.get_config()
        if config:
            return config.registry_url
        return None
