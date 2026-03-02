
"""
Policy Engine for Nucleus Daemon.
Handles 'Adaptive Policy' (Directives) and 'Bounded Autonomy' (Mission Parameters).

Strategic Role:
- Reads `directives.md` to align Daemon with user intent.
- Enforces `MissionParameters` (Budget, Time, Safety) to prevent "Strategic Drift".
- Provides the `SafetyLevel` context for "Unshackled" operations.
"""

from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict
import json 
import logging

logger = logging.getLogger(__name__)

class SafetyLevel(Enum):
    SAFE = "safe"           # Standard SaaS-like filters
    MODERATE = "moderate"   # Less restrictive, warns on high risk
    RAW = "raw"             # "Unshackled" - No middleware constraints (User liability)

class ExecutionMode(Enum):
    PLANNING = "planning"
    EXECUTION = "execution"
    VERIFICATION = "verification"

@dataclass
class MissionParameters:
    """The Compact: Bounded Autonomy Agreement"""
    max_budget_usd: float = 1.0
    max_steps: int = 10
    timeout_seconds: int = 600
    allowed_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)
    safety_level: SafetyLevel = SafetyLevel.SAFE
    # If true, requires explicit human ratification before "Write" actions
    require_ratification: bool = False

class DirectivesLoader:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.directives_path = brain_path / "ledger" / "directives.md"
        # Support json config as alternative
        self.config_path = brain_path / "ledger" / "policy.json"

    def load_policy(self) -> Dict:
        """Load the current policy directives"""
        policy = {
            "mode": "default",
            "priorities": [],
            "constraints": [],
            "safety_level": SafetyLevel.SAFE.value
        }
        
        # 1. Try Config JSON first (Structured)
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    if data:
                        policy.update(data)
            except Exception as e:
                logger.error(f"Failed to load policy.json: {e}")

        # 2. Parse Markdown Directives (Context)
        # For now, we just verify it exists to be available for LLM context injection
        # In Phase 60, we might NLP parse strict rules from MD.
        policy["directives_text"] = self._read_directives_text()
        
        return policy

    def _read_directives_text(self) -> str:
        if self.directives_path.exists():
            return self.directives_path.read_text()
        return "No directives found. Operate in default safe mode."

    def get_mission_parameters(self, task_type: str) -> MissionParameters:
        """Factory for Mission Parameters based on Task Type"""
        policy = self.load_policy()
        safety_val = policy.get("safety_level", "safe")
        
        try:
            safety = SafetyLevel(safety_val)
        except ValueError:
            safety = SafetyLevel.SAFE

        # Default Profiles
        if task_type == "quick_check":
            return MissionParameters(
                max_budget_usd=0.05,
                max_steps=5,
                timeout_seconds=60,
                safety_level=safety
            )
        elif task_type == "deep_research":
            return MissionParameters(
                max_budget_usd=2.0,
                max_steps=30,
                timeout_seconds=1800,
                safety_level=safety,
                blocked_tools=["write_to_file", "run_command"] # Read only
            )
        elif task_type == "autonomous_fix":
            return MissionParameters(
                max_budget_usd=0.5,
                max_steps=15,
                timeout_seconds=300,
                safety_level=safety,
                require_ratification=True # Fixes usually need approval in V1
            )
        
        # Default
        return MissionParameters(safety_level=safety)
