#!/usr/bin/env python3
"""Scan a BUILT artifact for OTHER PEOPLE's personal data before it ships.

The identity gate next to this one holds hashes of the operator's own terms. It
was measured on 2026-09-19 against a two-row prospect list — name, email, name,
email — and reported CLEAN, correctly: none of those names are the operator's.
The secret scanner matched nothing either, because an email address is not a
credential.

So a `prospects.csv` could pass every control in this repo and land in a
published wheel carrying real names and addresses of people who never agreed to
anything. That is a worse disclosure than the one the rest of the chain exists to
prevent, and it had no instrument at all. This is that instrument.

Exit codes, matching artifact_identity_gate.py:
    0  clean        — nothing unexplained
    2  found        — third-party contact data; the artifact must not be published
    3  INSUFFICIENT — the scan could not run, so nothing was checked

WHAT IT DOES NOT COVER, stated rather than implied:
  * Phone numbers. Measured first: the shape matches a 13-digit id already in
    src/, and nothing else. A rule that fires on identifiers and timestamps gets
    suppressed, and a suppressed rule protects no one. Not included.
  * Names without an address. There is no way to tell a contributor's name in a
    changelog from a prospect's name in a list, so the signal here is the
    ADDRESS, and the row shape around it.

Allowlist: .known-external-contacts.txt, one reason per entry, same shape as
.known-divergent.txt. An address on it is one someone decided about.
"""

from __future__ import annotations

import csv
import io
import re
import sys
import tarfile
import zipfile
from pathlib import Path

EXIT_CLEAN, EXIT_FOUND, EXIT_INSUFFICIENT = 0, 2, 3

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Domains that cannot belong to a real third party. Measured from this repo:
# alice@example.com, t@test.com, foo@bar.com, a@b.com and friends are fixtures.
PLACEHOLDER_DOMAINS = {
    "example.com", "example.org", "example.net", "test.com", "test.org",
    "bar.com", "b.com", "y.com", "x.com", "t.com", "t.invalid", "invalid",
    "localhost", "race-test.com", "persist-test.com", "email.com", "domain.com",
    "mail.com", "company.com", "acme.com", "foo.com", "baz.com",
    # This repo's own synthetic test domains, measured from the worktree scan.
    # Without them --worktree is 58 files of noise, and a noisy gate is ignored.
    "case-test.com", "seq-test.com", "concurrent-test.com", "chatgpt-user.com",
    "eidetic-works.local", "mcp.tool",
}
# Addresses that are the product's own, or a protocol endpoint rather than a person.
SELF_OR_PROTOCOL = re.compile(
    r"@(nucleusos\.dev|nucleus-mcp\.com|eidetic\.works)$|^git@github\.com$"
    r"|@users\.noreply\.github\.com$", re.I)

# `Icon-App-20x20@2x.png` matches the address pattern: user "Icon-App-20x20",
# domain "2x.png", TLD "png". Apple asset catalogs are full of them, so every
# Flutter or iOS repo starts at ~15 files of noise — measured by the gq lane on
# GentleQuest's Contents.json. The fix is the CLASS, not a placeholder per
# project: a "domain" ending in a media or document extension is a filename.
# Deliberately narrow — .app and .dev are real TLDs, and only extensions with no
# plausible TLD collision are listed.
FILENAME_TAIL = re.compile(
    r"\.(png|jpe?g|gif|webp|svg|ico|bmp|tiff?|pdf|mp4|mov|avi|webm|mp3|wav|"
    r"zip|gz|tgz|whl|woff2?|ttf|otf|eot|css|scss|jsx?|tsx?|py|rb|go|rs|java|"
    r"json|ya?ml|toml|md|txt|csv|tsv|html?|xml)$", re.I)

NAME_COL = re.compile(r"^(name|full[_ ]?name|first[_ ]?name|last[_ ]?name|contact)$", re.I)
MAIL_COL = re.compile(r"^(e[-_ ]?mail|email[_ ]?address|mail)$", re.I)


def load_allowlist(start: Path) -> set[str]:
    for base in (start, *start.parents):
        f = base / ".known-external-contacts.txt"
        if f.is_file():
            return {ln.strip().lower() for ln in f.read_text().splitlines()
                    if ln.strip() and not ln.startswith("#")}
    return set()


def suspicious_addresses(text: str, allow: set[str]) -> set[str]:
    out = set()
    for a in EMAIL.findall(text):
        low = a.lower()
        if low in allow or SELF_OR_PROTOCOL.search(low):
            continue
        dom = low.rsplit("@", 1)[-1]
        if dom in PLACEHOLDER_DOMAINS or FILENAME_TAIL.search(dom):
            continue
        out.add(a)
    return out


