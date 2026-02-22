import unittest
import json
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch

# Import the module under test
import mcp_server_nucleus as nucleus

class TestDepthTracker(unittest.TestCase):
    """Tests for Depth Tracker Tier 1 MVP functionality."""
    
    def setUp(self):
        # Create a temp brain directory
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir)
        (self.brain_path / "ledger").mkdir(parents=True)
        (self.brain_path / "session").mkdir(parents=True)
        
        # Mock get_brain_path where it's actually used (in depth_ops module)
        self.patcher = patch('mcp_server_nucleus.runtime.depth_ops.get_brain_path', return_value=self.brain_path)
        self.patcher.start()
        
        # Reset depth state at start of each test
        nucleus._depth_reset()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_initial_depth_is_zero(self):
        """Test that initial depth is 0 (root level)."""
        result = nucleus._depth_show()
        
        self.assertEqual(result['current_depth'], 0)
        self.assertEqual(result['status'], '🟢 SAFE')
        print("✅ pass: test_initial_depth_is_zero")

    def test_push_increases_depth(self):
        """Test that pushing a topic increases depth."""
        result = nucleus._depth_push("Building Nucleus")
        
        self.assertEqual(result['current_depth'], 1)
        self.assertEqual(result['topic'], "Building Nucleus")
        self.assertIn("Building Nucleus", result['breadcrumbs'])
        print("✅ pass: test_push_increases_depth")

    def test_pop_decreases_depth(self):
        """Test that popping decreases depth."""
        # Push twice
        nucleus._depth_push("Level 1")
        nucleus._depth_push("Level 2")
        
        # Pop once
        result = nucleus._depth_pop()
        
        self.assertEqual(result['current_depth'], 1)
        self.assertEqual(result['returned_to'], "Level 1")
        print("✅ pass: test_pop_decreases_depth")

    def test_pop_at_root_is_safe(self):
        """Test that popping at root level doesn't crash."""
        result = nucleus._depth_pop()
        
        self.assertEqual(result['current_depth'], 0)
        self.assertIn("root", result['message'].lower())
        print("✅ pass: test_pop_at_root_is_safe")

    def test_reset_clears_all_levels(self):
        """Test that reset returns to root."""
        # Push multiple times
        nucleus._depth_push("Level 1")
        nucleus._depth_push("Level 2")
        nucleus._depth_push("Level 3")
        
        # Reset
        result = nucleus._depth_reset()
        
        self.assertEqual(result['current_depth'], 0)
        self.assertIn("reset", result['message'].lower())
        print("✅ pass: test_reset_clears_all_levels")

    def test_warning_at_max_depth(self):
        """Test that warnings trigger at max depth."""
        # Set max to 3
        nucleus._depth_set_max(3)
        
        # Push to level 3
        nucleus._depth_push("Level 1")
        nucleus._depth_push("Level 2")
        result = nucleus._depth_push("Level 3")  # Should trigger warning
        
        self.assertIsNotNone(result.get('warning'))
        self.assertEqual(result['warning_level'], 'danger')
        print("✅ pass: test_warning_at_max_depth")

    def test_caution_at_level_3(self):
        """Test that caution triggers at level 3 (when max is 5)."""
        # Default max is 5, so level 3 should be caution
        nucleus._depth_push("Level 1")
        nucleus._depth_push("Level 2")
        result = nucleus._depth_push("Level 3")
        
        self.assertIsNotNone(result.get('warning'))
        self.assertEqual(result['warning_level'], 'caution')
        print("✅ pass: test_caution_at_level_3")

    def test_set_max_depth(self):
        """Test setting max safe depth."""
        result = nucleus._depth_set_max(7)
        
        # Function returns 'new_max' not 'max_safe_depth'
        self.assertEqual(result['new_max'], 7)
        print("✅ pass: test_set_max_depth")

    def test_set_max_depth_validation(self):
        """Test that invalid max depths are rejected."""
        result = nucleus._depth_set_max(15)
        
        self.assertIn('error', result)
        print("✅ pass: test_set_max_depth_validation")

    def test_breadcrumbs_build_correctly(self):
        """Test that breadcrumbs show the path."""
        nucleus._depth_push("Project A")
        nucleus._depth_push("Feature X")
        result = nucleus._depth_push("Bug Fix")
        
        self.assertIn("Project A", result['breadcrumbs'])
        self.assertIn("Feature X", result['breadcrumbs'])
        self.assertIn("Bug Fix", result['breadcrumbs'])
        print("✅ pass: test_breadcrumbs_build_correctly")

    def test_depth_persists(self):
        """Test that depth state persists to file."""
        nucleus._depth_push("Persistent Topic")
        
        # Read file directly
        depth_file = self.brain_path / "session" / "depth.json"
        self.assertTrue(depth_file.exists())
        
        with open(depth_file) as f:
            data = json.load(f)
        
        self.assertEqual(data['current_depth'], 1)
        self.assertEqual(len(data['levels']), 1)
        print("✅ pass: test_depth_persists")

    def test_visual_indicator_format(self):
        """Test that visual indicator is formatted correctly."""
        result = nucleus._depth_show()
        
        indicator = result['indicator']
        # Indicator format is [███░░] not "DEPTH: x/y"
        self.assertIn("[", indicator)
        self.assertIn("]", indicator)
        print("✅ pass: test_visual_indicator_format")


if __name__ == '__main__':
    unittest.main()
