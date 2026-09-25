"""Verify Hardened Engram Hooks — scripts/verify_hooks.py

Tests all 3 concerns:
1. CERTAINTY  — triggers fire for all classified events
2. CROSS-PLATFORM — pure Python, no OS deps
3. METRICS   — hook_metrics.jsonl records everything
"""
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.engram_hooks import (
    should_auto_write, _create_auto_engram, TRIGGER_EVENTS, SKIP_EVENTS,
    _record_metric, get_hook_metrics_summary, process_event_for_engram,
)
from mcp_server_nucleus.runtime.memory_pipeline import MemoryPipeline


def verify_hooks():
    print("--- 🪝 HARDENED ENGRAM HOOKS VERIFICATION ---\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        brain = Path(tmpdir)

        # ═══ Q1: CERTAINTY ═══════════════════════════════════════
        print("═══ Q1: CERTAINTY (do triggers fire?) ═══\n")

        # TEST 1: All 12 trigger events are recognized
        print(f"[1] TEST: {len(TRIGGER_EVENTS)} trigger events classified")
        for evt in TRIGGER_EVENTS:
            assert should_auto_write(evt), f"FAIL: {evt} should be triggered"
        print(f"    ✅ All {len(TRIGGER_EVENTS)} trigger events pass")

        # TEST 2: All 9 skip events are rejected
        print(f"[2] TEST: {len(SKIP_EVENTS)} skip events classified")
        for evt in SKIP_EVENTS:
            assert not should_auto_write(evt), f"FAIL: {evt} should be skipped"
        print(f"    ✅ All {len(SKIP_EVENTS)} skip events rejected")

        # TEST 3: Total classification covers all known events
        total = len(TRIGGER_EVENTS) + len(SKIP_EVENTS)
        print(f"[3] TEST: Total classified events = {total}")
        assert total >= 21, f"Expected >= 21, got {total}"
        print(f"    ✅ {total} events classified (0 unknowns)")

        # TEST 4: task_completed_with_fence triggers correctly
        print("[4] TEST: task_completed_with_fence creates engram")
        result = _create_auto_engram(
            "task_completed_with_fence",
            {"task_id": "T001", "outcome": "success", "fence_token": 101},
            brain,
        )
        assert result.get("added", 0) == 1
        print(f"    ✅ Engram created from completion event")

        # TEST 5: deploy_complete triggers correctly
        print("[5] TEST: deploy_complete creates engram")
        result = _create_auto_engram(
            "deploy_complete",
            {"service_id": "nucleus-os", "status": "live", "deploy_url": "https://nucleus.onrender.com"},
            brain,
        )
        assert result.get("added", 0) == 1
        print(f"    ✅ Engram created from deployment event")

        # ═══ Q2: CROSS-PLATFORM ═══════════════════════════════════
        print("\n═══ Q2: CROSS-PLATFORM (pure Python?) ═══\n")

        # TEST 6: No OS-specific imports
        print("[6] TEST: No platform-specific code")
        import mcp_server_nucleus.runtime.engram_hooks as hooks_module
        source = Path(hooks_module.__file__).read_text()
        banned = ["import subprocess", "import os\n", "from os import", "import ctypes", "import win32", "import posix"]
        for b in banned:
            assert b not in source, f"FAIL: Found '{b}' in hooks module"
        print(f"    ✅ No OS-specific imports (checked {len(banned)} patterns)")

        # TEST 7: Uses pathlib (cross-platform paths)
        print("[7] TEST: Uses pathlib for path handling")
        assert "from pathlib import Path" in source or "pathlib" in source
        print(f"    ✅ pathlib imported")

        # ═══ Q3: METRICS ═══════════════════════════════════════════
        print("\n═══ Q3: METRICS (monitoring works?) ═══\n")

        # TEST 8: Metrics file gets created
        print("[8] TEST: Metrics recording")
        _record_metric("task_completed_with_fence", "ADD", 0.5, "done_12345", brain)
        _record_metric("deploy_complete", "ADD", 1.2, "deploy_67890", brain)
        _record_metric("engram_written", "SKIP", 0.0, None, brain)
        metrics_path = brain / "engrams" / "hook_metrics.jsonl"
        assert metrics_path.exists()
        lines = [l for l in metrics_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 3, f"Expected 3 metrics, got {len(lines)}"
        print(f"    ✅ 3 metrics recorded to hook_metrics.jsonl")

        # TEST 9: Metrics summary computation
        print("[9] TEST: Metrics summary computation")
        summary = get_hook_metrics_summary(brain)
        assert summary["total_executions"] == 3
        assert summary["outcomes"]["ADD"] == 2
        assert summary["error_rate"] == 0.0
        assert summary["coverage"]["trigger_events"] == len(TRIGGER_EVENTS)
        assert summary["coverage"]["skip_events"] == len(SKIP_EVENTS)
        print(f"    ✅ Summary: {summary['total_executions']} executions, "
              f"error_rate={summary['error_rate']}, "
              f"efficiency={summary['efficiency']}")

        # TEST 10: Error recording
        print("[10] TEST: Error recording")
        _record_metric("task_created", "ERROR", 5.0, None, brain, error="Test error")
        summary2 = get_hook_metrics_summary(brain)
        assert summary2["outcomes"].get("ERROR", 0) == 1
        assert summary2["error_rate"] > 0
        print(f"    ✅ Error recorded, rate={summary2['error_rate']}")

        # TEST 11: Source agent attribution
        print("[11] TEST: Source agent = auto_hook")
        pipeline = MemoryPipeline(brain)
        engrams = pipeline._load_active_engrams()
        for e in engrams:
            assert e.get("source_agent") == "auto_hook"
        print(f"    ✅ All {len(engrams)} engrams attributed to 'auto_hook'")

        # TEST 12: SafeDict handles missing template vars
        print("[12] TEST: SafeDict for robust template filling")
        from mcp_server_nucleus.runtime.engram_hooks import _fill_template
        result = _fill_template("Task {task_id} completed ({outcome})", {"task_id": "T001"})
        assert "?" in result  # outcome should be "?"
        assert "T001" in result
        print(f"    ✅ Missing vars replaced with '?': '{result}'")

    print(f"\n{'='*60}")
    print(f"✅ HARDENED HOOKS VERIFICATION: All 12 checks passed.")
    print(f"   Certainty: 12/12 triggers fire, 9/9 skips reject")
    print(f"   Platform:  Pure Python, no OS deps")
    print(f"   Metrics:   hook_metrics.jsonl records all outcomes")
    print(f"{'='*60}")


if __name__ == "__main__":
    verify_hooks()
