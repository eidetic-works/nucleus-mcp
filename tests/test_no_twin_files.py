"""Catch literal copies between repos — the duplication that actually happened.

The split found the same file living in two repos at different lengths:
`providers/brain_rag.py` at 1,926 lines in one and 3,921 in the other,
`brain_telegram.py` 453 lines apart. Each copy began as an exact duplicate made
because the original was somewhere the author could not reach from where they
stood. Byte-identical detection is the point where that is still cheap to undo.

Only byte-identical. Eight attempts at fuzzy duplicate-detection on this corpus
topped out at 11.1% recall with 90% precision (two hold-outs, lexical and
embedding retrieval, three judge configurations) — the measurements are in the
plan file. This test does not resurrect any of them.

It SKIPS when no sibling repo is configured, and that is deliberate: a default
test that reads another repo's working tree makes one session's mid-rebase fail
an unrelated session's suite. Configure siblings explicitly with
NUCLEUS_SIBLING_REPOS to turn it on.

It compares COMMITTED content (git blob ids at a named ref), never the files on
disk. The first version walked the filesystem and reported 714 twins against a
sibling whose default branch contains none of them — the checkout simply sat on
a branch predating the split. A cross-repo check that depends on which branch
someone else has open is not a check.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import sibling_repos

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build",
             ".pytest_cache", ".ruff_cache", ".mypy_cache", "site-packages", "archive",
             ".brain", ".brain.backup"}
# Files that are meant to be identical everywhere.
UNIVERSAL = {"__init__.py", "LICENSE", ".gitignore", "py.typed", "conftest.py",
             "secret-scan", "pre-commit", "install_hooks.sh", "requirements.txt"}
MIN_BYTES = 200   # below this, identical content is coincidence, not a copy


def _digest(p: Path) -> str | None:
    try:
        data = p.read_bytes()
    except OSError:
        return None
    if len(data) < MIN_BYTES:
        return None
    return hashlib.sha256(data).hexdigest()


def _git_blob_index(root: Path, ref: str) -> dict[str, str]:
    """{path: blob_id} for a committed tree — independent of the checked-out branch.

    Keyed by PATH, not by blob id. Keying by blob id answers "does this content
    exist anywhere in the other repo", which is a different question and a much
    looser one: identical boilerplate at unrelated paths scores as a twin, and so
    does any file that merely moved. Two sessions measuring this way reported 72
    and 116 twins for a set that is 43 when the question is asked correctly.
    """
    import subprocess

    r = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "-z", ref],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    out: dict[str, str] = {}
    for entry in r.stdout.split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) < 3 or parts[1] != "blob":
            continue
        name = Path(path).name
        if name in UNIVERSAL or any(part in SKIP_DIRS for part in Path(path).parts):
            continue
        if Path(path).suffix not in {".py", ".sh", ".md", ".toml", ".json", ".yml", ".yaml"}:
            continue
        out[path] = parts[2]
    return out


def _default_ref(root: Path) -> str:
    import subprocess

    for ref in ("main", "master", "HEAD"):
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "-q", ref],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return ref
    return "HEAD"


def _index(root: Path) -> dict[str, str]:
    """{relative path: content digest} — same reason as _git_blob_index above."""
    out: dict[str, str] = {}
    for p in root.rglob("*"):
        if not p.is_file() or p.name in UNIVERSAL:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix not in {".py", ".sh", ".md", ".toml", ".json", ".yml", ".yaml"}:
            continue
        d = _digest(p)
        if d:
            out[str(p.relative_to(root))] = d
    return out


def configured_siblings() -> list[Path]:
    roots = [r for r in sibling_repos.search_roots() if r != sibling_repos.PROJECT_ROOT]
    return [r for r in roots if r.is_dir() and r.resolve() != REPO_ROOT.resolve()]


def find_twins(root: Path, siblings: list[Path]) -> list[tuple[Path, Path]]:
    """Filesystem comparison — used by the fixture tests, which build plain dirs."""
    ours = _index(root)
    twins: list[tuple[Path, Path]] = []
    for sib in siblings:
        theirs = _index(sib)
        for rel in sorted(set(ours) & set(theirs)):
            if ours[rel] == theirs[rel]:
                twins.append((root / rel, sib / rel))
    return twins


def find_committed_twins(root: Path, siblings: list[Path]) -> list[tuple[str, str, Path]]:
    """Committed-content comparison — what the real cross-repo check uses."""
    ours = _git_blob_index(root, _default_ref(root))
    found: list[tuple[str, str, Path]] = []
    for sib in siblings:
        theirs = _git_blob_index(sib, _default_ref(sib))
        for path in sorted(set(ours) & set(theirs)):
            if ours[path] == theirs[path]:
                found.append((path, path, sib))
    return found


def test_finds_a_planted_twin(tmp_path):
    """The control: two identical files in two trees must be reported."""
    a, b = tmp_path / "a", tmp_path / "b"
    (a / "pkg").mkdir(parents=True)
    (b / "pkg").mkdir(parents=True)
    body = "# a real module\n" + "x = 1\n" * 40
    (a / "pkg" / "dup.py").write_text(body)
    (b / "pkg" / "dup.py").write_text(body)
    (a / "pkg" / "only_here.py").write_text("# unique\n" + "y = 2\n" * 40)

    twins = find_twins(a, [b])
    assert len(twins) == 1, f"expected exactly the planted twin, got {twins}"
    assert twins[0][0].name == "dup.py"


def test_near_identical_files_are_not_reported(tmp_path):
    """Byte-identical only: one changed character must not count as a copy."""
    a, b = tmp_path / "a", tmp_path / "b"
    (a / "pkg").mkdir(parents=True)
    (b / "pkg").mkdir(parents=True)
    body = "# a real module\n" + "x = 1\n" * 40
    (a / "pkg" / "dup.py").write_text(body)
    (b / "pkg" / "dup.py").write_text(body + "# diverged\n")
    assert find_twins(a, [b]) == []


def test_tiny_files_are_not_reported(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    (a / "pkg").mkdir(parents=True)
    (b / "pkg").mkdir(parents=True)
    (a / "pkg" / "t.py").write_text("x = 1\n")
    (b / "pkg" / "t.py").write_text("x = 1\n")
    assert find_twins(a, [b]) == [], "a one-line match is coincidence, not a copy"


def test_same_content_at_a_different_path_is_not_a_twin(tmp_path):
    """The planted failure for the defect this test itself carried.

    A twin is the same file in two repos. Identical content at an unrelated path
    is either shared boilerplate or a file that moved — neither is a copy anyone
    has to keep in sync, and counting them is how a 43-file set was reported as
    72 and as 116 in the same week.
    """
    a, b = tmp_path / "a", tmp_path / "b"
    (a / "pkg").mkdir(parents=True)
    (b / "other").mkdir(parents=True)
    body = "# a real module\n" + "x = 1\n" * 40
    (a / "pkg" / "here.py").write_text(body)
    (b / "other" / "moved.py").write_text(body)
    assert find_twins(a, [b]) == [], (
        "identical content at a different path is not a twin; matching on content "
        "alone is the measurement defect this test exists to not repeat"
    )


# Duplication that is expected and not a copy-in-waiting: each repo needs its own
# CI definitions and its own well-known files; there is no shared-action setup to
# point them at, and a change to one is not supposed to reach the other.
ACCEPTED_PREFIXES = (".github/", ".well-known/", ".pre-commit-config.yaml")


@pytest.mark.skipif(
    not os.environ.get("NUCLEUS_SIBLING_REPOS") and not configured_siblings(),
    reason="no sibling repo configured; set NUCLEUS_SIBLING_REPOS to enable "
           "(a default test must not read another repo's working tree)",
)
def test_no_byte_identical_twins_with_configured_siblings():
    siblings = configured_siblings()
    known_file = PKG_ROOT / ".known-twins.txt"
    known = set()
    if known_file.exists():
        known = {ln.strip() for ln in known_file.read_text().splitlines()
                 if ln.strip() and not ln.startswith("#")}
    twins = [t for t in find_committed_twins(REPO_ROOT, siblings)
             if not t[0].startswith(ACCEPTED_PREFIXES) and t[0] not in known]
    assert not twins, (
        "NEW byte-identical copies across repos (not in .known-twins.txt) — the shape "
        "brain_rag.py at 1,926 vs 3,921 lines:\n"
        + "\n".join(f"  {ours}\n    == {sib.name}:{theirs}" for ours, theirs, sib in twins[:15])
    )
