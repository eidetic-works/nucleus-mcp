"""Regression test for crit_verify_bypass: _verify_diff_content threshold.

Before the fix, the threshold was 5 real lines — an LLM could add a trivial
comment (# TODO) to the right file and pass verification. The fix raises the
threshold to 10 real lines AND requires at least one function/class definition
(or >=20 real lines for substantial config-only changes).

This test mocks git subprocess calls and verifies the threshold logic directly.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _mk_completed(returncode=0, stdout="", stderr=""):
    r = MagicMock(spec=subprocess.CompletedProcess)
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = stderr
    return r


def _make_executor():
    """Create an ExecutorDaemon-like object with just _verify_diff_content."""
    from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon
    # We can't easily construct a full ExecutorDaemon, so we call the method
    # as an unbound function with a mock self that has .config.repo_root
    return ExecutorDaemon


def _patch_git(diff_stat_output, diff_full_output):
    """Patch subprocess.run to return canned git diff output."""
    def _fake_run(cmd, **kwargs):
        if "--stat" in cmd:
            return _mk_completed(stdout=diff_stat_output)
        return _mk_completed(stdout=diff_full_output)
    return patch("subprocess.run", side_effect=_fake_run)


@pytest.fixture
def fake_repo(tmp_path):
    """A fake repo root that exists."""
    repo = tmp_path / "fake-repo"
    repo.mkdir()
    return repo


class TestVerifyDiffContentThreshold:
    """Tests for crit_verify_bypass fix: threshold raised from 5 to 10 + function/class check."""

    def test_trivial_comment_fails(self, fake_repo):
        """A diff with only 3 comment lines must NOT pass (was passing with threshold=5)."""
        diff = (
            "diff --git a/file.py b/file.py\n"
            "+# TODO: fix later\n"
            "+# FIXME: not done\n"
            "+# NOTE: placeholder\n"
        )
        stat = " file.py | 3 +\n 3 files changed, 3 insertions(+)\n"

        ExecutorDaemon = _make_executor()
        # Create a minimal mock self
        class FakeSelf:
            class config:
                repo_root = fake_repo
        fake_self = FakeSelf()

        with _patch_git(stat, diff):
            result = ExecutorDaemon._verify_diff_content(fake_self, "abc123")
        assert result["pass"] is False, "Trivial comments must not pass verification"
        assert result["real_lines"] == 0  # comments don't count as real lines

    def test_five_real_lines_without_function_fails(self, fake_repo):
        """5 real lines without a function/class definition must NOT pass.

        Before the fix: threshold was 5, so 5 real lines passed.
        After the fix: threshold is 10 AND requires function/class OR >=20 lines.
        """
        diff = (
            "diff --git a/file.py b/file.py\n"
            "+x = 1\n"
            "+y = 2\n"
            "+z = 3\n"
            "+a = 4\n"
            "+b = 5\n"
        )
        stat = " file.py | 5 +\n 1 file changed, 5 insertions(+)\n"

        ExecutorDaemon = _make_executor()
        class FakeSelf:
            class config:
                repo_root = fake_repo
        fake_self = FakeSelf()

        with _patch_git(stat, diff):
            result = ExecutorDaemon._verify_diff_content(fake_self, "abc123")
        assert result["pass"] is False, "5 real lines without function/class must not pass"
        assert result["real_lines"] == 5

    def test_ten_real_lines_with_function_passes(self, fake_repo):
        """10 real lines including a function definition must pass."""
        diff = (
            "diff --git a/file.py b/file.py\n"
            "+def fix_bug():\n"
            "+    x = 1\n"
            "+    y = 2\n"
            "+    z = 3\n"
            "+    a = 4\n"
            "+    b = 5\n"
            "+    c = 6\n"
            "+    d = 7\n"
            "+    e = 8\n"
            "+    return x + y + z\n"
        )
        stat = " file.py | 10 +\n 1 file changed, 10 insertions(+)\n"

        ExecutorDaemon = _make_executor()
        class FakeSelf:
            class config:
                repo_root = fake_repo
        fake_self = FakeSelf()

        with _patch_git(stat, diff):
            result = ExecutorDaemon._verify_diff_content(fake_self, "abc123")
        assert result["pass"] is True, "10 real lines with function def must pass"
        assert result["real_lines"] == 10
        assert result["has_function_or_class"] is True

    def test_twenty_config_lines_without_function_passes(self, fake_repo):
        """20 real config lines without a function definition must pass (substantial config change)."""
        lines = [f"+key_{i} = value_{i}" for i in range(20)]
        diff = "diff --git a/config.py b/config.py\n" + "\n".join(lines) + "\n"
        stat = " config.py | 20 +\n 1 file changed, 20 insertions(+)\n"

        ExecutorDaemon = _make_executor()
        class FakeSelf:
            class config:
                repo_root = fake_repo
        fake_self = FakeSelf()

        with _patch_git(stat, diff):
            result = ExecutorDaemon._verify_diff_content(fake_self, "abc123")
        assert result["pass"] is True, "20 real config lines must pass (substantial)"
        assert result["real_lines"] == 20
        assert result["has_function_or_class"] is False

    def test_ten_config_lines_without_function_fails(self, fake_repo):
        """10 real config lines without a function definition must NOT pass.

        10 lines meets the threshold but lacks function/class and doesn't reach 20.
        """
        lines = [f"+key_{i} = value_{i}" for i in range(10)]
        diff = "diff --git a/config.py b/config.py\n" + "\n".join(lines) + "\n"
        stat = " config.py | 10 +\n 1 file changed, 10 insertions(+)\n"

        ExecutorDaemon = _make_executor()
        class FakeSelf:
            class config:
                repo_root = fake_repo
        fake_self = FakeSelf()

        with _patch_git(stat, diff):
            result = ExecutorDaemon._verify_diff_content(fake_self, "abc123")
        assert result["pass"] is False, "10 config lines without function/class must not pass"
        assert result["real_lines"] == 10

    def test_class_definition_counts_as_function_or_class(self, fake_repo):
        """A class definition should satisfy the has_function_or_class check."""
        diff = (
            "diff --git a/file.py b/file.py\n"
            "+class NewFeature:\n"
            "+    def __init__(self):\n"
            "+        self.x = 1\n"
            "+        self.y = 2\n"
            "+        self.z = 3\n"
            "+        self.a = 4\n"
            "+        self.b = 5\n"
            "+        self.c = 6\n"
            "+        self.d = 7\n"
            "+        pass\n"
        )
        stat = " file.py | 10 +\n 1 file changed, 10 insertions(+)\n"

        ExecutorDaemon = _make_executor()
        class FakeSelf:
            class config:
                repo_root = fake_repo
        fake_self = FakeSelf()

        with _patch_git(stat, diff):
            result = ExecutorDaemon._verify_diff_content(fake_self, "abc123")
        assert result["pass"] is True
        assert result["has_function_or_class"] is True
