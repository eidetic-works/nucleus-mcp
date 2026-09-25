"""Automatic detection of a mode='read' dispatch that mutated the working tree.

THE RISK THIS GUARDS (2026-08-18): devin's read_flags moved from
("--permission-mode", "auto") -- confirmed insufficient, blocks real tool
calls -- to ("--permission-mode", "dangerous"), identical to write_flags.
That grants a 'read' dispatch real, unrestricted file-write access. The only
existing backstop (expect_paths/_snapshot_paths) is opt-in; most callers,
including this session's own vendor-lane dispatches, never pass it. This
test file proves the AUTOMATIC replacement actually works: a git-porcelain
snapshot taken before/after every read-mode dispatch, unconditionally.

Each test states its failure direction; a check that can only pass is not a
check.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server_nucleus.runtime import vendor_dispatch as vd


@pytest.fixture()
def git_repo():
    """A real, throwaway git repo -- not a mock of git, the actual binary,
    so _git_porcelain_snapshot exercises its real subprocess.run path."""
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["git", "init", "-q"], cwd=td, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=td, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=td, check=True)
        (Path(td) / "seed.txt").write_text("seed\n")
        subprocess.run(["git", "add", "seed.txt"], cwd=td, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=td, check=True)
        yield td


class _FakeCompletedProcess:
    def __init__(self, stdout="ok output here", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _run_executor(repo_dir: str, mode: str, side_effect_writes_file: bool):
    """Run VendorCLIExecutor against a fake vendor subprocess, optionally
    writing a file as a side effect (simulating a rogue tool call), with
    subprocess.run patched only for the VENDOR call, not for git."""
    real_subprocess_run = subprocess.run

    def fake_run(argv, **kwargs):
        # Only fake the vendor CLI invocation (argv[0] is a binary path,
        # cwd=None per the vendor call's own convention); let every git
        # subprocess.run (which passes cwd=repo_dir explicitly) hit the
        # real binary so _git_porcelain_snapshot exercises real git.
        if kwargs.get("cwd") is None and "input" in kwargs:
            if side_effect_writes_file:
                (Path(repo_dir) / "written_by_vendor.txt").write_text("surprise\n")
            return _FakeCompletedProcess()
        return real_subprocess_run(argv, **kwargs)

    executor = vd.VendorCLIExecutor("devin", "do a thing", mode=mode)
    import os
    old_cwd = os.getcwd()
    os.chdir(repo_dir)
    try:
        with patch("subprocess.run", side_effect=fake_run), \
             patch("shutil.which", return_value="/usr/bin/devin"):
            return executor.run()
    finally:
        os.chdir(old_cwd)


def test_read_mode_clean_tree_stays_ok(git_repo):
    """POSITIVE: mode='read', nothing written -> normal status, unaffected."""
    result = _run_executor(git_repo, mode="read", side_effect_writes_file=False)
    assert result.status != "read_mode_wrote_files", (
        "clean read-mode dispatch was incorrectly flagged as having written files"
    )


def test_read_mode_that_writes_a_file_is_caught(git_repo):
    """THE ACTUAL RISK CASE: mode='read' but the vendor writes a file anyway
    -- must be caught, not silently 'ok'."""
    result = _run_executor(git_repo, mode="read", side_effect_writes_file=True)
    assert result.status == "read_mode_wrote_files", (
        f"a read-mode dispatch mutated the working tree but status was "
        f"{result.status!r}, not 'read_mode_wrote_files' -- the automatic "
        f"backstop did not catch it"
    )


def test_write_mode_same_file_write_is_not_flagged(git_repo):
    """OPPOSED: the identical file-write side effect under mode='write' must
    NOT trigger this status -- the check is read-mode-only by design."""
    result = _run_executor(git_repo, mode="write", side_effect_writes_file=True)
    assert result.status != "read_mode_wrote_files", (
        "write-mode dispatch was flagged by the read-mode-only write detector"
    )


def test_write_mode_behavior_completely_unchanged(git_repo):
    """Confirm this fix touches read-mode only: write mode with no side
    effect gets the same status it always would (not read_mode_wrote_files,
    not some other new state)."""
    result = _run_executor(git_repo, mode="write", side_effect_writes_file=False)
    assert result.status == "ok"


def test_git_porcelain_snapshot_fails_open_outside_a_repo():
    """OPPOSED: _git_porcelain_snapshot itself must return None (not "" and
    not raise) when cwd is not a git repo -- "" would read as "confirmed
    clean" for a directory we simply couldn't check."""
    with tempfile.TemporaryDirectory() as not_a_repo:
        result = vd._git_porcelain_snapshot(cwd=not_a_repo)
        assert result is None, (
            f"expected None (cannot verify) for a non-git directory, got {result!r} "
            "-- an empty string here would falsely read as a confirmed-clean repo"
        )
