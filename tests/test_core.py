"""
Core tests for Nucleus MCP - Updated for v1.0.5 API
"""

import json
import tempfile
import os
from pathlib import Path

import pytest


class TestBrainPath:
    """Tests for brain path functionality."""
    
    def test_get_brain_path_requires_env(self):
        """Test that brain path requires env var (v1.0+ behavior)."""
        from mcp_server_nucleus import get_brain_path
        
        # Clear env var
        old_val = os.environ.pop("NUCLEAR_BRAIN_PATH", None)
        
        try:
            with pytest.raises(ValueError):
                get_brain_path()
        finally:
            if old_val:
                os.environ["NUCLEAR_BRAIN_PATH"] = old_val
    
    def test_get_brain_path_from_env(self):
        """Test brain path from environment variable."""
        from mcp_server_nucleus import get_brain_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                path = get_brain_path()
                assert path == Path(tmpdir)
                assert path.exists()
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


class TestMakeResponse:
    """Tests for response formatting."""
    
    def test_make_response_success(self):
        """Test successful response format."""
        from mcp_server_nucleus import make_response
        
        response = make_response(True, data={"key": "value"})
        data = json.loads(response)
        
        assert data["success"] is True
        assert data["data"]["key"] == "value"
        assert "timestamp" in data
    
    def test_make_response_failure(self):
        """Test failure response format."""
        from mcp_server_nucleus import make_response
        
        response = make_response(False, error="Error message")
        data = json.loads(response)
        
        assert data["success"] is False
        assert data["error"] == "Error message"
    
    def test_make_response_with_error_code(self):
        """Test response with error code."""
        from mcp_server_nucleus import make_response
        
        response = make_response(False, error="Not found", error_code="ERR_NOT_FOUND")
        data = json.loads(response)
        
        assert data["error_code"] == "ERR_NOT_FOUND"


class TestStateManagement:
    """Tests for state management."""
    
    def test_get_state_empty(self):
        """Test getting state when empty."""
        from mcp_server_nucleus import _get_state
        
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
            # Create ledger directory
            Path(tmpdir, "ledger").mkdir(parents=True, exist_ok=True)
            
            try:
                result = _update_state({"test_key": "test_value"})
                assert "successfully" in result.lower() or "error" not in result.lower()
                
                state = _get_state()
                assert state.get("test_key") == "test_value"
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


class TestEventEmission:
    """Tests for event logging."""
    
    def test_emit_event(self):
        """Test event emission."""
        from mcp_server_nucleus import _emit_event
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            # Create ledger directory (required for event writing)
            Path(tmpdir, "ledger").mkdir(parents=True, exist_ok=True)
            
            try:
                _emit_event("TEST_EVENT", "test_emitter", {"key": "value"})
                
                events_path = Path(tmpdir) / "ledger" / "events.jsonl"
                assert events_path.exists()
                
                with open(events_path) as f:
                    line = f.readline()
                    event = json.loads(line)
                
                assert event["type"] == "TEST_EVENT"
                assert event["data"]["key"] == "value"
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


class TestEngramTools:
    """Tests for engram (memory) tools."""
    
    def test_write_and_query_engram(self):
        """Test writing and querying engrams."""
        from mcp_server_nucleus import _brain_write_engram_impl, _brain_query_engrams_impl
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                # Write an engram (context must be valid: Feature, Architecture, Brand, Strategy, Decision)
                result = _brain_write_engram_impl(
                    key="test_key",
                    value="Test knowledge",
                    context="Decision",
                    intensity=5
                )
                data = json.loads(result)
                assert data["success"] is True
                assert "engram" in data["data"]
                assert data["data"]["engram"]["key"] == "test_key"
                
                # Query engrams by context
                result = _brain_query_engrams_impl(context="Decision", min_intensity=1)
                data = json.loads(result)
                assert data["success"] is True
                assert len(data["data"]["engrams"]) > 0
                assert "Test knowledge" in data["data"]["engrams"][0]["value"]
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
                # Call the public function directly
                result = brain_identify_agent("test_agent", "cursor")
                data = json.loads(result)
                
                # v1.0.5 returns flat structure with agent_id
                assert data["agent_id"] == "test_agent"
                assert data["environment"] == "cursor"
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
                
                # Returns error when sync not enabled (expected behavior)
                assert "error" in data or "status" in data or "success" in data
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


class TestHealthCheck:
    """Tests for health check."""
    
    def test_brain_health(self):
        """Test brain health check."""
        from mcp_server_nucleus import _brain_health_impl
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["NUCLEAR_BRAIN_PATH"] = tmpdir
            
            try:
                result = _brain_health_impl()
                data = json.loads(result)
                
                # v1.0.5 returns flat structure with status
                assert "status" in data
                assert "uptime_seconds" in data
            finally:
                os.environ.pop("NUCLEAR_BRAIN_PATH", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
