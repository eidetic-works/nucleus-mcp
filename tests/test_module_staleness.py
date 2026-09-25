"""Tests for module staleness detection (fw-1786072975).

Verifies that _module_staleness reports whether the running process
holds stale code relative to the repo on disk.
"""
import json
import os
import time
import pytest


class TestModuleStaleness:
    def test_returns_dict_with_required_fields(self):
        """_module_staleness returns a dict with the expected keys."""
        from mcp_server_nucleus.runtime.health_ops import _module_staleness
        result = _module_staleness()
        assert isinstance(result, dict)
        assert "stale" in result
        assert "repo_git_sha" in result
        assert "loaded_package_path" in result

    def test_fresh_process_reports_not_stale(self):
        """A freshly started process should report stale=False."""
        from mcp_server_nucleus.runtime.health_ops import _module_staleness
        result = _module_staleness()
        # In a test process that just started, newest_py should be ~now
        # and proc_start should be ~now, so stale should be False
        assert result["stale"] is False

    def test_version_impl_includes_staleness(self):
        """_brain_version_impl includes module_staleness in its output."""
        from mcp_server_nucleus.runtime.health_ops import _brain_version_impl
        result = _brain_version_impl()
        assert "module_staleness" in result
        assert isinstance(result["module_staleness"], dict)
        assert "stale" in result["module_staleness"]

    def test_reports_git_sha(self):
        """The git SHA is reported when available."""
        from mcp_server_nucleus.runtime.health_ops import _module_staleness
        result = _module_staleness()
        # In a git repo, the SHA should be a non-empty string
        if "error" not in result:
            sha = result.get("repo_git_sha")
            if sha is not None:
                assert isinstance(sha, str)
                assert len(sha) >= 7  # short SHA

    def test_reports_newest_py_file(self):
        """The newest .py file path is reported."""
        from mcp_server_nucleus.runtime.health_ops import _module_staleness
        result = _module_staleness()
        if "error" not in result:
            assert "newest_py_file" in result
            assert "newest_py_mtime" in result
            assert result["newest_py_file"]  # non-empty
