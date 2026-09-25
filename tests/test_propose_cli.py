"""Tests for the `nucleus agent-os propose` CLI verb."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.agent_os.propose_cli import propose
from mcp_server_nucleus.runtime.agent_os.safe_first_pr import SafeTask
from tests.test_safe_first_pr import _commit_all, _init_git_repo


@pytest.fixture
def sign_key(monkeypatch):
    """Provide a stable witness signing key for tests that do not need to
    exercise the scratch-key path."""
    monkeypatch.setenv("NUCLEUS_WITNESS_SIGN_KEY", "test-signing-key")


def _git_output(argv, cwd, check=True):
    result = subprocess.run(
        ["git", *argv],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )
    return result.stdout


def test_no_tasks_returns_zero(sign_key, tmp_path, capsys):
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# init\n")
    _commit_all(tmp_path)

    rc = propose(str(tmp_path), apply=False)
    out = capsys.readouterr().out

    assert rc == 0
    assert "no safe tasks found" in out


def test_default_dry_run_does_not_write(sign_key, tmp_path, capsys):
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "intro.md").write_text(
        "See [the missing guide](missing.md) for details.\n"
    )
    (tmp_path / "docs" / "exists.md").write_text("# Exists\n")
    _commit_all(tmp_path)

    rc = propose(str(tmp_path), apply=False)
    out = capsys.readouterr().out

    assert rc == 0
    assert "---" in out  # unified-diff header present
    status = _git_output(["status", "--porcelain"], tmp_path)
    assert status == ""
    branches = _git_output(["branch", "--format=%(refname:short)"], tmp_path)
    assert "safe-pr" not in branches


def test_apply_creates_branch_and_commit(sign_key, tmp_path, capsys):
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "intro.md").write_text(
        "See [the missing guide](missing.md) for details.\n"
    )
    (tmp_path / "docs" / "exists.md").write_text("# Exists\n")
    _commit_all(tmp_path)

    rc = propose(str(tmp_path), apply=True)
    out = capsys.readouterr().out
    assert rc == 0, out

    # The file was changed.
    assert "missing.md" not in (tmp_path / "docs" / "intro.md").read_text()

    # A new branch exists and its HEAD is a real commit.
    branches = _git_output(
        ["for-each-ref", "--format=%(refname:short)", "refs/heads"], tmp_path
    )
    branch = next(b for b in branches.splitlines() if b.startswith("safe-pr/"))
    sha = _git_output(["rev-parse", branch], tmp_path).strip()
    assert _git_output(["cat-file", "-t", sha], tmp_path).strip() == "commit"


def test_apply_emits_commit_claim(sign_key, tmp_path, capsys):
    _init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "intro.md").write_text(
        "See [the missing guide](missing.md) for details.\n"
    )
    (tmp_path / "docs" / "exists.md").write_text("# Exists\n")
    _commit_all(tmp_path)

    rc = propose(str(tmp_path), apply=True)
    out = capsys.readouterr().out
    assert rc == 0, out

    branches = _git_output(
        ["for-each-ref", "--format=%(refname:short)", "refs/heads"], tmp_path
    )
    branch = next(b for b in branches.splitlines() if b.startswith("safe-pr/"))
    sha = _git_output(["rev-parse", branch], tmp_path).strip()

    assert "GIT COMMIT EXISTS:" in out
    assert sha in out


def test_scratch_key_notice_printed_when_unset(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("NUCLEUS_WITNESS_SIGN_KEY", raising=False)
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# init\n")
    _commit_all(tmp_path)

    rc = propose(str(tmp_path), apply=False)
    out = capsys.readouterr().out

    assert rc == 0
    assert "minted a scratch key" in out


def test_scratch_key_notice_not_printed_when_set(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("NUCLEUS_WITNESS_SIGN_KEY", "test-signing-key")
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# init\n")
    _commit_all(tmp_path)

    rc = propose(str(tmp_path), apply=False)
    out = capsys.readouterr().out

    assert rc == 0
    assert "minted a scratch key" not in out


def test_unsafe_task_returns_two(sign_key, tmp_path, capsys, monkeypatch):
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# init\n")
    _commit_all(tmp_path)

    from mcp_server_nucleus.runtime.agent_os import propose_cli

    monkeypatch.setattr(
        propose_cli,
        "scan_for_safe_tasks",
        lambda repo: [
            SafeTask(
                path="scripts/x.sh",
                kind="broken_link",
                description="broken link to missing file",
                evidence="see [missing](missing.md)",
            )
        ],
    )

    rc = propose(str(tmp_path), apply=False)
    out = capsys.readouterr().out

    assert rc == 2
    assert "scripts" in out.lower() or "disallowed directory" in out.lower()
