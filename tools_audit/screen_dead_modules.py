#!/usr/bin/env python3
"""Re-screen the candidate-dead runtime modules, then optionally delete them.

Why this exists
---------------
A 35-module deletion list was produced by auditing the private MIRROR of this
repo (audit ledger DS-1..DS-4). That checkout has `tests/` and most of
`scripts/` marked `export-ignore`, so they are simply absent from it. A test or
script importing `runtime.pulse` or `runtime.swarm` is therefore INVISIBLE to
any search run there, and the mirror is regenerated from the parent tree anyway,
so deleting in it accomplishes nothing.

Run this in the real development tree, where those directories exist.

    python3 tools_audit/screen_dead_modules.py              # report only
    python3 tools_audit/screen_dead_modules.py --delete     # delete the clean ones

It refuses to delete when `tests/` is missing, because that is the signature of
the mirror and the one condition under which the screen cannot be trusted.

What it checks, per module
--------------------------
Every reference form an import-statement grep misses:
  1. literal imports
  2. dynamic imports whose argument contains the module name
  3. the bare module name in ANY file, including json/toml/yaml/md
  4. the module's own top-level def/class names, referenced elsewhere
Self-matches are excluded throughout.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

# Screened dead against the mirror on 2026-09-11 by a 7-agent pass plus an
# adversarial reviewer that failed to overturn any of them. environment_detector
# was on the original DS-4 list and is NOT here: it is reachable through
# runtime/__init__.py's PEP 562 _LAZY_MAP, which is exactly the form the original
# import-statement grep missed.
CANDIDATES = [
    "runtime/align_ops.py", "runtime/auto_awake.py", "runtime/backup_ops.py",
    "runtime/board_ops.py", "runtime/critic.py", "runtime/cross_repo_census.py",
    "runtime/emergence_rate.py", "runtime/fetcher.py", "runtime/gateway.py",
    "runtime/growth_registry.py", "runtime/health_sidecar.py", "runtime/hygiene.py",
    "runtime/incident_ops.py", "runtime/inspector.py", "runtime/isolation_layer.py",
    "runtime/mounter.py", "runtime/nudge_ops.py", "runtime/oauth_shim_http.py",
    "runtime/orchestrator_v3.py", "runtime/org_delegate.py", "runtime/otel_export.py",
    "runtime/pm_view_ops.py", "runtime/process_manager.py", "runtime/proposals.py",
    "runtime/publisher.py", "runtime/pulse.py", "runtime/sonnet_pair_daemon.py",
    "runtime/stripe_billing.py", "runtime/swarm.py", "runtime/verify_cli.py",
    "runtime/identity/gatekeeper.py", "runtime/jobs/marketplace_job.py",
    "runtime/auth/oauth_provider.py", "runtime/agent_os/oauth_probe.py",
]

PKG = "src/mcp_server_nucleus"
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
# Files that list these module names BECAUSE they are the audit of them. Counting
# them as references would make every module look alive forever.
SELF_REFERENTIAL = {"AUDIT_LEDGER.md"}


def repo_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here.parent, *here.parents):
        if (candidate / PKG).is_dir():
            return candidate
    sys.exit(f"could not locate {PKG}/ above {here}")


# Names too generic to search for: a hit tells you nothing. Found the hard way —
# emergence_rate.py exports `Pattern`, which matched unrelated lines all over the repo
# and made a dead module look alive.
GENERIC_NAMES = {
    "Pattern", "Config", "Result", "Error", "Item", "Node", "Entry", "Record",
    "State", "Status", "Store", "Client", "Server", "Manager", "Handler",
}

# A real reference imports the module, or names it as a string some loader imports.
# Anything else that merely contains the name is a coincidence until proven otherwise.
IMPORTISH = re.compile(
    r"\bimport\b|\bfrom\s|import_module|__import__|entry_points|console_scripts"
)


def public_names(path: Path) -> list[str]:
    """Top-level def/class names, which a re-export could reach without the module name."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return []
    names = [
        n.name for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not n.name.startswith("_")
        and n.name not in GENERIC_NAMES
        and len(n.name) >= 8          # short names collide with unrelated identifiers
    ]
    # Longest first: distinctive names produce fewer false positives.
    return sorted(names, key=len, reverse=True)[:5]


