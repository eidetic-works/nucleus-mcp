import sys
import os
import json
import traceback

sys.path.insert(0, "./src")

# Force brain path for native execution
os.environ["NUCLEAR_BRAIN_PATH"] = "/Users/lokeshgarg/ai-mvp-backend/.brain"

from mcp_server_nucleus.tools.tasks import register

class MockMCP:
    def tool(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

helpers = {
    "make_response": lambda success, data=None, error=None: {"success": success, "data": data, "error": error},
    "emit_event": lambda *args, **kwargs: "evt-123",
    "read_events": lambda *args: [],
    "get_state": lambda *args: {},
    "update_state": lambda *args: None,
    "get_brain_path": lambda: "/Users/lokeshgarg/ai-mvp-backend/.brain"
}

mcp = MockMCP()
tools = register(mcp, helpers)
nucleus_tasks_tool = tools[0][1]

def run_test(action, params):
    print(f"\n--- Testing action: {action} ---")
    try:
        res = nucleus_tasks_tool(action, params)
        if isinstance(res, str):
            res = json.loads(res)
        print(f"SUCCESS: {res.get('success')}")
        if res.get('error'):
            print(f"ERROR: {res.get('error')}")
    except Exception as e:
        print(f"CRASH: {e}")
        traceback.print_exc()

# 1. list
run_test("list", {})

# 2. add
run_test("add", {"description": "QA Swarm Mock Test", "priority": 1, "source": "qa-swarm", "task_id": "task_qa_mock_123"})

# 3. get_next
run_test("get_next", {"skills": ["python"]})

# 4. claim
run_test("claim", {"agent_id": "qa-tester", "task_id": "task_qa_mock_123"})

# 5. update
run_test("update", {"task_id": "task_qa_mock_123", "updates": {"status": "in_progress"}})

# 6. import_jsonl
# skip for file requirement, pass bad path
run_test("import_jsonl", {"jsonl_path": "/tmp/nonexistent.jsonl"})

# 7. escalate
run_test("escalate", {"task_id": "task_qa_mock_123", "reason": "Testing escalation"})

# 8. depth_push
run_test("depth_push", {"topic": "Deep Dive"})

# 9. depth_show
run_test("depth_show", {})

# 10. depth_map
run_test("depth_map", {})

# 11. depth_set_max
run_test("depth_set_max", {"max_depth": 3})

# 12. depth_pop
run_test("depth_pop", {})

# 13. depth_reset
run_test("depth_reset", {})

# 14. context_switch
run_test("context_switch", {"new_context": "Testing ADHD loop"})

# 15. context_switch_status
run_test("context_switch_status", {})

# 16. context_switch_reset
run_test("context_switch_reset", {})

print("\nAll 16 tasks tested!")
