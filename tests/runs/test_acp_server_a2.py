"""ACP stdio server A2 tests for session/prompt with streaming updates."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mcp_server_nucleus.runs.store import RunStore


@pytest.fixture
def brain_tmp(tmp_path: Path) -> Path:
    brain = tmp_path / "brain"
    brain.mkdir(parents=True, exist_ok=True)
    return brain


def _git_init(path: Path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@test.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, check=True)
    (path / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def _install_fake_agy(tmp_path: Path, script: str) -> Path:
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    script_path = bindir / "agy"
    script_path.write_text("#!/bin/sh\n" + script)
    script_path.chmod(0o755)
    return bindir


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


async def _drain_notifications(proc: asyncio.subprocess.Process, session_id: str, timeout: float = 20.0):
    """Read session/update notifications for *session_id* until the stream ends or timeout."""
    end = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < end:
        remaining = end - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=max(0.5, remaining))
        except asyncio.TimeoutError:
            break
        if not line:
            break
        text = line.decode().strip()
        if not text:
            continue
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(msg, dict):
            continue
        if msg.get("method") == "session/update" and msg.get("params", {}).get("sessionId") == session_id:
            yield msg


async def _wait_for_terminal_state(
    proc: asyncio.subprocess.Process,
    session_id: str,
    terminal_states: set[str],
    timeout: float = 20.0,
) -> dict:
    async for note in _drain_notifications(proc, session_id, timeout=timeout):
        update = note.get("params", {}).get("update", {})
        meta = update.get("_meta") or update.get("field_meta") or {}
        state = meta.get("state")
        if state in terminal_states:
            return note
    raise RuntimeError(f"timed out waiting for terminal state in {terminal_states}")


@pytest.mark.asyncio
async def test_session_prompt_runs_to_completion(brain_tmp: Path) -> None:
    project = brain_tmp / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _install_fake_agy(
        brain_tmp,
        'cat > /dev/null\necho changed > out.txt\necho done\nexit 0\n',
    )

    # Pre-create the project with a valid trust mode so the prompt flow
    # can create a run without pausing for trust approval.
    with RunStore(str(brain_tmp / "runs" / "store.sqlite")) as store:
        store.create_project(str(project), "default")

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain_tmp)
    env["PATH"] = f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}"

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

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "session/prompt",
                "params": {
                    "sessionId": "new",
                    "prompt": [{"type": "text", "text": "write a file"}],
                    "_meta": {"cwd": str(project)},
                },
            },
        )
        response = await _read_response(proc, 2)
        session_id = response["result"]["_meta"]["session_id"]
        assert session_id

        terminal = {"completed", "ready_for_review", "failed", "cancelled"}
        final = await _wait_for_terminal_state(proc, session_id, terminal, timeout=20.0)
        meta = final["params"]["update"]["_meta"]
        assert meta["state"] in ("completed", "ready_for_review"), meta["state"]

        run = response["result"]["_meta"].get("run") or {}
        assert run.get("events", 0) > 0 or meta.get("result", {}).get("events", 0) > 0
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_session_prompt_cancellation(brain_tmp: Path) -> None:
    project = brain_tmp / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _install_fake_agy(
        brain_tmp,
        'cat > /dev/null\nfor i in $(seq 1 40); do echo "line $i"; sleep 0.2; done\necho done\nexit 0\n',
    )

    # Pre-create the project with a valid trust mode so the prompt flow
    # can create a run without pausing for trust approval.
    with RunStore(str(brain_tmp / "runs" / "store.sqlite")) as store:
        store.create_project(str(project), "default")

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain_tmp)
    env["PATH"] = f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}"

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
        await _read_response(proc, 1)

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "session/prompt",
                "params": {
                    "sessionId": "new",
                    "prompt": [{"type": "text", "text": "count"}],
                    "_meta": {"cwd": str(project)},
                },
            },
        )
        response = await _read_response(proc, 2)
        session_id = response["result"]["_meta"]["session_id"]

        running = {"running"}
        await _wait_for_terminal_state(proc, session_id, running, timeout=10.0)

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "method": "session/cancel",
                "params": {"sessionId": session_id},
            },
        )

        final = await _wait_for_terminal_state(proc, session_id, {"cancelled"}, timeout=15.0)
        meta = final["params"]["update"]["_meta"]
        assert meta["state"] == "cancelled"
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()
