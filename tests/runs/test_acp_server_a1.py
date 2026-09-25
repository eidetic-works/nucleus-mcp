"""ACP stdio server integration tests for nucleus-acp."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.store import RunStore


@pytest.fixture
def brain_tmp(tmp_path: Path) -> Path:
    brain = tmp_path / "brain"
    brain.mkdir(parents=True, exist_ok=True)
    return brain


async def _write_message(proc: asyncio.subprocess.Process, msg: dict) -> None:
    line = json.dumps(msg) + "\n"
    proc.stdin.write(line.encode())
    await proc.stdin.drain()


async def _read_response(proc: asyncio.subprocess.Process, req_id: int, timeout: float = 10.0) -> dict:
    while True:
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
        if not line:
            raise RuntimeError("server closed stdout while waiting for response")
        text = line.decode().strip()
        if not text:
            continue
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict) and msg.get("id") == req_id:
            return msg
        # notifications and other traffic are ignored


@pytest.mark.asyncio
async def test_acp_server_lifecycle(brain_tmp: Path) -> None:
    # Pre-create the project root with a valid trust mode so session/new
    # does not pause for a trust-mode approval.
    with RunStore(str(brain_tmp / "runs" / "store.sqlite")) as store:
        store.create_project(str(brain_tmp), "default")

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain_tmp)

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "mcp_server_nucleus.runs.acp_server",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    try:
        cwd = str(brain_tmp)

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": 1,
                    "clientInfo": {"name": "test", "version": "0.1"},
                    "mcpServers": [],
                },
            },
        )
        init = await _read_response(proc, 1)
        assert init["result"]["protocolVersion"] == 1
        assert init["result"]["agentInfo"]["name"] == "nucleus-acp"

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "session/new",
                "params": {
                    "cwd": cwd,
                    "mcpServers": [],
                    "_meta": {"prompt": "Hello Nucleus"},
                },
            },
        )
        new = await _read_response(proc, 2)
        session_id = new["result"]["sessionId"]
        assert session_id

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "session/list",
                "params": {"cwd": cwd},
            },
        )
        listed = await _read_response(proc, 3)
        ids = [s["sessionId"] for s in listed["result"]["sessions"]]
        assert session_id in ids

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "session/load",
                "params": {
                    "cwd": cwd,
                    "sessionId": session_id,
                    "mcpServers": [],
                },
            },
        )
        loaded = await _read_response(proc, 4)
        assert loaded["result"]["_meta"]["session_id"] == session_id

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "method": "session/cancel",
                "params": {"sessionId": session_id},
            },
        )
        await asyncio.sleep(0.1)

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "session/load",
                "params": {
                    "cwd": cwd,
                    "sessionId": session_id,
                    "mcpServers": [],
                },
            },
        )
        cancelled = await _read_response(proc, 5)
        assert cancelled["result"]["_meta"]["state"] == "cancelled"
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()
