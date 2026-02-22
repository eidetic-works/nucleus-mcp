#!/usr/bin/env python3
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.orchestrator_unified import UnifiedOrchestrator
from mcp_server_nucleus.runtime.common import setup_nucleus_logging

def double_check():
    print("=== 🔬 Nucleus Phase 4 Double Check ===")
    
    # 1. Logging Check
    print("\n[1] Logging Test")
    os.environ["NUCLEUS_LOG_JSON"] = "true"
    # Re-initialize logger to pick up env var
    logger = setup_nucleus_logging("check_logger")
    logger.info("This should be a JSON log entry")
    
    # 2. Orchestrator Check
    print("\n[2] Orchestrator Test")
    brain_path = Path("/tmp/nucleus_test_brain")
    brain_path.mkdir(parents=True, exist_ok=True)
    (brain_path / "ledger").mkdir(parents=True, exist_ok=True)
    (brain_path / "swarms").mkdir(parents=True, exist_ok=True)
    
    orch = UnifiedOrchestrator(brain_path=brain_path)
    
    # Add a task
    print("Adding task...")
    res = orch.add_task("Verification task")
    print(f"Result: {res['success']}")
    
    # Check persistence
    tasks_file = brain_path / "ledger" / "tasks.json"
    if tasks_file.exists():
        with open(tasks_file) as f:
            data = json.load(f)
            task_count = len(data.get("tasks", []))
            print(f"Tasks in file: {task_count}")
            if task_count > 0:
                print("✅ Task persistence verified")
            else:
                print("❌ Task not persisted correctly")
    else:
        print("❌ tasks.json not created")

    # 3. Mission Check (Interface)
    print("\n[3] Mission Interface Test")
    if hasattr(orch, 'start_mission'):
        print("✅ UnifiedOrchestrator.start_mission exists")
    else:
        print("❌ UnifiedOrchestrator.start_mission MISSING")

    print("\n=== Double Check Complete ===")

if __name__ == "__main__":
    double_check()
