"""The archive oracle must explain every dropped file — and must be able to fail.

`validate_public_surface.sh` used to print `Archive: N files` and compare N to
nothing, so it could not tell "export-ignore did its job" from "a third of the
tree vanished". During the split, `git archive` dropped 12 of 363 files silently.

The obvious fix is wrong: asking `git check-attr` once per dropped path leaves
75% of them unexplained, because directory rules are written with a trailing
slash. These tests pin the behaviour that makes the oracle trustworthy — it
queries each ancestor both ways — and, more importantly, prove it reports a file
that is dropped for no stated reason.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import archive_manifest as am


def _repo(tmp_path: Path, gitattributes: str, files: dict[str, str]) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    (tmp_path / ".gitattributes").write_text(gitattributes)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "seed"], check=True)
    return tmp_path


def test_directory_rule_with_trailing_slash_is_explained(tmp_path):
    """The exact spelling that broke the naive oracle."""
    repo = _repo(
        tmp_path,
        "assets/ export-ignore\n",
        {"keep.py": "x = 1\n", "assets/a.bin": "a\n", "assets/deep/b.bin": "b\n"},
    )
    rep = am.explained_drops(repo)
    assert "assets/a.bin" in rep.dropped
    assert "assets/deep/b.bin" in rep.dropped
    assert rep.unexplained == set(), (
        "a trailing-slash directory rule must explain its descendants; "
        f"unexplained={sorted(rep.unexplained)}"
    )
    assert "keep.py" in rep.archived


def test_directory_rule_without_trailing_slash_is_also_explained(tmp_path):
    repo = _repo(
        tmp_path,
        "assets export-ignore\n",
        {"keep.py": "x = 1\n", "assets/a.bin": "a\n"},
    )
    rep = am.explained_drops(repo)
    assert rep.unexplained == set(), f"unexplained={sorted(rep.unexplained)}"


def test_a_file_dropped_for_no_stated_rule_is_reported(tmp_path):
    """The planted failure: remove the rule that explained a drop.

    Here the drop itself is genuine (the rule is still in the committed tree),
    so instead the oracle is asked about a tree whose .gitattributes no longer
    covers it — which is what a silently-lost file looks like.
    """
    repo = _repo(
        tmp_path,
        "assets/ export-ignore\n",
        {"keep.py": "x = 1\n", "assets/a.bin": "a\n"},
    )
    # Rewrite history's .gitattributes so the rule is gone, while a.bin is still
    # excluded by the ARCHIVE built from the earlier state we stub in below.
    (repo / ".gitattributes").write_text("# no rules\n")
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "drop rules"], check=True)

    real_archived = am.archived_files
    try:
        am.archived_files = lambda root, ref="HEAD": {".gitattributes", "keep.py"}
        rep = am.explained_drops(repo)
    finally:
        am.archived_files = real_archived

    assert "assets/a.bin" in rep.unexplained, (
        "a file missing from the archive with no export-ignore rule must be "
        f"reported; got unexplained={sorted(rep.unexplained)}"
    )


def test_submodules_are_not_counted_as_unexplained(tmp_path):
    repo = _repo(tmp_path, "", {"keep.py": "x = 1\n"})
    rep = am.explained_drops(repo)
    assert rep.unexplained == set()
    assert rep.gitlinks == set(), "no submodules in this fixture"


def test_ancestor_query_covers_both_spellings():
    got = am._ancestors_both_ways("assets/deep/b.bin")
    assert "assets" in got and "assets/" in got
    assert "assets/deep" in got and "assets/deep/" in got
    assert got[-1] == "assets/deep/b.bin"


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / ".git").exists()
    and not (Path(__file__).resolve().parents[2] / ".git").exists(),
    reason="not in a git checkout",
)
def test_this_repo_has_no_unexplained_drops():
    root = Path(__file__).resolve().parents[1]
    rep = am.explained_drops(root)
    assert rep.unexplained == set(), (
        "git archive is dropping files this repo cannot account for:\n  "
        + "\n  ".join(sorted(rep.unexplained)[:20])
    )
