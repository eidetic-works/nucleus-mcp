"""The files this repo's checks READ must themselves be tracked and not ignored.

The gq lane lost its entire baseline to this: `.gitignore` had `/*.txt`, so
`.known-failures.txt` was never tracked. Every green verify run it reported was
honest and meaningless — the file existed in that working tree and would not
exist in a fresh clone, so a contributor would have had no baseline at all.
`git add` printed nothing and `git status` showed nothing, which is why nobody
noticed.

The same rule bit this repo in the other direction the same night:
`.known-divergent.txt` could not be staged at all, under an `*.txt` pattern whose
own comment said "at root".

So this is not about one pattern. Any future ignore rule — a broadened glob, a
new `*.json`, an editor's suggestion — can silently unhook a file that a gate
depends on, and the gate keeps passing. The assertion below is over the SET of
files the checks read, so it catches the rule nobody has written yet.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_ROOT.parent

# Every file some check reads and would silently degrade without.
GOVERNANCE = [
    ".known-failures.txt",                              # root suite baseline
    "mcp-server-nucleus/.known-failures.txt",           # package suite baseline
    "mcp-server-nucleus/.known-twins.txt",              # twin drift
    "mcp-server-nucleus/.known-divergent.txt",          # expected divergence
    "mcp-server-nucleus/.known-external-contacts.txt",  # PII gate allowlist
]


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                          capture_output=True, text=True)


@pytest.mark.skipif(not (REPO_ROOT / ".git").exists()
                    and not (REPO_ROOT / ".git").is_file(),
                    reason="not a git checkout")
@pytest.mark.parametrize("rel", GOVERNANCE)
def test_governance_file_is_tracked(rel):
    """Present in a fresh clone, not merely on this machine."""
    assert _git("ls-files", "--error-unmatch", rel).returncode == 0, (
        f"{rel} is NOT tracked. Whatever reads it degrades silently: the check "
        "still passes, against a file a contributor will not have."
    )


@pytest.mark.skipif(not (REPO_ROOT / ".git").exists()
                    and not (REPO_ROOT / ".git").is_file(),
                    reason="not a git checkout")
@pytest.mark.parametrize("rel", GOVERNANCE)
def test_governance_file_is_not_ignored(rel):
    """Re-addable after deletion.

    Tracked and ignored is a real state: a tracked file keeps its history while
    an ignore rule applies to it, so deleting and recreating it puts it back
    outside version control with no error anywhere.
    """
    r = _git("check-ignore", "-v", "--no-index", rel)
    # check-ignore exits 0 when the path IS ignored; a negation rule (!path)
    # also exits 0, so the rule text decides.
    if r.returncode == 0:
        rule = r.stdout.split("\t")[0] if r.stdout else "?"
        assert ":!" in rule or "!" in rule.rsplit(":", 1)[-1], (
            f"{rel} matches ignore rule [{rule}] — delete it and it cannot be "
            "re-added, and the check that reads it goes quiet"
        )


def test_the_check_would_notice_an_untracked_file(tmp_path):
    """The control: prove the tracked assertion can fail."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "present.txt").write_text("x\n")
    (tmp_path / "absent.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "present.txt"], check=True)

    def tracked(name: str) -> bool:
        return subprocess.run(
            ["git", "-C", str(tmp_path), "ls-files", "--error-unmatch", name],
            capture_output=True).returncode == 0

    assert tracked("present.txt")
    assert not tracked("absent.txt"), (
        "the tracked check must be able to say NO, or its yes means nothing"
    )
