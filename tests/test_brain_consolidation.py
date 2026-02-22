#!/usr/bin/env python3
"""Unit tests for Brain Consolidation Tier 1.

Tests the _archive_resolved_files() function which moves .resolved.* 
and .metadata.json backup files to archive/resolved/.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Set up test environment
_test_dir = tempfile.mkdtemp(prefix="nucleus_consolidation_env_")
os.environ["NUCLEAR_BRAIN_PATH"] = _test_dir


class TestBrainConsolidation(unittest.TestCase):
    """Test cases for brain consolidation feature."""
    
    def setUp(self):
        """Set up test brain directory structure."""
        self.test_dir = tempfile.mkdtemp(prefix="nucleus_consolidation_test_")
        self.brain_path = Path(self.test_dir)
        self.ledger_path = self.brain_path / "ledger"
        self.ledger_path.mkdir(parents=True, exist_ok=True)
        
        # Create events.jsonl for emit_event
        (self.ledger_path / "events.jsonl").touch()
        
        # Patch get_brain_path where it's used in __init__.py and extracted modules
        self.patcher = patch('mcp_server_nucleus.get_brain_path', return_value=self.brain_path)
        self.patcher2 = patch('mcp_server_nucleus.runtime.consolidation_ops.get_brain_path', return_value=self.brain_path)
        self.mock_brain_path = self.patcher.start()
        self.mock_brain_path2 = self.patcher2.start()
    
    def tearDown(self):
        """Clean up test directory."""
        self.patcher.stop()
        self.patcher2.stop()
        shutil.rmtree(self.test_dir)
    
    def test_archive_resolved_moves_files(self):
        """Test that .resolved.* files are moved to archive."""
        from mcp_server_nucleus import _archive_resolved_files
        
        # Create test resolved files
        (self.brain_path / "task.md.resolved").write_text("backup 1")
        (self.brain_path / "task.md.resolved.0").write_text("backup 2")
        (self.brain_path / "task.md.resolved.1").write_text("backup 3")
        
        result = _archive_resolved_files()
        
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("files_moved"), 3)
        
        # Verify files are in archive
        archive_dir = Path(result.get("archive_path"))
        self.assertTrue(archive_dir.exists())
        self.assertEqual(len(list(archive_dir.glob("*"))), 3)
        
        # Verify files are no longer in brain root
        self.assertEqual(len(list(self.brain_path.glob("*.resolved*"))), 0)
    
    def test_archive_resolved_creates_directory(self):
        """Test that archive/resolved/ is created if missing."""
        from mcp_server_nucleus import _archive_resolved_files
        
        archive_dir = self.brain_path / "archive" / "resolved"
        self.assertFalse(archive_dir.exists())
        
        # Create one test file
        (self.brain_path / "test.md.resolved").write_text("content")
        
        result = _archive_resolved_files()
        
        self.assertTrue(result.get("success"))
        self.assertTrue(archive_dir.exists())
    
    def test_archive_resolved_skips_primary_files(self):
        """Test that primary files (not .resolved) are NOT moved."""
        from mcp_server_nucleus import _archive_resolved_files
        
        # Create primary file and resolved file
        primary = self.brain_path / "task.md"
        resolved = self.brain_path / "task.md.resolved"
        
        primary.write_text("primary content")
        resolved.write_text("backup content")
        
        result = _archive_resolved_files()
        
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("files_moved"), 1)
        
        # Primary file should still exist
        self.assertTrue(primary.exists())
        # Resolved should be gone
        self.assertFalse(resolved.exists())
    
    def test_archive_handles_metadata_json(self):
        """Test that .metadata.json files are also archived."""
        from mcp_server_nucleus import _archive_resolved_files
        
        # Create metadata files
        (self.brain_path / "task.md.metadata.json").write_text("{}")
        (self.brain_path / "notes.md.metadata.json").write_text("{}")
        
        result = _archive_resolved_files()
        
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("files_moved"), 2)
    
    def test_archive_empty_returns_success(self):
        """Test that archiving with no files returns success with 0 count."""
        from mcp_server_nucleus import _archive_resolved_files
        
        # No files to archive
        result = _archive_resolved_files()
        
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("files_moved"), 0)


if __name__ == "__main__":
    unittest.main()
