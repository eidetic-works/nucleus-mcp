"""
Core tests for Nucleus MCP
"""

import json
import tempfile
import os
from pathlib import Path

import pytest


class TestBrainPath:
    """Tests for brain path functionality."""
    
    def test_get_brain_path_default(self):
        """Test default brain path."""
        from mcp_server_nucleus import get_brain_path
        
        # Clear env var
        old_val = os.environ.pop("NUCLEAR_BRAIN_PATH", None)
        
        try:
            path = get_brain_path()
            assert path == Path(".brain")
        finally:
            if old_val:
                os.environ["NUCLEAR_BRAIN_PATH"] = old_val
    
    def test_get_brain_path_from_env(self):
        """Test brain path from environment variable."""
        from mcp_server_nucleus import get_brain_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_brain"
            os.environ["NUCLEAR_BRAIN_PATH"] = str(test_path)
            
            try:
                path = get_brain_path()
                assert path == test_path
                assert path.exists()  # Should be created
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


class TestMakeResponse:
    """Tests for response formatting."""
    
    def test_make_response_success(self):
        """Test successful response format."""
        from mcp_server_nucleus import make_response
        
        response = make_response(True, "Test message")
        data = json.loads(response)
        
        assert data["success"] is True
        assert data["message"] == "Test message"
        assert "timestamp" in data
    
    def test_make_response_failure(self):
        """Test failure response format."""
        from mcp_server_nucleus import make_response
        
        response = make_response(False, "Error message")
        data = json.loads(response)
        
        assert data["success"] is False
        assert data["message"] == "Error message"
    
    def test_make_response_with_data(self):
        """Test response with additional data."""
        from mcp_server_nucleus import make_response
        
        response = make_response(True, "Test", {"key": "value"})
        data = json.loads(response)
        
        assert data["data"]["key"] == "value"


class TestStateManagement:
    """Tests for state management."""
    
    def test_get_state_empty(self):
        """Test getting state when empty."""
        from mcp_server_nucleus import _get_state, get_brain_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                state = _get_state()
                assert state == {}
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)
    
    def test_update_state(self):
        """Test updating state."""
        from mcp_server_nucleus import _update_state, _get_state
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                _update_state({"test_key": "test_value"})
                state = _get_state()
                
                assert state["test_key"] == "test_value"
                assert "last_updated" in state
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


class TestEventEmission:
    """Tests for event logging."""
    
    def test_emit_event(self):
        """Test event emission."""
        from mcp_server_nucleus import _emit_event, get_brain_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                _emit_event("TEST_EVENT", {"key": "value"})
                
                events_path = Path(tmpdir) / "ledger" / "events.jsonl"
                assert events_path.exists()
                
                with open(events_path) as f:
                    line = f.readline()
                    event = json.loads(line)
                
                assert event["type"] == "TEST_EVENT"
                assert event["data"]["key"] == "value"
                assert "timestamp" in event
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


class TestEngramTools:
    """Tests for engram (memory) tools."""
    
    def test_write_and_query_engram(self):
        """Test writing and querying engrams."""
        from mcp_server_nucleus import brain_write_engram, brain_query_engrams
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                # Write an engram
                result = brain_write_engram(
                    content="Test knowledge",
                    category="test",
                    tags=["unit-test"]
                )
                data = json.loads(result)
                assert data["success"] is True
                assert "engram_id" in data["data"]
                
                # Query engrams
                result = brain_query_engrams(query="knowledge")
                data = json.loads(result)
                assert data["success"] is True
                assert len(data["data"]["engrams"]) > 0
                assert "Test knowledge" in data["data"]["engrams"][0]["content"]
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


class TestSyncTools:
    """Tests for sync functionality."""
    
    def test_identify_agent(self):
        """Test agent identification."""
        from mcp_server_nucleus import brain_identify_agent
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                result = brain_identify_agent("test_agent", "cursor")
                data = json.loads(result)
                
                assert data["success"] is True
                assert data["data"]["agent"]["id"] == "test_agent"
                assert data["data"]["agent"]["type"] == "cursor"
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)
    
    def test_sync_now(self):
        """Test manual sync."""
        from mcp_server_nucleus import brain_sync_now
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                result = brain_sync_now()
                data = json.loads(result)
                
                assert data["success"] is True
                assert "last_sync" in data["data"]["sync"]
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


class TestHealthCheck:
    """Tests for health check."""
    
    def test_brain_health(self):
        """Test brain health check."""
        from mcp_server_nucleus import brain_health
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                result = brain_health()
                data = json.loads(result)
                
                assert "checks" in data["data"]
                assert "uptime_seconds" in data["data"]["checks"]
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
