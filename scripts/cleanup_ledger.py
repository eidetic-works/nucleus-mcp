#!/usr/bin/env python3
"""
Brain Task Ledger Cleanup — Opus-Level
=======================================
Removes CLOSED/test/duplicate tasks from tasks.json,
closes stale auto-scanned commitments in the commitment ledger,
and archives everything safely.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

BRAIN = Path("/Users/lokeshgarg/ai-mvp-backend/.brain")
NOW = datetime.now().isoformat()
ARCHIVE_DIR = BRAIN / "archive" / "ledger_cleanup_20260219"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# STAGE 1: Clean tasks.json
# ============================================================
def clean_tasks():
    tasks_path = BRAIN / "ledger" / "tasks.json"
    shutil.copy2(tasks_path, ARCHIVE_DIR / "tasks.json.bak")
    print(f"[1] Backed up tasks.json")

    with open(tasks_path, "r") as f:
        tasks = json.load(f)

    print(f"[1] BEFORE: {len(tasks)} tasks")

    keep = []
    archive = []
    for t in tasks:
        tid = t.get("id", "?")
        desc = t.get("description", "?")
        status = t.get("status", "?")

        if status == "CLOSED":
            archive.append(t)
            continue
        if desc in ["test task", "Standard Task", "GTM Task"]:
            archive.append(t)
            continue
        if tid == "brand_convergence_v2":
            archive.append(t)
            continue
        if "[SWARM]" in desc and "MASTER_STRATEGY" in desc:
            t["status"] = "DONE"
            t["updated_at"] = NOW
        if tid == "brand_convergence_v3":
            t["status"] = "DONE"
            t["updated_at"] = NOW
        keep.append(t)

    with open(ARCHIVE_DIR / "archived_tasks.json", "w") as f:
        json.dump(archive, f, indent=2)

    with open(tasks_path, "w") as f:
        json.dump(keep, f, indent=2)

    print(f"[1] AFTER:  {len(keep)} tasks (archived {len(archive)})")
    for t in keep:
        print(f"    [{t.get('status'):8}] [P{t.get('priority')}] {t['id'][:22]:22} {t['description'][:55]}")

# ============================================================
# STAGE 2: Clean commitment ledger
# ============================================================
def clean_commitments():
    cl_path = BRAIN / "commitments" / "ledger.json"
    if not cl_path.exists():
        print("[2] No commitment ledger found, skipping")
        return

    size_kb = cl_path.stat().st_size / 1024
    print(f"\n[2] Commitment ledger: {size_kb:.0f}KB")
    shutil.copy2(cl_path, ARCHIVE_DIR / "commitment_ledger.json.bak")
    print(f"[2] Backed up commitment ledger")

    with open(cl_path, "r") as f:
        ledger = json.load(f)

    comms = ledger.get("commitments", [])
    print(f"[2] BEFORE: {len(comms)} commitments")

    # Count by source
    sources = {}
    for c in comms:
        src = c.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    print(f"    Sources: {sources}")

    # Close stale items
    closed_count = 0
    for c in comms:
        src = c.get("source", "unknown")
        st = c.get("status", "open")

        if src == "scanned" and st == "open":
            c["status"] = "closed"
            c["closed_reason"] = "ledger_cleanup_opus_20260219"
            closed_count += 1

        created = c.get("created", "")
        if created and "2026-01" in created and st == "open":
            if src in ["manual", "nar_auto"]:
                c["status"] = "closed"
                c["closed_reason"] = "stale_jan_cleanup"
                closed_count += 1

    ledger["commitments"] = comms
    with open(cl_path, "w") as f:
        json.dump(ledger, f)  # No indent to save space

    remaining_open = len([c for c in comms if c.get("status") == "open"])
    print(f"[2] Closed {closed_count} stale items")
    print(f"[2] AFTER:  {remaining_open} open commitments")
    new_size = cl_path.stat().st_size / 1024
    print(f"[2] File:   {size_kb:.0f}KB -> {new_size:.0f}KB")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("BRAIN TASK LEDGER CLEANUP (Opus)")
    print("=" * 60)
    clean_tasks()
    clean_commitments()
    print(f"\n{'=' * 60}")
    print("CLEANUP COMPLETE. Backups in:")
    print(f"  {ARCHIVE_DIR}")
    print("=" * 60)
