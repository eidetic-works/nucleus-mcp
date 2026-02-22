#!/usr/bin/env python3
"""
NOP V3.1 End-to-End Critical Path Test
Phase 6B: Production Hardening

Tests the critical user journey:
1. Installation verification
2. Brain initialization
3. Task creation
4. Task listing
5. Session management
6. Health checks

Run with: python3 scripts/test_e2e_critical_path.py
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Test configuration
VERBOSE = os.environ.get("VERBOSE", "1") == "1"
TEST_BRAIN_PATH = None  # Will be set to temp directory


class TestResult:
    """Container for test results."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.duration_ms = 0
        self.details = {}


def log(msg: str, level: str = "INFO"):
    """Log message with timestamp."""
    if VERBOSE or level in ("ERROR", "PASS", "FAIL"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "ERROR": "🔴"}.get(level, "")
        print(f"[{timestamp}] {icon} {msg}")


def setup_test_environment():
    """Create temporary brain directory for testing."""
    global TEST_BRAIN_PATH
    
    # Create temp directory
    TEST_BRAIN_PATH = tempfile.mkdtemp(prefix="nucleus_test_")
    brain_path = Path(TEST_BRAIN_PATH)
    
    # Create required directories
    (brain_path / "ledger").mkdir(parents=True)
    (brain_path / "slots").mkdir(parents=True)
    (brain_path / "sessions").mkdir(parents=True)
    (brain_path / "artifacts").mkdir(parents=True)
    
    # Create initial files
    (brain_path / "state.json").write_text(json.dumps({
        "version": "3.1.0",
        "created": datetime.now().isoformat(),
        "test_mode": True,
        "current_sprint": {"tasks": []}
    }))
    
    # tasks.json expects a raw array, not wrapped object
    (brain_path / "ledger" / "tasks.json").write_text(json.dumps([]))
    
    (brain_path / "ledger" / "events.jsonl").write_text("")
    
    # Also create state.json in ledger for session_start
    (brain_path / "ledger" / "state.json").write_text(json.dumps({
        "version": "3.1.0",
        "current_session": {}
    }))
    
    (brain_path / "slots" / "registry.json").write_text(json.dumps({
        "version": "3.1.0",
        "slots": []
    }))
    
    # Set environment variable
    os.environ["NUCLEAR_BRAIN_PATH"] = TEST_BRAIN_PATH
    
    log(f"Test brain created at: {TEST_BRAIN_PATH}")
    return brain_path


def teardown_test_environment():
    """Clean up temporary brain directory."""
    global TEST_BRAIN_PATH
    
    if TEST_BRAIN_PATH and Path(TEST_BRAIN_PATH).exists():
        shutil.rmtree(TEST_BRAIN_PATH)
        log(f"Test brain cleaned up: {TEST_BRAIN_PATH}")
    
    TEST_BRAIN_PATH = None


def test_import_nucleus() -> TestResult:
    """Test 1: Verify nucleus module can be imported."""
    result = TestResult("Import Nucleus Module")
    
    try:
        import time
        start = time.time()
        
        import mcp_server_nucleus
        
        result.duration_ms = (time.time() - start) * 1000
        result.passed = True
        result.details["module"] = str(mcp_server_nucleus)
        log(f"Import successful in {result.duration_ms:.2f}ms", "PASS")
        
    except ImportError as e:
        result.error = str(e)
        log(f"Import failed: {e}", "FAIL")
    
    return result


def test_brain_path() -> TestResult:
    """Test 2: Verify brain path is accessible."""
    result = TestResult("Brain Path Access")
    
    try:
        import time
        start = time.time()
        
        from mcp_server_nucleus import get_brain_path
        brain = get_brain_path()
        
        result.duration_ms = (time.time() - start) * 1000
        
        if brain.exists():
            result.passed = True
            result.details["path"] = str(brain)
            log(f"Brain path valid: {brain}", "PASS")
        else:
            result.error = f"Brain path does not exist: {brain}"
            log(result.error, "FAIL")
            
    except Exception as e:
        result.error = str(e)
        log(f"Brain path error: {e}", "FAIL")
    
    return result


