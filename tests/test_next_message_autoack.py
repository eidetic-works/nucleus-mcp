from mcp_server_nucleus.runtime.stdio_server import make_response
import asyncio
import pytest
from pathlib import Path

from mcp_server_nucleus.tools.sync import register
from mcp_server_nucleus.runtime.relay.core import relay_post, relay_inbox
from unittest.mock import MagicMock

class _RecordingCtx:
    """Async-compatible Context stub that records info/warning calls."""
    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []

    async def info(self, msg: str) -> None:
        self.infos.append(msg)

    async def warning(self, msg: str) -> None:
        self.warnings.append(msg)

def test_nucleus_next_message_autoacks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Set up brain path
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    
    # Post a message to a test recipient
    post_res = relay_post(
        to="test_role",
        subject="Autoack Test",
        body="Does it auto-ack?",
        sender="test_sender",
        force_fs=True
    )
    assert post_res["sent"] is True
    
    # Verify the message is unread in the inbox
    inbox_before = relay_inbox(unread_only=True, recipient="test_role", force_fs=True)
    assert inbox_before["count"] == 1
    
    ctx = _RecordingCtx()
    
    mcp = MagicMock()
    tools_registered = {}
    
    def mock_tool(**kwargs):
        def decorator(func):
            tools_registered[func.__name__] = func
            return func
        return decorator
    
    mcp.tool = mock_tool
    helpers = {"emit_event": MagicMock(), "get_brain_path": MagicMock(), "make_response": make_response}
    register(mcp, helpers)
    
    nucleus_next_message = tools_registered["nucleus_next_message"]

    async def run_tool():
        return await nucleus_next_message(
            ctx,
            recipient="test_role"
        )
        
    result = asyncio.run(run_tool())
    
    # Assert it returned the message and auto-acked
    assert result["message"] is not None
    assert result["message"]["subject"] == "Autoack Test"
    assert result["acked"] is True
    
    # Verify the inbox is now empty (no unread messages)
    inbox_after = relay_inbox(unread_only=True, recipient="test_role", force_fs=True)
    assert inbox_after["count"] == 0
