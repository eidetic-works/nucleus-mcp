"""Tests for explain_changes snapshot and claim emission."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List

import pytest

from mcp_server_nucleus.runtime.agent_os.explain_changes import (
    emit_claims,
    load_snapshot,
    save_snapshot,
    snapshot,
    summarize,
    verify_claims,
)
from mcp_server_nucleus.runtime.verifier import (
    Claim,
    RuleReasoner,
    _GIT_BRANCH_EXISTS_RE,
    _GIT_COMMIT_EXISTS_RE,
    _TESTS_PASSED_RE,
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {repo} "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )
    return result


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A scratch git repo with an initial empty commit on the default branch."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test User")
    _git(r, "commit", "--allow-empty", "-m", "initial")
    return r


def test_snapshot_real_repo(repo: Path) -> None:
    (repo / "a.py").write_text("a")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-m", "add a")

    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    snap = snapshot(repo)

    assert snap["head_sha"] == head
    assert snap["tracked"]["a.py"]  # blob SHA is non-empty
    assert "main" in snap["branches"] or "master" in snap["branches"]


def test_adding_file_emits_one_file_exists_claim(repo: Path) -> None:
    before = snapshot(repo)
    (repo / "new_file.py").write_text("new content")
    _git(repo, "add", "new_file.py")
    after = snapshot(repo)

    claims = emit_claims(before, after)
    assert claims == ["FILE EXISTS: new_file.py"]


def test_deleting_file_does_not_emit_file_exists_claim(repo: Path) -> None:
    (repo / "del_me.py").write_text("delete me")
    _git(repo, "add", "del_me.py")
    _git(repo, "commit", "-m", "add del_me")

    before = snapshot(repo)
    _git(repo, "rm", "del_me.py")
    after = snapshot(repo)

    claims = emit_claims(before, after)
    assert not any(c.startswith("FILE EXISTS: del_me.py") for c in claims)


def test_new_commit_emits_commit_exists_claim(repo: Path) -> None:
    before = snapshot(repo)
    _git(repo, "commit", "--allow-empty", "-m", "second")
    sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    after = snapshot(repo)

    claims = emit_claims(before, after)
    expected = f"GIT COMMIT EXISTS: {sha} on branch {branch}"
    assert expected in claims


def test_new_branch_emits_branch_exists_claim(repo: Path) -> None:
    _git(repo, "branch", "feature")
    before = snapshot(repo)
    _git(repo, "checkout", "-b", "release")
    after = snapshot(repo)

    claims = emit_claims(before, after)
    assert "GIT BRANCH EXISTS: release" in claims


def test_identical_snapshots_produce_zero_claims(repo: Path) -> None:
    snap = snapshot(repo)
    assert emit_claims(snap, dict(snap)) == []


def test_run_id_controls_tests_passed_claim(repo: Path) -> None:
    (repo / "x.py").write_text("x")
    _git(repo, "add", "x.py")
    _git(repo, "commit", "-m", "add x")

    before = snapshot(repo)
    (repo / "y.py").write_text("y")
    _git(repo, "add", "y.py")
    _git(repo, "commit", "-m", "add y")
    after = snapshot(repo)

    without = emit_claims(before, after)
    assert not any(c.startswith("TESTS PASSED:") for c in without)

    with_run = emit_claims(before, after, run_id="run-abc")
    assert "TESTS PASSED: run-abc" in with_run


def test_save_and_load_snapshot_roundtrip(repo: Path, tmp_path: Path) -> None:
    snap = snapshot(repo)
    path = tmp_path / "snap.json"
    save_snapshot(snap, path)
    loaded = load_snapshot(path)
    assert loaded == snap


def test_every_claim_matches_verifier_regexes(repo: Path) -> None:
    before = snapshot(repo)

    (repo / "widget.py").write_text("widget")
    _git(repo, "add", "widget.py")
    _git(repo, "commit", "-m", "add widget")
    _git(repo, "branch", "feature")

    after = snapshot(repo)
    claims = emit_claims(before, after, run_id="run-xyz")

    assert claims
    for claim in claims:
        if claim.startswith("FILE EXISTS:"):
            anchors = RuleReasoner().decompose(Claim("c", "test", "agent", claim))
            assert any(a.kind == "fs" for a in anchors), f"no fs anchor for {claim}"
        elif claim.startswith("GIT BRANCH EXISTS:"):
            assert _GIT_BRANCH_EXISTS_RE.search(claim)
            anchors = RuleReasoner().decompose(Claim("c", "test", "agent", claim))
            assert any(
                a.kind == "git" and a.spec.get("op") == "branch_exists"
                for a in anchors
            )
        elif claim.startswith("GIT COMMIT EXISTS:"):
            assert _GIT_COMMIT_EXISTS_RE.search(claim)
            anchors = RuleReasoner().decompose(Claim("c", "test", "agent", claim))
            assert any(
                a.kind == "git" and a.spec.get("op") == "commit_exists"
                for a in anchors
            )
        elif claim.startswith("TESTS PASSED:"):
            assert _TESTS_PASSED_RE.search(claim)
            anchors = RuleReasoner().decompose(Claim("c", "test", "agent", claim))
            assert any(
                a.kind == "tests_passed" for a in anchors
            )
        else:
            pytest.fail(f"unexpected claim shape: {claim}")


def test_unanchorable_path_is_reported_not_claimed(repo: Path) -> None:
    """A FILE EXISTS claim that cannot round-trip to its own path is not claimed.

    Emitting one produces a sentence that looks verified in a summary and is in
    fact answered about a DIFFERENT path. It must not be claimed -- and must not
    vanish either, or the summary silently implies it covered the whole diff.

    The example is a filename containing a space: the FILE EXISTS regex takes the
    first whitespace-delimited token, so "FILE EXISTS: a b.py" anchors ``a``.
    That is worse than unanchored -- it REFUTES confidently while the real file
    sits on disk.

    (Extensionless paths like Makefile used to be the example here. They now
    anchor correctly and ARE claimed; see the opposed test below.)
    """
    before = snapshot(repo)
    (repo / "a b.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "real.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "add both")
    after = snapshot(repo)

    residue: list[str] = []
    claims = emit_claims(before, after, unanchorable=residue)

    assert "FILE EXISTS: real.py" in claims
    assert not any("a b.py" in c for c in claims), "truncating path was claimed"
    assert "a b.py" in residue, "truncating path vanished instead of being reported"


def test_unanchorable_claim_would_indeed_not_anchor(repo: Path) -> None:
    """OPPOSED: proves the skip above is protecting against something real.

    The skip is not "no fs anchor is produced" -- one IS produced for "a b.py".
    It is that the anchor answers about the WRONG path. This test pins that
    distinction, because an allowlist that merely asked "did we get an anchor?"
    would wave the truncating case straight through.

    If the FILE EXISTS regex ever learns to handle whitespace in paths, this
    test fails and the skip should be removed rather than left as dead caution.
    """
    from mcp_server_nucleus.runtime import verifier as V

    r = V.RuleReasoner()

    def fs_paths(claim_text: str) -> list:
        return [
            (a.spec or {}).get("path")
            for a in r.decompose(V.Claim("c", "p", "a", claim_text))
            if a.kind == "fs"
        ]

    assert fs_paths("FILE EXISTS: real.py") == ["real.py"], "expected .py to round-trip"
    # Extensionless paths now anchor correctly -- the old skip was too narrow.
    assert fs_paths("FILE EXISTS: Makefile") == ["Makefile"], "Makefile should round-trip"
    # The real hazard: an anchor IS produced, for a path we never asked about.
    truncated = fs_paths("FILE EXISTS: a b.py")
    assert truncated and truncated != ["a b.py"], "space-path no longer truncates"
    assert truncated == ["a"], f"expected truncation to 'a', got {truncated}"


# ── E3: verify_claims ──────────────────────────────────────────────

def test_verify_claims_confirms_real_added_py_file(repo: Path) -> None:
    """A real, tracked .py file should be CONFIRMED by the verifier."""
    before = snapshot(repo)
    (repo / "new_file.py").write_text("new content")
    _git(repo, "add", "new_file.py")
    after = snapshot(repo)

    claims = emit_claims(before, after)
    verified = verify_claims(claims, repo_root=repo)

    assert any("new_file.py" in c for c in verified["confirmed"])
    assert not any("new_file.py" in c for c in verified["refuted"])
    assert not any("new_file.py" in c for c in verified["unverifiable"])


def test_verify_claims_refutes_or_unverifies_missing_file(repo: Path) -> None:
    """A non-existent file must NOT be CONFIRMED."""
    claims = ["FILE EXISTS: does_not_exist_anywhere.py"]
    verified = verify_claims(claims, repo_root=repo)

    assert not any("does_not_exist_anywhere.py" in c for c in verified["confirmed"])
    assert len(verified["refuted"]) + len(verified["unverifiable"]) == 1


# ── E4: summarize ──────────────────────────────────────────────────

def test_summarize_contains_confirmed_filename(repo: Path) -> None:
    """The summary should name the confirmed change."""
    before = snapshot(repo)
    (repo / "confirmed.py").write_text("x")
    _git(repo, "add", "confirmed.py")
    after = snapshot(repo)

    claims = emit_claims(before, after)
    verified = verify_claims(claims, repo_root=repo)
    summary = summarize(verified)

    assert "confirmed.py" in summary


def test_summarize_does_not_state_refuted_filename_as_fact(repo: Path) -> None:
    """A refuted claim's filename should not appear as a stated fact."""
    before = snapshot(repo)
    (repo / "real.py").write_text("x")
    _git(repo, "add", "real.py")
    after = snapshot(repo)

    claims = emit_claims(before, after) + ["FILE EXISTS: does_not_exist_anywhere.py"]
    verified = verify_claims(claims, repo_root=repo)
    summary = summarize(verified)

    assert "does_not_exist_anywhere.py" not in summary