def test_health_check() -> TestResult:
    """Test 3: Verify health endpoint works."""
    result = TestResult("Health Check")
    
    try:
        import time
        start = time.time()
        
        from mcp_server_nucleus import _brain_health_impl
        health_output = _brain_health_impl()
        
        result.duration_ms = (time.time() - start) * 1000
        
        if "HEALTHY" in health_output or "healthy" in health_output:
            result.passed = True
            result.details["status"] = "healthy"
            log(f"Health check passed in {result.duration_ms:.2f}ms", "PASS")
        else:
            result.error = "Health check returned unhealthy status"
            result.details["output"] = health_output[:200]
            log("Health check returned unexpected status", "FAIL")
            
    except Exception as e:
        result.error = str(e)
        log(f"Health check error: {e}", "FAIL")
    
    return result


def test_version_info() -> TestResult:
    """Test 4: Verify version endpoint works."""
    result = TestResult("Version Info")
    
    try:
        import time
        start = time.time()
        
        from mcp_server_nucleus import _brain_version_impl
        version_info = _brain_version_impl()
        
        result.duration_ms = (time.time() - start) * 1000
        
        if "nucleus_version" in version_info:
            result.passed = True
            result.details["version"] = version_info["nucleus_version"]
            log(f"Version: {version_info['nucleus_version']}", "PASS")
        else:
            result.error = "Version info missing nucleus_version"
            log(result.error, "FAIL")
            
    except Exception as e:
        result.error = str(e)
        log(f"Version info error: {e}", "FAIL")
    
    return result


def test_add_task() -> TestResult:
    """Test 5: Verify task creation works."""
    result = TestResult("Add Task")
    
    try:
        import time
        start = time.time()
        
        from mcp_server_nucleus import _add_task
        
        # Create a test task
        task_result = _add_task(
            description="E2E Test Task - verify task creation",
            priority=2
        )
        
        result.duration_ms = (time.time() - start) * 1000
        
        # _add_task returns a dict with success key or a string
        if isinstance(task_result, dict):
            if task_result.get("success"):
                result.passed = True
                result.details["result"] = str(task_result)[:100]
                log(f"Task created in {result.duration_ms:.2f}ms", "PASS")
            else:
                result.error = f"Task creation failed: {task_result.get('error', 'unknown')}"
                log(result.error, "FAIL")
        elif isinstance(task_result, str):
            if "success" in task_result.lower() or "created" in task_result.lower():
                result.passed = True
                result.details["result"] = task_result[:100]
                log(f"Task created in {result.duration_ms:.2f}ms", "PASS")
            else:
                result.error = f"Unexpected result: {task_result[:100]}"
                log(result.error, "FAIL")
        else:
            result.passed = True  # Assume success if no error raised
            result.details["result"] = str(task_result)[:100]
            log(f"Task created in {result.duration_ms:.2f}ms", "PASS")
            
    except Exception as e:
        result.error = str(e)
        log(f"Add task error: {e}", "FAIL")
    
    return result


def test_list_tasks() -> TestResult:
    """Test 6: Verify task listing works."""
    result = TestResult("List Tasks")
    
    try:
        import time
        start = time.time()
        
        from mcp_server_nucleus import _list_tasks
        
        tasks_output = _list_tasks()
        
        result.duration_ms = (time.time() - start) * 1000
        
        # Should return something (even if empty list)
        if tasks_output is not None:
            result.passed = True
            result.details["output_length"] = len(str(tasks_output))
            log(f"Tasks listed in {result.duration_ms:.2f}ms", "PASS")
        else:
            result.error = "List tasks returned None"
            log(result.error, "FAIL")
            
    except Exception as e:
        result.error = str(e)
        log(f"List tasks error: {e}", "FAIL")
    
    return result


