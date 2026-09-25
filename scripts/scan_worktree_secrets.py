#!/usr/bin/env python3
"""Scan the working tree for secret-shaped strings — including files git hides.

The pre-commit secret scan reads `git diff --cached`, so a live key is invisible
to it until someone runs `git add`. On 2026-09-17 two files holding a real API
key and a bot token sat in a repo root for ten hours; nothing was watching, and
they were only caught when an unrelated `git add -A` swept them toward a commit.
A key in a *gitignored* file is invisible to that scan forever.

So this walks three sets, and says how many files were in each — a scan that
silently covered nothing must not look like a clean scan:

    tracked     git ls-files
    untracked   git ls-files --others --exclude-standard
    ignored     git ls-files --others --ignored --exclude-standard   <- the blind spot

Every match is masked to a 6-character prefix plus a length. The report is not a
second copy of the secret.

    python3 scripts/scan_worktree_secrets.py [path]
    exit 0 = nothing found   exit 1 = findings   exit 3 = could not scan
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

EXIT_CLEAN, EXIT_FOUND, EXIT_INSUFFICIENT = 0, 1, 3

# Vendor key shapes. Generic by construction: no personal data lives in this file.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("google api key", re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")),
    ("aws access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("gitlab token", re.compile(r"glpat-[A-Za-z0-9_\-]{20,}")),
    ("slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("stripe secret", re.compile(r"sk_live_[A-Za-z0-9]{20,}")),
    ("stripe webhook", re.compile(r"whsec_[A-Za-z0-9]{20,}")),
    ("perplexity key", re.compile(r"pplx-[A-Za-z0-9]{32,}")),
    ("resend key", re.compile(r"re_[A-Za-z0-9]{20,}")),
    ("telegram bot token", re.compile(r"\b\d{8,12}:AA[A-Za-z0-9_\-]{30,}")),
    ("openai key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{32,}")),
    # {80,} rather than {20,}: a real Anthropic key is ~100 characters
    # (sk-ant-api03- plus ~95 of body). At {20,} this fired on THIS repo's own
    # test fixtures — sk-ant-oat01-AbCdEfGh-, sk-ant-...-SCRUBBED,
    # sk-ant-sid02-stub — so publish_readiness.sh could not pass on a clean
    # tree, which is how a gate gets bypassed instead of fixed. Measured before
    # changing: the longest sk-ant string anywhere in this repo is 51 chars, and
    # no genuine key is present. Positive control lives in
    # tests/test_scan_worktree_secrets.py and builds a full-length key at
    # runtime, so no literal key is ever written to disk here.
    ("anthropic key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{80,}")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
]

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
             ".pytest_cache", ".ruff_cache", ".mypy_cache", "site-packages"}
MAX_BYTES = 2_000_000


def mask(s: str) -> str:
    return f"{s[:6]}…({len(s)} chars)"


def git_set(root: Path, *args: str) -> list[Path]:
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [root / p for p in r.stdout.split("\0") if p]


def scannable(p: Path) -> bool:
    if any(part in SKIP_DIRS for part in p.parts):
        return False
    try:
        if not p.is_file() or p.stat().st_size > MAX_BYTES:
            return False
    except OSError:
        return False
    return True


def scan_files(files: list[Path]) -> list[tuple[Path, str, str]]:
    out = []
    for f in files:
        if not scannable(f):
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        for label, pat in PATTERNS:
            m = pat.search(text)
            if m:
                out.append((f, label, mask(m.group(0))))
                break
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    if not (root / ".git").exists() and subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-dir"],
            capture_output=True).returncode != 0:
        print(f"INSUFFICIENT: {root} is not a git repository, so nothing was scanned")
        return EXIT_INSUFFICIENT

    sets = {
        "tracked": git_set(root),
        "untracked": git_set(root, "--others", "--exclude-standard"),
        "ignored": git_set(root, "--others", "--ignored", "--exclude-standard"),
    }
    findings: list[tuple[Path, str, str, str]] = []
    for name, files in sets.items():
        scanned = [f for f in files if scannable(f)]
        print(f"  {name:<10} {len(files):>6} listed, {len(scanned):>6} scanned")
        for f, label, masked in scan_files(files):
            findings.append((f, label, masked, name))

    if not findings:
        print("  no secret-shaped strings found")
        return EXIT_CLEAN

    print(f"  FOUND {len(findings)} file(s) containing secret-shaped strings:")
    for f, label, masked, where in findings:
        try:
            rel = f.relative_to(root)
        except ValueError:
            rel = f
        print(f"    [{where}] {rel}  <- {label} {masked}")
    return EXIT_FOUND


if __name__ == "__main__":
    sys.exit(main(sys.argv))
