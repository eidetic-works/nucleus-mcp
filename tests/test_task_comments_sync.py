"""Tests for task_comment_add and task_comment_list via nucleus_sync tool."""
import json
import pytest

@pytest.fixture
def temp_brain(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    return str(tmp_path)

@pytest.mark.anyio
async def test_task_comments_via_sync(temp_brain):
    from mcp_server_nucleus.tools.sync import register
    
    class MockMCP:
        def tool(self, title=None, annotations=None):
            def decorator(func):
                return func
            return decorator
            
    mock_mcp = MockMCP()
    tools = register(mock_mcp, {
        "make_response": lambda *args, **kwargs: None,
        "emit_event": lambda *args, **kwargs: None,
        "get_state": lambda *args, **kwargs: {},
        "set_state": lambda *args, **kwargs: None,
        "get_brain_path": lambda *args, **kwargs: temp_brain
    })
    
    sync_tool = dict(tools)["nucleus_sync"]
    
    # Post a comment
    task_id = "test_comment_task"
    post_res_str = await sync_tool(
        action="task_comment_add",
        params={
            "task_id": task_id,
            "message": "This is a test comment via sync",
            "sender": "principal"
        }
    )
    post_res = json.loads(post_res_str)
    assert post_res.get("message_id") is not None
    assert post_res.get("subject") == f"[task-comment] {task_id}"
    
    # List comments
    list_res_str = await sync_tool(
        action="task_comment_list",
        params={
            "task_id": task_id
        }
    )
    list_res = json.loads(list_res_str)
    assert list_res["count"] == 1
    assert len(list_res["messages"]) == 1
    assert list_res["messages"][0]["body"] == "This is a test comment via sync"
    assert list_res["messages"][0]["from"] == "principal"
