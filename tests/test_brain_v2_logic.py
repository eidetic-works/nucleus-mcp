import unittest
import json
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch

# Import the module under test
import mcp_server_nucleus as nucleus

class TestBrainV2Logic(unittest.TestCase):
    def setUp(self):
        # Create a temp brain directory
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir)
        (self.brain_path / "ledger").mkdir(parents=True)
        
        # Mock get_brain_path where it's used in task_ops module
        self.patcher1 = patch('mcp_server_nucleus.runtime.task_ops.get_brain_path', return_value=self.brain_path)
        self.patcher1.start()
        
        # Mock _get_state for V1 fallback path - return state from our test dir
        def mock_get_state():
            state_path = self.brain_path / "ledger" / "state.json"
            if state_path.exists():
                with open(state_path) as f:
                    return json.load(f)
            return {}
        
        self.patcher2 = patch('mcp_server_nucleus.runtime.task_ops._get_state', side_effect=mock_get_state)
        self.patcher2.start()

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        shutil.rmtree(self.test_dir)

    def test_fallback_to_v1(self):
        """Test that we read from state.json if tasks.json is missing"""
        # Setup V1 state
        v1_tasks = [{"id": "v1-task", "description": "Old Task"}]
        state = {"current_sprint": {"tasks": v1_tasks}}
        with open(self.brain_path / "ledger" / "state.json", "w") as f:
            json.dump(state, f)
            
        # Ensure tasks.json does NOT exist
        tasks_json = self.brain_path / "ledger" / "tasks.json"
        if tasks_json.exists():
            os.remove(tasks_json)

        # Run
        tasks = nucleus._get_tasks_list()
        
        # Verify
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["description"], "Old Task")
        print("✅ pass: test_fallback_to_v1")

    def test_precedence_of_v2(self):
        """Test that tasks.json takes precedence over state.json"""
        # Setup V1 state (noise)
        v1_tasks = [{"id": "v1-task", "description": "Old Task"}]
        with open(self.brain_path / "ledger" / "state.json", "w") as f:
            json.dump({"current_sprint": {"tasks": v1_tasks}}, f)

        # Setup V2 state (signal)
        v2_tasks = [{"id": "v2-task", "description": "New V2 Task"}]
        with open(self.brain_path / "ledger" / "tasks.json", "w") as f:
            json.dump(v2_tasks, f)

        # Run
        tasks = nucleus._get_tasks_list()
        
        # Verify we got V2
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["description"], "New V2 Task")
        print("✅ pass: test_precedence_of_v2")

    def test_save_v2_if_exists(self):
        """Test that we save to tasks.json if it exists"""
        # Create empty tasks.json
        (self.brain_path / "ledger" / "tasks.json").write_text("[]")
        
        # Save a new task
        new_tasks = [{"id": "1", "description": "Saved Task"}]
        result = nucleus._save_tasks_list(new_tasks)
        
        # Verify return message
        self.assertIn("V2", result)
        
        # Verify file content
        content = json.loads((self.brain_path / "ledger" / "tasks.json").read_text())
        self.assertEqual(content[0]["description"], "Saved Task")
        print("✅ pass: test_save_v2_if_exists")

if __name__ == '__main__':
    unittest.main()
