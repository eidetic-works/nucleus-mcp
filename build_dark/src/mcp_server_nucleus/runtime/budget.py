"""
BudgetAuditor: The Financial Fuse.
Strictly enforces spending limits for Nucleus operations.

Strategic Role:
- Tracks cumulative spend across sessions.
- "Hard Fuse": Cuts off execution if budget exceeded.
- Uses BrainLock for accurate accounting.
- Supports Per-Agent BudgetGuard.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from .locking import get_lock
from .capabilities.base import Capability

logger = logging.getLogger("BUDGET_AUDITOR")

class BudgetAuditor:
    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.ledger_path = brain_path / "ledger" / "budget_ledger.json"
        
        # Ensure ledger dir exists
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
    def _load_ledger(self) -> Dict:
        if self.ledger_path.exists():
            try:
                return json.loads(self.ledger_path.read_text())
            except Exception:
                pass
        return {
            "total_spend_usd": 0.0,
            "daily_spend_usd": {}, # "YYYY-MM-DD": float
            "agent_spend_usd": {}, # "str(agent_id)": float (Cumulative)
            "transactions": []
        }
        
    def _save_ledger(self, ledger: Dict):
        self.ledger_path.write_text(json.dumps(ledger, indent=2))
        
    def check_authorization(self, completed_cost: float = 0.0) -> bool:
        """
        Global check (Not agent specific).
        For now, just a placeholder or daily limit check.
        """
        return True

    def record_expense(self, amount_usd: float, description: str, source: str = "llm"):
        """Record a completed expense globally and per-agent"""
        with get_lock("budget", self.brain_path).section():
            ledger = self._load_ledger()
            today = datetime.now().strftime("%Y-%m-%d")
            
            ledger["total_spend_usd"] += amount_usd
            ledger["daily_spend_usd"][today] = ledger["daily_spend_usd"].get(today, 0.0) + amount_usd
            
            # If source is an agent ID, track per agent
            if source:
                 ledger["agent_spend_usd"][source] = ledger["agent_spend_usd"].get(source, 0.0) + amount_usd
            
            ledger["transactions"].append({
                "timestamp": datetime.now().isoformat(),
                "amount": amount_usd,
                "description": description,
                "source": source
            })
            
            # Trim transactions if too long
            if len(ledger["transactions"]) > 1000:
                ledger["transactions"] = ledger["transactions"][-1000:]
                
            self._save_ledger(ledger)
            
    def get_agent_spend(self, agent_id: str) -> float:
        """Get total spend for a specific agent"""
        ledger = self._load_ledger()
        return ledger.get("agent_spend_usd", {}).get(agent_id, 0.0)


class BudgetGuard(Capability):
    """
    Wraps an imported capability to enforce strict budget limits for a specific agent.
    "Host Policy overrides Agent Policy".
    """
    def __init__(self, inner: Capability, auditor: BudgetAuditor, agent_id: str, max_budget_usd: float = 0.0):
        # Initialize Abstract Base Class
        # Note: We don't call super().__init__() because ABCs don't need it, 
        # but we must ensure we don't violate property requirements.
        self.inner = inner
        self.auditor = auditor
        self.agent_id = agent_id
        self.max_budget_usd = max_budget_usd
        
        # Load initial spend state
        self.spent_usd = self.auditor.get_agent_spend(agent_id)

    @property
    def name(self) -> str:
        return self.inner.name

    @property
    def description(self) -> str:
        return f"{self.inner.description} (Budget: ${self.max_budget_usd})"

    def get_tools(self) -> List[Dict[str, Any]]:
        # We might want to wrap tool descriptions too, but for now we delegate
        return self.inner.get_tools()
        
    def execute(self, params: Dict[str, Any]) -> str:
        # Sync simple spending state (in case other tools updated it)
        self.spent_usd = self.auditor.get_agent_spend(self.agent_id)

        # 1. Pre-Check (Hard Fuse)
        if self.spent_usd >= self.max_budget_usd and self.max_budget_usd >= 0: 
            # Note: We can treat max_budget_usd < 0 as infinite if we wanted, 
            # but for now let's say >=0 is required.
            if self.max_budget_usd == 0:
                 return "❌ SECURITY BLOCK: Zero Cost Budget Enforced."
            
            # Allow execution if we are extremely close (floating point epsilon) 
            # OR if we want to strict block. Let's strict block.
            return f"❌ SECURITY BLOCK: Budget Exceeded (${self.spent_usd:.4f}/${self.max_budget_usd:.2f})"
            
        # 2. Execute Inner Tool
        logger.info(f"💰 BudgetGuard Allowing {self.agent_id} call (Spent: ${self.spent_usd})")
        try:
            result = self.inner.execute(params)
        except Exception as e:
            # Even if it fails, did it cost money? 
            # For network tools/LLM, yes. For local function errors, maybe not.
            # We assume "Attempted Execution" costs standard rate for now.
             result = f"Error: {e}"

        # 3. Post-Check (Record Cost)
        # In a real system, we'd measure token usage or network bytes.
        # For simulation/Phase 57, we assume a flat rate per tool call.
        COST_PER_CALL = 0.01 
        
        self.auditor.record_expense(
            amount_usd=COST_PER_CALL,
            description=f"Action: {self.inner.name}",
            source=self.agent_id
        )
        
        # Update local tracking
        self.spent_usd += COST_PER_CALL
        
        return result
