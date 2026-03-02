"""
Tests for Budget Alerts - Cost threshold monitoring
"""

import pytest
from unittest.mock import patch, MagicMock

from mcp_server_nucleus.runtime.budget_alerts import (
    BudgetMonitor, BudgetAlert, get_budget_monitor
)


class TestBudgetAlert:
    """Tests for BudgetAlert dataclass."""
    
    def test_create_alert(self):
        alert = BudgetAlert(
            alert_type="daily",
            threshold_usd=10.0,
            current_usd=12.0,
            percentage=120.0,
            timestamp="2026-02-24T10:00:00Z"
        )
        assert alert.alert_type == "daily"
        assert alert.threshold_usd == 10.0
        assert alert.current_usd == 12.0
    
    def test_to_dict(self):
        alert = BudgetAlert(
            alert_type="per_agent",
            threshold_usd=0.5,
            current_usd=0.75,
            percentage=150.0,
            timestamp="2026-02-24T10:00:00Z",
            agent_id="agent-123",
            persona="researcher"
        )
        d = alert.to_dict()
        assert d["agent_id"] == "agent-123"
        assert d["persona"] == "researcher"


class TestBudgetMonitor:
    """Tests for BudgetMonitor."""
    
    @pytest.fixture
    def monitor(self):
        return BudgetMonitor(
            daily_budget_usd=10.0,
            hourly_budget_usd=2.0,
            per_agent_budget_usd=0.5
        )
    
    def test_check_agent_under_budget(self, monitor):
        alert = monitor.check_agent_cost("agent-1", "devops", 0.25)
        assert alert is None
    
    def test_check_agent_over_budget(self, monitor):
        alerts = []
        monitor.alert_callback = lambda a: alerts.append(a)
        
        alert = monitor.check_agent_cost("agent-1", "devops", 0.75)
        assert alert is not None
        assert alert.alert_type == "per_agent"
        assert len(alerts) == 1
    
    def test_record_spend_under_hourly(self, monitor):
        alert = monitor.record_spend(0.5)
        assert alert is None
    
    def test_record_spend_over_hourly(self, monitor):
        alerts = []
        monitor.alert_callback = lambda a: alerts.append(a)
        
        monitor.record_spend(1.5)
        alert = monitor.record_spend(1.0)  # Now over 2.0
        
        assert alert is not None
        assert alert.alert_type == "hourly"
    
    def test_record_spend_over_daily(self, monitor):
        alerts = []
        monitor.alert_callback = lambda a: alerts.append(a)
        
        # Spend over daily (10.0)
        for _ in range(6):
            monitor.record_spend(2.0)  # 12.0 total
        
        # Should have triggered daily alert
        assert any(a.alert_type == "daily" for a in alerts)
    
    def test_duplicate_alert_prevention(self, monitor):
        alerts = []
        monitor.alert_callback = lambda a: alerts.append(a)
        
        # Trigger same hourly alert twice
        monitor.record_spend(3.0)  # Over hourly
        monitor.record_spend(1.0)  # Still over, but shouldn't trigger again
        
        hourly_alerts = [a for a in alerts if a.alert_type == "hourly"]
        assert len(hourly_alerts) == 1  # Only one alert
    
    def test_get_status(self, monitor):
        monitor.record_spend(1.0)
        status = monitor.get_status()
        
        assert status["hourly"]["spent_usd"] == 1.0
        assert status["daily"]["spent_usd"] == 1.0
        assert status["per_agent_limit_usd"] == 0.5
    
    def test_custom_callback(self):
        callback_results = []
        
        def custom_callback(alert):
            callback_results.append(alert.alert_type)
        
        monitor = BudgetMonitor(
            per_agent_budget_usd=0.1,
            alert_callback=custom_callback
        )
        
        monitor.check_agent_cost("agent-1", "test", 0.5)
        
        assert "per_agent" in callback_results


class TestGlobalBudgetMonitor:
    """Tests for global budget monitor instance."""
    
    def test_get_budget_monitor(self):
        monitor1 = get_budget_monitor()
        monitor2 = get_budget_monitor()
        assert monitor1 is monitor2  # Same instance