def looks_like_a_contact_table(name: str, text: str) -> bool:
    """A CSV/TSV whose header pairs a name column with an email column.

    This is the prospect-list shape specifically. It fires even when every row is
    synthetic, because a list that LOOKS like contacts is not something to ship
    from a product repo either way.
    """
    if not name.lower().endswith((".csv", ".tsv")):
        return False
    try:
        head = next(csv.reader(io.StringIO(text[:8192])))
    except (StopIteration, csv.Error):
        return False
    cols = [c.strip() for c in head]
    return any(NAME_COL.match(c) for c in cols) and any(MAIL_COL.match(c) for c in cols)


def worktree_files(root: Path):
    """Every tracked text file. The worktree, not just the artifact.

    Scope learned from the gq lane, 2026-09-19: it ran this gate's rules over
    GentleQuest's tree and found a tracked 100-row journalist table — name,
    outlet, beat, email, twitter, linkedin, and a personalized hook per row.
    Nothing packaged it, so an artifact-only scan would have reported CLEAN
    forever. The repo is the thing that gets cloned, contributed to, and handed
    over; the artifact is only one way data leaves.
    """
    import subprocess
    skip = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz",
            ".whl", ".woff", ".woff2", ".ttf", ".mp4", ".mov", ".webp"}
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                         capture_output=True, text=True)
    for rel in out.stdout.split("\0"):
        if not rel or Path(rel).suffix.lower() in skip:
            continue
        f = root / rel
        try:
            yield rel, f.read_text(errors="replace")
        except OSError:
            continue


def members(art: Path):
    if art.suffix == ".whl" or art.suffix == ".zip":
        with zipfile.ZipFile(art) as z:
            for n in z.namelist():
                if n.endswith("/"):
                    continue
                yield n, z.read(n).decode("utf-8", "replace")
    elif "".join(art.suffixes[-2:]) in (".tar.gz", ".tgz") or art.suffix == ".gz":
        with tarfile.open(art) as t:
            for m in t.getmembers():
                if not m.isfile():
                    continue
                f = t.extractfile(m)
                if f:
                    yield m.name, f.read().decode("utf-8", "replace")
    else:
        raise ValueError(f"not a wheel or sdist: {art.name}")


def scan_worktree(root: Path) -> int:
    """Report contact data in the tracked tree, tables loudest."""
    allow = load_allowlist(Path(__file__).resolve().parent)
    addrs: dict[str, set[str]] = {}
    tables: list[str] = []
    scanned = 0
    for rel, text in worktree_files(root):
        scanned += 1
        found = suspicious_addresses(text, allow)
        if found:
            addrs[rel] = found
        if looks_like_a_contact_table(rel, text):
            tables.append(rel)
    if not scanned:
        print(f"INSUFFICIENT: no tracked text files under {root}")
        return EXIT_INSUFFICIENT
    distinct = {a for v in addrs.values() for a in v}
    print(f"scanned {scanned} tracked text files")
    print(f"  contact-table shaped files: {len(tables)}")
    for t in tables:
        print(f"    TABLE  {t}")
    print(f"  files with a non-fixture address: {len(addrs)}  "
          f"({len(distinct)} distinct)")
    for rel, v in sorted(addrs.items(), key=lambda kv: -len(kv[1]))[:12]:
        print(f"    {len(v):3}  {rel}")
    # A table is the prospect-list shape and is always a finding. Loose addresses
    # in a private repo are a judgement call, so they are REPORTED, not failed —
    # a gate that fails on a changelog's contributor address gets turned off.
    return EXIT_FOUND if tables else EXIT_CLEAN


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if len(argv) == 3 and argv[1] == "--worktree":
        return scan_worktree(Path(argv[2]))
    if len(argv) != 2:
        print("usage: third_party_pii_gate.py <artifact.whl|artifact.tar.gz>")
        print("       third_party_pii_gate.py --worktree <repo root>")
        return EXIT_INSUFFICIENT
    art = Path(argv[1])
    if not art.is_file():
        print(f"INSUFFICIENT: no such artifact: {art}")
        return EXIT_INSUFFICIENT

    allow = load_allowlist(Path(__file__).resolve().parent)
    findings: list[str] = []
    scanned = 0
    try:
        for name, text in members(art):
            scanned += 1
            for a in sorted(suspicious_addresses(text, allow)):
                user, _, dom = a.partition("@")
                findings.append(f"{name}: {user[:2]}…@{dom}")
            if looks_like_a_contact_table(name, text):
                findings.append(f"{name}: header pairs a name column with an email column")
    except Exception as e:  # noqa: BLE001 - any read failure means nothing was checked
        print(f"INSUFFICIENT: could not read {art.name}: {e}")
        return EXIT_INSUFFICIENT

    if not scanned:
        print(f"INSUFFICIENT: {art.name} contained no readable members")
        return EXIT_INSUFFICIENT
    if findings:
        print(f"FOUND: third-party contact data in {art.name} ({scanned} members):")
        for f in findings[:20]:
            print(f"  {f}")
        print("  Addresses are masked. If one of these is legitimate, add it to "
              ".known-external-contacts.txt with the reason.")
        return EXIT_FOUND
    print(f"CLEAN: no third-party contact data in {art.name} ({scanned} members)")
    return EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
