"""A dispatch may only commit inside its own declared scope.

Why this exists: on 2026-08-19 a sweep task committed a hand-written test file
under the name `sweep_docs_archive_md` -- a commit titled for a doc, containing
zero docs -- while ARCHIVE.md, the file that task actually edited, stayed
uncommitted. Attribution was "every path whose porcelain status changed during
the dispatch window", which is necessary but not sufficient: a concurrent
writer's file changes during that window too. The commit both claimed work it
did not do and missed the work it did.

Each test names its failure direction. The negative controls matter more than
the positive one here: a scope gate that never refuses anything is the bug it
was written to fix.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon


def _repo(tmp: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    for k, v in (("user.email", "t@t.t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp), "config", k, v], check=True)
    (tmp / "docs").mkdir()
    (tmp / "docs" / "TARGET.md").write_text("# Target\noriginal\n")
    (tmp / "docs" / "OTHER.md").write_text("# Other\noriginal\n")
    subprocess.run(["git", "-C", str(tmp), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp), "commit", "-qm", "base"], check=True)
    return tmp


def _daemon(repo: Path, declared_desc: str):
    d = ExecutorDaemon.__new__(ExecutorDaemon)
    d.config = MagicMock()
    d.config.repo_root = repo
    d.config.brain_path = repo / ".brain"
    d.agent_id = "lane_test:1"
    d.vendor = "testvendor"
    ops = MagicMock()
    ops._list_tasks.return_value = [{"id": "t1", "description": declared_desc}]
    d._task_ops = MagicMock(return_value=ops)
    return d


def test_commits_the_file_the_task_declared():
    """POSITIVE: the declared target, edited by the vendor, must be committed."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        d = _daemon(repo, "Audit `docs/TARGET.md` for false claims")
        pre = d._worktree_state()
        (repo / "docs" / "TARGET.md").write_text("# Target\ncorrected\n")
        sha = d._verify_and_commit_worktree("t1", pre)
        assert sha != "unknown", "declared file was not committed"
        files = subprocess.run(
            ["git", "-C", str(repo), "show", "--name-only", "--format=", sha],
            capture_output=True, text=True).stdout.split()
        assert files == ["docs/TARGET.md"], files


def test_a_concurrent_writers_file_is_never_claimed():
    """OPPOSED — the actual bug. Another writer edits an undeclared file inside
    the dispatch window. It must stay uncommitted and must not enter this
    task's commit."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        d = _daemon(repo, "Audit `docs/TARGET.md` for false claims")
        pre = d._worktree_state()
        (repo / "docs" / "TARGET.md").write_text("# Target\ncorrected\n")
        (repo / "docs" / "OTHER.md").write_text("# Other\nsomeone else\n")  # concurrent
        sha = d._verify_and_commit_worktree("t1", pre)
        files = subprocess.run(
            ["git", "-C", str(repo), "show", "--name-only", "--format=", sha],
            capture_output=True, text=True).stdout.split()
        assert "docs/OTHER.md" not in files, f"claimed a foreign writer's file: {files}"
        assert "docs/TARGET.md" in files
        porcelain = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True).stdout
        assert "docs/OTHER.md" in porcelain, "foreign work was swept in, not left alone"


def test_editing_only_an_undeclared_file_commits_nothing():
    """OPPOSED: the exact shape of the real defect -- the vendor's declared file
    is untouched and something else changed. That is not this task's output, so
    it must return 'unknown' and fail verification rather than commit."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        d = _daemon(repo, "Audit `docs/TARGET.md` for false claims")
        pre = d._worktree_state()
        (repo / "docs" / "OTHER.md").write_text("# Other\nunrelated\n")
        assert d._verify_and_commit_worktree("t1", pre) == "unknown"
        log = subprocess.run(["git", "-C", str(repo), "log", "--oneline"],
                             capture_output=True, text=True).stdout.strip().splitlines()
        assert len(log) == 1, f"committed something despite no in-scope change: {log}"


def test_a_task_declaring_nothing_commits_nothing():
    """OPPOSED: with no declared scope there is no attributable set. Falling
    back to 'everything that changed' is precisely the wide behaviour that
    caused the bug, so absence of scope must refuse, not widen."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        d = _daemon(repo, "Do some work with no path named at all")
        pre = d._worktree_state()
        (repo / "docs" / "TARGET.md").write_text("# Target\nchanged\n")
        assert d._verify_and_commit_worktree("t1", pre) == "unknown"


def test_declared_paths_ignores_backticked_nonfiles():
    """OPPOSED: descriptions are full of backticked non-paths (`grep`, flags).
    Treating those as scope would silently re-widen the gate."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        d = _daemon(repo, "Use `grep` and `--exclude-preset` on `docs/TARGET.md`")
        assert d._declared_paths("t1") == ["docs/TARGET.md"]


def test_pause_records_a_reason():
    """A pause that carries no reason is an unreadable failure: the ledger said
    retry_count=2, pause_reason=None."""
    d = ExecutorDaemon.__new__(ExecutorDaemon)
    d.config = MagicMock()
    d.agent_id = "lane_test:1"
    d.lane_name = "lane_test"
    d.vendor = "testvendor"
    ops = MagicMock()
    d._task_ops = MagicMock(return_value=ops)
    d._relay = MagicMock()
    d._pause_and_ask("t1", 2, RuntimeError("verification returned no commit SHA"))
    payload = ops._update_task.call_args[0][1]
    assert payload["status"] == "PAUSED"
    assert payload.get("pause_reason"), "pause_reason left unset -- the original bug"
    assert "no commit SHA" in payload["pause_reason"]
    # This asserts the CALL only. It passed while pause_reason still read None
    # on every real task, because _update_task filtered the field away against
    # its valid_keys allowlist and reported success. Persistence is asserted
    # against real storage in test_task_ops_update_field_persistence.py; that
    # is the test that can actually fail if the field stops being stored.


def test_a_declared_output_path_that_does_not_exist_yet_is_in_scope():
    """An audit task must be able to WRITE its report.

    The dead-instrument template asks the vendor to write findings to
    docs/audits/<name>.md. That file does not exist when the task starts, so a
    scope gate keyed on "is this an existing file?" refused the task's own
    output as foreign work and left the report uncommitted. A reporting task
    whose report cannot be committed has no success state at all.
    """
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        (repo / "docs" / "audits").mkdir(parents=True)
        d = _daemon(repo, "Audit `docs/TARGET.md`; write findings to "
                          "`docs/audits/dead_instrument_target.md`")
        declared = d._declared_paths("t1")
        assert "docs/audits/dead_instrument_target.md" in declared, (
            "the task's declared output path was not in scope, so its report "
            "could never be committed"
        )


def test_a_declared_output_in_a_MISSING_directory_is_refused():
    """OPPOSED: the parent must already exist. Otherwise 'declare any path you
    like' is back, and a vendor could write outside the repo's known layout."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        d = _daemon(repo, "Audit `docs/TARGET.md`; write to `no/such/dir/out.md`")
        assert "no/such/dir/out.md" not in d._declared_paths("t1")


def test_a_bare_word_with_no_directory_is_still_not_a_path():
    """OPPOSED, and the one that caught the first version of this widening:
    `grep` has parent '.', which IS a directory, so parent-exists ALONE turned
    every backticked prose token into declared scope."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        d = _daemon(repo, "Use `grep` and `--flag` on `docs/TARGET.md`")
        assert d._declared_paths("t1") == ["docs/TARGET.md"]
