"""
v0.6.0 DSoR (Decision System of Record) Test Suite

Tests for:
1. DecisionMade event emission
2. Context Manager state hashing
3. IPC Auth token lifecycle
4. Token metering integration
"""

import os
import tempfile
import shutil
import unittest
from pathlib import Path


class TestContextManager(unittest.TestCase):
    """Tests for context_manager.py"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir(parents=True)
        (self.brain_path / "ledger").mkdir()
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if "NUCLEAR_BRAIN_PATH" in os.environ:
            del os.environ["NUCLEAR_BRAIN_PATH"]
    
    def test_context_manager_import(self):
        """Test that context_manager imports correctly"""
        from mcp_server_nucleus.runtime.context_manager import (
            ContextManager, ContextSnapshot
        )
        self.assertIsNotNone(ContextManager)
        self.assertIsNotNone(ContextSnapshot)
    
    def test_take_snapshot(self):
        """Test taking a context snapshot"""
        from mcp_server_nucleus.runtime.context_manager import ContextManager
        
        cm = ContextManager(self.brain_path)
        snapshot = cm.take_snapshot()
        
        self.assertIsNotNone(snapshot.snapshot_id)
        self.assertIsNotNone(snapshot.state_hash)
        self.assertIsNotNone(snapshot.timestamp)
        self.assertTrue(snapshot.snapshot_id.startswith("snap-"))
    
    def test_compute_world_state_hash(self):
        """Test world state hash computation"""
        from mcp_server_nucleus.runtime.context_manager import ContextManager
        
        cm = ContextManager(self.brain_path)
        hash1, components1 = cm.compute_world_state_hash()
        hash2, components2 = cm.compute_world_state_hash()
        
        # Same state should produce same hash
        self.assertEqual(hash1, hash2)
        self.assertEqual(components1, components2)
    
    def test_state_verification(self):
        """Test state integrity verification"""
        from mcp_server_nucleus.runtime.context_manager import ContextManager
        
        cm = ContextManager(self.brain_path)
        before = cm.take_snapshot()
        
        # No changes - should be valid
        after = cm.take_snapshot()
        result = cm.verify_state_integrity(before, after)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.before_hash, result.after_hash)
    
    def test_state_drift_detection(self):
        """Test that state drift is detected"""
        from mcp_server_nucleus.runtime.context_manager import ContextManager
        
        cm = ContextManager(self.brain_path)
        before = cm.take_snapshot()
        
        # Create a change in ledger
        tasks_file = self.brain_path / "ledger" / "tasks.json"
        tasks_file.write_text('{"tasks": [{"id": "test"}]}')
        
        after = cm.take_snapshot()
        result = cm.verify_state_integrity(before, after)
        
        # Should detect drift in ledger component
        self.assertNotEqual(result.before_hash, result.after_hash)
        self.assertIn("ledger", result.mutations_detected)
    
    def test_snapshot_persistence(self):
        """Test snapshot persistence and loading"""
        from mcp_server_nucleus.runtime.context_manager import ContextManager
        
        cm = ContextManager(self.brain_path)
        snapshot = cm.take_snapshot(metadata={"test": True})
        
        # Persist
        path = cm.persist_snapshot(snapshot)
        self.assertTrue(path.exists())
        
        # Load
        loaded = cm.load_snapshot(snapshot.snapshot_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.snapshot_id, snapshot.snapshot_id)
        self.assertEqual(loaded.state_hash, snapshot.state_hash)


class TestIPCAuth(unittest.TestCase):
    """Tests for ipc_auth.py"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir(parents=True)
        (self.brain_path / "ledger").mkdir()
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if "NUCLEAR_BRAIN_PATH" in os.environ:
            del os.environ["NUCLEAR_BRAIN_PATH"]
    
    def test_ipc_auth_import(self):
        """Test that ipc_auth imports correctly"""
        from mcp_server_nucleus.runtime.ipc_auth import (
            IPCAuthManager, IPCToken
        )
        self.assertIsNotNone(IPCAuthManager)
        self.assertIsNotNone(IPCToken)
    
    def test_token_issuance(self):
        """Test IPC token issuance"""
        from mcp_server_nucleus.runtime.ipc_auth import IPCAuthManager
        
        manager = IPCAuthManager(self.brain_path)
        token = manager.issue_token(scope="tool_call", decision_id="dec-test-001")
        
        self.assertIsNotNone(token.token_id)
        self.assertTrue(token.token_id.startswith("ipc-"))
        self.assertEqual(token.scope, "tool_call")
        self.assertEqual(token.decision_id, "dec-test-001")
        self.assertFalse(token.consumed)
    
    def test_token_validation(self):
        """Test IPC token validation"""
        from mcp_server_nucleus.runtime.ipc_auth import IPCAuthManager
        
        manager = IPCAuthManager(self.brain_path)
        token = manager.issue_token(scope="tool_call")
        
        # Valid token
        is_valid, error = manager.validate_token(token.token_id, scope="tool_call")
        self.assertTrue(is_valid)
        
        # Wrong scope
        is_valid, error = manager.validate_token(token.token_id, scope="admin")
        self.assertFalse(is_valid)
        self.assertIn("Scope mismatch", error)
    
    def test_token_single_use(self):
        """Test that tokens are single-use"""
        from mcp_server_nucleus.runtime.ipc_auth import IPCAuthManager
        
        manager = IPCAuthManager(self.brain_path)
        token = manager.issue_token(scope="tool_call")
        
        # First consumption should succeed
        result = manager.consume_token(token.token_id)
        self.assertTrue(result)
        
        # Second consumption should fail
        result = manager.consume_token(token.token_id)
        self.assertFalse(result)
        
        # Validation should also fail
        is_valid, error = manager.validate_token(token.token_id, scope="tool_call")
        self.assertFalse(is_valid)
        self.assertIn("consumed", error.lower())
    
    def test_token_metering(self):
        """Test token consumption metering"""
        from mcp_server_nucleus.runtime.ipc_auth import IPCAuthManager
        
        manager = IPCAuthManager(self.brain_path)
        
        # Issue and consume multiple tokens
        for i in range(3):
            token = manager.issue_token(scope="tool_call", decision_id=f"dec-{i}")
            manager.consume_token(token.token_id, resource_type="tool_call", units=1.0)
        
        summary = manager.get_metering_summary()
        
        self.assertEqual(summary["total_entries"], 3)
        self.assertEqual(summary["total_units"], 3.0)
        self.assertEqual(summary["decisions_linked"], 3)
    
    def test_metering_persistence(self):
        """Test that metering entries are persisted"""
        from mcp_server_nucleus.runtime.ipc_auth import IPCAuthManager
        
        manager = IPCAuthManager(self.brain_path)
        token = manager.issue_token(scope="tool_call", decision_id="dec-test")
        manager.consume_token(token.token_id, resource_type="tool_call", units=1.0)
        
        # Check metering file exists
        meter_file = self.brain_path / "ledger" / "metering" / "token_meter.jsonl"
        self.assertTrue(meter_file.exists())
        
        # Verify content
        content = meter_file.read_text()
        self.assertIn("dec-test", content)
        self.assertIn("tool_call", content)


