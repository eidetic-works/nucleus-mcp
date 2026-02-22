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
        save_resp_json = nucleus.brain_save_session(
            context="Integration Test",
            active_task="Testing cycle",
            pending_decisions=["Should we merge?"],
            breadcrumbs=["Home", "Tests"],
            next_steps=["Verify success"]
        )
        save_resp = json.loads(save_resp_json)
        self.assertTrue(save_resp["success"])
        session_id = save_resp["data"]["session_id"]
        
        # 2. Resume session
        resume_resp_json = nucleus.brain_resume_session(session_id)
        resume_resp = json.loads(resume_resp_json)
        self.assertTrue(resume_resp["success"])
        
        data = resume_resp["data"]
        self.assertEqual(data["context"], "Integration Test")
        self.assertEqual(data["active_task"], "Testing cycle")
        self.assertIn("Should we merge?", data["pending_decisions"])
        self.assertEqual(data["breadcrumbs"], ["Home", "Tests"])
        print("✅ pass: test_session_save_resume_cycle")

    def test_task_crud_operations(self):
        """AG-007: Test full task CRUD queue operations"""
        # 1. Add Task
        add_resp_json = nucleus.brain_add_task(
            description="Integration Task",
            priority=1,
            required_skills=["testing"]
        )
        add_resp = json.loads(add_resp_json)
        self.assertTrue(add_resp["success"])
        task_id = add_resp["data"]["id"]
        
        # 2. List Tasks
        list_resp_json = nucleus.brain_list_tasks(status="PENDING")
        list_resp = json.loads(list_resp_json)
        self.assertTrue(list_resp["success"])
        found = any(t["id"] == task_id for t in list_resp["data"])
        self.assertTrue(found)
        
        # 3. Update Task
        update_resp_json = nucleus.brain_update_task(task_id, {"status": "DONE"})
        update_resp = json.loads(update_resp_json)
        self.assertTrue(update_resp["success"])
        
        # 4. Verify Update
        list_done_json = nucleus.brain_list_tasks(status="DONE")
        list_done = json.loads(list_done_json)
        found_done = any(t["id"] == task_id for t in list_done["data"])
        self.assertTrue(found_done)
        print("✅ pass: test_task_crud_operations")

    def test_event_emission_reading(self):
        """AG-007: Test event pipeline (emit -> read)"""
        # 1. Emit Event
        emit_resp_json = nucleus.brain_emit_event(
            event_type="test_event",
            emitter="integration_suite",
            data={"foo": "bar"},
            description="Test event for integration"
        )
        emit_resp = json.loads(emit_resp_json)
        self.assertTrue(emit_resp["success"])
        event_id = emit_resp["data"]["event_id"]
        
        # 2. Read Events
        read_resp_json = nucleus.brain_read_events(limit=5)
        read_resp = json.loads(read_resp_json)
        self.assertTrue(read_resp["success"])
        
        # Check if our event is in the list
        found = any(e["event_id"] == event_id for e in read_resp["data"]["events"])
        self.assertTrue(found)
        
        # 3. Verify Timestamp format (ISO 8601 UTC)
        event = next(e for e in read_resp["data"]["events"] if e["event_id"] == event_id)
        timestamp = event["timestamp"]
        self.assertTrue(timestamp.endswith("Z"))
        self.assertIn("T", timestamp)
        print("✅ pass: test_event_emission_reading")

    def test_brain_health(self):
        """AG-001: Test brain_health() tool"""
        health_resp_json = nucleus.brain_health()
        health_resp = json.loads(health_resp_json)
        self.assertEqual(health_resp["status"], "healthy")
        # Version is now dynamic (1.0.4+)
        self.assertIn("version", health_resp)
        self.assertIn("uptime_seconds", health_resp)
        self.assertIn("brain_path", health_resp)
        print("✅ pass: test_brain_health")

if __name__ == '__main__':
    unittest.main()
