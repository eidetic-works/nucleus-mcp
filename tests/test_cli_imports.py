"""Regression tests for CLI import fixes.

Verifies that CLI handler functions import from the correct modules
and don't crash with ImportError. These tests caught real bugs:
- handle_status_command imported from __init__.py instead of satellite_ops
- handle_consolidate_command imported _get_archive_path which wasn't in __init__.py
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from argparse import Namespace


# ── Status command import fix ────────────────────────────────

class TestStatusCommandImports:
    """Regression: nucleus status was importing _get_satellite_view from __init__.py
    but it only exists in runtime/satellite_ops.py."""

    def test_handle_status_imports_from_satellite_ops(self):
        """Verify the import path uses runtime.satellite_ops, not __init__."""
        import inspect
        from mcp_server_nucleus.cli import handle_status_command
        source = inspect.getsource(handle_status_command)
        assert "satellite_ops" in source
        assert "from mcp_server_nucleus import" not in source.split("satellite_ops")[0].split("def handle_status_command")[1]

    def test_satellite_ops_exports_required_functions(self):
        """Verify satellite_ops has the functions we need."""
        from mcp_server_nucleus.runtime.satellite_ops import (
            _get_satellite_view,
            _format_satellite_cli,
        )
        assert callable(_get_satellite_view)
        assert callable(_format_satellite_cli)

    @patch("mcp_server_nucleus.runtime.satellite_ops._get_satellite_view")
    @patch("mcp_server_nucleus.runtime.satellite_ops._format_satellite_cli")
    def test_status_command_runs_without_import_error(self, mock_fmt, mock_view, capsys):
        """End-to-end: handle_status_command doesn't raise ImportError."""
        mock_view.return_value = {"health": "ok"}
        mock_fmt.return_value = "SATELLITE VIEW: ok"

        from mcp_server_nucleus.cli import handle_status_command
        args = Namespace(minimal=False, sprint=False, full=False)
        handle_status_command(args)

        captured = capsys.readouterr()
        assert "SATELLITE VIEW" in captured.out
        mock_view.assert_called_once_with("standard")

    @patch("mcp_server_nucleus.runtime.satellite_ops._get_satellite_view")
    def test_status_minimal_flag(self, mock_view, capsys):
        """Verify --minimal passes correct detail_level."""
        mock_view.return_value = {}
        from mcp_server_nucleus.cli import handle_status_command
        args = Namespace(minimal=True, sprint=False, full=False)
        with patch("mcp_server_nucleus.runtime.satellite_ops._format_satellite_cli", return_value="min"):
            handle_status_command(args)
        mock_view.assert_called_once_with("minimal")

    @patch("mcp_server_nucleus.runtime.satellite_ops._get_satellite_view")
    def test_status_sprint_flag(self, mock_view, capsys):
        """Verify --sprint passes correct detail_level."""
        mock_view.return_value = {}
        from mcp_server_nucleus.cli import handle_status_command
        args = Namespace(minimal=False, sprint=True, full=False)
        with patch("mcp_server_nucleus.runtime.satellite_ops._format_satellite_cli", return_value="sp"):
            handle_status_command(args)
        mock_view.assert_called_once_with("sprint")

    @patch("mcp_server_nucleus.runtime.satellite_ops._get_satellite_view")
    def test_status_full_flag(self, mock_view, capsys):
        """Verify --full passes correct detail_level."""
        mock_view.return_value = {}
        from mcp_server_nucleus.cli import handle_status_command
        args = Namespace(minimal=False, sprint=False, full=True)
        with patch("mcp_server_nucleus.runtime.satellite_ops._format_satellite_cli", return_value="full"):
            handle_status_command(args)
        mock_view.assert_called_once_with("full")

    @patch("mcp_server_nucleus.runtime.satellite_ops._get_satellite_view", side_effect=ValueError("NUCLEAR_BRAIN_PATH not set"))
    def test_status_graceful_error(self, mock_view, capsys):
        """Verify status command shows helpful error on brain path failure."""
        from mcp_server_nucleus.cli import handle_status_command
        args = Namespace(minimal=False, sprint=False, full=False)
        handle_status_command(args)
        captured = capsys.readouterr()
        assert "Error" in captured.out or "error" in captured.out.lower()


# ── Consolidate command import fix ───────────────────────────

