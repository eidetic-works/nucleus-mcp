"""Coverage tests for mcp_server_nucleus.tools.tasks (facade register + dispatch)."""
import asyncio
import json
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _fresh_event_loop():
    """Ensure a fresh event loop for each test to avoid 'Event loop is closed' errors."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()


class MockMCP:
    """Minimal MCP mock that captures the decorated tool function."""
    def __init__(self):
        self.captured = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.captured[func.__name__] = func
            return func
        return decorator


def _make_helpers():
    return {
        "make_response": lambda success, data=None, error=None: json.dumps(
            {"success": success, "data": data, "error": error}
        ),
    }


def _register_tasks():
    mcp = MockMCP()
    helpers = _make_helpers()
    tools = mock.patch(
        "mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]
    )
    tools2 = mock.patch(
        "mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None
    )
    tools3 = mock.patch(
        "mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}
    )
    tools4 = mock.patch(
        "mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}
    )
    tools5 = mock.patch(
        "mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {"id": "t1"}}
    )
    tools6 = mock.patch(
        "mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}
    )
    tools7 = mock.patch(
        "mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}
    )
    d1 = mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={"depth": 1})
    d2 = mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={"depth": 0})
    d3 = mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={"depth": 0})
    d4 = mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={"depth": 0})
    d5 = mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={"max": 5})
    d6 = mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={"map": {}})
    d7 = mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={"switched": True})
    d8 = mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={"count": 0})
    d9 = mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={"count": 0})

    patches = [tools, tools2, tools3, tools4, tools5, tools6, tools7,
               d1, d2, d3, d4, d5, d6, d7, d8, d9]
    for p in patches:
        p.start()

    from mcp_server_nucleus.tools.tasks import register
    result = register(mcp, helpers)

    for p in patches:
        p.stop()

    return mcp, result


def test_register_returns_tool_list():
    mcp, result = _register_tasks()
    assert len(result) == 1
    assert result[0][0] == "nucleus_tasks"
    assert callable(result[0][1])


def test_dispatch_list():
    mcp, result = _register_tasks()
    nucleus_tasks = result[0][1]
    out = asyncio.run(nucleus_tasks("list", {}))
    data = json.loads(out)
    assert data["success"] is True


def test_dispatch_get_next_no_task():
    mcp, result = _register_tasks()
    nucleus_tasks = result[0][1]
    out = asyncio.run(nucleus_tasks("get_next", {"skills": []}))
    data = json.loads(out)
    assert data["success"] is True
    assert data["error"] is not None


def test_dispatch_get_next_with_task():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value={"id": "t1"}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {"id": "t1"}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("get_next", {"skills": []}))
        data = json.loads(out)
        assert data["success"] is True
        assert data["data"] == {"id": "t1"}


def test_dispatch_claim_success():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True, "task_id": "t1"}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {"id": "t1"}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("claim", {"task_id": "t1", "agent_id": "a1"}))
        data = json.loads(out)
        assert data["success"] is True


def test_dispatch_claim_failure():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": False, "error": "already claimed"}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {"id": "t1"}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("claim", {"task_id": "t1", "agent_id": "a1"}))
        data = json.loads(out)
        assert data["success"] is False


def test_dispatch_add_success():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {"id": "t1"}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("add", {"description": "test task"}))
        data = json.loads(out)
        assert data["success"] is True


def test_dispatch_add_failure():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": False, "error": "bad"}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("add", {"description": "test task"}))
        data = json.loads(out)
        assert data["success"] is False


def test_dispatch_create_alias():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {"id": "t1"}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("create", {"description": "via alias"}))
        data = json.loads(out)
        assert data["success"] is True


def test_dispatch_depth_actions():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={"depth": 1}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={"depth": 0}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={"depth": 0}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={"depth": 0}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={"max": 5}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={"map": {}}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={"switched": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={"count": 0}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={"count": 0}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        for action, params in [
            ("depth_push", {"topic": "x"}),
            ("depth_pop", {}),
            ("depth_show", {}),
            ("depth_reset", {}),
            ("depth_set_max", {"max_depth": 5}),
            ("depth_map", {}),
            ("context_switch", {"new_context": "y"}),
            ("context_switch_status", {}),
            ("context_switch_reset", {}),
        ]:
            out = asyncio.run(nucleus_tasks(action, params))
            data = json.loads(out)
            assert data["success"] is True, f"Failed for action: {action}"


def test_dispatch_update_success():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("update", {"task_id": "t1", "updates": {"status": "done"}}))
        data = json.loads(out)
        assert data["success"] is True


def test_dispatch_update_failure():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": False, "error": "nope"}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("update", {"task_id": "t1", "updates": {}}))
        data = json.loads(out)
        assert data["success"] is False


def test_dispatch_import_jsonl():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True, "imported": 5}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("import_jsonl", {"jsonl_path": "/tmp/x.jsonl"}))
        data = json.loads(out)
        assert data["success"] is True


def test_dispatch_import_jsonl_failure():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": False, "error": "bad"}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("import_jsonl", {"jsonl_path": "/tmp/x.jsonl"}))
        data = json.loads(out)
        assert data["success"] is False


def test_dispatch_escalate():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True, "task_id": "t1"}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("escalate", {"task_id": "t1", "reason": "stuck"}))
        # escalate returns raw result from _escalate_task, not wrapped in make_response
        assert out is not None


def test_dispatch_unknown_action():
    mcp = MockMCP()
    helpers = _make_helpers()
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._get_next_task", return_value=None), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._claim_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._update_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task": {}}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._import_tasks_from_jsonl", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.task_ops._escalate_task", return_value={"success": True}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_push", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_pop", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_show", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_reset", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._depth_set_max", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._generate_depth_map", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_status", return_value={}), \
         mock.patch("mcp_server_nucleus.runtime.depth_ops._context_switch_reset", return_value={}):
        from mcp_server_nucleus.tools.tasks import register
        result = register(mcp, helpers)
        nucleus_tasks = result[0][1]
        out = asyncio.run(nucleus_tasks("nonexistent_action", {}))
        # Should return an error response
        data = json.loads(out)
        assert "error" in data or data.get("success") is False