def search(root: Path, needle: str, exclude: Path) -> tuple[list[str], list[str], list[str]]:
    """(real_refs, prose_mentions, suspect_hits) for `needle`, excluding its own file."""
    try:
        out = subprocess.run(
            # -w: whole word. Without it "critic" matches "critical" and every
            # dead module looks referenced.
            ["rg", "--no-heading", "-n", "-w", "--fixed-strings", needle, str(root)],
            capture_output=True, text=True, timeout=120,
        ).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        out = ""
        pattern = re.compile(r"\b" + re.escape(needle) + r"\b")
        for f in root.rglob("*"):
            if not f.is_file() or any(p in SKIP_DIRS for p in f.parts):
                continue
            try:
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if pattern.search(line):
                        out += f"{f}:{i}:{line}\n"
            except OSError:
                continue

    code, prose, suspect = [], [], []
    ex = str(exclude.resolve())
    for line in out.splitlines():
        if any(f"/{d}/" in line for d in SKIP_DIRS):
            continue
        path = line.split(":", 1)[0].strip()
        if path == ex:
            continue                                   # self-match
        if Path(path).name in SELF_REFERENTIAL or "/tools_audit/" in path:
            continue                                   # this screen and its own ledger
        entry = line.strip()[:200]
        if path.endswith((".md", ".txt", ".rst")):
            # A mention in prose is a doc to update, not a reason to keep code alive.
            prose.append(entry)
            continue
        body = entry.split(":", 2)[-1].lstrip()
        if body[:1] in {"#", "*"} or body.startswith("//"):
            continue                 # a comment naming the module does not call it
        if IMPORTISH.search(body):
            code.append(entry)
        else:
            suspect.append(entry)    # names it, but not in a way that imports it
    return code, prose, suspect


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delete", action="store_true",
                    help="delete modules that come back with zero references")
    ap.add_argument("--force-in-mirror", action="store_true",
                    help=argparse.SUPPRESS)   # deliberately undocumented
    args = ap.parse_args()

    root = repo_root()
    pkg = root / PKG
    has_tests = (root / "tests").is_dir()

    print(f"repo:  {root}")
    print(f"tests/ present: {has_tests}")
    if not has_tests:
        print("\n  !!  tests/ is absent. This looks like the export-ignored mirror,")
        print("      where a test importing one of these modules is invisible.")
        print("      Screening will run, but --delete is refused here.\n")

    dead, alive, missing = [], [], []
    for rel in CANDIDATES:
        path = pkg / rel
        if not path.exists():
            missing.append(rel)
            continue

        stem = Path(rel).stem
        code, prose, suspect = search(root, stem, path)
        matched_on = stem
        if not code:
            # The public-name fallback can raise a question but never settle one.
            # A name defined in a dead module is often ALSO defined in the live
            # module that replaced it — critic.py and swarm.py both define
            # get_brain_path, mounter.py defines get_mounter, orchestrator_v3.py
            # defines get_orchestrator — and every hit for those names turned out
            # to be an import from runtime.common, mounter_ops and
            # orchestrator_unified respectively. Finding the live import proves
            # nothing about the dead twin, so these go to `suspect` for a human
            # to read, never to `code`.
            for name in public_names(path):
                more_code, more_prose, more_suspect = search(root, name, path)
                prose += more_prose
                suspect += [f"[{name}] {h}" for h in more_code + more_suspect]

        lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        if code:
            alive.append((rel, lines, matched_on, code[:3]))
        else:
            dead.append((rel, lines, prose[:2], suspect[:3]))

    print(f"\n{'-' * 72}\nDEAD — no reference of any form ({len(dead)})\n{'-' * 72}")
    for rel, lines, prose, suspect in dead:
        note = f"   (mentioned in {len(prose)}+ doc{'s' if len(prose) != 1 else ''})" if prose else ""
        print(f"  {rel:<46} {lines:>6} lines{note}")
    print(f"\n  total: {sum(n for _, n, _, _ in dead):,} lines")
    suspects = [(rel, sus) for rel, _, _, sus in dead if sus]
    if suspects:
        print("\n  Named in code but never imported — read these before deleting.")
        print("  Usually a naming coincidence, occasionally a loader you have not spotted:")
        for rel, sus in suspects:
            for hit in sus[:1]:
                print(f"    {Path(rel).stem}: {hit[:110]}")
    doc_mentions = [(rel, prose) for rel, _, prose, _ in dead if prose]
    if doc_mentions:
        print("\n  Docs still describing modules that are about to go away —")
        print("  update these in the same commit, or the docs start lying again:")
        for rel, prose in doc_mentions:
            for hit in prose[:1]:
                print(f"    {Path(rel).stem}: {hit[:110]}")

    if alive:
        print(f"\n{'-' * 72}\nREFERENCED — do NOT delete ({len(alive)})\n{'-' * 72}")
        for rel, lines, needle, refs in alive:
            print(f"  {rel}  ({lines} lines, matched on {needle!r})")
            for r in refs:
                print(f"      {r}")

    if missing:
        print(f"\nNOT FOUND (already gone?): {', '.join(missing)}")

    if not args.delete:
        print("\nReport only. Re-run with --delete to remove the dead ones.")
        return 0

    if not has_tests and not args.force_in_mirror:
        print("\nRefusing to delete: tests/ is absent, so this screen is not trustworthy here.")
        return 1

    for rel, _, _ in dead:
        (pkg / rel).unlink()
    print(f"\nDeleted {len(dead)} modules. Now run the full suite before committing:")
    print("    pytest tests/ -q && ruff check src/")
    print("Commit with a dated sweep note naming this screen, per the repo convention.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
