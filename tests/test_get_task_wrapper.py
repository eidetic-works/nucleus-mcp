"""Test _get_task wrapper function.

Verifies that the _get_task convenience wrapper:
1. Returns a task dict when the task exists
2. Returns None when the task doesn't exist
3. Is importable from task_ops
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestGetTask:
    """Test the _get_task wrapper function."""

    def test_get_task_is_importable(self):
        """_get_task should be importable from task_ops."""
        from mcp_server_nucleus.runtime.task_ops import _get_task
        assert callable(_get_task), "_get_task should be callable"

    def test_get_task_returns_none_for_nonexistent(self):
        """_get_task should return None for a nonexistent task ID."""
        from mcp_server_nucleus.runtime.task_ops import _get_task
        result = _get_task("nonexistent_task_id_12345")
        assert result is None, f"Should return None for nonexistent task. Got: {result}"

    def test_get_task_returns_dict_for_existing(self):
        """_get_task should return a dict with 'id' and 'description' for an existing task."""
        from mcp_server_nucleus.runtime.task_ops import _get_task, _add_task
        # Create a task
        result = _add_task(
            description="Test task for _get_task wrapper",
            priority=3,
            source="test",
        )
        assert result.get("success"), f"Failed to create test task: {result}"
        task_id = result["task"]["id"]
        try:
            # Now retrieve it
            retrieved = _get_task(task_id)
            assert retrieved is not None, "Should retrieve the created task"
            assert isinstance(retrieved, dict), "Should return a dict"
            assert retrieved.get("id") == task_id, "ID should match"
            assert "description" in retrieved, "Should have description field"
        finally:
            # Clean up
            from mcp_server_nucleus.runtime.task_ops import _update_task
            _update_task(task_id, {"status": "DONE"})