def test_summarize_surfaces_refuted_count(repo: Path) -> None:
    """With one confirmed and one refuted, the summary must still surface
    that something was not verified — never silently omit it."""
    before = snapshot(repo)
    (repo / "confirmed.py").write_text("x")
    _git(repo, "add", "confirmed.py")
    after = snapshot(repo)

    claims = emit_claims(before, after) + ["FILE EXISTS: missing.py"]
    verified = verify_claims(claims, repo_root=repo)
    summary = summarize(verified)

    assert "not verified" in summary
    assert "1" in summary


def test_summarize_empty_confirmed_is_plain(repo: Path) -> None:
    """If nothing was confirmed, the summary must say so plainly."""
    claims = ["FILE EXISTS: missing.py"]
    verified = verify_claims(claims, repo_root=repo)
    summary = summarize(verified)

    assert "Nothing was confirmed as changed" in summary or "No changes were" in summary
    assert "success" not in summary.lower()


def test_summarize_includes_unanchorable_paths(repo: Path) -> None:
    """Unanchorable paths must appear in the summary as also-changed."""
    before = snapshot(repo)
    (repo / "real.py").write_text("x = 1")
    _git(repo, "add", "real.py")
    after = snapshot(repo)

    claims = emit_claims(before, after)
    verified = verify_claims(claims, repo_root=repo)
    summary = summarize(verified, unanchorable=["Makefile"])

    assert "Makefile" in summary


def test_modified_file_is_reported_not_silently_dropped(repo: Path) -> None:
    """A commit that only MODIFIES files must not summarise as "no changes".

    Found by running this module on its own commit: two files changed, zero
    claims emitted, and the summary read "Nothing was confirmed as changed. No
    changes were found to verify." -- a confident report of nothing, identical
    to what a genuinely clean diff produces. Modified files cannot be CLAIMED
    (FILE EXISTS proves existence, not change) but they must be REPORTED.
    """
    (repo / "mod_me.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "add")
    before = snapshot(repo)

    (repo / "mod_me.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "modify")
    after = snapshot(repo)

    modified: list[str] = []
    claims = emit_claims(before, after, modified=modified)

    assert "mod_me.py" in modified, "a modified file vanished from the diff"
    assert not any("FILE EXISTS: mod_me.py" in c for c in claims), (
        "a modified file was claimed as FILE EXISTS -- that anchors to "
        "existence, which was never in question"
    )

    summary = summarize(verify_claims(claims, repo_root=repo), modified=modified)
    assert "mod_me.py" in summary, "modification absent from the summary"
    assert "No changes were found" not in summary, (
        "summary claims no changes while a file was modified"
    )
