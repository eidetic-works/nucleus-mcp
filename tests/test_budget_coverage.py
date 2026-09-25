"""Comprehensive tests for runtime/budget.py — BudgetAuditor, BudgetGuard."""
import json
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import MagicMock

import pytest

from mcp_server_nucleus.runtime.budget import BudgetAuditor, BudgetGuard
from mcp_server_nucleus.runtime.capabilities.base import Capability


class MockCapability(Capability):
    """Mock capability for testing BudgetGuard."""
    def __init__(self, name="mock_tool", description="A mock tool", execute_result="OK"):
        self._name = name
        self._description = description
        self._execute_result = execute_result

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def get_tools(self) -> List[Dict[str, Any]]:
        return [{"name": self._name, "description": self._description}]

    def execute(self, params: Dict[str, Any]) -> str:
        return self._execute_result


class FailingCapability(Capability):
    """Capability that raises on execute."""
    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "Always fails"

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def execute(self, params: Dict[str, Any]) -> str:
        raise RuntimeError("execution failed")


# ── BudgetAuditor ────────────────────────────────────────────────

class TestBudgetAuditor:
    def test_init_creates_dirs(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        assert auditor.brain_path == brain
        assert auditor.ledger_path == brain / "ledger" / "budget_ledger.json"
        assert auditor.ledger_path.parent.exists()

    def test_load_ledger_empty(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        ledger = auditor._load_ledger()
        assert ledger["total_spend_usd"] == 0.0
        assert ledger["daily_spend_usd"] == {}
        assert ledger["agent_spend_usd"] == {}
        assert ledger["transactions"] == []

    def test_load_ledger_existing(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        data = {"total_spend_usd": 1.5, "daily_spend_usd": {"2026-01-01": 1.5},
                "agent_spend_usd": {"agent1": 0.5}, "transactions": [{"t": 1}]}
        auditor.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        auditor.ledger_path.write_text(json.dumps(data))
        ledger = auditor._load_ledger()
        assert ledger["total_spend_usd"] == 1.5
        assert ledger["agent_spend_usd"]["agent1"] == 0.5

    def test_load_ledger_corrupt(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        auditor.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        auditor.ledger_path.write_text("not valid json{{{")
        ledger = auditor._load_ledger()
        assert ledger["total_spend_usd"] == 0.0

    def test_save_ledger(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        data = {"total_spend_usd": 2.0, "daily_spend_usd": {}, "agent_spend_usd": {}, "transactions": []}
        auditor._save_ledger(data)
        loaded = json.loads(auditor.ledger_path.read_text())
        assert loaded["total_spend_usd"] == 2.0

    def test_record_expense(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        auditor.record_expense(0.05, "test call", source="agent1")
        ledger = auditor._load_ledger()
        assert ledger["total_spend_usd"] == 0.05
        assert ledger["agent_spend_usd"]["agent1"] == 0.05
        assert len(ledger["transactions"]) == 1
        assert ledger["transactions"][0]["amount"] == 0.05
        assert ledger["transactions"][0]["description"] == "test call"
        assert ledger["transactions"][0]["source"] == "agent1"

    def test_record_expense_no_source(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        auditor.record_expense(0.10, "global call", source="")
        ledger = auditor._load_ledger()
        assert ledger["total_spend_usd"] == 0.10
        assert "agent_spend_usd" not in ledger or len(ledger["agent_spend_usd"]) == 0

    def test_record_expense_multiple(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        auditor.record_expense(0.01, "call1", source="a1")
        auditor.record_expense(0.02, "call2", source="a2")
        auditor.record_expense(0.03, "call3", source="a1")
        ledger = auditor._load_ledger()
        assert ledger["total_spend_usd"] == 0.06
        assert ledger["agent_spend_usd"]["a1"] == 0.04
        assert ledger["agent_spend_usd"]["a2"] == 0.02
        assert len(ledger["transactions"]) == 3

    def test_record_expense_trims_transactions(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        for i in range(1005):
            auditor.record_expense(0.001, f"call_{i}", source="a1")
        ledger = auditor._load_ledger()
        assert len(ledger["transactions"]) == 1000

    def test_get_agent_spend(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        auditor.record_expense(0.05, "call", source="agent1")
        assert auditor.get_agent_spend("agent1") == 0.05

    def test_get_agent_spend_not_found(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        assert auditor.get_agent_spend("nonexistent") == 0.0

    def test_check_authorization_always_true(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        assert auditor.check_authorization() is True
        assert auditor.check_authorization(completed_cost=100.0) is True


# ── BudgetGuard ──────────────────────────────────────────────────

class TestBudgetGuard:
    def test_init(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        inner = MockCapability()
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=1.0)
        assert guard.inner == inner
        assert guard.auditor == auditor
        assert guard.agent_id == "agent1"
        assert guard.max_budget_usd == 1.0
        assert guard.spent_usd == 0.0

    def test_name_property(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        inner = MockCapability(name="my_tool")
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=1.0)
        assert guard.name == "my_tool"

    def test_description_property(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        inner = MockCapability(description="My desc")
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=1.0)
        assert "My desc" in guard.description
        assert "$1.0" in guard.description

    def test_get_tools_delegates(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        inner = MockCapability()
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=1.0)
        tools = guard.get_tools()
        assert tools == inner.get_tools()

    def test_execute_within_budget(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        inner = MockCapability(execute_result="success")
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=1.0)
        result = guard.execute({"param": "value"})
        assert result == "success"
        assert guard.spent_usd == 0.01
        assert auditor.get_agent_spend("agent1") == 0.01

    def test_execute_zero_budget_blocks(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        inner = MockCapability(execute_result="success")
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=0.0)
        result = guard.execute({})
        assert "SECURITY BLOCK" in result
        assert "Zero Cost Budget" in result

    def test_execute_budget_exceeded_blocks(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        # Pre-record expenses to exceed budget
        auditor.record_expense(0.50, "prior", source="agent1")
        inner = MockCapability(execute_result="success")
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=0.05)
        result = guard.execute({})
        assert "SECURITY BLOCK" in result
        assert "Budget Exceeded" in result

    def test_execute_inner_raises(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        inner = FailingCapability()
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=1.0)
        result = guard.execute({})
        assert "Error:" in result
        assert "execution failed" in result
        # Still records the cost
        assert auditor.get_agent_spend("agent1") == 0.01

    def test_execute_updates_spent_usd(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        inner = MockCapability(execute_result="ok")
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=1.0)
        guard.execute({})
        assert guard.spent_usd == 0.01
        guard.execute({})
        assert guard.spent_usd == 0.02

    def test_init_loads_initial_spend(self, tmp_path):
        brain = tmp_path / "brain"
        auditor = BudgetAuditor(brain)
        auditor.record_expense(0.03, "prior", source="agent1")
        inner = MockCapability()
        guard = BudgetGuard(inner, auditor, "agent1", max_budget_usd=1.0)
        assert guard.spent_usd == 0.03
