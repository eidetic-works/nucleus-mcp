"""Verify ADUN Memory Pipeline — scripts/verify_adun.py"""
import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.memory_pipeline import MemoryPipeline, EngramOp


def verify_adun():
    # Use a temp dir so we don't pollute the real brain
    with tempfile.TemporaryDirectory() as tmpdir:
        brain = Path(tmpdir)
        pipeline = MemoryPipeline(brain)

        print("--- 🧠 ADUN MEMORY PIPELINE TEST ---\n")

        # 1. ADD — New engram
        print("[1] ADD: Writing a new engram")
        r1 = pipeline.process("PostgreSQL chosen for ACID compliance", context="Architecture", intensity=8, key="db_choice")
        print(f"    Result: added={r1.get('added')}, mode={r1.get('mode')}")
        assert r1["added"] == 1, f"Expected 1 add, got {r1['added']}"

        # 2. NOOP — Exact duplicate
        print("[2] NOOP: Writing same engram again (duplicate)")
        r2 = pipeline.process("PostgreSQL chosen for ACID compliance", context="Architecture", intensity=8, key="db_choice")
        print(f"    Result: skipped={r2.get('skipped')}, mode={r2.get('mode')}")
        assert r2["skipped"] == 1, f"Expected 1 skip, got {r2['skipped']}"

        # 3. UPDATE — Same key, different value
        print("[3] UPDATE: Same key, new value")
        r3 = pipeline.process("PostgreSQL chosen for ACID + JSONB support", context="Architecture", intensity=9, key="db_choice")
        print(f"    Result: updated={r3.get('updated')}, mode={r3.get('mode')}")
        assert r3["updated"] == 1, f"Expected 1 update, got {r3['updated']}"

        # Verify version incremented
        engrams = pipeline._load_active_engrams()
        db_engram = next((e for e in engrams if e["key"] == "db_choice"), None)
        print(f"    Version after update: {db_engram.get('version')}")
        assert db_engram["version"] == 2, f"Expected version 2, got {db_engram['version']}"

        # 4. DELETE — Soft delete
        print("[4] DELETE: Removing an engram")
        r4 = pipeline.process("", context="Architecture", key="db_choice", operation="delete")
        print(f"    Result: deleted={r4.get('deleted')}, mode={r4.get('mode')}")
        assert r4["deleted"] == 1, f"Expected 1 delete, got {r4['deleted']}"

        # Verify it's no longer in active engrams
        active = pipeline._load_active_engrams()
        assert not any(e["key"] == "db_choice" for e in active), "Deleted engram still active!"
        print(f"    Active engrams after delete: {len(active)}")

        # 5. AUTO ADD — No explicit key
        print("[5] AUTO ADD: Pipeline generates key automatically")
        r5 = pipeline.process("Gemini Flash is cheaper than Opus for swarm compute", context="Strategy", intensity=7)
        print(f"    Result: added={r5.get('added')}, atoms={r5.get('atoms_extracted')}, mode={r5.get('mode')}")
        assert r5["added"] >= 1, f"Expected at least 1 add, got {r5['added']}"

        # 6. Verify history log exists
        print("[6] AUDIT: Checking history log")
        assert pipeline.history_path.exists(), "History log not created!"
        with open(pipeline.history_path) as f:
            history_count = sum(1 for line in f if line.strip())
        print(f"    History entries: {history_count}")
        assert history_count >= 4, f"Expected >= 4 history entries, got {history_count}"

        print("\n✅ ADUN Pipeline Verification SUCCESS: All operations functional.")


if __name__ == "__main__":
    verify_adun()
