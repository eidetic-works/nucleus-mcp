"""Verify Morning Brief — scripts/verify_morning_brief.py"""
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.memory_pipeline import MemoryPipeline
from mcp_server_nucleus.runtime.morning_brief_ops import (
    _morning_brief_impl,
    _retrieve_top_engrams,
    _retrieve_tasks,
    _retrieve_yesterday,
    _generate_recommendation,
)


def verify_morning_brief():
    print("--- 🧠 MORNING BRIEF VERIFICATION ---\n")

    # Use a temp dir with pre-seeded data
    with tempfile.TemporaryDirectory() as tmpdir:
        brain = Path(tmpdir)

        # SETUP: Seed engrams via ADUN pipeline
        print("[1] SEEDING: Writing test engrams via ADUN pipeline")
        pipeline = MemoryPipeline(brain)
        pipeline.process("PostgreSQL chosen for ACID compliance", context="Architecture", intensity=9, key="db_choice")
        pipeline.process("Budget constraint — Gemini only, no OpenAI", context="Decision", intensity=10, key="no_openai")
        pipeline.process("Flash plus disciplined prompting beats Opus", context="Strategy", intensity=7, key="flash_discipline")

        engrams = pipeline._load_active_engrams()
        print(f"    Engrams seeded: {len(engrams)}")
        assert len(engrams) == 3, f"Expected 3 engrams, got {len(engrams)}"

        # SETUP: Seed tasks
        print("[2] SEEDING: Writing test tasks")
        tasks_dir = brain / "ledger"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        tasks_path = tasks_dir / "tasks.jsonl"
        with open(tasks_path, "w") as f:
            f.write(json.dumps({"id": "T001", "description": "Build brain_morning_brief MCP tool", "priority": 9, "status": "in_progress"}) + "\n")
            f.write(json.dumps({"id": "T002", "description": "Record Alive Moment demo video", "priority": 8, "status": "pending"}) + "\n")
            f.write(json.dumps({"id": "T003", "description": "Post demo on Reddit r/ClaudeAI", "priority": 7, "status": "pending"}) + "\n")
        print(f"    Tasks seeded: 3")

        # SETUP: Seed events
        print("[3] SEEDING: Writing test events (simulating yesterday)")
        events_path = tasks_dir / "events.jsonl"
        with open(events_path, "w") as f:
            f.write(json.dumps({"event_type": "engram_written", "emitter": "brain_write_engram", "timestamp": datetime.now().isoformat(), "data": {"key": "db_choice"}}) + "\n")
            f.write(json.dumps({"event_type": "task_claimed", "emitter": "brain_claim_task", "timestamp": datetime.now().isoformat(), "data": {"task_id": "T001"}}) + "\n")
        print(f"    Events seeded: 2")

        # TEST: Retrieve top engrams
        print("\n[4] TEST: Retrieve top engrams")
        mem = _retrieve_top_engrams(brain)
        print(f"    Count: {mem['count']}, Showing: {mem['showing']}")
        assert mem["count"] == 3, f"Expected 3 engrams, got {mem['count']}"
        # Check scoring: no_openai (intensity 10) should be first
        assert mem["engrams"][0]["key"] == "no_openai", f"Expected no_openai first, got {mem['engrams'][0]['key']}"

        # TEST: Retrieve tasks
        print("[5] TEST: Retrieve tasks")
        tasks = _retrieve_tasks(brain)
        print(f"    In-progress: {len(tasks['in_progress'])}, Pending: {len(tasks['pending'])}")
        assert len(tasks["in_progress"]) == 1
        assert len(tasks["pending"]) == 2

        # TEST: Retrieve yesterday
        print("[6] TEST: Retrieve yesterday's events")
        yesterday = _retrieve_yesterday(brain)
        print(f"    Events: {yesterday['count']}")
        assert yesterday["count"] == 2

        # TEST: Generate recommendation
        print("[7] TEST: Generate recommendation")
        sections = {"memory": mem, "tasks": tasks, "yesterday": yesterday}
        rec = _generate_recommendation(sections)
        print(f"    Action: {rec['action']}")
        print(f"    Task: {rec['task']}")
        assert rec["action"] == "CONTINUE", f"Expected CONTINUE (has in-progress), got {rec['action']}"
        assert "morning_brief" in rec["task"].lower() or "T001" in str(rec.get("task_id", ""))

        # TEST: Full brief generation (monkey-patch get_brain_path)
        print("[8] TEST: Full Morning Brief generation")
        import mcp_server_nucleus.runtime.morning_brief_ops as mb
        original_import = mb.__builtins__ if hasattr(mb, '__builtins__') else None

        # Direct call with brain path override
        import mcp_server_nucleus.runtime.common as common
        original_get_brain = common.get_brain_path
        common.get_brain_path = lambda: brain

        try:
            result = _morning_brief_impl()
            formatted = result.get("formatted", "")
            print(f"    Generated in: {result['meta']['generation_time_ms']}ms")
            assert "NUCLEUS MORNING BRIEF" in formatted
            assert "no_openai" in formatted
            assert "CONTINUE" in formatted
            print(f"\n{'='*60}")
            print(formatted)
            print(f"{'='*60}")
        finally:
            common.get_brain_path = original_get_brain

        print("\n✅ Morning Brief Verification SUCCESS: All 8 checks passed.")


if __name__ == "__main__":
    verify_morning_brief()
