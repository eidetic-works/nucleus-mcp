"""The executor must commit on the vendor's behalf, because the vendor cannot.

THE CONTRADICTION (found 2026-08-19 on the first real sweep): the vendor
dispatch preamble's non-negotiable #2 forbids `git commit` — correctly, because
"This working tree is shared with other agents running concurrently; their
uncommitted work is in it right now." But the lane's _verify_diff_content()
required a commit SHA and diffed {sha}~1..{sha}. So an OBEDIENT vendor always
failed with "no commit SHA", retried twice, and paused.

Two subsystems built on opposite assumptions. Every LLM task in a shared tree
failed structurally regardless of work quality — two tasks produced correct,
careful doc corrections and both were rejected.

Resolution: vendor edits, executor commits, serialized by a repo lock. The lane
package previously had NO git serialization anywhere, so two concurrent
executors could interleave add/commit and one lane's commit could swallow
another's staged work.

Each test names its failure direction.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon
from mcp_server_nucleus.runtime.lane.config import LaneConfig


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a],
                          capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture()
def repo_daemon():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "t@t.com")
        _git(repo, "config", "user.name", "t")
        (repo / "seed.md").write_text("seed\n")
        _git(repo, "add", "seed.md")
        _git(repo, "commit", "-q", "-m", "seed")
        cfg = LaneConfig(repo_root=repo, brain_path=repo / ".brain",
                         spec_path=repo / "SPEC.md")
        d = ExecutorDaemon(config=cfg, agent_id="lane_devin",
                           lane="lane_devin", vendor="devin")

        # A dispatch may only commit inside its declared scope, so these tests
        # must declare one. Registering it here rather than stubbing
        # _declared_paths keeps the scope gate itself under test.
        registry = {}

        def declare(task_id, *paths):
            registry[task_id] = {
                "id": task_id,
                "description": "Audit " + " ".join(f"`{x}`" for x in paths),
            }

        class _Ops:
            @staticmethod
            def _list_tasks():
                return list(registry.values())

        d._task_ops = lambda: _Ops()
        d.declare = declare
        yield repo, d


def test_vendor_edit_gets_committed_by_executor(repo_daemon):
    """THE FIX: a vendor that edits but (correctly) does not commit must still
    reach a real commit SHA."""
    repo, d = repo_daemon
    d.declare("task_x", "doc.md")
    pre = d._worktree_state()
    (repo / "doc.md").write_text("line1\nline2\nline3\nline4\nline5\nline6\n")
    sha = d._verify_and_commit_worktree("task_x", pre)
    assert sha != "unknown", "executor failed to commit the vendor's edit"
    assert len(sha) == 40
    # .brain/ is created by the daemon itself and is present in BOTH snapshots,
    # so it is correctly excluded from the commit. Assert on the vendor's file.
    assert "doc.md" not in d._worktree_state(), "doc.md should be committed, not dirty"


def test_committed_diff_passes_verification(repo_daemon):
    """END TO END: the commit the executor makes must satisfy the SAME
    verification that was rejecting everything before."""
    repo, d = repo_daemon
    d.declare("task_x", "doc.md")
    pre = d._worktree_state()
    (repo / "doc.md").write_text("\n".join(f"real content line {i}" for i in range(12)) + "\n")
    sha = d._verify_and_commit_worktree("task_x", pre)
    check = d._verify_diff_content(sha)
    assert check["pass"], f"verification still fails after commit: {check}"
    assert check["real_lines"] >= 5


def test_no_changes_yields_unknown_not_a_fake_pass(repo_daemon):
    """OPPOSED, load-bearing: a vendor that changed NOTHING must NOT get a
    commit. Returning a SHA here would manufacture a pass for work that never
    happened — the exact fabricated-success shape this repo exists to catch."""
    repo, d = repo_daemon
    pre = d._worktree_state()
    sha = d._verify_and_commit_worktree("task_empty", pre)
    assert sha == "unknown"
    assert d._verify_diff_content(sha)["pass"] is False


def test_only_this_dispatchs_files_are_committed(repo_daemon):
    """OPPOSED: another lane's uncommitted work must NOT be swept into this
    task's commit. This is the precise hazard the dispatch preamble names."""
    repo, d = repo_daemon
    d.declare("task_mine", "mine.md")
    (repo / "other_lane_wip.md").write_text("another agent is mid-edit here\n")
    pre = d._worktree_state()          # snapshot AFTER the foreign edit exists
    (repo / "mine.md").write_text("\n".join(f"my line {i}" for i in range(8)) + "\n")
    sha = d._verify_and_commit_worktree("task_mine", pre)
    assert sha != "unknown"
    files = subprocess.run(["git", "-C", str(repo), "show", "--name-only",
                            "--format=", sha], capture_output=True, text=True).stdout
    assert "mine.md" in files
    assert "other_lane_wip.md" not in files, "swallowed another lane's work"
    assert (repo / "other_lane_wip.md").exists()
    assert "other_lane_wip.md" in d._worktree_state(), "foreign work must stay uncommitted"


def test_trivial_edit_still_fails_verification(repo_daemon):
    """OPPOSED: committing does not bypass the real-content bar. A one-line
    comment must still fail the >=5-real-lines check (crit_verify_bypass)."""
    repo, d = repo_daemon
    d.declare("task_trivial", "doc.py")
    pre = d._worktree_state()
    (repo / "doc.py").write_text("# TODO\n")
    sha = d._verify_and_commit_worktree("task_trivial", pre)
    # No `if sha != "unknown"` guard here on purpose: that made this test pass
    # vacuously whenever the commit did not happen, which is a check that cannot
    # fail. The commit MUST happen, and verification MUST still reject it.
    assert sha != "unknown", "trivial edit was not committed; the bar is untested"
    assert d._verify_diff_content(sha)["pass"] is False, (
        "a trivial comment passed verification — the bypass guard is gone"
    )
