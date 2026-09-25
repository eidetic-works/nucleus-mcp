import pytest
from mcp_server_nucleus.runtime.founder_absence import readiness_score, enter_quiescent_mode

def test_readiness_score(monkeypatch):
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_discover_tools", lambda: True)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_route_messages", lambda: True)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_rebuild_memory_index", lambda: True)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_triage_alerts", lambda: True)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.are_endpoints_monitored", lambda: True)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_generate_reports", lambda: True)

    score = readiness_score()
    assert score == 1.0

def test_readiness_score_partial(monkeypatch):
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_discover_tools", lambda: True)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_route_messages", lambda: False)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_rebuild_memory_index", lambda: True)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_triage_alerts", lambda: False)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.are_endpoints_monitored", lambda: True)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.can_generate_reports", lambda: False)

    score = readiness_score()
    assert score == 0.5

def test_enter_quiescent_mode_success(monkeypatch):
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.readiness_score", lambda: 0.8)
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.run_autonomous_maintenance", lambda: {"fake": "results"})

    res = enter_quiescent_mode(12)
    assert res["success"] is True
    assert res["mode"] == "quiescent"

def test_enter_quiescent_mode_failure(monkeypatch):
    monkeypatch.setattr("mcp_server_nucleus.runtime.founder_absence.readiness_score", lambda: 0.2)

    res = enter_quiescent_mode(12)
    assert res["success"] is False
    assert res["error"] == "Readiness too low"
