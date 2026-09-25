"""_tracked() must distinguish "not tracked" from "could not check".

Both used to return False, so a git timeout or a missing git binary was
reported as "the vendor cited a file git does not track" -- an accusation
manufactured out of our own tooling failing. The verdict is INSUFFICIENT in
both cases, but the refusal log is read by humans deciding whether a vendor did
its job, and a wrong reason there costs a correct vendor its result.

Measured git return codes: 0 = tracked, 1 = genuinely untracked, 128 = git
could not answer. The third state is real and observable, not theoretical.
"""

import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.lane import verdict as V


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], capture_output=True)
    (tmp_path / "tracked.py").write_text("x = 1\n")
    (tmp_path / "untracked.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tracked.py"], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init"], capture_output=True)
    return tmp_path


def test_tracked_file_is_true(repo):
    assert V._tracked(repo, "tracked.py") is True


def test_untracked_file_is_false_not_none(repo):
    """OPPOSED: a real negative must stay a real negative. If this returned
    None the anti-fabrication control would be dead -- every invented path
    would become 'could not check' and sail through as merely unverifiable."""
    assert V._tracked(repo, "untracked.py") is False


def test_git_unavailable_is_none_not_false(tmp_path):
    """The broken input, written first: git cannot answer (not a repo).
    Before the fix this returned False and read as a fabricated path."""
    assert V._tracked(tmp_path, "anything.py") is None


def test_timeout_is_none_not_false(repo, monkeypatch):
    def _boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=15)

    monkeypatch.setattr(subprocess, "run", _boom)
    assert V._tracked(repo, "tracked.py") is None


def test_judge_reason_does_not_blame_the_vendor_when_git_could_not_answer(tmp_path):
    """End to end: with git unable to answer, the refusal must say the check
    did not run -- not that the paths are untracked."""
    block = (
        "VERDICT: CLEAN\n"
        "TASK_ID: t1\n"
        "CLAIMS_CHECKED: 3\n"
        "- a | TRUE | src/alpha.py | alpha_sym\n"
        "- b | TRUE | src/beta.py | beta_sym\n"
        "- c | TRUE | src/gamma.py | gamma_sym\n"
    )
    j = V.judge_clean(V.parse_verdict(block), tmp_path, has_in_scope_diff=False, task_id="t1")
    assert not j.accepted
    assert "could not determine git tracking" in j.reason, j.reason
    assert "NOT a finding against the vendor" in j.reason, j.reason
