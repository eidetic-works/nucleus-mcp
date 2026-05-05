import json
import pytest
from starlette.testclient import TestClient

from starlette.applications import Starlette
from starlette.routing import Route
import mcp_server_nucleus.http_transport.relay_route as rr
from mcp_server_nucleus.runtime.marketplace import register_tool, ReputationSignals

app = Starlette(routes=[Route("/relay/{recipient}/status", rr.get_relay_status, methods=["GET"])])

# Valid tokens for testing (normally NUCLEUS_RELAY_TOKEN_MAP handles this)
# Assuming tests configure NUCLEUS_RELAY_TOKEN_MAP in conftest or similar.

def test_status_includes_tier_badge_for_registered_address(tmp_path, monkeypatch):
    """Register an address, record interactions, verify badge presence and tier."""
    monkeypatch.setenv("NUCLEUS_RELAY_TOKEN_MAP", '{"test-token": "test_sender"}')
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    
    address = "testpeer@nucleus"
    
    # 1. Register
    card_data = {
        "address": address,
        "display_name": "Test Peer",
        "accepts": ["task"],
        "emits": ["result"]
    }
    register_tool(card_data, brain_path=tmp_path)
    
    # 2. Record 5 interactions to bump to 'Active'
    for i in range(5):
        ReputationSignals.record_interaction(
            to_address=address,
            from_address=f"sender-{i}@nucleus",
            latency_ms=100,
            success=True,
            brain_path=tmp_path
        )
        
    # 3. GET status
    client = TestClient(app)
    response = client.get(
        "/relay/testpeer/status",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["recipient"] == "testpeer"
    assert "marketplace" in data
    
    mp = data["marketplace"]
    assert mp is not None
    assert mp["registered"] is True
    # At 5 connections with 100% success rate, tier is Active
    assert mp["tier"] == "Active"
    assert mp["reputation_score"] == 5
    assert mp["last_interaction_at"] is not None

def test_status_marketplace_null_for_unregistered_address(tmp_path, monkeypatch):
    """No registration, GET status, assert marketplace is None and 200."""
    monkeypatch.setenv("NUCLEUS_RELAY_TOKEN_MAP", '{"test-token": "test_sender"}')
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    
    client = TestClient(app)
    response = client.get(
        "/relay/ghost_peer/status",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["recipient"] == "ghost_peer"
    assert "marketplace" in data
    assert data["marketplace"] is None

def test_status_marketplace_lookup_failure_doesnt_break_status(tmp_path, monkeypatch):
    """Monkeypatch lookup_by_address to raise; GET status, assert 200 with marketplace is None."""
    monkeypatch.setenv("NUCLEUS_RELAY_TOKEN_MAP", '{"test-token": "test_sender"}')
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    
    import mcp_server_nucleus.http_transport.relay_route as relay_route
    def _fail_lookup(*args, **kwargs):
        raise RuntimeError("simulated DB crash")
    
    monkeypatch.setattr(relay_route, "lookup_by_address", _fail_lookup, raising=False)
    
    client = TestClient(app)
    response = client.get(
        "/relay/test_peer/status",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["recipient"] == "test_peer"
    assert "marketplace" in data
    assert data["marketplace"] is None
