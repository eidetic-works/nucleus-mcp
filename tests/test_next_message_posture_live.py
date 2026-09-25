import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from mcp_server_nucleus.tools.sync import register

from mcp_server_nucleus.runtime.posture import declare_posture, approve_posture
from mcp_server_nucleus.runtime.relay.core import relay_post

# We need a small helper to mock make_response since it's a helper passed in MCP registration
def make_response(success, data=None, error=None):
    if success:
        return json.dumps({"success": True, "data": data})
    return json.dumps({"success": False, "error": error})

class _RecordingCtx:
    def __init__(self):
        pass
    async def info(self, msg):
        pass
    async def error(self, msg):
        pass
    async def warning(self, msg):
        pass
    async def debug(self, msg):
        pass

def test_next_message_posture_live(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Set up brain path
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(tmp_path / ".brain" / "relay_state"))
    monkeypatch.delenv("NUCLEUS_SESSION_ROLE", raising=False) # Ensure no explicit override
    
    # Set posture (auto-detect should use this)
    declare_posture(role="peer", approach="execute", agent_id="posture_role")
    approve_posture()

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

    nucleus_next_message = tools_registered["nucleus_next_message"]

    async def run_test():
        # Post a message directly to posture_role
        relay_post(
            to="posture_role",
            subject="Posture Test Message",
            body="Checking if posture works",
            sender="test_sender",
            force_fs=True
        )

        # Call next_message. It should pick up the message from role_posture_role
        next_res = await nucleus_next_message(ctx=_RecordingCtx())
        
        msg = next_res.get("message")
        assert msg is not None
        assert msg["subject"] == "Posture Test Message"

    asyncio.run(run_test())
