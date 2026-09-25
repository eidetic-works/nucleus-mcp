"""Tests for provenance isolation in _run_verify_stage (fw-1786116954).

Verifies that when another agent or the operator commits to the same
working tree while a build is running, those concurrent commits are
NOT attributed as build output. The declared scope (from _declared_scope)
is used to split changed files into attributed (verified) and unattributed
(reported but not verified).
"""
import pytest
from unittest.mock import patch, MagicMock
from mcp_server_nucleus.runtime import execution_verifier
from mcp_server_nucleus.runtime import ground


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Set up a mock environment for _run_verify_stage."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestProvenanceIsolation:
    """Tests that concurrent same-worktree commits are separated from build output."""

    def test_unattributed_files_separated_when_scope_declared(self, mock_env):
        """Files outside the declared scope are reported as unattributed."""
        from mcp_server_nucleus.runtime import build_runner

        # Simulate: build declared scope is "src/foo.py", but git diff
        # also shows "README.md" (a concurrent commit by the operator).
        all_files = ["src/foo.py", "README.md"]
        declared = {"src/foo.py"}

        with patch.object(execution_verifier, "_get_changed_files",
                          return_value=all_files), \
             patch.object(build_runner, "_declared_scope", return_value=declared), \
             patch.object(ground, "detect_project_root",
                          return_value=mock_env):
            ok, details = build_runner._run_verify_stage(
                "fix bug in src/foo.py", "abc123", "def456"
            )

        assert "unattributed_files" in details
        assert "README.md" in details["unattributed_files"]
        assert "src/foo.py" not in details["unattributed_files"]
        assert "src/foo.py" in details["changed_files"]
        assert "README.md" not in details["changed_files"]

    def test_empty_scope_is_deny_by_default(self, mock_env):
        """Empty declared scope (deny-by-default) → no files attributed.

        Regression: empty scope was treated as permissive, so concurrent
        same-worktree commits were attributed as build output. Empty scope
        must mean 'no files claimed' — all changed files are unattributed
        and tier 0 fails.
        """
        from mcp_server_nucleus.runtime import build_runner

        all_files = ["src/foo.py", "README.md"]

        with patch.object(execution_verifier, "_get_changed_files",
                          return_value=all_files), \
             patch.object(build_runner, "_declared_scope", return_value=set()), \
             patch.object(ground, "detect_project_root",
                          return_value=mock_env):
            ok, details = build_runner._run_verify_stage(
                "fix bug", "abc123", "def456"
            )

        assert ok is False
        assert details["tier0"]["status"] == "FAILED"
        assert details["changed_files"] == []
        assert set(details["unattributed_files"]) == {"src/foo.py", "README.md"}

    def test_concurrent_commits_not_attributed_when_scope_empty(self, mock_env):
        """Concurrent same-worktree commits are NOT attributed when scope is empty.

        The core defect (fw-1786116954): an empty declared scope was permissive,
        so concurrent commits by another agent/operator in the same working tree
        were attributed as build output. With deny-by-default semantics, empty
        scope means no files are claimed — concurrent commits land in
        unattributed_files and tier 0 fails (the build itself changed nothing).
        """
        from mcp_server_nucleus.runtime import build_runner

        # Simulate: build declared no scope, but git diff shows files that
        # a concurrent agent committed to the same working tree.
        concurrent_files = ["src/foo.py", "docs/guide.md", "README.md"]

        with patch.object(execution_verifier, "_get_changed_files",
                          return_value=concurrent_files), \
             patch.object(build_runner, "_declared_scope", return_value=set()), \
             patch.object(ground, "detect_project_root",
                          return_value=mock_env):
            ok, details = build_runner._run_verify_stage(
                "fix bug", "abc123", "def456"
            )

        assert ok is False
        assert details["tier0"]["status"] == "FAILED"
        # No files attributed to the build — all are unattributed concurrent commits.
        assert details["changed_files"] == []
        assert set(details["unattributed_files"]) == set(concurrent_files)
        # Tiers 1–3 never ran (short-circuited by tier 0 failure).
        assert details["tier1"]["status"] == "SKIPPED"
        assert details["tier2"]["status"] == "SKIPPED"
        assert details["tier3"]["status"] == "SKIPPED"

    def test_tier0_fails_when_only_unattributed_files(self, mock_env):
        """If all changed files are unattributed, tier 0 fails (build changed nothing)."""
        from mcp_server_nucleus.runtime import build_runner

        all_files = ["README.md", "docs/guide.md"]
        declared = {"src/foo.py"}

        with patch.object(execution_verifier, "_get_changed_files",
                          return_value=all_files), \
             patch.object(build_runner, "_declared_scope", return_value=declared), \
             patch.object(ground, "detect_project_root",
                          return_value=mock_env):
            ok, details = build_runner._run_verify_stage(
                "fix bug in src/foo.py", "abc123", "def456"
            )

        assert ok is False
        assert details["tier0"]["status"] == "FAILED"
        assert details["changed_files"] == []
        assert set(details["unattributed_files"]) == {"README.md", "docs/guide.md"}

    def test_no_unattributed_when_all_in_scope(self, mock_env):
        """All files within declared scope → no unattributed files."""
        from mcp_server_nucleus.runtime import build_runner

        all_files = ["src/foo.py", "src/bar.py"]
        declared = {"src/foo.py", "src/bar.py"}

        with patch.object(execution_verifier, "_get_changed_files",
                          return_value=all_files), \
             patch.object(build_runner, "_declared_scope", return_value=declared), \
             patch.object(ground, "detect_project_root",
                          return_value=mock_env):
            ok, details = build_runner._run_verify_stage(
                "fix bug in src/foo.py and src/bar.py", "abc123", "def456"
            )

        assert details["unattributed_files"] == []
        assert set(details["changed_files"]) == {"src/foo.py", "src/bar.py"}
