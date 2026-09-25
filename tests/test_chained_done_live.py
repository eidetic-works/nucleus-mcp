import asyncio
from pathlib import Path
import pytest
from mcp_server_nucleus.tools.tasks import register
from mcp_server_nucleus.runtime.relay.core import relay_post
from unittest.mock import MagicMock
import json

def make_response(success, data=None, error=None):
    resp = {"success": success}
    if data is not None:
        resp["data"] = data
    if error is not None:
        resp["error"] = error
    return resp

class _RecordingCtx:
    def __init__(self):
        self.session_id = "test-session"
        self.warnings = []
    @property
    def session_id_attr(self):
        return self.session_id
    async def warning(self, msg: str) -> None:
        self.warnings.append(msg)

def test_chained_done_live(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Set up brain path
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(tmp_path / ".brain" / "relay_state"))
    monkeypatch.setenv("NUCLEUS_SESSION_ROLE", "role_test_role")
    
    # Initialize the tools
    tools_registered = {}
    mock_mcp = MagicMock()
    
    def mock_tool(**kwargs):
        def decorator(func):
            tools_registered[func.__name__] = func
            return func
        return decorator
        
    mock_mcp.tool = mock_tool
    helpers = {"emit_event": MagicMock(), "get_brain_path": MagicMock(), "make_response": make_response}
    register(mock_mcp, helpers)
    
    nucleus_tasks = tools_registered["nucleus_tasks"]
    ctx = _RecordingCtx()

    async def run_test():
        # Add a task first
        add_result_str = await nucleus_tasks(
            action="add",
            params={
                "task_id": "chained_test_task",
                "description": "A test task",
                "required_role": "test_role"
            }
        )
        add_result = json.loads(add_result_str)
        assert add_result.get("success") is True
        
        # Post a message so there's a next message in the inbox
        relay_post(
            to="role_test_role",
            subject="Next Task Message",
            body="Do the next thing.",
            sender="test_sender",
            force_fs=True
        )
        
        # Now mark the task as DONE
        done_result_str = await nucleus_tasks(
            action="update",
            params={
                "task_id": "chained_test_task",
                "updates": {"status": "DONE"}
            }
        )
        done_result = json.loads(done_result_str)
        
        assert done_result.get("success") is True
        # Verify the chained response includes next_message
        assert "next_message" in done_result["data"]
        assert done_result["data"]["next_message"] is not None
        # The next_message is the first unread message in the inbox.
        # This could be the task notification [TASK] or the manually posted
        # "Next Task Message" — both are valid. Just verify it's a real message.
        assert "subject" in done_result["data"]["next_message"]
        
    asyncio.run(run_test())
