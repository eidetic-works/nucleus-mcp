import asyncio
import json
from pathlib import Path
import pytest

from mcp_server_nucleus.runtime.relay_notify import relay_subscribe_notifications_impl

class _RecordingCtx:
    """Async-compatible Context stub that records info/warning calls."""
    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []

    async def info(self, msg: str) -> None:
        self.infos.append(msg)

    async def warning(self, msg: str) -> None:
        self.warnings.append(msg)

def _write_envelope(dir_: Path, name: str, **fields) -> Path:
    p = dir_ / f"{name}.json"
    p.write_text(json.dumps({"id": name, "from": "test", "subject": "smoke", "read": False, **fields}))
    return p

@pytest.mark.asyncio
async def test_relay_subscribe_surfaces_unread_on_first_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Create an unread relay, then call relay_subscribe — it should fire ctx.info for the unread relay."""
    from mcp_server_nucleus.runtime.relay_notify import _resolve_inbox_dir, relay_subscribe_notifications_impl

    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    monkeypatch.setenv("NUCLEUS_RELAY_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)

    inbox = _resolve_inbox_dir("main")
    inbox.mkdir(parents=True, exist_ok=True)

    # Create an unread relay before subscribing
    envelope = _write_envelope(inbox, "unread_msg", subject="old_unread")
    
    ctx = _RecordingCtx()
    
    # Run the subscription loop for a short time
    sub_task = asyncio.create_task(
        relay_subscribe_notifications_impl(ctx, timeout_seconds=60, role="main")
    )

    # Allow it to scan the directory
    await asyncio.sleep(1.0)
    sub_task.cancel()
    try:
        await sub_task
    except asyncio.CancelledError:
        pass

    arrival_msgs = [m for m in ctx.infos if "[relay-arrival]" in m]
    assert len(arrival_msgs) == 1, f"expected 1 arrival, got: {ctx.infos}"
    assert "unread_msg" in arrival_msgs[0]
    assert "old_unread" in arrival_msgs[0]
