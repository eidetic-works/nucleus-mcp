"""Account for every file `git archive` drops, so the count means something.

`validate_public_surface.sh` printed `Archive: N files` and compared N to
nothing. The number was decoration: it could not distinguish "export-ignore
worked as intended" from "the archive silently lost a third of the tree". During
the 2026-09-17 split, `git archive` dropped 12 of 363 files with no error and no
exit code, because six directories carried `export-ignore`.

The naive oracle is worse than none. Asking `git check-attr export-ignore` for
each dropped path leaves 788 of 1,053 "unexplained" — a 75% false-positive rate,
because `.gitattributes` writes directory rules with a trailing slash
(`assets/ export-ignore`) and check-attr does not report those for descendants.
Querying each ancestor BOTH ways (`assets` and `assets/`) reduces unexplained to
exactly the submodule gitlinks, which `git archive` legitimately omits.

Measured on this repo at the time of writing: 1701 tracked, 648 archived,
1053 dropped, 0 unexplained.
"""

from __future__ import annotations

import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ArchiveReport:
    tracked: set[str] = field(default_factory=set)
    archived: set[str] = field(default_factory=set)
    dropped: set[str] = field(default_factory=set)
    explained: set[str] = field(default_factory=set)
    gitlinks: set[str] = field(default_factory=set)
    unexplained: set[str] = field(default_factory=set)

    def summary(self) -> str:
        return (
            f"tracked={len(self.tracked)} archived={len(self.archived)} "
            f"dropped={len(self.dropped)} explained={len(self.explained)} "
            f"gitlinks={len(self.gitlinks)} unexplained={len(self.unexplained)}"
        )


def _git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()[:200]}")
    return r.stdout


def tracked_files(root: Path) -> set[str]:
    return {p for p in _git(root, "ls-files", "-z").split("\0") if p}


def gitlink_paths(root: Path) -> set[str]:
    """Submodules: git archive omits them by design, not by rule."""
    out = _git(root, "ls-files", "-s")
    return {line.split("\t", 1)[1] for line in out.splitlines() if line.startswith("160000")}


def archived_files(root: Path, ref: str = "HEAD") -> set[str]:
    with tempfile.TemporaryDirectory() as td:
        tar = Path(td) / "a.tar"
        with open(tar, "wb") as fh:
            r = subprocess.run(["git", "-C", str(root), "archive", ref],
                               stdout=fh, stderr=subprocess.PIPE)
        if r.returncode != 0:
            raise RuntimeError(f"git archive failed: {r.stderr.decode()[:200]}")
        with tarfile.open(tar) as t:
            return {m.name for m in t.getmembers() if m.isfile()}


def _ancestors_both_ways(path: str) -> list[str]:
    """`assets/x/y.py` -> assets, assets/, assets/x, assets/x/, assets/x/y.py

    Both spellings matter: a directory rule written `assets/ export-ignore` is
    not reported by check-attr for `assets`, and vice versa. Querying one form
    only is what produced the 788 false positives.
    """
    parts = path.split("/")
    out: list[str] = []
    for i in range(1, len(parts)):
        d = "/".join(parts[:i])
        out.extend([d, d + "/"])
    out.append(path)
    return out


def explained_by_export_ignore(root: Path, dropped: set[str]) -> set[str]:
    queries: list[str] = []
    owner: dict[str, str] = {}
    for p in dropped:
        for q in _ancestors_both_ways(p):
            queries.append(q)
            owner.setdefault(q, p)
    if not queries:
        return set()
    r = subprocess.run(
        ["git", "-C", str(root), "check-attr", "--stdin", "-z", "export-ignore"],
        input="\0".join(queries) + "\0", capture_output=True, text=True,
    )
    explained: set[str] = set()
    fields = r.stdout.split("\0")
    for i in range(0, len(fields) - 2, 3):
        path, _attr, value = fields[i], fields[i + 1], fields[i + 2]
        if value == "set":
            for p in dropped:
                if p == path or p.startswith(path.rstrip("/") + "/"):
                    explained.add(p)
    return explained


def explained_drops(root: Path, ref: str = "HEAD") -> ArchiveReport:
    rep = ArchiveReport()
    rep.tracked = tracked_files(root)
    rep.archived = archived_files(root, ref)
    rep.dropped = rep.tracked - rep.archived
    rep.gitlinks = gitlink_paths(root) & rep.dropped
    rep.explained = explained_by_export_ignore(root, rep.dropped - rep.gitlinks)
    rep.unexplained = rep.dropped - rep.gitlinks - rep.explained
    return rep


def main() -> int:
    import sys

    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    rep = explained_drops(root)
    print(rep.summary())
    if rep.unexplained:
        print(f"UNEXPLAINED ({len(rep.unexplained)}) — files git archive dropped for no stated rule:")
        for p in sorted(rep.unexplained)[:20]:
            print(f"  {p}")
        return 1
    print("every dropped file is explained by an export-ignore rule or is a submodule")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
