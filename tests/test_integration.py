import unittest
import json
import tempfile
import os
import shutil
from pathlib import Path

# Set up test environment BEFORE importing nucleus
_test_dir = tempfile.mkdtemp()
os.environ["NUCLEAR_BRAIN_PATH"] = _test_dir

# Now import the module under test
import mcp_server_nucleus as nucleus
from mcp_server_nucleus.runtime.health_ops import _brain_health_impl

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Use the pre-created temp brain directory
        self.test_dir = _test_dir
        os.environ["NUCLEAR_BRAIN_PATH"] = self.test_dir
        self.brain_path = Path(self.test_dir)
        
        # Ensure directories exist (may have been cleaned up)
        (self.brain_path / "ledger").mkdir(parents=True, exist_ok=True)
        (self.brain_path / "sessions").mkdir(parents=True, exist_ok=True)
        (self.brain_path / "artifacts").mkdir(parents=True, exist_ok=True)
        
        # Initialize tasks.json for task tests
        tasks_file = self.brain_path / "ledger" / "tasks.json"
        if not tasks_file.exists():
            tasks_file.write_text("[]")
        
        # Initialize events.jsonl for event tests
        events_file = self.brain_path / "ledger" / "events.jsonl"
        if not events_file.exists():
            events_file.write_text("")
        
        # Mock depth state file for session
        (self.brain_path / "session").mkdir(parents=True, exist_ok=True)
        (self.brain_path / "session" / "depth.json").write_text(json.dumps({
            "current_depth": 0,
            "levels": [],
            "max_safe_depth": 5
        }))

    def tearDown(self):
        # Clean up test files but keep directory for next test
        def _clean_dir(path: Path):
            for p in path.glob("*"):
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p)

        _clean_dir(self.brain_path / "ledger")
        _clean_dir(self.brain_path / "sessions")
        _clean_dir(self.brain_path / "session")

    def test_session_save_resume_cycle(self):
        """AG-007: Test session save and resume full cycle"""
        # 1. Save session
        save_resp = nucleus._save_session(
            context="Integration Test",
            active_task="Testing cycle",
            pending_decisions=["Should we merge?"],
            breadcrumbs=["Home", "Tests"],
            next_steps=["Verify success"]
        )
        self.assertTrue(save_resp.get("success", True) if "success" in save_resp else "session_id" in save_resp)
        session_id = save_resp.get("data", save_resp).get("session_id", save_resp.get("session_id"))
        
        # 2. Resume session
        resume_resp = nucleus._resume_session(session_id)
        self.assertTrue(resume_resp.get("success", True) if "success" in resume_resp else "session_id" in resume_resp)
        
        data = resume_resp.get("data", resume_resp)
        self.assertEqual(data["context"], "Integration Test")
        self.assertEqual(data["active_task"], "Testing cycle")
        self.assertIn("Should we merge?", data["pending_decisions"])
        self.assertEqual(data["breadcrumbs"], ["Home", "Tests"])
        print("✅ pass: test_session_save_resume_cycle")

    def test_task_crud_operations(self):
        """AG-007: Test full task CRUD queue operations"""
        # 1. Add Task
        add_resp = nucleus._add_task(
            description="Integration Task",
            priority=1,
            required_skills=["testing"]
        )
        self.assertTrue(add_resp.get("success", False))
        task_id = add_resp.get("task", {}).get("id")
        
        # 2. List Tasks
        tasks_list = nucleus._list_tasks(status="PENDING")
        self.assertIsInstance(tasks_list, list)
        
        found = any(t["id"] == task_id for t in tasks_list)
        self.assertTrue(found)
        
        # 3. Update Task
        update_resp = nucleus._update_task(task_id, {"status": "DONE"})
        self.assertTrue(update_resp.get("success", False))
        
        # 4. Verify Update
        tasks_done_list = nucleus._list_tasks(status="DONE")
        found_done = any(t["id"] == task_id for t in tasks_done_list)
        self.assertTrue(found_done)
        print("✅ pass: test_task_crud_operations")

    def test_event_emission_reading(self):
        """AG-007: Test event pipeline (emit -> read)"""
        # 1. Emit Event
        event_id = nucleus._emit_event(
            event_type="test_event",
            emitter="integration_suite",
            data={"foo": "bar"},
            description="Test event for integration"
        )
        self.assertIsInstance(event_id, str)
        self.assertTrue(event_id.startswith("evt-"))
        
        # 2. Read Events
        events_list = nucleus._read_events(limit=5)
        self.assertIsInstance(events_list, list)
        
        # Check if our event is in the list
        found = any(e["event_id"] == event_id for e in events_list)
        self.assertTrue(found)
        
        # 3. Verify Timestamp format (ISO 8601 UTC)
        event = next(e for e in events_list if e["event_id"] == event_id)
        timestamp = event["timestamp"]
        self.assertTrue(timestamp.endswith("Z"))
        self.assertIn("T", timestamp)
        print("✅ pass: test_event_emission_reading")

    def test_brain_health(self):
        """AG-001: Test brain_health() tool"""
        health_resp_json = _brain_health_impl()
        health_resp = json.loads(health_resp_json) if isinstance(health_resp_json, str) else health_resp_json
        self.assertEqual(health_resp["status"], "healthy")
        # Version is now dynamic (1.0.4+)
        self.assertIn("version", health_resp)
        self.assertIn("uptime_seconds", health_resp)
        self.assertIn("brain_path", health_resp)
        print("✅ pass: test_brain_health")

if __name__ == '__main__':
    unittest.main()
