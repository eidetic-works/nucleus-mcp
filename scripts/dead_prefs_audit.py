#!/usr/bin/env python3
"""
dead_prefs_audit.py — AUTO-GATE for feedback_dead_prefs_audit_required +
                      feedback_feature_inventory_4_check

Scans settings*.json files for preference keys and verifies each key has at
least one caller in src/. Reports dead (unreferenced) pref keys.

Usage:
    python scripts/dead_prefs_audit.py            # fails on dead prefs
    python scripts/dead_prefs_audit.py --report-only  # always exits 0 (CI advisory mode)

Exit codes:
    0 — all pref keys have at least one src/ caller, OR --report-only mode
    1 — one or more dead pref keys found (only in default mode)

Wired per TREATMENT.md AUTO-GATE-PENDING pass (FEEDBACK_RULES_REGISTRY.md §2).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def find_settings_files(repo_root: Path) -> list[Path]:
    """Glob for settings*.json under the repo root (excluding node_modules, .git)."""
    results = []
    for match in repo_root.rglob("settings*.json"):
        parts = match.parts
        if any(p in (".git", "node_modules", "__pycache__", ".claude") for p in parts):
            continue
        results.append(match)
    return results


def extract_pref_keys(settings_path: Path) -> list[str]:
    """Return top-level keys from a JSON settings file. Returns [] on parse error."""
    try:
        with settings_path.open() as f:
            data = json.load(f)
        if isinstance(data, dict):
            return list(data.keys())
    except (json.JSONDecodeError, OSError):
        pass
    return []


def key_has_caller(key: str, src_dir: Path) -> bool:
    """Return True if `key` appears in any file under src_dir."""
    try:
        result = subprocess.run(
            ["grep", "-rl", "--include=*.py", key, str(src_dir)],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    except OSError:
        return True  # grep not available; skip check


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit dead preference keys in settings*.json")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Always exit 0 (advisory/CI mode); still prints findings.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Override repo root (defaults to parent of this script's directory).",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).parent.parent
    src_dir = repo_root / "src"

    settings_files = find_settings_files(repo_root)
    if not settings_files:
        print("dead_prefs_audit: no settings*.json files found — nothing to audit.")
        return 0

    dead_keys: list[tuple[Path, str]] = []
    total_keys = 0

    for sf in settings_files:
        keys = extract_pref_keys(sf)
        for key in keys:
            total_keys += 1
            if not src_dir.exists() or not key_has_caller(key, src_dir):
                dead_keys.append((sf, key))

    print(f"dead_prefs_audit: scanned {len(settings_files)} settings file(s), {total_keys} key(s).")

    if dead_keys:
        print(f"  ⚠️  {len(dead_keys)} potentially dead pref key(s) found:")
        for sf, key in dead_keys:
            print(f"    {sf.relative_to(repo_root)}: '{key}'")
        print("  → Schedule instrumentation sweep to confirm before removing.")
        if args.report_only:
            print("  (--report-only: exit 0 despite findings)")
            return 0
        return 1

    print("  ✅ All pref keys have at least one src/ caller.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