class TestDecisionMadeIntegration(unittest.TestCase):
    """Tests for DecisionMade event emission in agent.py"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir(parents=True)
        (self.brain_path / "ledger").mkdir()
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if "NUCLEAR_BRAIN_PATH" in os.environ:
            del os.environ["NUCLEAR_BRAIN_PATH"]
    
    def test_decision_made_class(self):
        """Test DecisionMade class structure"""
        from mcp_server_nucleus.runtime.agent import DecisionMade
        
        decision = DecisionMade(
            decision_id="dec-test-001",
            reasoning="Test reasoning",
            context_hash="abc123",
            confidence=0.9
        )
        
        self.assertEqual(decision.decision_id, "dec-test-001")
        self.assertEqual(decision.reasoning, "Test reasoning")
        self.assertEqual(decision.context_hash, "abc123")
        self.assertEqual(decision.confidence, 0.9)
        self.assertIsNotNone(decision.timestamp)
    
    def test_decision_to_dict(self):
        """Test DecisionMade serialization"""
        from mcp_server_nucleus.runtime.agent import DecisionMade
        
        decision = DecisionMade(
            decision_id="dec-test-002",
            reasoning="Test",
            context_hash="def456"
        )
        
        data = decision.to_dict()
        
        self.assertIn("decision_id", data)
        self.assertIn("reasoning", data)
        self.assertIn("context_hash", data)
        self.assertIn("confidence", data)
        self.assertIn("timestamp", data)
    
    def test_ephemeral_agent_has_decision_ledger(self):
        """Test that EphemeralAgent tracks decisions"""
        from mcp_server_nucleus.runtime.agent import EphemeralAgent
        
        context = {
            "persona": "TestAgent",
            "intent": "Test intent",
            "tools": []
        }
        
        agent = EphemeralAgent(context)
        
        self.assertIsNotNone(agent._decision_ledger)
        self.assertEqual(len(agent._decision_ledger), 0)
    
    def test_context_hash_computation(self):
        """Test context hash computation"""
        from mcp_server_nucleus.runtime.agent import EphemeralAgent
        
        context = {
            "persona": "TestAgent",
            "intent": "Test intent",
            "tools": [{"name": "test_tool"}]
        }
        
        agent = EphemeralAgent(context)
        history = ["Step 1", "Step 2"]
        
        hash1 = agent._compute_context_hash(history)
        hash2 = agent._compute_context_hash(history)
        
        # Same inputs should produce same hash
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 16)  # Truncated SHA-256


if __name__ == "__main__":
    unittest.main()
