#!/usr/bin/env python3
"""Scan a BUILT artifact — wheel or sdist — for operator identity before it ships.

RELEASE_GATE.md has described this script as the last gate before publishing, and
credited it with catching the 1.16.6 poisoning. It did not exist: not in the tree,
not in git history. This is that gate, written.

Why the artifact and not the source tree: the tree is not what `pip install`
delivers. A file can be clean in git and still land in the wheel through package
data, a build hook, or a stray file under src/. Scanning the thing that ships is
the only check that answers the question being asked.

Exit codes (the first two are RELEASE_GATE.md's contract, the third is new):
    0  clean       — no term matched
    2  poisoned    — at least one term matched; the artifact must not be published
    3  INSUFFICIENT— no term list could be found, so nothing was actually checked.
                     An empty list must never read as "clean".

The gate holds HASHES of terms, never the terms themselves, so this file can sit
in a public repo without becoming the leak it prevents. Terms are loaded from
outside the package:

    $NUCLEUS_IDENTITY_TERMS_FILE
    <repo>/.githooks/pre-commit-pseudonymity-guard
    <repo>/.brain/policies/pseudonymity_blocklist.json
    ... then the same walk upward through parent directories.

Usage:
    python3 scripts/artifact_identity_gate.py dist/nucleus_mcp-1.16.9.tar.gz
    python3 scripts/artifact_identity_gate.py dist/*.whl
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tarfile
import zipfile
from pathlib import Path

EXIT_CLEAN = 0
EXIT_POISONED = 2
EXIT_INSUFFICIENT = 3

# Structural patterns — shapes, not identities, so they are safe to keep here.
#
# These are deliberately narrow. A first draft matched any /home/<name> and any
# email, and flagged `/home/ubuntu/.nucleus_relay_env` in a help string and
# `you@example.com` in an HTML placeholder — the same over-matching that made
# this repo's archive oracle wrong on 788 of 1,053 files. A gate that cries wolf
# on its own clean artifact teaches everyone to skip it.
PLACEHOLDER_USER = re.compile(
    rb"^(ubuntu|root|user|username|name|you|me|someone|runner|ec2-user|admin|"
    rb"NAME|USER|OPERATOR|\.\.\.)$"
)
PLACEHOLDER_DOMAIN = re.compile(rb"@(example\.(com|org|net)|test|localhost|domain\.com|email\.com)$")

STRUCTURAL = [
    (re.compile(rb"/(?:Users|home)/([A-Za-z][A-Za-z0-9_.-]*)"), "absolute home path"),
    (re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "email address"),
]
# Addresses meant to be published.
EMAIL_ALLOW = re.compile(rb"^(noreply|no-reply|hello|support|security|info|admin)@")


def _structural_hit(data: bytes) -> str | None:
    """Return a label for a real structural leak, or None for a placeholder."""
    m = STRUCTURAL[0][0].search(data)
    if m and not PLACEHOLDER_USER.match(m.group(1)):
        return f"absolute home path ({m.group(0).decode(errors='replace')})"
    for m in re.finditer(STRUCTURAL[1][0], data):
        addr = m.group(0)
        if EMAIL_ALLOW.match(addr) or PLACEHOLDER_DOMAIN.search(addr):
            continue
        return "email address"
    return None


def _term_sources(start: Path) -> list[Path]:
    out: list[Path] = []
    env = os.environ.get("NUCLEUS_IDENTITY_TERMS_FILE")
    if env:
        out.append(Path(env).expanduser())
    here = start.resolve()
    for d in (here, *here.parents):
        out.append(d / ".githooks" / "pre-commit-pseudonymity-guard")
        out.append(d / ".brain" / "policies" / "pseudonymity_blocklist.json")
    return out


def load_terms(start: Path) -> tuple[list[str], Path | None]:
    """Return (terms, source). An empty list means INSUFFICIENT, never 'clean'."""
    for src in _term_sources(start):
        if not src.is_file():
            continue
        try:
            raw = src.read_text(errors="replace")
        except OSError:
            continue
        if src.suffix == ".json":
            try:
                data = json.loads(raw)
            except ValueError:
                continue
            terms = [t for t in _flatten(data) if isinstance(t, str) and len(t) > 3]
        else:
            # shell array entries: "term"    # comment
            terms = [m.group(1) for m in re.finditer(r'^\s*"([^"]{4,})"', raw, re.M)]
        terms = sorted({t.strip() for t in terms if t.strip() and not t.startswith("#")})
        if terms:
            return terms, src
    return [], None


def _flatten(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _flatten(v)


def members(path: Path):
    """Yield (name, bytes) for every member, whatever the archive kind."""
    if path.suffix == ".whl" or path.name.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                try:
                    yield info.filename, z.read(info)
                except Exception:
                    yield info.filename, b""
    else:
        with tarfile.open(path) as t:
            for info in t.getmembers():
                if not info.isfile():
                    continue
                f = t.extractfile(info)
                yield info.name, (f.read() if f else b"")


def scan(path: Path, terms: list[str]) -> list[tuple[str, str]]:
    """Return [(member, what matched)] — the term itself is never returned."""
    digests = {hashlib.sha256(t.lower().encode()).hexdigest(): i for i, t in enumerate(terms)}
    word = re.compile(rb"[A-Za-z0-9_.@+-]{4,}")
    hits: list[tuple[str, str]] = []
    for name, data in members(path):
        if not data:
            continue
        for m in word.finditer(data):
            tok = m.group(0).lower()
            if hashlib.sha256(tok).hexdigest() in digests:
                hits.append((name, f"identity term #{digests[hashlib.sha256(tok).hexdigest()]}"))
                break
        else:
            label = _structural_hit(data)
            if label:
                hits.append((name, label))
    return hits


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in ("-h", "--help"):
        # Without this, `--help` was read as a filename and answered
        # "INSUFFICIENT: no such artifact: --help" — correct as a verdict and
        # useless as an answer to the question actually asked.
        print(__doc__.strip())
        return 0
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: artifact_identity_gate.py <artifact.whl|artifact.tar.gz>")
        return EXIT_INSUFFICIENT
    art = Path(argv[1])
    if not art.is_file():
        print(f"INSUFFICIENT: no such artifact: {art}")
        return EXIT_INSUFFICIENT

    terms, source = load_terms(Path.cwd())
    if not terms:
        tried = "\n  ".join(str(p) for p in _term_sources(Path.cwd())[:6])
        print("INSUFFICIENT: no identity term list found, so nothing was checked.")
        print(f"  looked in:\n  {tried}")
        print("  set NUCLEUS_IDENTITY_TERMS_FILE to the list you want enforced.")
        return EXIT_INSUFFICIENT

    hits = scan(art, terms)
    kind = "wheel" if art.suffix == ".whl" else "sdist"
    print(f"artifact : {art.name}  ({kind})")
    print(f"sha256   : {hashlib.sha256(art.read_bytes()).hexdigest()}")
    print(f"terms    : {len(terms)} loaded from {source}")
    if hits:
        print(f"POISONED : {len(hits)} member(s) matched — this artifact must not be published")
        for name, why in hits[:20]:
            print(f"    {name}  <- {why}")
        return EXIT_POISONED
    print("CLEAN    : no identity term or structural match in any member")
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv))
