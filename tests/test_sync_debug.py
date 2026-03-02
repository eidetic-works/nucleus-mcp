import sys
import os
import json
import traceback

sys.path.insert(0, "./src")
os.environ["NUCLEAR_BRAIN_PATH"] = "/path/to/your/project/.brain"

from mcp_server_nucleus.tools.sync import register

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
    "get_brain_path": lambda: "/path/to/your/project/.brain"
}

mcp = MockMCP()
tools = register(mcp, helpers)
nucleus_sync_tool = tools[0][1]

def run_test(action, params):
    print(f"\n--- Testing action: {action} ---")
    try:
        res = nucleus_sync_tool(action, params)
        if isinstance(res, str):
            res = json.loads(res)
        if "error" in res and res["error"] is not None:
            print(f"SUCCESS: False\nERROR: {res['error']}")
        else:
            print(f"SUCCESS: True")
    except Exception as e:
        print(f"CRASH: {e}")
        traceback.print_exc()

run_test("identify_agent", {"agent_id": "test_agent", "environment": "dev"})
run_test("sync_status", {})
run_test("sync_now", {})
# sync_auto writes to gitignore, so we pass
run_test("sync_auto", {"enable": False})
run_test("sync_resolve", {"file_path": "fake.json"})
run_test("read_artifact", {"path": "dummy.md"})
run_test("write_artifact", {"path": "dummy.md", "content": "mock"})
run_test("list_artifacts", {})
run_test("trigger_agent", {"agent": "test_agent", "task_description": "mock"})
run_test("get_triggers", {})
run_test("evaluate_triggers", {"event_type": "TEST", "emitter": "test"})
run_test("start_deploy_poll", {"service_id": "srv-123"})
run_test("check_deploy", {"service_id": "srv-123"})
run_test("complete_deploy", {"service_id": "srv-123", "success": True})
run_test("smoke_test", {"url": "http://localhost"})

print("\nAll 15 sync tools tested!")
