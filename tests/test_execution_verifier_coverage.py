"""
Comprehensive coverage tests for runtime/execution_verifier.py.

All external calls (subprocess, git, HTTP) are mocked — no real network.
"""
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import execution_verifier as ev


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mk_completed(returncode=0, stdout="", stderr=""):
    """Create a mock subprocess.CompletedProcess."""
    r = MagicMock(spec=subprocess.CompletedProcess)
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = stderr
    return r


@pytest.fixture
def project_root(tmp_path):
    """A temporary project root with a git repo."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / ".git").mkdir()
    return root


# ---------------------------------------------------------------------------
# _tier0_diff_nonempty
# ---------------------------------------------------------------------------

class TestTier0DiffNonempty:
    def test_empty_list_fails(self):
        sig = ev._tier0_diff_nonempty([])
        assert sig["passed"] is False
        assert sig["files_count"] == 0
        assert sig["tier"] == 0
        assert sig["check"] == "diff_nonempty"

    def test_nonempty_list_passes(self):
        sig = ev._tier0_diff_nonempty(["a.py", "b.py"])
        assert sig["passed"] is True
        assert sig["files_count"] == 2


# ---------------------------------------------------------------------------
# _get_changed_files
# ---------------------------------------------------------------------------

class TestGetChangedFiles:
    def test_no_changes(self, project_root):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mk_completed(stdout="")
            files = ev._get_changed_files("", "", project_root)
        assert files == []

    def test_unstaged_files(self, project_root):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mk_completed(stdout="src/a.py\nsrc/b.py\n")
            files = ev._get_changed_files("", "", project_root)
        assert "src/a.py" in files
        assert "src/b.py" in files

    def test_with_pre_head(self, project_root):
        # Call order: submodule paths, diff --name-only, diff --cached,
        # diff --name-only pre_head, ls-files, cat-file (per untracked)
        side_effects = [
            _mk_completed(stdout=""),             # submodule paths (no .gitmodules)
            _mk_completed(stdout="unstaged.py\n"),  # diff --name-only
            _mk_completed(stdout="staged.py\n"),    # diff --cached --name-only
            _mk_completed(stdout="committed.py\n"), # diff --name-only pre_head
            _mk_completed(stdout=""),             # ls-files (no untracked)
        ]
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = side_effects
            files = ev._get_changed_files("", "abc123", project_root)
        assert "unstaged.py" in files
        assert "staged.py" in files
        assert "committed.py" in files

    def test_git_exception_returns_empty(self, project_root):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5)):
            files = ev._get_changed_files("", "", project_root)
        assert files == []

    def test_empty_pre_head_skips_diff_pre_head(self, project_root):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mk_completed(stdout="a.py\n")
            files = ev._get_changed_files("", "", project_root)
        # 4 git calls: submodule paths + diff + diff --cached + ls-files
        # (no diff --name-only pre_head call since pre_head is empty)
        assert mock_run.call_count == 4

    def test_concurrent_commit_contamination_excluded(self, project_root):
        """fw-1786034381: files from other sessions' commits must NOT appear.

        The old code used `git log --name-only pre_head..HEAD` which captures
        ALL commits between pre_head and HEAD — including commits from other
        concurrent sessions. The fix uses `git diff --name-only pre_head` which
        compares pre_head to the WORKING TREE, so only this session's changes
        are visible.
        """
        # Simulate: this session edited 'my_file.py' (unstaged),
        # another session committed 'other_session_file.py' (NOT in our working tree)
        side_effects = [
            _mk_completed(stdout=""),                   # submodule paths
            _mk_completed(stdout="my_file.py\n"),       # diff --name-only (unstaged)
            _mk_completed(stdout=""),                   # diff --cached (staged)
            _mk_completed(stdout="my_file.py\n"),       # diff --name-only pre_head
            _mk_completed(stdout=""),                   # ls-files (no untracked)
        ]
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = side_effects
            files = ev._get_changed_files("", "abc123", project_root)
        # my_file.py is in (this session's edit), other_session_file.py is NOT
        assert "my_file.py" in files
        assert "other_session_file.py" not in files

    def test_build_context_submodule_only_fails_tier0(self, project_root):
        """fw-1785907505: a build whose only diff is a submodule pointer bump
        must FAIL Tier 0.

        Called with the DEFAULT context (``"build"``, not passed explicitly) —
        that is the context ``build_runner._run_verify_stage`` uses. The staged
        diff names only the submodule directory (a mode-160000 gitlink bump,
        not a file edit), so it is filtered out, ``changed_files`` is empty, and
        Tier 0 (diff nonempty) reports ``passed is False``.
        """
        side_effects = [
            # git config --file .gitmodules --get-regexp path
            _mk_completed(stdout="submodule.nucleus-mcp.path nucleus-mcp\n"),
            _mk_completed(stdout=""),               # diff --name-only (unstaged)
            _mk_completed(stdout="nucleus-mcp\n"),  # diff --cached (pointer bump)
            _mk_completed(stdout=""),               # ls-files (no untracked)
        ]
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = side_effects
            files = ev._get_changed_files("", "", project_root)
        assert files == []
        sig = ev._tier0_diff_nonempty(files)
        assert sig["passed"] is False
        assert sig["files_count"] == 0

    def test_pre_commit_context_staged_submodule_passes_tier0(self, project_root):
        """fw-1786069497: a STAGED submodule pointer bump must PASS Tier 0
        under ``context="pre_commit"``.

        The opposed pair to ``test_build_context_submodule_only_fails_tier0``:
        same staged gitlink bump, opposite verdict, because ``git add``ing the
        pointer makes it the deliberate subject of the commit. Only the staged
        source is exempt — unstaged and ``pre_head`` both return empty here, so
        the submodule path can only have arrived via ``diff --cached``.
        """
        side_effects = [
            # git config --file .gitmodules --get-regexp path
            _mk_completed(stdout="submodule.nucleus-mcp.path nucleus-mcp\n"),
            _mk_completed(stdout=""),               # diff --name-only (unstaged)
            _mk_completed(stdout="nucleus-mcp\n"),  # diff --cached (pointer bump)
            _mk_completed(stdout=""),               # diff --name-only pre_head
            _mk_completed(stdout=""),               # ls-files (no untracked)
        ]
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = side_effects
            files = ev._get_changed_files(
                "", "abc123", project_root, context="pre_commit")
        assert files == ["nucleus-mcp"]
        sig = ev._tier0_diff_nonempty(files)
        assert sig["passed"] is True
        assert sig["files_count"] == 1

    def test_pre_commit_context_unstaged_submodule_still_filtered(self, project_root):
        """fw-1786069497: the ``pre_commit`` exemption is STAGED-only.

        Same context as ``test_pre_commit_context_staged_submodule_passes_tier0``
        but the pointer bump sits in the UNSTAGED diff and nothing is staged.
        An accidental pointer move (a submodule checkout left behind, never
        ``git add``ed) is not the deliberate subject of a commit, so it is still
        filtered, ``changed_files`` is empty, and Tier 0 FAILS.
        """
        side_effects = [
            # git config --file .gitmodules --get-regexp path
            _mk_completed(stdout="submodule.nucleus-mcp.path nucleus-mcp\n"),
            _mk_completed(stdout="nucleus-mcp\n"),  # diff --name-only (unstaged bump)
            _mk_completed(stdout=""),               # diff --cached (nothing staged)
            _mk_completed(stdout=""),               # diff --name-only pre_head
            _mk_completed(stdout=""),               # ls-files (no untracked)
        ]
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = side_effects
            files = ev._get_changed_files(
                "", "abc123", project_root, context="pre_commit")
        assert files == []
        sig = ev._tier0_diff_nonempty(files)
        assert sig["passed"] is False
        assert sig["files_count"] == 0

    def test_build_context_default_when_no_context_arg(self, project_root):
        """fw-1786069497: omitting ``context`` keeps the BUILD behavior.

        Byte-for-byte the call ``build_runner._run_verify_stage`` makes —
        ``_get_changed_files("", pre_head, root)``, no ``context`` kwarg — and
        byte-for-byte the mocks of
        ``test_pre_commit_context_staged_submodule_passes_tier0``. The only
        difference is the missing kwarg, so the opposite verdict here proves
        the default resolves to ``"build"``: the staged gitlink bump is still
        filtered, ``changed_files`` is empty, and Tier 0 FAILS. Adding the
        ``pre_commit`` exemption did not silently widen the build path.
        """
        side_effects = [
            # git config --file .gitmodules --get-regexp path
            _mk_completed(stdout="submodule.nucleus-mcp.path nucleus-mcp\n"),
            _mk_completed(stdout=""),               # diff --name-only (unstaged)
            _mk_completed(stdout="nucleus-mcp\n"),  # diff --cached (pointer bump)
            _mk_completed(stdout=""),               # diff --name-only pre_head
            _mk_completed(stdout=""),               # ls-files (no untracked)
        ]
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = side_effects
            files = ev._get_changed_files("", "abc123", project_root)
        assert files == []
        sig = ev._tier0_diff_nonempty(files)
        assert sig["passed"] is False
        assert sig["files_count"] == 0


# ---------------------------------------------------------------------------
# _run_check
# ---------------------------------------------------------------------------

class TestRunCheck:
    def test_success(self):
        with patch("subprocess.run", return_value=_mk_completed(0, "", "")):
            sig = ev._run_check(["python", "-c", "pass"], "py_compile", "a.py")
        assert sig["passed"] is True
        assert sig["check"] == "py_compile"
        assert sig["file"] == "a.py"

    def test_failure(self):
        with patch("subprocess.run", return_value=_mk_completed(1, "", "SyntaxError")):
            sig = ev._run_check(["python", "-c", "fail"], "py_compile", "a.py")
        assert sig["passed"] is False
        assert "SyntaxError" in sig["error"]

    def test_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=5)):
            sig = ev._run_check(["python"], "py_compile", "a.py")
        assert sig["passed"] is False
        assert sig["error"] == "timeout"

    def test_file_not_found_is_insufficient_not_passed(self):
        """A missing tool is INSUFFICIENT, never a pass.

        This test previously asserted `sig["passed"] is True` and is renamed
        rather than deleted, because it encoded the bug as an expectation:
        a check that never executed counted toward the tier verdict as though
        the file had been verified. Uninstall the linter and the tree goes
        green.

        The assertion is not being relaxed to accommodate a change -- it is
        being corrected. `insufficient` already existed in execution_verifier
        for exactly this ("unknown coerced into a verdict. INSUFFICIENT is the
        honest value"); the passed=True branch routed around it, because the
        scan that sets it only inspects signals where passed is False.
        """
        with patch("subprocess.run", side_effect=FileNotFoundError("no such tool")):
            sig = ev._run_check(["nonexistent-tool"], "bash_syntax", "a.sh")
        assert sig["passed"] is False
        assert sig["insufficient"] is True
        assert "could not RUN" in sig["error"] and "NOT verified" in sig["error"]

    def test_generic_exception(self):
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            sig = ev._run_check(["python"], "py_compile", "a.py")
        assert sig["passed"] is False
        assert "boom" in sig["error"]


# ---------------------------------------------------------------------------
# _check_json
# ---------------------------------------------------------------------------

class TestCheckJson:
    def test_valid_json(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text('{"key": "value"}')
        sig = ev._check_json(f, "a.json")
        assert sig["passed"] is True
        assert sig["check"] == "json_parse"

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("{invalid json}")
        sig = ev._check_json(f, "a.json")
        assert sig["passed"] is False
        assert sig["error"]


# ---------------------------------------------------------------------------
# _check_yaml
# ---------------------------------------------------------------------------

class TestCheckYaml:
    def test_valid_yaml(self, tmp_path):
        f = tmp_path / "a.yaml"
        f.write_text("key: value\n")
        sig = ev._check_yaml(f, "a.yaml")
        assert sig["passed"] is True
        assert sig["check"] == "yaml_parse"

    def test_invalid_yaml(self, tmp_path):
        f = tmp_path / "a.yaml"
        f.write_text("key: : :\n  bad: [unclosed")
        sig = ev._check_yaml(f, "a.yaml")
        assert sig["passed"] is False
        assert sig["error"]


# ---------------------------------------------------------------------------
# _find_venv_python
# ---------------------------------------------------------------------------

class TestFindVenvPython:
    def test_no_venv(self, project_root):
        result = ev._find_venv_python("src/app.py", project_root)
        assert result is None

    def test_finds_venv(self, project_root):
        src_dir = project_root / "src"
        src_dir.mkdir()
        f = src_dir / "app.py"
        f.write_text("x = 1")
        venv_bin = project_root / "src" / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").write_text("#!/bin/sh")
        result = ev._find_venv_python("src/app.py", project_root)
        assert result is not None
        assert "python" in result

    def test_finds_venv_at_root(self, project_root):
        f = project_root / "app.py"
        f.write_text("x = 1")
        venv_bin = project_root / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").write_text("#!/bin/sh")
        result = ev._find_venv_python("app.py", project_root)
        assert result is not None

    def test_worktree_fallback_finds_main_checkout_venv(self, tmp_path):
        # Simulate a linked worktree: project_root is a separate dir, but the
        # git common dir points back to a main checkout that has .venv.
        main_checkout = tmp_path / "main"
        main_checkout.mkdir()
        main_git = main_checkout / ".git"
        main_git.mkdir()
        main_venv_bin = main_checkout / ".venv" / "bin"
        main_venv_bin.mkdir(parents=True)
        (main_venv_bin / "python").write_text("#!/bin/sh")

        worktree = tmp_path / "wt"
        worktree.mkdir()
        (worktree / "src").mkdir()
        (worktree / "src" / "app.py").write_text("x = 1")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mk_completed(
                returncode=0, stdout=str(main_git) + "\n"
            )
            result = ev._find_venv_python("src/app.py", worktree)

        assert result is not None
        assert result == str(main_venv_bin / "python")

    def test_worktree_fallback_no_venv_in_main_returns_none(self, tmp_path):
        main_checkout = tmp_path / "main"
        main_checkout.mkdir()
        main_git = main_checkout / ".git"
        main_git.mkdir()
        # No .venv in main checkout

        worktree = tmp_path / "wt"
        worktree.mkdir()
        (worktree / "src").mkdir()
        (worktree / "src" / "app.py").write_text("x = 1")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mk_completed(
                returncode=0, stdout=str(main_git) + "\n"
            )
            result = ev._find_venv_python("src/app.py", worktree)

        assert result is None

    def test_worktree_fallback_git_fails_returns_none(self, tmp_path):
        worktree = tmp_path / "wt"
        worktree.mkdir()
        (worktree / "src").mkdir()
        (worktree / "src" / "app.py").write_text("x = 1")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _mk_completed(returncode=128, stderr="fatal: not a git repository")
            result = ev._find_venv_python("src/app.py", worktree)

        assert result is None

    def test_worktree_fallback_subprocess_raises_returns_none(self, tmp_path):
        worktree = tmp_path / "wt"
        worktree.mkdir()
        (worktree / "src").mkdir()
        (worktree / "src" / "app.py").write_text("x = 1")

        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            result = ev._find_venv_python("src/app.py", worktree)

        assert result is None


# ---------------------------------------------------------------------------
# _tier1_syntax_check
# ---------------------------------------------------------------------------

class TestTier1SyntaxCheck:
    def test_no_files(self, project_root):
        sigs = ev._tier1_syntax_check([], project_root, 10)
        assert sigs == []

    def test_nonexistent_file_skipped(self, project_root):
        sigs = ev._tier1_syntax_check(["nonexistent.py"], project_root, 10)
        assert sigs == []

    def test_python_file_checked(self, project_root):
        f = project_root / "app.py"
        f.write_text("x = 1")
        with patch("subprocess.run", return_value=_mk_completed(0, "", "")):
            sigs = ev._tier1_syntax_check(["app.py"], project_root, 10)
        assert len(sigs) == 1
        assert sigs[0]["tier"] == 1
        assert sigs[0]["passed"] is True

    def test_python_file_syntax_error(self, project_root):
        f = project_root / "app.py"
        f.write_text("x = 1")
        with patch("subprocess.run", return_value=_mk_completed(1, "", "SyntaxError")):
            sigs = ev._tier1_syntax_check(["app.py"], project_root, 10)
        assert sigs[0]["passed"] is False

    def test_json_file_checked(self, project_root):
        f = project_root / "config.json"
        f.write_text('{"ok": true}')
        sigs = ev._tier1_syntax_check(["config.json"], project_root, 10)
        assert len(sigs) == 1
        assert sigs[0]["check"] == "json_parse"
        assert sigs[0]["passed"] is True

    def test_yaml_file_checked(self, project_root):
        f = project_root / "config.yaml"
        f.write_text("key: val\n")
        sigs = ev._tier1_syntax_check(["config.yaml"], project_root, 10)
        assert len(sigs) == 1
        assert sigs[0]["check"] == "yaml_parse"
        assert sigs[0]["passed"] is True

    def test_unknown_extension_skipped(self, project_root):
        f = project_root / "data.txt"
        f.write_text("hello")
        sigs = ev._tier1_syntax_check(["data.txt"], project_root, 10)
        assert sigs == []

    def test_budget_exceeded(self, project_root):
        f = project_root / "app.py"
        f.write_text("x = 1")
        # budget of 0 should cause immediate break (time.monotonic check)
        # Use negative budget to force break
        sigs = ev._tier1_syntax_check(["app.py"], project_root, -1)
        assert sigs == []


# ---------------------------------------------------------------------------
# _tier2_import_check
# ---------------------------------------------------------------------------

class TestTier2ImportCheck:
    def test_no_files(self, project_root):
        sigs = ev._tier2_import_check([], project_root, 10)
        assert sigs == []

    def test_skip_init(self, project_root):
        sigs = ev._tier2_import_check(["__init__.py"], project_root, 10)
        assert sigs == []

    def test_skip_test_files(self, project_root):
        sigs = ev._tier2_import_check(["test_foo.py"], project_root, 10)
        assert sigs == []

    def test_hyphenated_paths_sanitized(self, project_root):
        with patch("subprocess.run", return_value=_mk_completed(0, "", "")):
            sigs = ev._tier2_import_check(["mcp-server/app.py"], project_root, 10)
        assert len(sigs) == 1
        assert sigs[0]["module"] == "mcp_server.app"

    def test_invalid_identifier_skipped(self, project_root):
        sigs = ev._tier2_import_check(["path/123invalid.py"], project_root, 10)
        assert sigs == []

    def test_import_success(self, project_root):
        f = project_root / "app.py"
        f.write_text("x = 1")
        with patch("subprocess.run", return_value=_mk_completed(0, "", "")):
            sigs = ev._tier2_import_check(["app.py"], project_root, 10)
        assert len(sigs) == 1
        assert sigs[0]["passed"] is True
        assert sigs[0]["module"] == "app"

    def test_import_failure(self, project_root):
        f = project_root / "app.py"
        f.write_text("x = 1")
        with patch("subprocess.run", return_value=_mk_completed(1, "", "ImportError")):
            sigs = ev._tier2_import_check(["app.py"], project_root, 10)
        assert sigs[0]["passed"] is False
        assert "ImportError" in sigs[0]["error"]

    def test_import_timeout(self, project_root):
        f = project_root / "app.py"
        f.write_text("x = 1")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=5)):
            sigs = ev._tier2_import_check(["app.py"], project_root, 10)
        assert sigs[0]["passed"] is False
        assert sigs[0]["error"] == "timeout"

    def test_import_exception(self, project_root):
        f = project_root / "app.py"
        f.write_text("x = 1")
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            sigs = ev._tier2_import_check(["app.py"], project_root, 10)
        assert sigs[0]["passed"] is False
        assert "boom" in sigs[0]["error"]

    def test_subproject_path(self, project_root):
        sub = project_root / "backend"
        sub.mkdir()
        f = sub / "app" / "main.py"
        f.parent.mkdir(parents=True)
        f.write_text("x = 1")
        with patch("subprocess.run", return_value=_mk_completed(0, "", "")):
            sigs = ev._tier2_import_check(["backend/app/main.py"], project_root, 10)
        assert len(sigs) == 1
        assert sigs[0]["module"] == "app.main"

    def test_caps_at_5_files(self, project_root):
        files = []
        for i in range(7):
            p = f"mod{i}.py"
            (project_root / p).write_text("x = 1")
            files.append(p)
        with patch("subprocess.run", return_value=_mk_completed(0, "", "")):
            sigs = ev._tier2_import_check(files, project_root, 10)
        assert len(sigs) <= 5


# ---------------------------------------------------------------------------
# _tier3_test_execution
# ---------------------------------------------------------------------------

class TestTier3TestExecution:
    def test_no_test_files(self, project_root):
        sigs = ev._tier3_test_execution([], {}, project_root, 10)
        assert sigs == []

    def test_task_specified_test_file(self, project_root):
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): assert True")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution([], {"test_file": "test_app.py"}, project_root, 10)
        # 1 per-file + 1 aggregate skip (budget 10 < 30 min)
        assert len(sigs) == 2
        assert sigs[0]["passed"] is True

    def test_changed_test_file(self, project_root):
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): assert True")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        assert len(sigs) == 2
        assert sigs[0]["file"] == "test_app.py"

    def test_discovered_test_same_dir(self, project_root):
        (project_root / "app.py").write_text("x = 1")
        (project_root / "test_app.py").write_text("def test_x(): pass")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["app.py"], {}, project_root, 10)
        assert len(sigs) == 2

    def test_discovered_test_tests_dir(self, project_root):
        (project_root / "app.py").write_text("x = 1")
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_app.py").write_text("def test_x(): pass")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["app.py"], {}, project_root, 10)
        assert len(sigs) == 2

    def test_discovered_tests_same_dir_exact_sorts_first(self, project_root):
        (project_root / "app.py").write_text("x = 1")
        (project_root / "test_app.py").write_text("def test_x(): pass")
        (project_root / "test_app_extra.py").write_text("def test_y(): pass")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["app.py"], {}, project_root, 10)
        # 2 per-file + 1 aggregate skip
        assert len(sigs) == 3
        assert sigs[0]["file"] == "test_app.py"
        assert sigs[1]["file"] == "test_app_extra.py"

    def test_test_failure(self, project_root):
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): assert False")
        with patch("subprocess.run", return_value=_mk_completed(1, "1 failed", "")):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        assert sigs[0]["passed"] is False

    def test_test_timeout(self, project_root):
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): pass")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=30)):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        assert sigs[0]["passed"] is False
        assert sigs[0]["error"] == "timeout"

    def test_test_exception(self, project_root):
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): pass")
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        assert sigs[0]["passed"] is False
        assert "boom" in sigs[0]["error"]

    def test_pytest_not_available(self, project_root):
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): pass")
        with patch(
            "subprocess.run",
            return_value=_mk_completed(1, "", "No module named pytest"),
        ):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        # 1 per-file (unrunnable) + 1 aggregate skip (per_file_failed)
        assert len(sigs) == 2
        assert sigs[0]["passed"] is False
        assert sigs[0]["unrunnable"] is True
        assert sigs[0]["reason"] == "pytest_not_available"
        assert "python" in sigs[0]

    def test_pytest_not_available_case_insensitive(self, project_root):
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): pass")
        with patch(
            "subprocess.run",
            return_value=_mk_completed(1, "", "NO MODULE NAMED PYTEST"),
        ):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        assert sigs[0]["unrunnable"] is True
        assert sigs[0]["reason"] == "pytest_not_available"

    def test_python_key_on_timeout_and_exception(self, project_root):
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): pass")
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="x", timeout=30),
        ):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        assert "python" in sigs[0]

        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        assert "python" in sigs[0]

    def test_non_python_changed_skipped(self, project_root):
        sigs = ev._tier3_test_execution(["data.txt"], {}, project_root, 10)
        assert sigs == []

    def test_task_test_file_not_exist(self, project_root):
        sigs = ev._tier3_test_execution([], {"test_file": "nonexistent.py"}, project_root, 10)
        assert sigs == []

    def test_unrunnable_interpreter_pytest_not_available(self, project_root):
        """The interpreter runs but pytest is not installed → unrunnable.

        The signal must carry ``passed=False`` (it did not pass), the
        ``unrunnable`` flag (the environment cannot run the check, so the
        verdict says nothing about the code), the machine-readable
        ``reason=='pytest_not_available'``, and the ``python`` key recording
        which interpreter was attempted.
        """
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): pass")
        with patch(
            "subprocess.run",
            return_value=_mk_completed(1, "", "No module named pytest"),
        ):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        # 1 per-file (unrunnable) + 1 aggregate skip (per_file_failed)
        assert len(sigs) == 2
        assert sigs[0]["passed"] is False
        assert sigs[0]["unrunnable"] is True
        assert sigs[0]["reason"] == "pytest_not_available"
        assert "python" in sigs[0]

    def test_genuine_failure_not_unrunnable(self, project_root):
        """A real test failure (returncode=1, no pytest-missing message) is a
        genuine failure, NOT unrunnable. Control for the unrunnable case: the
        ``unrunnable`` flag must only fire when pytest itself is absent, never
        for an ordinary assertion failure.
        """
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): assert False")
        with patch(
            "subprocess.run",
            return_value=_mk_completed(1, "1 failed\nassert False", ""),
        ):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        # 1 per-file (genuine fail) + 1 aggregate skip (per_file_failed)
        assert len(sigs) == 2
        assert sigs[0]["passed"] is False
        assert "unrunnable" not in sigs[0]

    def test_genuine_pass_not_unrunnable(self, project_root):
        """A real test pass (returncode=0) is a genuine pass, NOT unrunnable.
        Control for the unrunnable case: a clean pass must never carry the
        ``unrunnable`` flag.
        """
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): assert True")
        with patch(
            "subprocess.run",
            return_value=_mk_completed(0, "1 passed", ""),
        ):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        # 1 per-file (genuine pass) + 1 aggregate skip (budget_too_tight)
        assert len(sigs) == 2
        assert sigs[0]["passed"] is True
        assert "unrunnable" not in sigs[0]

    def test_discovered_test_models_suffix_only(self, project_root):
        """A changed ``app.py`` whose only test is ``tests/test_app_models.py``
        (no ``test_app.py`` anywhere) is discovered via the glob and reported
        with its full path.
        """
        (project_root / "app.py").write_text("x = 1")
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_app_models.py").write_text("def test_x(): pass")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["app.py"], {}, project_root, 10)
        # 1 per-file + 1 aggregate skip (budget_too_tight)
        assert len(sigs) == 2
        assert sigs[0]["file"] == "tests/test_app_models.py"

    def test_pre_existing_failure_excluded_from_verdict(self, project_root):
        """A pre-existing failure in ``tests/test_clinical.py`` is excluded
        from the FAIL verdict when the changed file is ``cli.py``.

        The glob ``test_cli_*.py`` requires an underscore boundary after the
        stem ``cli``, so ``test_clinical.py`` (no underscore after ``cli``) is
        NOT discovered. With no test file discovered, Tier 3 produces no
        signals — no FAIL verdict is possible for a failure the verifier
        never ran.
        """
        (project_root / "cli.py").write_text("x = 1")
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_clinical.py").write_text("def test_x(): assert False")
        with patch(
            "subprocess.run",
            return_value=_mk_completed(1, "1 failed", ""),
        ):
            sigs = ev._tier3_test_execution(["cli.py"], {}, project_root, 10)
        assert sigs == []

    def test_changed_module_no_test_anywhere(self, project_root):
        """A changed module with no test file anywhere is SKIPPED by Tier 3.

        Control for the widened glob: the discovery glob must not manufacture
        matches from unrelated files. ``lonely.py`` has no ``test_lonely.py``
        in the project root, no ``tests/test_lonely*.py``, nothing — so Tier 3
        produces no signals.
        """
        (project_root / "lonely.py").write_text("x = 1")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["lonely.py"], {}, project_root, 10)
        assert sigs == []

    def test_cap_survives_widening_exact_not_crowded_out(self, project_root):
        """A changed ``mod.py`` with 4 matching test files (``test_mod.py``,
        ``test_mod_a.py``, ``test_mod_b.py``, ``test_mod_c.py``) — the cap at 3
        survives the widened glob, and the exact-match ``test_mod.py`` is not
        crowded out by the suffixed siblings.
        """
        (project_root / "mod.py").write_text("x = 1")
        for name in ("test_mod.py", "test_mod_a.py", "test_mod_b.py", "test_mod_c.py"):
            (project_root / name).write_text("def test_x(): pass")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["mod.py"], {}, project_root, 10)
        # 3 per-file (capped) + 1 aggregate skip (budget_too_tight)
        assert len(sigs) == 4
        run_files = [s["file"] for s in sigs]
        assert "test_mod.py" in run_files

    def test_real_failure_referencing_changed_module_still_fails(self, project_root):
        """Opposed pair to ``test_pre_existing_candidate_classified_as_warning``:
        a failing test that DOES reference the changed module is a genuine
        regression, not a pre-existing candidate.

        ``cli.py`` is the changed file. ``tests/test_cli.py`` matches the
        discovery glob and its content (``import cli`` + ``assert False``)
        references ``cli`` as a word — the failure is attributable to the
        change. The signal must carry ``passed=False`` (so it FAILS the
        verdict) and must NOT be classified as ``pre_existing_candidate``
        (no ``classification`` field, or one that is not
        ``pre_existing_candidate``). This is a genuine FAIL, not excluded.
        """
        (project_root / "cli.py").write_text("x = 1")
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_cli.py").write_text("import cli\ndef test_x(): assert False")
        with patch(
            "subprocess.run",
            return_value=_mk_completed(1, "1 failed\nassert False", ""),
        ):
            sigs = ev._tier3_test_execution(["cli.py"], {}, project_root, 10)
        # Find the signal for test_cli.py
        cli_sigs = [s for s in sigs if s["file"] == "tests/test_cli.py"]
        assert len(cli_sigs) == 1
        sig = cli_sigs[0]
        assert sig["passed"] is False
        # Not classified as pre-existing — genuine FAIL
        assert sig.get("classification") != "pre_existing_candidate"
        # At least one signal in the batch carries passed=False (genuine FAIL)
        assert any(s["passed"] is False for s in sigs)

    def test_pre_existing_candidate_classified_as_warning(self, project_root):
        """A failing test that does NOT reference the changed module is a
        pre-existing candidate, not a regression.

        ``cli.py`` is the changed file. ``tests/test_cli_extra.py`` matches the
        ``test_cli_*.py`` discovery glob, but its content (``def test_x():
        assert False``) contains no reference to ``cli`` as a word — the failure
        was there before the change. Tier 3 classifies this as
        ``pre_existing_candidate``: the signal carries ``passed=True`` (so it
        does not fail the verdict), ``warning=True`` (so it is surfaced for
        human review), ``classification="pre_existing_candidate"``, and
        ``test_returncode=1`` (the actual pytest exit code). No signal in the
        batch carries ``passed=False``.
        """
        (project_root / "cli.py").write_text("x = 1")
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_cli_extra.py").write_text("def test_x(): assert False")
        with patch(
            "subprocess.run",
            return_value=_mk_completed(1, "1 failed", ""),
        ):
            sigs = ev._tier3_test_execution(["cli.py"], {}, project_root, 10)
        # Find the signal for test_cli_extra.py
        extra_sigs = [s for s in sigs if s["file"] == "tests/test_cli_extra.py"]
        assert len(extra_sigs) == 1
        sig = extra_sigs[0]
        assert sig["passed"] is True
        assert sig["classification"] == "pre_existing_candidate"
        assert sig["warning"] is True
        assert sig["test_returncode"] == 1
        # No signal in the batch carries passed=False
        assert not any(s["passed"] is False for s in sigs)

    def test_glob_boundary_cli_matches_exact_and_underscore_only(self, project_root):
        """Glob boundary for stem ``cli``: ``test_cli.py`` and
        ``test_cli_extra.py`` match, ``test_clinical.py`` does NOT.

        The discovery glob ``test_cli_*.py`` requires an underscore boundary
        after the stem ``cli``, so ``test_clinical.py`` (``cli`` followed by
        ``nical``, no underscore) is excluded. The exact match
        ``test_cli.py`` and the underscore-suffixed ``test_cli_extra.py`` are
        both discovered and reported.
        """
        (project_root / "cli.py").write_text("x = 1")
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_cli.py").write_text("def test_x(): pass")
        (tests_dir / "test_cli_extra.py").write_text("def test_y(): pass")
        (tests_dir / "test_clinical.py").write_text("def test_z(): pass")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["cli.py"], {}, project_root, 10)
        run_files = [s["file"] for s in sigs]
        assert "tests/test_cli.py" in run_files
        assert "tests/test_cli_extra.py" in run_files
        assert "tests/test_clinical.py" not in run_files

    def test_glob_boundary_pulse_does_not_match_pulsed(self, project_root):
        """Glob boundary for stem ``pulse``: ``test_pulsed.py`` does NOT match.

        The discovery glob ``test_pulse_*.py`` requires an underscore boundary
        after the stem ``pulse``, so ``test_pulsed.py`` (``pulse`` followed by
        ``d``, no underscore) is excluded. There is no ``test_pulse.py`` exact
        match either, so Tier 3 discovers no test file and produces no signals.
        """
        (project_root / "pulse.py").write_text("x = 1")
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_pulsed.py").write_text("def test_x(): pass")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["pulse.py"], {}, project_root, 10)
        assert sigs == []

    # ── Aggregate skip recording (regression) ───────────────────────────

    def test_aggregate_skip_recorded_when_budget_too_tight(self, project_root):
        """When the budget is too tight to afford the aggregate pass, the
        skip MUST be recorded as a signal — not silently dropped.

        ``budget_s=10`` is below ``_TIER3_AGGREGATE_MIN_BUDGET_S`` (30.0),
        so the aggregate pass is skipped. The per-file test passes, so the
        only reason for the skip is the tight budget. The skip signal must
        carry ``skipped=True``, ``collection_mode="aggregate"``, and
        ``reason="budget_too_tight"``.
        """
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): assert True")
        with patch("subprocess.run", return_value=_mk_completed(0, "1 passed", "")):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 10)
        agg_sigs = [s for s in sigs if s.get("collection_mode") == "aggregate"]
        assert len(agg_sigs) == 1
        sig = agg_sigs[0]
        assert sig["skipped"] is True
        assert sig["reason"] == "budget_too_tight"
        assert sig["passed"] is True
        assert sig["tier"] == 3
        assert sig["check"] == "pytest"

    def test_aggregate_skip_recorded_when_per_file_failed(self, project_root):
        """When a per-file test fails, the aggregate pass is skipped (it
        would not add signal value). The skip MUST be recorded with
        ``reason="per_file_failed"``.
        """
        tf = project_root / "test_app.py"
        tf.write_text("def test_x(): assert False")
        with patch(
            "subprocess.run",
            return_value=_mk_completed(1, "1 failed\nassert False", ""),
        ):
            sigs = ev._tier3_test_execution(["test_app.py"], {}, project_root, 60)
        agg_sigs = [s for s in sigs if s.get("collection_mode") == "aggregate"]
        assert len(agg_sigs) == 1
        sig = agg_sigs[0]
        assert sig["skipped"] is True
        assert sig["reason"] == "per_file_failed"
        assert sig["passed"] is True


# ---------------------------------------------------------------------------
# _tier4_process_exit
# ---------------------------------------------------------------------------

class TestTier4ProcessExit:
    def test_success(self, project_root):
        with patch("subprocess.run", return_value=_mk_completed(0, "ok", "")):
            sig = ev._tier4_process_exit({"cmd": ["echo", "hi"]}, project_root, 10)
        assert sig["passed"] is True
        assert sig["check"] == "process_exit"

    def test_failure(self, project_root):
        with patch("subprocess.run", return_value=_mk_completed(1, "", "err")):
            sig = ev._tier4_process_exit({"cmd": ["false"]}, project_root, 10)
        assert sig["passed"] is False

    def test_custom_exit_code(self, project_root):
        with patch("subprocess.run", return_value=_mk_completed(2, "", "")):
            sig = ev._tier4_process_exit({"cmd": ["cmd"], "expect_exit": 2}, project_root, 10)
        assert sig["passed"] is True

    def test_timeout(self, project_root):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=30)):
            sig = ev._tier4_process_exit({"cmd": ["sleep", "100"]}, project_root, 10)
        assert sig["passed"] is False
        assert sig["error"] == "timeout"

    def test_exception(self, project_root):
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            sig = ev._tier4_process_exit({"cmd": ["x"]}, project_root, 10)
        assert sig["passed"] is False
        assert "boom" in sig["error"]

    def test_with_cwd(self, project_root):
        sub = project_root / "subdir"
        sub.mkdir()
        with patch("subprocess.run", return_value=_mk_completed(0, "", "")) as mock_run:
            sig = ev._tier4_process_exit({"cmd": ["ls"], "cwd": "subdir"}, project_root, 10)
        assert sig["passed"] is True
        assert mock_run.call_args.kwargs["cwd"] == str(sub)


# ---------------------------------------------------------------------------
# _tier4_http_check
# ---------------------------------------------------------------------------

class TestTier4HttpCheck:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            sig = ev._tier4_http_check("http://127.0.0.1:8000", "/health", 200, 5)
        assert sig["passed"] is True
        assert sig["status"] == 200
        assert sig["check"] == "http_health"

    def test_wrong_status(self):
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            sig = ev._tier4_http_check("http://127.0.0.1:8000", "/health", 200, 5)
        assert sig["passed"] is False
        assert sig["status"] == 500

    def test_http_error(self):
        import urllib.error
        err = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            sig = ev._tier4_http_check("http://127.0.0.1:8000", "/health", 200, 5)
        assert sig["passed"] is False
        assert sig["status"] == 404

    def test_connection_error(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            sig = ev._tier4_http_check("http://127.0.0.1:8000", "/health", 200, 5)
        assert sig["passed"] is False
        assert "refused" in sig["error"]


# ---------------------------------------------------------------------------
# _tier4_http_json
# ---------------------------------------------------------------------------

class TestTier4HttpJson:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"key": "value"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            sig = ev._tier4_http_json("http://127.0.0.1:8000", "/api", "GET", 200, ["key"], None, 5)
        assert sig["passed"] is True
        assert sig["missing_keys"] == []

    def test_missing_keys(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"other": "val"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            sig = ev._tier4_http_json("http://127.0.0.1:8000", "/api", "GET", 200, ["key"], None, 5)
        assert sig["passed"] is False
        assert "key" in sig["missing_keys"]

    def test_http_error(self):
        import urllib.error
        err = urllib.error.HTTPError("url", 500, "Server Error", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            sig = ev._tier4_http_json("http://127.0.0.1:8000", "/api", "POST", 200, [], {"x": 1}, 5)
        assert sig["passed"] is False

    def test_connection_error(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            sig = ev._tier4_http_json("http://127.0.0.1:8000", "/api", "GET", 200, [], None, 5)
        assert sig["passed"] is False
        assert "refused" in sig["error"]

    def test_with_body(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"result": "ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            sig = ev._tier4_http_json("http://127.0.0.1:8000", "/api", "POST", 200, ["result"], {"q": "test"}, 5)
        assert sig["passed"] is True


# ---------------------------------------------------------------------------
# _poll_for_port
# ---------------------------------------------------------------------------

class TestPollForPort:
    def test_finds_port(self):
        proc = MagicMock()
        proc.poll.return_value = None
        proc.stdout.readline.return_value = "Uvicorn running on http://127.0.0.1:8080\n"
        with patch("select.select", return_value=([proc.stdout], [], [])):
            port = ev._poll_for_port(proc, 2)
        assert port == 8080

    def test_finds_port_serving(self):
        proc = MagicMock()
        proc.poll.return_value = None
        proc.stdout.readline.return_value = "Serving HTTP on 0.0.0.0 port 9000\n"
        with patch("select.select", return_value=([proc.stdout], [], [])):
            port = ev._poll_for_port(proc, 2)
        assert port == 9000

    def test_process_exited_no_port(self):
        proc = MagicMock()
        proc.poll.return_value = 0
        proc.stdout.read.return_value = "some output"
        port = ev._poll_for_port(proc, 1)
        assert port is None

    def test_timeout_no_port(self):
        proc = MagicMock()
        proc.poll.return_value = None
        proc.stdout.readline.return_value = ""
        with patch("select.select", return_value=([], [], [])):
            port = ev._poll_for_port(proc, 0.2)
        assert port is None

    def test_select_exception(self):
        proc = MagicMock()
        proc.poll.return_value = None
        proc.stdout.readline.return_value = "Uvicorn running on http://127.0.0.1:8080\n"
        with patch("select.select", side_effect=OSError("bad fd")):
            # After select fails, it sleeps and retries. Eventually times out.
            port = ev._poll_for_port(proc, 0.3)
        assert port is None


# ---------------------------------------------------------------------------
# _tier4_runtime_check
# ---------------------------------------------------------------------------

class TestTier4RuntimeCheck:
    def test_empty_checks(self, project_root):
        sigs = ev._tier4_runtime_check([], project_root, 10)
        assert sigs == []

    def test_process_exit_check(self, project_root):
        with patch("subprocess.run", return_value=_mk_completed(0, "ok", "")):
            sigs = ev._tier4_runtime_check(
                [{"type": "process_exit", "cmd": ["echo", "hi"]}], project_root, 10
            )
        assert len(sigs) == 1
        assert sigs[0]["tier"] == 4
        assert sigs[0]["passed"] is True

    def test_http_health_no_cmd_skipped(self, project_root):
        sigs = ev._tier4_runtime_check(
            [{"type": "http_health", "cmd": []}], project_root, 10
        )
        assert sigs == []

    def test_http_health_server_no_port(self, project_root):
        proc_mock = MagicMock()
        proc_mock.poll.return_value = None
        proc_mock.stdout.readline.return_value = ""
        proc_mock.terminate = MagicMock()
        proc_mock.wait = MagicMock()
        with patch("subprocess.Popen", return_value=proc_mock), \
             patch("select.select", return_value=([], [], [])):
            sigs = ev._tier4_runtime_check(
                [{"type": "http_health", "cmd": ["python", "-m", "uvicorn"],
                  "startup_wait_s": 0.2}], project_root, 5
            )
        assert len(sigs) == 1
        assert sigs[0]["passed"] is False
        assert "did not start" in sigs[0].get("error", "")

    def test_http_health_success(self, project_root):
        proc_mock = MagicMock()
        proc_mock.poll.return_value = None
        proc_mock.stdout.readline.return_value = "Uvicorn running on http://127.0.0.1:8080\n"
        proc_mock.terminate = MagicMock()
        proc_mock.wait = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("subprocess.Popen", return_value=proc_mock), \
             patch("urllib.request.urlopen", return_value=mock_resp), \
             patch("select.select", return_value=([proc_mock.stdout], [], [])):
            sigs = ev._tier4_runtime_check(
                [{"type": "http_health", "cmd": ["python", "-m", "uvicorn"],
                  "startup_wait_s": 2, "url": "/health", "expect_status": 200}],
                project_root, 10
            )
        assert len(sigs) == 1
        assert sigs[0]["passed"] is True
        assert sigs[0]["port"] == 8080

    def test_http_json_success(self, project_root):
        proc_mock = MagicMock()
        proc_mock.poll.return_value = None
        proc_mock.stdout.readline.return_value = "Uvicorn running on http://127.0.0.1:9090\n"
        proc_mock.terminate = MagicMock()
        proc_mock.wait = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("subprocess.Popen", return_value=proc_mock), \
             patch("urllib.request.urlopen", return_value=mock_resp), \
             patch("select.select", return_value=([proc_mock.stdout], [], [])):
            sigs = ev._tier4_runtime_check(
                [{"type": "http_json", "cmd": ["python", "-m", "uvicorn"],
                  "startup_wait_s": 2, "url": "/api", "expect_status": 200,
                  "expect_keys": ["status"], "method": "GET"}],
                project_root, 10
            )
        assert len(sigs) == 1
        assert sigs[0]["passed"] is True

    def test_unknown_check_type_no_port(self, project_root):
        proc_mock = MagicMock()
        proc_mock.poll.return_value = None
        proc_mock.stdout.readline.return_value = ""
        proc_mock.terminate = MagicMock()
        proc_mock.wait = MagicMock()
        with patch("subprocess.Popen", return_value=proc_mock), \
             patch("select.select", return_value=([], [], [])):
            sigs = ev._tier4_runtime_check(
                [{"type": "unknown", "cmd": ["python"], "startup_wait_s": 0.2}],
                project_root, 5
            )
        # Unknown type with cmd starts a server; port polling fails → signal with error
        assert len(sigs) == 1
        assert sigs[0]["passed"] is False

    def test_popen_exception(self, project_root):
        with patch("subprocess.Popen", side_effect=OSError("no such file")):
            sigs = ev._tier4_runtime_check(
                [{"type": "http_health", "cmd": ["nonexistent"], "startup_wait_s": 1}],
                project_root, 5
            )
        assert len(sigs) == 1
        assert sigs[0]["passed"] is False


# ---------------------------------------------------------------------------
# detect_runtime_checks
# ---------------------------------------------------------------------------

class TestDetectRuntimeChecks:
    def test_empty_project(self, tmp_path):
        checks = ev.detect_runtime_checks(tmp_path)
        assert checks == []

    def test_fastapi_detection(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["fastapi", "uvicorn"]\n'
        )
        checks = ev.detect_runtime_checks(tmp_path)
        assert len(checks) == 1
        assert checks[0]["type"] == "http_health"
        assert checks[0]["detected_from"] == "pyproject.toml"

    def test_node_detection(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"start": "node server.js"}})
        )
        checks = ev.detect_runtime_checks(tmp_path)
        assert len(checks) == 1
        assert checks[0]["detected_from"] == "package.json"

    def test_dockerfile_detection(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM node:18\nEXPOSE 3000\n")
        checks = ev.detect_runtime_checks(tmp_path)
        assert len(checks) == 1
        assert checks[0]["detected_from"] == "Dockerfile"

    def test_dockerfile_no_expose(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM node:18\n")
        checks = ev.detect_runtime_checks(tmp_path)
        assert checks == []

    def test_package_json_no_start(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"scripts": {}}))
        checks = ev.detect_runtime_checks(tmp_path)
        assert checks == []

    def test_pyproject_no_fastapi(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
        checks = ev.detect_runtime_checks(tmp_path)
        assert checks == []

    def test_package_json_invalid(self, tmp_path):
        (tmp_path / "package.json").write_text("not valid json")
        checks = ev.detect_runtime_checks(tmp_path)
        assert checks == []

    def test_all_three(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('dependencies = ["uvicorn"]')
        (tmp_path / "package.json").write_text(json.dumps({"scripts": {"start": "x"}}))
        (tmp_path / "Dockerfile").write_text("EXPOSE 8080\n")
        checks = ev.detect_runtime_checks(tmp_path)
        assert len(checks) == 3


# ---------------------------------------------------------------------------
# extract_claims
# ---------------------------------------------------------------------------

class TestExtractClaims:
    def test_empty_text(self):
        assert ev.extract_claims("") == []

    def test_count_claim_plus(self):
        claims = ev.extract_claims("Add +5 tests to the suite")
        count_claims = [c for c in claims if c["claim_type"] == "count"]
        assert len(count_claims) >= 1
        assert count_claims[0]["quantity"] == 5
        assert count_claims[0]["unit"] == "test"

    def test_count_claim_add(self):
        claims = ev.extract_claims("add 3 files to the project")
        count_claims = [c for c in claims if c["claim_type"] == "count"]
        assert any(c["quantity"] == 3 for c in count_claims)

    def test_count_claim_new(self):
        claims = ev.extract_claims("5 new endpoints")
        count_claims = [c for c in claims if c["claim_type"] == "count"]
        assert any(c["quantity"] == 5 and c["unit"] == "endpoint" for c in count_claims)

    def test_file_claim(self):
        claims = ev.extract_claims("create file `src/app.py` for the feature")
        file_claims = [c for c in claims if c["claim_type"] == "file"]
        assert any(c["target"] == "src/app.py" for c in file_claims)

    def test_file_claim_txt_absolute(self):
        """extract_claims should recognize .txt files at absolute paths."""
        claims = ev.extract_claims('Create /tmp/parallel_agy.txt with text "agy was here"')
        file_claims = [c for c in claims if c["claim_type"] == "file"]
        assert any(c["target"] == "/tmp/parallel_agy.txt" for c in file_claims)

    def test_file_claim_txt_relative(self):
        """extract_claims should recognize relative .txt paths."""
        claims = ev.extract_claims("write notes.txt with the meeting summary")
        file_claims = [c for c in claims if c["claim_type"] == "file"]
        assert any(c["target"] == "notes.txt" for c in file_claims)

    def test_file_claim_csv(self):
        """extract_claims should recognize .csv files."""
        claims = ev.extract_claims("add data.csv to the project")
        file_claims = [c for c in claims if c["claim_type"] == "file"]
        assert any(c["target"] == "data.csv" for c in file_claims)

    def test_file_claim_toml(self):
        """extract_claims should recognize .toml config files."""
        claims = ev.extract_claims("create pyproject.toml for the package")
        file_claims = [c for c in claims if c["claim_type"] == "file"]
        assert any(c["target"] == "pyproject.toml" for c in file_claims)

    def test_increase_by(self):
        claims = ev.extract_claims("increase by 10 lines")
        count_claims = [c for c in claims if c["claim_type"] == "count"]
        assert any(c["quantity"] == 10 for c in count_claims)

    def test_dedup(self):
        claims = ev.extract_claims("+5 tests +5 tests")
        # Same raw_match should be deduplicated
        count_claims = [c for c in claims if c["claim_type"] == "count"]
        assert len(count_claims) == 1

    def test_no_claims(self):
        claims = ev.extract_claims("This is a plan with no measurable claims.")
        assert claims == []


# ---------------------------------------------------------------------------
# _measure_count
# ---------------------------------------------------------------------------

class TestMeasureCount:
    def test_test_count(self, tmp_path):
        (tmp_path / "test_a.py").write_text("def test_one(): pass\ndef test_two(): pass\n")
        (tmp_path / "test_b.py").write_text("def test_three(): pass\n")
        assert ev._measure_count("test", tmp_path) == 3

    def test_file_count(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        assert ev._measure_count("file", tmp_path) >= 2

    def test_line_count(self, tmp_path):
        (tmp_path / "a.py").write_text("line1\nline2\nline3\n")
        result = ev._measure_count("line", tmp_path)
        assert result >= 3

    def test_endpoint_count(self, tmp_path):
        (tmp_path / "app.py").write_text(
            "@app.get('/health')\n@router.post('/data')\n"
        )
        result = ev._measure_count("endpoint", tmp_path)
        assert result >= 2

    def test_function_count(self, tmp_path):
        (tmp_path / "a.py").write_text("def foo(): pass\ndef bar(): pass\n")
        result = ev._measure_count("function", tmp_path)
        assert result >= 2

    def test_module_count(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "test_b.py").write_text("x = 1")
        result = ev._measure_count("module", tmp_path)
        # modules excludes test_ files
        assert result >= 1

    def test_chunk_count(self, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        (brain / "data.jsonl").write_text('{"a":1}\n{"b":2}\n')
        result = ev._measure_count("chunk", tmp_path)
        assert result >= 2

    def test_unknown_unit(self, tmp_path):
        assert ev._measure_count("unknown", tmp_path) == 0

    def test_exception_returns_zero(self):
        # Non-existent path should not crash
        result = ev._measure_count("test", Path("/nonexistent/path/xyz"))
        assert result == 0


# ---------------------------------------------------------------------------
# capture_outcome_baseline
# ---------------------------------------------------------------------------

class TestCaptureOutcomeBaseline:
    def test_captures_baseline(self, tmp_path):
        plan = "Add +5 tests and create file `src/new.py`"
        result = ev.capture_outcome_baseline(plan, tmp_path)
        assert "claims" in result
        assert "captured_at" in result
        assert "plan_hash" in result
        assert len(result["plan_hash"]) == 12
        # File should be written
        baseline_file = tmp_path / ".brain" / "driver" / "outcome_baseline.json"
        assert baseline_file.exists()
        saved = json.loads(baseline_file.read_text())
        assert saved["plan_hash"] == result["plan_hash"]

    def test_no_claims(self, tmp_path):
        result = ev.capture_outcome_baseline("no claims here", tmp_path)
        assert result["claims"] == []
        assert result["plan_hash"]


# ---------------------------------------------------------------------------
# _tier5_outcome_check
# ---------------------------------------------------------------------------

class TestTier5OutcomeCheck:
    def test_baseline_not_found(self, tmp_path):
        sigs = ev._tier5_outcome_check("plan", tmp_path, 10, tmp_path / "missing.json")
        assert sigs == []

    def test_invalid_json(self, tmp_path):
        bf = tmp_path / "baseline.json"
        bf.write_text("not json")
        sigs = ev._tier5_outcome_check("plan", tmp_path, 10, bf)
        assert sigs == []

    def test_count_claim_pass(self, tmp_path):
        bf = tmp_path / "baseline.json"
        bf.write_text(json.dumps({
            "claims": [{
                "claim_type": "count",
                "unit": "test",
                "claimed_delta": 4,
                "baseline_value": 0,
                "raw_match": "+4 tests",
            }]
        }))
        # Create test files so current > baseline
        (tmp_path / "test_a.py").write_text(
            "def test_one(): pass\ndef test_two(): pass\ndef test_three(): pass\ndef test_four(): pass\n"
        )
        sigs = ev._tier5_outcome_check("plan", tmp_path, 10, bf)
        assert len(sigs) == 1
        assert sigs[0]["passed"] is True

    def test_count_claim_fail(self, tmp_path):
        bf = tmp_path / "baseline.json"
        bf.write_text(json.dumps({
            "claims": [{
                "claim_type": "count",
                "unit": "test",
                "claimed_delta": 100,
                "baseline_value": 0,
                "raw_match": "+100 tests",
            }]
        }))
        sigs = ev._tier5_outcome_check("plan", tmp_path, 10, bf)
        assert len(sigs) == 1
        assert sigs[0]["passed"] is False
        assert "PREMATURE VICTORY" in sigs[0]["error"]

    def test_file_claim_pass(self, tmp_path):
        bf = tmp_path / "baseline.json"
        bf.write_text(json.dumps({
            "claims": [{
                "claim_type": "file",
                "target": "new_file.py",
                "baseline_exists": False,
                "raw_match": "create new_file.py",
            }]
        }))
        (tmp_path / "new_file.py").write_text("x = 1")
        sigs = ev._tier5_outcome_check("plan", tmp_path, 10, bf)
        assert len(sigs) == 1
        assert sigs[0]["passed"] is True

    def test_file_claim_fail(self, tmp_path):
        bf = tmp_path / "baseline.json"
        bf.write_text(json.dumps({
            "claims": [{
                "claim_type": "file",
                "target": "missing.py",
                "baseline_exists": False,
                "raw_match": "create missing.py",
            }]
        }))
        sigs = ev._tier5_outcome_check("plan", tmp_path, 10, bf)
        assert len(sigs) == 1
        assert sigs[0]["passed"] is False

    def test_empty_claims(self, tmp_path):
        bf = tmp_path / "baseline.json"
        bf.write_text(json.dumps({"claims": []}))
        sigs = ev._tier5_outcome_check("plan", tmp_path, 10, bf)
        assert sigs == []


# ---------------------------------------------------------------------------
# _find_recent_plan
# ---------------------------------------------------------------------------

class TestFindRecentPlan:
    def test_no_plan(self, tmp_path):
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = ev._find_recent_plan(tmp_path)
        assert result is None

    def test_manual_plan(self, tmp_path):
        driver = tmp_path / ".brain" / "driver"
        driver.mkdir(parents=True)
        plan = driver / "current_plan.md"
        plan.write_text("# Plan")
        with patch("pathlib.Path.home", return_value=tmp_path / "fakehome"):
            result = ev._find_recent_plan(tmp_path)
        assert result == plan

    def test_claude_plan(self, tmp_path):
        fake_home = tmp_path / "fakehome"
        plans_dir = fake_home / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        plan1 = plans_dir / "plan1.md"
        plan1.write_text("# Plan 1")
        time.sleep(0.05)
        plan2 = plans_dir / "plan2.md"
        plan2.write_text("# Plan 2")
        with patch("pathlib.Path.home", return_value=fake_home):
            result = ev._find_recent_plan(tmp_path)
        assert result == plan2  # most recent


# ---------------------------------------------------------------------------
# build_calibration_dpo
# ---------------------------------------------------------------------------

class TestBuildCalibrationDpo:
    def test_verified_returns_none(self):
        result = ev.build_calibration_dpo({}, {}, {"verified": True})
        assert result is None

    def test_no_failed_signals(self):
        result = ev.build_calibration_dpo({}, {}, {
            "verified": False,
            "signals": [{"passed": True, "check": "ok"}],
        })
        assert result is None

    def test_with_failed_signals(self):
        task = {"description": "do something"}
        response = {"result": "I did it correctly"}
        verif = {
            "verified": False,
            "signals": [
                {"passed": False, "check": "py_compile", "file": "app.py", "error": "SyntaxError"},
            ],
        }
        result = ev.build_calibration_dpo(task, response, verif)
        assert result is not None
        assert result["prompt"] == "do something"
        assert result["rejected"] == "I did it correctly"
        assert "SyntaxError" in result["chosen"]
        assert result["metadata"]["source"] == "calibration_dpo"
        assert result["metadata"]["quality"] == "gold"

    def test_failed_signal_no_error(self):
        task = {"description": "task"}
        response = {"result": "response"}
        verif = {
            "verified": False,
            "signals": [{"passed": False, "check": "import", "module": "app"}],
        }
        result = ev.build_calibration_dpo(task, response, verif)
        assert result is not None
        assert "import" in result["chosen"]


# ---------------------------------------------------------------------------
# verify_execution (integration with mocks)
# ---------------------------------------------------------------------------

class TestVerifyExecution:
    def test_empty_diff_all_skipped(self, project_root):
        config = {"execution_verification_tiers": [0]}
        with patch("subprocess.run") as mock_run:
            # Call order: submodule paths, diff, diff --cached, ls-files
            mock_run.side_effect = [
                _mk_completed(stdout=""),  # submodule paths (no .gitmodules)
                _mk_completed(stdout=""),  # diff --name-only
                _mk_completed(stdout=""),  # diff --cached --name-only
                _mk_completed(stdout=""),  # ls-files --others --exclude-standard
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert result["verified"] is False
        assert result["tier_reached"] == -1
        assert 0 in result["tiers_failed"]

    def test_tier0_passes_with_files(self, project_root):
        config = {"execution_verification_tiers": [0]}
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mk_completed(stdout="app.py\n"),
                _mk_completed(stdout=""),
                _mk_completed(stdout="abc123\n"),
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert result["verified"] is True
        assert 0 in result["tiers_passed"]

    def test_verify_execution_passes_context_from_config(self, project_root):
        """fw-1786069497: ``config["_verification_context"]`` reaches
        ``_get_changed_files``.

        The `TestGetChangedFiles` pre_commit tests pin the *filter*; this pins
        the *wiring*. ``ground.run_ground`` never calls ``_get_changed_files``
        directly — it only puts the key in the config dict it hands to
        ``verify_execution``. If that key were dropped, renamed, or read under a
        different name here, every one of those tests would stay green while the
        pre-commit hook silently reverted to build-path filtering.

        Same staged-gitlink-bump mocks as
        ``test_pre_commit_context_staged_submodule_passes_tier0``, driven
        through the public entry point: Tier 0 must PASS. Drop the
        ``_verification_context`` key and this asserts False (the default is
        ``"build"``), so the assertion is a real guard on the handoff.
        """
        config = {
            "execution_verification_tiers": [0],
            "_verification_context": "pre_commit",
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # git config --file .gitmodules --get-regexp path
                _mk_completed(stdout="submodule.nucleus-mcp.path nucleus-mcp\n"),
                _mk_completed(stdout=""),               # diff --name-only (unstaged)
                _mk_completed(stdout="nucleus-mcp\n"),  # diff --cached (pointer bump)
                _mk_completed(stdout=""),               # diff --name-only pre_head
                _mk_completed(stdout=""),               # ls-files (no untracked)
                _mk_completed(stdout="abc123\n"),       # rev-parse HEAD
            ]
            result = ev.verify_execution("", "abc123", config, project_root)
        assert 0 in result["tiers_passed"]
        assert result["verified"] is True
        tier0 = [s for s in result["signals"] if s["tier"] == 0][0]
        assert tier0["files_count"] == 1

    def test_disabled_tiers_skipped(self, project_root):
        config = {"execution_verification_tiers": []}
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mk_completed(stdout="app.py\n"),
                _mk_completed(stdout=""),
                _mk_completed(stdout="abc123\n"),
            ]
            result = ev.verify_execution("", "", config, project_root)
        # All tiers skipped, no tiers passed
        assert result["verified"] is False
        assert 0 in result["tiers_skipped"]

    def test_full_flow_with_mocks(self, project_root):
        """Test a full flow with tier 0-3 enabled and mocked subprocess."""
        (project_root / "app.py").write_text("x = 1")
        config = {
            "execution_verification_tiers": [0, 1, 2, 3],
            "execution_verification_timeout_s": 30,
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mk_completed(stdout="app.py\n"),  # diff --name-only
                _mk_completed(stdout=""),  # diff --cached
                _mk_completed(stdout="sha\n"),  # rev-parse HEAD
                _mk_completed(0, "", ""),  # py_compile
                _mk_completed(0, "", ""),  # import
                _mk_completed(0, "1 passed", ""),  # pytest (if test file found)
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert "signals" in result
        assert "receipt_id" in result
        assert "duration_s" in result
        assert "commit_sha" in result

    def test_with_task_id(self, project_root):
        config = {
            "execution_verification_tiers": [0],
            "_current_task": {"id": "task_123"},
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mk_completed(stdout="app.py\n"),
                _mk_completed(stdout=""),
                _mk_completed(stdout="sha\n"),
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert result["task_id"] == "task_123"

    def test_git_rev_parse_failure(self, project_root):
        config = {"execution_verification_tiers": [0]}
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mk_completed(stdout="app.py\n"),
                _mk_completed(stdout=""),
                _mk_completed(1, "", "error"),  # rev-parse fails
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert result["commit_sha"] == ""

    def test_git_rev_parse_exception(self, project_root):
        config = {"execution_verification_tiers": [0]}

        # We need the first two calls to succeed and the third to raise
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                return _mk_completed(stdout="app.py\n" if call_count[0] == 1 else "")
            raise subprocess.TimeoutExpired(cmd="git", timeout=3)

        with patch("subprocess.run", side_effect=side_effect):
            result = ev.verify_execution("", "", config, project_root)
        assert result["commit_sha"] == ""

    def test_tier4_with_runtime_checks(self, project_root):
        config = {
            "execution_verification_tiers": [0, 4],
            "execution_verification_runtime_checks": [
                {"type": "process_exit", "cmd": ["echo", "hi"]}
            ],
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mk_completed(stdout=""),           # submodule paths
                _mk_completed(stdout="app.py\n"),   # diff --name-only
                _mk_completed(stdout=""),           # diff --cached
                _mk_completed(stdout=""),           # ls-files (no untracked)
                _mk_completed(0, "hi", ""),         # process_exit (tier 4)
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert 4 in result["tiers_passed"]

    def test_tier4_no_checks_skipped(self, project_root):
        config = {
            "execution_verification_tiers": [0, 4],
            "execution_verification_runtime_checks": [],
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mk_completed(stdout="app.py\n"),
                _mk_completed(stdout=""),
                _mk_completed(stdout="sha\n"),
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert 4 in result["tiers_skipped"]

    def test_tier5_skipped_no_baseline(self, project_root):
        config = {"execution_verification_tiers": [0, 5]}
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mk_completed(stdout="app.py\n"),
                _mk_completed(stdout=""),
                _mk_completed(stdout="sha\n"),
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert 5 in result["tiers_skipped"]

    def test_tier5_with_baseline(self, project_root):
        # Set up baseline
        driver = project_root / ".brain" / "driver"
        driver.mkdir(parents=True)
        baseline = driver / "outcome_baseline.json"
        baseline.write_text(json.dumps({
            "claims": [{
                "claim_type": "file",
                "target": "new.py",
                "baseline_exists": False,
                "raw_match": "create new.py",
            }]
        }))
        (project_root / "new.py").write_text("x = 1")
        # Set up plan file
        plan = driver / "current_plan.md"
        plan.write_text("# Plan")

        config = {"execution_verification_tiers": [0, 5]}
        with patch("subprocess.run") as mock_run, \
             patch("pathlib.Path.home", return_value=project_root / "fakehome"):
            mock_run.side_effect = [
                _mk_completed(stdout="new.py\n"),
                _mk_completed(stdout=""),
                _mk_completed(stdout="sha\n"),
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert 5 in result["tiers_passed"]

    def test_python_path_config(self, project_root):
        (project_root / "app.py").write_text("x = 1")
        config = {
            "execution_verification_tiers": [0, 2],
            "python_path": "/custom/python",
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mk_completed(stdout=""),           # submodule paths
                _mk_completed(stdout="app.py\n"),   # diff --name-only
                _mk_completed(stdout=""),           # diff --cached
                _mk_completed(stdout=""),           # ls-files (no untracked)
                _mk_completed(0, "", ""),           # import check (tier 2)
            ]
            result = ev.verify_execution("", "", config, project_root)
        assert 2 in result["tiers_passed"]