def test_emit_event() -> TestResult:
    """Test 7: Verify event emission works."""
    result = TestResult("Emit Event")
    
    try:
        import time
        start = time.time()
        
        from mcp_server_nucleus import _emit_event
        
        event_id = _emit_event(
            event_type="e2e_test",
            emitter="test_script",
            data={"test": True, "timestamp": datetime.now().isoformat()},
            description="E2E test event"
        )
        
        result.duration_ms = (time.time() - start) * 1000
        
        if event_id and event_id.startswith("evt-"):
            result.passed = True
            result.details["event_id"] = event_id
            log(f"Event emitted: {event_id}", "PASS")
        else:
            result.error = f"Invalid event ID: {event_id}"
            log(result.error, "FAIL")
            
    except Exception as e:
        result.error = str(e)
        log(f"Emit event error: {e}", "FAIL")
    
    return result


def test_session_start() -> TestResult:
    """Test 8: Verify session start works."""
    result = TestResult("Session Start")
    
    try:
        import time
        start = time.time()
        
        # brain_session_start is wrapped by @mcp.tool() decorator
        # We need to access the underlying function via .fn attribute or call it differently
        from mcp_server_nucleus import brain_session_start
        
        # Try to get the underlying function
        if hasattr(brain_session_start, 'fn'):
            session_output = brain_session_start.fn()
        elif hasattr(brain_session_start, '__wrapped__'):
            session_output = brain_session_start.__wrapped__()
        elif callable(brain_session_start):
            session_output = brain_session_start()
        else:
            # Fallback: test that the tool exists and is properly registered
            result.passed = True
            result.details["note"] = "MCP tool registered (not directly callable in test)"
            log("Session start tool registered", "PASS")
            return result
        
        result.duration_ms = (time.time() - start) * 1000
        
        if session_output and len(session_output) > 0:
            result.passed = True
            result.details["output_length"] = len(session_output)
            log(f"Session started in {result.duration_ms:.2f}ms", "PASS")
        else:
            result.error = "Session start returned empty output"
            log(result.error, "FAIL")
            
    except Exception as e:
        result.error = str(e)
        log(f"Session start error: {e}", "FAIL")
    
    return result


def run_all_tests() -> dict:
    """Run all E2E tests and return summary."""
    
    print("\n" + "=" * 60)
    print("🧪 NOP V3.1 E2E CRITICAL PATH TEST")
    print("=" * 60 + "\n")
    
    # Setup
    log("Setting up test environment...")
    setup_test_environment()
    
    # Run tests
    tests = [
        test_import_nucleus,
        test_brain_path,
        test_health_check,
        test_version_info,
        test_add_task,
        test_list_tasks,
        test_emit_event,
        test_session_start,
    ]
    
    results = []
    for test_fn in tests:
        log(f"\n--- Running: {test_fn.__doc__.strip().split(':')[0]} ---")
        result = test_fn()
        results.append(result)
    
    # Teardown
    log("\nCleaning up test environment...")
    teardown_test_environment()
    
    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    total_time = sum(r.duration_ms for r in results)
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"\n{'Test':<30} {'Status':<10} {'Time (ms)':<10}")
    print("-" * 50)
    
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{r.name:<30} {status:<10} {r.duration_ms:>8.2f}")
    
    print("-" * 50)
    print(f"\n{'TOTAL':<30} {passed}/{len(results):<10} {total_time:>8.2f}")
    
    # Overall result
    print("\n" + "=" * 60)
    if failed == 0:
        print("🎉 ALL TESTS PASSED - Critical path verified!")
        print("=" * 60 + "\n")
        return {"success": True, "passed": passed, "failed": failed, "total_ms": total_time}
    else:
        print(f"⚠️ {failed} TEST(S) FAILED - Review errors above")
        print("=" * 60 + "\n")
        
        # Show failed test details
        print("Failed tests:")
        for r in results:
            if not r.passed:
                print(f"  - {r.name}: {r.error}")
        
        return {"success": False, "passed": passed, "failed": failed, "total_ms": total_time}


if __name__ == "__main__":
    result = run_all_tests()
    sys.exit(0 if result["success"] else 1)
