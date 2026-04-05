"""
Budget Alerts - Cost threshold monitoring for Agent Runtime V2
===============================================================
Monitors agent execution costs and triggers alerts when thresholds are exceeded.

Part of Phase 68: Agent Runtime V2 Enhancement
"""

import os
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from .agent_runtime_v2 import get_execution_manager, AgentCostTracker

logger = logging.getLogger("nucleus.budget_alerts")

# Configuration
BUDGET_ALERT_DAILY_USD = float(os.environ.get("NUCLEUS_BUDGET_DAILY_USD", "10.0"))
BUDGET_ALERT_HOURLY_USD = float(os.environ.get("NUCLEUS_BUDGET_HOURLY_USD", "2.0"))
BUDGET_ALERT_PER_AGENT_USD = float(os.environ.get("NUCLEUS_BUDGET_PER_AGENT_USD", "0.50"))


@dataclass
class BudgetAlert:
    """Represents a budget alert."""
    alert_type: str  # "daily", "hourly", "per_agent"
    threshold_usd: float
    current_usd: float
    percentage: float
    timestamp: str
    agent_id: Optional[str] = None
    persona: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_type": self.alert_type,
            "threshold_usd": self.threshold_usd,
            "current_usd": self.current_usd,
            "percentage": self.percentage,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "persona": self.persona
        }


class BudgetMonitor:
    """
    Monitors agent execution costs against configured budgets.
    Triggers alerts via Telegram or custom callbacks.
    """
    
    def __init__(
        self,
        daily_budget_usd: float = BUDGET_ALERT_DAILY_USD,
        hourly_budget_usd: float = BUDGET_ALERT_HOURLY_USD,
        per_agent_budget_usd: float = BUDGET_ALERT_PER_AGENT_USD,
        alert_callback: Optional[Callable[[BudgetAlert], None]] = None
    ):
        self.daily_budget_usd = daily_budget_usd
        self.hourly_budget_usd = hourly_budget_usd
        self.per_agent_budget_usd = per_agent_budget_usd
        self.alert_callback = alert_callback or self._default_alert
        
        self._alerts_sent: Dict[str, str] = {}  # Prevent duplicate alerts
        self._daily_spend: float = 0.0
        self._hourly_spend: float = 0.0
        self._last_hourly_reset: datetime = datetime.now(timezone.utc)
        self._last_daily_reset: datetime = datetime.now(timezone.utc)
    
    def check_agent_cost(self, agent_id: str, persona: str, cost_usd: float) -> Optional[BudgetAlert]:
        """Check if a single agent's cost exceeds the per-agent budget."""
        if cost_usd > self.per_agent_budget_usd:
            alert = BudgetAlert(
                alert_type="per_agent",
                threshold_usd=self.per_agent_budget_usd,
                current_usd=cost_usd,
                percentage=(cost_usd / self.per_agent_budget_usd) * 100,
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent_id=agent_id,
                persona=persona
            )
            self._trigger_alert(alert)
            return alert
        return None
    
    def record_spend(self, cost_usd: float) -> Optional[BudgetAlert]:
        """Record spending and check hourly/daily budgets."""
        now = datetime.now(timezone.utc)
        
        # Reset hourly if needed
        if (now - self._last_hourly_reset).total_seconds() > 3600:
            self._hourly_spend = 0.0
            self._last_hourly_reset = now
        
        # Reset daily if needed
        if (now - self._last_daily_reset).total_seconds() > 86400:
            self._daily_spend = 0.0
            self._last_daily_reset = now
        
        self._hourly_spend += cost_usd
        self._daily_spend += cost_usd
        
        # Check hourly budget
        if self._hourly_spend > self.hourly_budget_usd:
            alert_key = f"hourly_{self._last_hourly_reset.isoformat()}"
            if alert_key not in self._alerts_sent:
                alert = BudgetAlert(
                    alert_type="hourly",
                    threshold_usd=self.hourly_budget_usd,
                    current_usd=self._hourly_spend,
                    percentage=(self._hourly_spend / self.hourly_budget_usd) * 100,
                    timestamp=now.isoformat()
                )
                self._trigger_alert(alert)
                self._alerts_sent[alert_key] = now.isoformat()
                return alert
        
        # Check daily budget
        if self._daily_spend > self.daily_budget_usd:
            alert_key = f"daily_{self._last_daily_reset.isoformat()}"
            if alert_key not in self._alerts_sent:
                alert = BudgetAlert(
                    alert_type="daily",
                    threshold_usd=self.daily_budget_usd,
                    current_usd=self._daily_spend,
                    percentage=(self._daily_spend / self.daily_budget_usd) * 100,
                    timestamp=now.isoformat()
                )
                self._trigger_alert(alert)
                self._alerts_sent[alert_key] = now.isoformat()
                return alert
        
        return None
    
    def _trigger_alert(self, alert: BudgetAlert) -> None:
        """Trigger the alert callback."""
        try:
            self.alert_callback(alert)
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
    
    def _default_alert(self, alert: BudgetAlert) -> None:
        """Default alert handler - logs and sends Telegram notification."""
        logger.warning(f"Budget alert: {alert.alert_type} - ${alert.current_usd:.4f} / ${alert.threshold_usd:.4f}")
        self._send_telegram_alert(alert)
    
    def _send_telegram_alert(self, alert: BudgetAlert) -> bool:
        """Send alert via all configured notification channels."""
        emoji = {"daily": "📊", "hourly": "⏰", "per_agent": "🤖"}.get(alert.alert_type, "⚠️")

        message = (
            f"{emoji} Budget Alert: {alert.alert_type.upper()}\n"
            f"Current: ${alert.current_usd:.4f}\n"
            f"Threshold: ${alert.threshold_usd:.4f}\n"
            f"Usage: {alert.percentage:.1f}%\n"
            f"Time: {alert.timestamp}"
        )
        if alert.agent_id:
            message += f"\nAgent: {alert.agent_id} ({alert.persona})"

        try:
            from .channels import get_channel_router
            router = get_channel_router()
            results = router.notify("Budget Alert", message, level="warning")
            return any(results.values())
        except Exception as e:
            logger.error(f"Channel alert failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        return {
            "daily": {
                "budget_usd": self.daily_budget_usd,
                "spent_usd": self._daily_spend,
                "remaining_usd": max(0, self.daily_budget_usd - self._daily_spend),
                "percentage": (self._daily_spend / self.daily_budget_usd) * 100
            },
            "hourly": {
                "budget_usd": self.hourly_budget_usd,
                "spent_usd": self._hourly_spend,
                "remaining_usd": max(0, self.hourly_budget_usd - self._hourly_spend),
                "percentage": (self._hourly_spend / self.hourly_budget_usd) * 100
            },
            "per_agent_limit_usd": self.per_agent_budget_usd,
            "alerts_sent": len(self._alerts_sent)
        }


# Global instance
_budget_monitor: Optional[BudgetMonitor] = None


def get_budget_monitor() -> BudgetMonitor:
    """Get or create global budget monitor."""
    global _budget_monitor
    if _budget_monitor is None:
        _budget_monitor = BudgetMonitor()
    return _budget_monitor
