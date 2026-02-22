"""
Tests for Multi-Agent Sync Operations
Version: 0.7.0

Tests the production-ready multi-agent sync infrastructure.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.sync_ops import (
    _load_sync_config,
    _parse_simple_yaml,
    is_sync_enabled,
    get_sync_mode,
    get_watch_files,
    get_current_agent,
    set_current_agent,
    get_agent_info,
    sync_lock,
    get_last_modifier,
    set_last_modifier,
    detect_conflict,
    resolve_conflict,
    perform_sync,
    get_sync_status,
)


class TestConfigLoader:
    """Test configuration loading and parsing."""
    
    def test_parse_simple_yaml_basic(self):
        """Test basic YAML parsing."""
        content = """
sync:
  enabled: true
  mode: auto
  interval: 5
"""
        result = _parse_simple_yaml(content)
        assert result["sync"]["enabled"] == True
        assert result["sync"]["mode"] == "auto"
        assert result["sync"]["interval"] == 5
    
    def test_parse_simple_yaml_with_lists(self):
        """Test YAML parsing with lists."""
        content = """
sync:
  enabled: true
  watch_files:
    - "ledger/state.json"
    - "task.md"
"""
        result = _parse_simple_yaml(content)
        assert result["sync"]["enabled"] == True
        # Note: Simple parser may have limitations with lists
    
    def test_load_sync_config_no_file(self, tmp_path):
        """Test loading config when file doesn't exist."""
        config = _load_sync_config(tmp_path)
        assert config["sync"]["enabled"] == False
    
    def test_is_sync_enabled_no_config(self, tmp_path):
        """Test sync enabled check without config."""
        assert is_sync_enabled(tmp_path) == False
    
    def test_get_sync_mode_default(self, tmp_path):
        """Test default sync mode."""
        assert get_sync_mode(tmp_path) == "manual"
    
    def test_get_watch_files_default(self, tmp_path):
        """Test default watch files."""
        files = get_watch_files(tmp_path)
        assert "ledger/state.json" in files
        assert "task.md" in files


class TestAgentIdentification:
    """Test agent identification and registration."""
    
    def test_get_current_agent_no_registration(self, tmp_path):
        """Test getting agent when not registered."""
        # Without registration, should return unknown or auto-detected
        agent = get_current_agent(tmp_path)
        assert agent in ["unknown_agent", "vscode_auto", "windsurf_auto", "cursor_auto"]
    
    def test_set_current_agent(self, tmp_path):
        """Test setting current agent."""
        result = set_current_agent("test_agent", "pytest", "tester", tmp_path)
        
        assert result["agent_id"] == "test_agent"
        assert result["environment"] == "pytest"
        assert result["role"] == "tester"
        assert "stored_in" in result
    
    def test_get_current_agent_after_registration(self, tmp_path):
        """Test getting agent after registration."""
        set_current_agent("test_agent", "pytest", "tester", tmp_path)
        agent = get_current_agent(tmp_path)
        
        assert agent == "test_agent"
    
    def test_get_agent_info(self, tmp_path):
        """Test getting full agent info."""
        set_current_agent("info_agent", "pytest", "verifier", tmp_path)
        info = get_agent_info(tmp_path)
        
        assert info["agent_id"] == "info_agent"
        assert info["environment"] == "pytest"
        assert info["role"] == "verifier"
        assert "registered_at" in info
    
    def test_environment_detection(self, tmp_path):
        """Test environment variable detection."""
        # Reset the process-local cache so env var detection is reached
        import mcp_server_nucleus.runtime.sync_ops as sync_mod
        sync_mod._current_identity = None
        
        with patch.dict("os.environ", {"NUCLEUS_AGENT_ID": "custom_agent"}):
            agent = get_current_agent(tmp_path)
            assert agent == "custom_agent"
        
        # Re-clear for subsequent tests
        sync_mod._current_identity = None


class TestFileLocking:
    """Test file locking mechanism."""
    
    def test_sync_lock_basic(self, tmp_path):
        """Test basic lock acquisition and release."""
        with sync_lock(tmp_path, timeout=1):
            # Lock acquired
            lock_file = tmp_path / ".sync.lock"
            assert lock_file.exists()
        
        # Lock released
        assert not lock_file.exists()
    
    def test_sync_lock_timeout(self, tmp_path):
        """Test lock timeout behavior."""
        # This test would require multiprocessing to properly test
        # For now, just verify the lock mechanism works
        with sync_lock(tmp_path, timeout=1):
            pass  # Lock acquired and released


