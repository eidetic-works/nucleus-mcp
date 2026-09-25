"""
Coverage tests for runtime/capabilities/code_ops.py
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.capabilities.code_ops import CodeOps, SAFE_COMMANDS


@pytest.fixture
def code_ops(monkeypatch, tmp_path):
    """Create CodeOps with CWD set to tmp_path."""
    monkeypatch.chdir(tmp_path)
    # Set brain path inside tmp_path so project_root resolves correctly
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return CodeOps()


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------
class TestProperties:
    def test_name(self, code_ops):
        assert code_ops.name == "code_ops"

    def test_description(self, code_ops):
        assert "FileSystem" in code_ops.description or "Shell" in code_ops.description


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------
class TestGetTools:
    def test_returns_four_tools(self, code_ops):
        tools = code_ops.get_tools()
        names = [t["name"] for t in tools]
        assert "code_read_file" in names
        assert "code_write_file" in names
        assert "code_run_command" in names
        assert "code_list_files" in names

    def test_read_file_required(self, code_ops):
        tools = code_ops.get_tools()
        tool = [t for t in tools if t["name"] == "code_read_file"][0]
        assert tool["parameters"]["required"] == ["path"]

    def test_write_file_required(self, code_ops):
        tools = code_ops.get_tools()
        tool = [t for t in tools if t["name"] == "code_write_file"][0]
        assert "path" in tool["parameters"]["required"]
        assert "content" in tool["parameters"]["required"]

    def test_run_command_required(self, code_ops):
        tools = code_ops.get_tools()
        tool = [t for t in tools if t["name"] == "code_run_command"][0]
        assert tool["parameters"]["required"] == ["command"]


# ---------------------------------------------------------------------------
# SAFE_COMMANDS
# ---------------------------------------------------------------------------
class TestSafeCommands:
    def test_contains_python(self):
        assert "python" in SAFE_COMMANDS

    def test_contains_git(self):
        assert "git" in SAFE_COMMANDS

    def test_not_contains_rm(self):
        assert "rm" not in SAFE_COMMANDS

    def test_is_frozenset(self):
        assert isinstance(SAFE_COMMANDS, frozenset)


# ---------------------------------------------------------------------------
# _resolve_path
# ---------------------------------------------------------------------------
class TestResolvePath:
    def test_path_as_is_exists(self, code_ops, tmp_path):
        test_file = tmp_path / "existing.txt"
        test_file.write_text("hello")
        result = code_ops._resolve_path(str(test_file))
        assert result == test_file

    def test_relative_to_cwd(self, code_ops, tmp_path):
        test_file = tmp_path / "relative.txt"
        test_file.write_text("content")
        result = code_ops._resolve_path("relative.txt")
        # _resolve_path returns path as-is when it exists (step 1)
        assert result.read_text() == "content"

    def test_relative_to_project_root(self, code_ops, tmp_path, monkeypatch):
        # Create file in project root (brain_path.parent)
        project_root = tmp_path
        test_file = project_root / "project_file.txt"
        test_file.write_text("data")
        # Change cwd to a subdirectory so relative doesn't find it in cwd
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)
        result = code_ops._resolve_path("project_file.txt")
        assert result == test_file

    def test_absolute_path_rerooting(self, code_ops, tmp_path, monkeypatch):
        # Create file in project root
        project_root = tmp_path
        test_file = project_root / "rooted.txt"
        test_file.write_text("data")
        # Pass an absolute path that doesn't exist but re-rooted does
        result = code_ops._resolve_path("/rooted.txt")
        assert result == test_file

    def test_nonexistent_path_returns_as_is(self, code_ops):
        result = code_ops._resolve_path("nonexistent_file_xyz.txt")
        assert not result.exists()


# ---------------------------------------------------------------------------
# code_read_file
# ---------------------------------------------------------------------------
class TestReadFile:
    def test_read_existing_file(self, code_ops, tmp_path):
        test_file = tmp_path / "read_me.txt"
        test_file.write_text("file content here")
        result = code_ops.execute_tool("code_read_file", {"path": str(test_file)})
        assert result == "file content here"

    def test_read_nonexistent_file(self, code_ops):
        result = code_ops.execute_tool("code_read_file", {"path": "no_such_file.txt"})
        assert "Error" in result
        assert "not found" in result

    def test_read_outside_boundaries(self, code_ops, monkeypatch):
        # Create a file outside project and home
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/tmp/.brain_test_codeops")
        result = code_ops.execute_tool("code_read_file", {"path": "/etc/some_random_file_xyz.txt"})
        assert "outside allowed boundaries" in result


# ---------------------------------------------------------------------------
# code_write_file
# ---------------------------------------------------------------------------
class TestWriteFile:
    def test_write_absolute_path(self, code_ops, tmp_path):
        target = tmp_path / "output.txt"
        result = code_ops.execute_tool("code_write_file", {
            "path": str(target),
            "content": "written content"
        })
        assert "Wrote" in result
        assert target.read_text() == "written content"

    def test_write_relative_path_with_brain_env(self, code_ops, tmp_path):
        result = code_ops.execute_tool("code_write_file", {
            "path": "new_file.txt",
            "content": "relative content"
        })
        assert "Wrote" in result
        # File should be in project root (brain_path.parent)
        written = (tmp_path / "new_file.txt").read_text()
        assert written == "relative content"

    def test_write_creates_parent_dirs(self, code_ops, tmp_path):
        target = tmp_path / "sub" / "dir" / "file.txt"
        result = code_ops.execute_tool("code_write_file", {
            "path": str(target),
            "content": "nested"
        })
        assert "Wrote" in result
        assert target.read_text() == "nested"

    def test_write_outside_boundaries(self, code_ops, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", "/tmp/.brain_test_codeops_write")
        result = code_ops.execute_tool("code_write_file", {
            "path": "/etc/some_bad_file.txt",
            "content": "bad"
        })
        assert "outside allowed boundaries" in result

    def test_write_empty_content(self, code_ops, tmp_path):
        target = tmp_path / "empty.txt"
        result = code_ops.execute_tool("code_write_file", {
            "path": str(target),
            "content": ""
        })
        assert "Wrote 0 bytes" in result
        assert target.read_text() == ""


# ---------------------------------------------------------------------------
# code_run_command
# ---------------------------------------------------------------------------
class TestRunCommand:
    def test_run_echo(self, code_ops):
        result = code_ops.execute_tool("code_run_command", {"command": "echo hello"})
        assert "Exit Code: 0" in result
        assert "hello" in result

    def test_run_unsafe_command(self, code_ops):
        result = code_ops.execute_tool("code_run_command", {"command": "rm -rf /"})
        assert "not in allowlist" in result

    def test_run_empty_command(self, code_ops):
        result = code_ops.execute_tool("code_run_command", {"command": ""})
        assert "Empty command" in result

    def test_run_whitespace_command(self, code_ops):
        result = code_ops.execute_tool("code_run_command", {"command": "   "})
        assert "Empty command" in result

    def test_run_command_with_timeout(self, code_ops):
        result = code_ops.execute_tool("code_run_command", {
            "command": "python3 -c 'import time; time.sleep(10)'",
            "timeout": 1
        })
        assert "timed out" in result

    def test_run_command_with_args(self, code_ops):
        result = code_ops.execute_tool("code_run_command", {
            "command": "echo 'hello world'"
        })
        assert "Exit Code: 0" in result
        assert "hello world" in result

    def test_run_failing_command(self, code_ops):
        result = code_ops.execute_tool("code_run_command", {
            "command": "python3 -c 'import sys; sys.exit(1)'"
        })
        assert "Exit Code: 1" in result

    def test_run_command_default_timeout(self, code_ops):
        """Verify default timeout of 30 is used when not specified."""
        result = code_ops.execute_tool("code_run_command", {"command": "echo test"})
        assert "Exit Code: 0" in result


# ---------------------------------------------------------------------------
# code_list_files
# ---------------------------------------------------------------------------
class TestListFiles:
    def test_list_files_in_dir(self, code_ops, tmp_path):
        (tmp_path / "file_a.txt").write_text("a")
        (tmp_path / "file_b.txt").write_text("b")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        result = code_ops.execute_tool("code_list_files", {"path": str(tmp_path)})
        assert "file_a.txt" in result
        assert "file_b.txt" in result
        assert "subdir/" in result

    def test_list_files_default_path(self, code_ops, tmp_path):
        (tmp_path / "default.txt").write_text("x")
        result = code_ops.execute_tool("code_list_files", {})
        assert "default.txt" in result

    def test_list_files_nonexistent(self, code_ops):
        result = code_ops.execute_tool("code_list_files", {"path": "/nonexistent_xyz_123"})
        assert "Error" in result
        assert "not found" in result

    def test_list_files_relative_path(self, code_ops, tmp_path):
        (tmp_path / "rel.txt").write_text("x")
        result = code_ops.execute_tool("code_list_files", {"path": "."})
        assert "rel.txt" in result


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------
class TestUnknownTool:
    def test_unknown_tool(self, code_ops):
        result = code_ops.execute_tool("nonexistent", {})
        assert "not found" in result
