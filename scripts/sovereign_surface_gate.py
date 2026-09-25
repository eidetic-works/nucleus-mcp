#!/usr/bin/env python3
"""Refuse to publish an artifact that carries a withheld module.

For 33 releases `validate_public_surface.sh` declared 21 paths SOVEREIGN and the
wheel shipped eight of them. Neither side was lying: the gate checked the
`git archive` mirror, `.gitattributes export-ignore` governs only that archive,
and hatchling builds from the VCS tree. Two mechanisms, one question, no overlap.

This gate asks the question of the thing that actually reaches a stranger — the
built wheel or sdist — and it reads the SAME list the packaging config excludes
from, `.withheld-modules.txt`, so the two cannot drift apart again.

Exit codes match artifact_identity_gate.py so publish_readiness.sh can treat
them identically:
    0  clean        — no withheld module in the artifact
    2  leaked       — at least one is present; the artifact must not be published
    3  INSUFFICIENT — no list, or the artifact could not be read. Nothing was
                      checked, and that must never read as clean.

    python3 scripts/sovereign_surface_gate.py dist/nucleus_mcp-1.16.9.tar.gz
    python3 scripts/sovereign_surface_gate.py dist/*.whl
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

EXIT_CLEAN, EXIT_LEAKED, EXIT_INSUFFICIENT = 0, 2, 3

LIST_NAME = ".withheld-modules.txt"
SRC_PREFIX = "src/"


def load_withheld(start: Path) -> tuple[list[str], Path | None]:
    """The one list. Absent means INSUFFICIENT, never clean."""
    for base in (start, *start.parents):
        f = base / LIST_NAME
        if f.is_file():
            entries = [ln.strip() for ln in f.read_text().splitlines()
                       if ln.strip() and not ln.startswith("#")]
            return entries, f
    return [], None


def as_package_paths(entry: str) -> list[str]:
    """`src/mcp_server_nucleus/siphon.py` is `mcp_server_nucleus/siphon.py` in a
    wheel and `<name>-<ver>/src/mcp_server_nucleus/siphon.py` in an sdist. Match
    on the suffix so one list covers both without the caller knowing which."""
    rel = entry[len(SRC_PREFIX):] if entry.startswith(SRC_PREFIX) else entry
    return [rel.rstrip("/"), entry.rstrip("/")]


def members(art: Path) -> list[str]:
    if art.suffix in (".whl", ".zip"):
        with zipfile.ZipFile(art) as z:
            return z.namelist()
    if art.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(art) as t:
            return t.getnames()
    raise ValueError(f"not a wheel or sdist: {art.name}")


def leaks(names: list[str], withheld: list[str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for entry in withheld:
        hits = []
        for cand in as_package_paths(entry):
            for n in names:
                # A directory entry matches anything beneath it; a file entry
                # matches the path itself, at any archive prefix depth.
                if n == cand or n.endswith("/" + cand) or f"/{cand}/" in f"/{n}/":
                    hits.append(n)
        if hits:
            found[entry] = sorted(set(hits))
    return found


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if len(argv) != 2:
        print("usage: sovereign_surface_gate.py <artifact.whl|artifact.tar.gz>")
        return EXIT_INSUFFICIENT
    art = Path(argv[1])
    if not art.is_file():
        print(f"INSUFFICIENT: no such artifact: {art}")
        return EXIT_INSUFFICIENT

    withheld, src = load_withheld(Path(__file__).resolve().parent)
    if not withheld:
        print(f"INSUFFICIENT: no {LIST_NAME} found. Nothing was checked, and an "
              "empty list must never read as clean.")
        return EXIT_INSUFFICIENT

    try:
        names = members(art)
    except Exception as e:  # noqa: BLE001 — any read failure means nothing was checked
        print(f"INSUFFICIENT: could not read {art.name}: {e}")
        return EXIT_INSUFFICIENT
    if not names:
        print(f"INSUFFICIENT: {art.name} has no members")
        return EXIT_INSUFFICIENT

    found = leaks(names, withheld)
    if found:
        total = sum(len(v) for v in found.values())
        print(f"LEAKED: {art.name} carries {total} file(s) from {len(found)} "
              f"withheld path(s) — listed in {src}:")
        for entry, hits in found.items():
            print(f"  {entry}")
            for h in hits[:6]:
                print(f"      {h}")
        print("  This artifact must not be published. Either exclude these in "
              "pyproject.toml, or remove the path from the list if it is no "
              "longer withheld — but do not publish while the two disagree.")
        return EXIT_LEAKED

    print(f"CLEAN: no withheld module in {art.name} "
          f"({len(names)} members, {len(withheld)} withheld paths checked)")
    return EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