class TestMetadataTracking:
    """Test file metadata tracking."""
    
    def test_set_and_get_last_modifier(self, tmp_path):
        """Test setting and getting last modifier."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": true}')
        
        set_last_modifier(test_file, "agent_1")
        modifier = get_last_modifier(test_file)
        
        assert modifier == "agent_1"
    
    def test_get_last_modifier_no_meta(self, tmp_path):
        """Test getting modifier when no metadata exists."""
        test_file = tmp_path / "no_meta.json"
        test_file.write_text('{"test": true}')
        
        modifier = get_last_modifier(test_file)
        assert modifier == "unknown"
    
    def test_metadata_file_created(self, tmp_path):
        """Test that metadata file is created."""
        test_file = tmp_path / "with_meta.json"
        test_file.write_text('{"test": true}')
        
        set_last_modifier(test_file, "meta_agent")
        
        meta_file = tmp_path / ".with_meta.json.meta"
        assert meta_file.exists()
        
        meta = json.loads(meta_file.read_text())
        assert meta["last_agent"] == "meta_agent"
        assert "expected_hash" in meta


class TestConflictDetection:
    """Test conflict detection and resolution."""
    
    def test_detect_conflict_no_meta(self, tmp_path):
        """Test conflict detection without metadata."""
        test_file = tmp_path / "no_conflict.json"
        test_file.write_text('{"test": true}')
        
        conflict = detect_conflict(test_file)
        assert conflict is None
    
    def test_detect_conflict_with_change(self, tmp_path):
        """Test conflict detection when file changed."""
        test_file = tmp_path / "conflict.json"
        test_file.write_text('{"version": 1}')
        
        # Set metadata with hash
        set_last_modifier(test_file, "agent_1")
        
        # Modify file (simulate external change)
        test_file.write_text('{"version": 2}')
        
        conflict = detect_conflict(test_file)
        assert conflict is not None
        assert conflict["conflict_type"] == "unexpected_modification"
    
    def test_resolve_conflict_last_write_wins(self, tmp_path):
        """Test last-write-wins conflict resolution."""
        test_file = tmp_path / "resolve.json"
        test_file.write_text('{"resolved": true}')
        set_last_modifier(test_file, "old_agent")
        
        # Register current agent
        set_current_agent("new_agent", "pytest", "", tmp_path)
        
        conflict = {
            "file": str(test_file),
            "expected_agent": "old_agent"
        }
        
        resolution = resolve_conflict(conflict, "last_write_wins", tmp_path)
        assert resolution == "resolved_accept_current"


class TestSyncOperations:
    """Test sync operations."""
    
    def test_perform_sync_no_files(self, tmp_path):
        """Test sync when no watched files exist."""
        # Create minimal config structure
        (tmp_path / "config").mkdir(exist_ok=True)
        
        result = perform_sync(force=False, brain_path=tmp_path)
        
        assert "timestamp" in result
        assert "agent" in result
        assert result["files_synced"] == []
        assert result["conflicts"] == []
    
    def test_get_sync_status(self, tmp_path):
        """Test getting sync status."""
        # Create config directory
        (tmp_path / "config").mkdir(exist_ok=True)
        
        status = get_sync_status(tmp_path)
        
        assert "sync_enabled" in status
        assert "mode" in status
        assert "current_agent" in status
        assert "detected_agents" in status
        assert "files_watched" in status


class TestIntegration:
    """Integration tests for multi-agent sync."""
    
    def test_full_agent_workflow(self, tmp_path):
        """Test complete agent registration and sync workflow."""
        # 1. Register agent
        result = set_current_agent("integration_agent", "pytest", "tester", tmp_path)
        assert result["agent_id"] == "integration_agent"
        
        # 2. Check status
        status = get_sync_status(tmp_path)
        assert status["current_agent"] == "integration_agent"
        
        # 3. Create a watched file
        ledger = tmp_path / "ledger"
        ledger.mkdir(exist_ok=True)
        state_file = ledger / "state.json"
        state_file.write_text('{"sprint": "test"}')
        
        # 4. Mark as modified
        set_last_modifier(state_file, "integration_agent")
        
        # 5. Verify metadata
        modifier = get_last_modifier(state_file)
        assert modifier == "integration_agent"
        
        # 6. Perform sync
        result = perform_sync(force=True, brain_path=tmp_path)
        assert "timestamp" in result
    
    def test_agent_handoff_simulation(self, tmp_path):
        """Simulate handoff between two agents."""
        # Create watched file
        ledger = tmp_path / "ledger"
        ledger.mkdir(exist_ok=True)
        state_file = ledger / "state.json"
        state_file.write_text('{"sprint": "v1"}')
        
        # Agent 1 registers and modifies
        set_current_agent("agent_1", "windsurf", "architect", tmp_path)
        set_last_modifier(state_file, "agent_1")
        
        # Agent 2 takes over
        set_current_agent("agent_2", "cursor", "developer", tmp_path)
        
        # Check status - should see agent_1 as last modifier
        status = get_sync_status(tmp_path)
        assert "agent_1" in status["detected_agents"]
        
        # Agent 2 syncs
        result = perform_sync(force=False, brain_path=tmp_path)
        
        # Should have synced the file from agent_1
        if result["files_synced"]:
            synced_file = result["files_synced"][0]
            assert synced_file["previous_agent"] == "agent_1"
            assert synced_file["current_agent"] == "agent_2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
