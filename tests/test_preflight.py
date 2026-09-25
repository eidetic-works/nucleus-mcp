"""Every assertion in preflight must fail on the input it exists to catch.

Each test below pairs a passing case with the planted failure taken from a real
incident in this project's transcripts. A module of assertions that has never
been shown to raise is in the same category as the gates it guards.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import preflight as pf


def _repo(tmp_path: Path, branch: str = "main") -> Path:
    subprocess.run(["git", "init", "-q", "-b", branch, str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "f.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "seed"], check=True)
    return tmp_path


# --- assert_branch: the 2,894-passes case ---------------------------------

def test_branch_matches(tmp_path):
    repo = _repo(tmp_path)
    assert pf.assert_branch("main", repo) == "main"


def test_branch_mismatch_raises_naming_both(tmp_path):
    repo = _repo(tmp_path)
    subprocess.run(["git", "-C", str(repo), "checkout", "-qb", "other"], check=True)
    with pytest.raises(pf.PreflightError) as e:
        pf.assert_branch("main", repo)
    assert "other" in str(e.value) and "main" in str(e.value)


def test_detached_head_is_a_failure_not_a_pass(tmp_path):
    repo = _repo(tmp_path)
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", sha], check=True)
    with pytest.raises(pf.PreflightError, match="detached"):
        pf.assert_branch("main", repo)


# --- assert_commit: tb's pinned-dependency case ---------------------------

def test_commit_matches_by_prefix(tmp_path):
    repo = _repo(tmp_path)
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    assert pf.assert_commit(sha[:10], repo) == sha


def test_commit_mismatch_raises(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(pf.PreflightError):
        pf.assert_commit("0" * 12, repo)


def test_empty_pin_is_rejected_rather_than_matching_anything(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(pf.PreflightError, match="too short"):
        pf.assert_commit("", repo)


# --- assert_non_empty: the filter-repo-on-an-empty-repo case --------------

def test_non_empty_passes_with_items():
    assert pf.assert_non_empty("files", ["a", "b"]) == ["a", "b"]


def test_empty_set_is_a_failure():
    with pytest.raises(pf.PreflightError, match="cannot fail"):
        pf.assert_non_empty("files", [])


def test_minimum_is_enforced():
    with pytest.raises(pf.PreflightError):
        pf.assert_non_empty("files", ["only-one"], minimum=2)


# --- assert_count_preserved: the git-archive case -------------------------

def test_count_preserved_passes_when_nothing_is_lost():
    pf.assert_count_preserved("members", ["a", "b", "c"], ["c", "b", "a"])


def test_missing_items_are_named_not_just_counted():
    before = [f"f{i}" for i in range(363)]
    after = before[:351]
    with pytest.raises(pf.PreflightError) as e:
        pf.assert_count_preserved("archive members", before, after)
    msg = str(e.value)
    assert "MISSING 12" in msg
    assert "f351" in msg, "the message must name what went missing, not only how many"


def test_explained_losses_do_not_fail():
    pf.assert_count_preserved("members", ["a", "b"], ["a"], explained=["b"])


def test_unexpected_additions_are_reported():
    with pytest.raises(pf.PreflightError, match="UNEXPECTED"):
        pf.assert_count_preserved("members", ["a"], ["a", "surprise"])


# --- require_can_fail: the meta-control -----------------------------------

def test_control_that_rejects_the_planted_input_passes():
    pf.require_can_fail("rejects-bad", lambda x: x != "planted", "planted")


def test_control_that_cannot_fail_is_itself_a_failure():
    with pytest.raises(pf.PreflightError, match="cannot"):
        pf.require_can_fail("always-green", lambda x: True, "planted")


def test_control_that_raises_counts_as_rejecting():
    def probe(_):
        raise ValueError("rejected")

    pf.require_can_fail("raises", probe, "planted")


# --- assert_repo_root / clean worktree ------------------------------------

def test_repo_root_found_from_a_subdirectory(tmp_path):
    (tmp_path / ".brain").mkdir()
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert pf.assert_repo_root(".brain", deep) == tmp_path.resolve()


def test_repo_root_missing_names_where_it_looked(tmp_path):
    with pytest.raises(pf.PreflightError) as e:
        pf.assert_repo_root(".nonexistent-marker", tmp_path)
    assert str(tmp_path.resolve()) in str(e.value)


def test_dirty_worktree_is_reported(tmp_path):
    repo = _repo(tmp_path)
    (repo / "new.txt").write_text("uncommitted\n")
    with pytest.raises(pf.PreflightError, match="uncommitted"):
        pf.assert_clean_worktree(repo)


def test_clean_worktree_passes(tmp_path):
    pf.assert_clean_worktree(_repo(tmp_path))