class TestConsolidateCommandImports:
    """Regression: nucleus consolidate imported _get_archive_path from __init__.py
    but it wasn't re-exported there."""

    def test_consolidation_ops_exports_required_functions(self):
        """Verify consolidation_ops has all functions needed by CLI."""
        from mcp_server_nucleus.runtime.consolidation_ops import (
            _archive_resolved_files,
            _get_archive_path,
            _generate_merge_proposals,
            _garbage_collect_tasks,
        )
        assert callable(_archive_resolved_files)
        assert callable(_get_archive_path)
        assert callable(_generate_merge_proposals)
        assert callable(_garbage_collect_tasks)

    def test_handle_consolidate_imports_from_consolidation_ops(self):
        """Verify the import path uses runtime.consolidation_ops."""
        import inspect
        from mcp_server_nucleus.cli import handle_consolidate_command
        source = inspect.getsource(handle_consolidate_command)
        assert "consolidation_ops" in source

    @patch("mcp_server_nucleus.runtime.consolidation_ops._archive_resolved_files")
    @patch("mcp_server_nucleus.runtime.consolidation_ops._get_archive_path")
    def test_consolidate_archive_runs(self, mock_path, mock_archive, capsys):
        """End-to-end: consolidate archive doesn't raise ImportError."""
        mock_archive.return_value = {"success": True, "files_moved": 0}
        from mcp_server_nucleus.cli import handle_consolidate_command
        args = Namespace(consolidate_action="archive")
        handle_consolidate_command(args)
        captured = capsys.readouterr()
        assert "clean" in captured.out.lower() or "archive" in captured.out.lower()

    @patch("mcp_server_nucleus.runtime.consolidation_ops._archive_resolved_files")
    @patch("mcp_server_nucleus.runtime.consolidation_ops._get_archive_path")
    def test_consolidate_archive_with_files(self, mock_path, mock_archive, capsys):
        """Verify archive output when files are moved."""
        mock_archive.return_value = {
            "success": True,
            "files_moved": 3,
            "archive_path": "/tmp/archive",
            "moved_files": ["a.bak", "b.bak", "c.bak"],
        }
        from mcp_server_nucleus.cli import handle_consolidate_command
        args = Namespace(consolidate_action="archive")
        handle_consolidate_command(args)
        captured = capsys.readouterr()
        assert "3" in captured.out
        assert "archive" in captured.out.lower()

    @patch("mcp_server_nucleus.runtime.consolidation_ops._generate_merge_proposals")
    def test_consolidate_propose_runs(self, mock_propose, capsys):
        """End-to-end: consolidate propose doesn't raise ImportError."""
        mock_propose.return_value = {"success": True, "total_proposals": 0}
        from mcp_server_nucleus.cli import handle_consolidate_command
        args = Namespace(consolidate_action="propose")
        handle_consolidate_command(args)
        captured = capsys.readouterr()
        assert "clean" in captured.out.lower() or "proposal" in captured.out.lower()

    @patch("mcp_server_nucleus.runtime.consolidation_ops._garbage_collect_tasks")
    def test_consolidate_tasks_runs(self, mock_gc, capsys):
        """End-to-end: consolidate tasks doesn't raise ImportError."""
        mock_gc.return_value = {"success": True, "archived": 0, "kept": 5}
        from mcp_server_nucleus.cli import handle_consolidate_command
        args = Namespace(consolidate_action="tasks", dry_run=False, max_age=72)
        handle_consolidate_command(args)
        captured = capsys.readouterr()
        assert "clean" in captured.out.lower() or "task" in captured.out.lower()

    @patch("mcp_server_nucleus.runtime.consolidation_ops._garbage_collect_tasks")
    def test_consolidate_tasks_dry_run(self, mock_gc, capsys):
        """Verify dry_run flag is passed through."""
        mock_gc.return_value = {
            "success": True, "archived": 2, "kept": 3,
            "breakdown": {"auto_generated": 1, "stale": 1}
        }
        from mcp_server_nucleus.cli import handle_consolidate_command
        args = Namespace(consolidate_action="tasks", dry_run=True, max_age=48)
        handle_consolidate_command(args)
        mock_gc.assert_called_once_with(max_age_hours=48, dry_run=True)
        captured = capsys.readouterr()
        assert "Would archive" in captured.out or "Preview" in captured.out.lower()
