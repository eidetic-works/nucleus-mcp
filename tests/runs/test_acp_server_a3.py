"""ACP stdio server A3 tests for aionui config and e2e session handshake."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import subprocess
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


async def _read_response(proc: asyncio.subprocess.Process, req_id: int, timeout: float = 30.0) -> dict:
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


def test_aionui_config_json() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    config_path = repo_root / ".devin" / "aionui-nucleus-agent.json"
    assert config_path.exists(), config_path
    config = json.loads(config_path.read_text())
    assert config["name"] == "Nucleus"
    assert config["command"] == "nucleus-acp"
    assert config["capabilities"]["prompt"] is True


@pytest.mark.asyncio
async def test_e2e_acp_handshake(brain_tmp: Path) -> None:
    project = brain_tmp / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _install_fake_agy(
        brain_tmp,
        "cat > /dev/null\necho 'hello world' > out.txt\necho done\nexit 0\n",
    )

    # Pre-create the project with a valid trust mode so session/new
    # does not pause for a trust-mode approval.
    with RunStore(str(brain_tmp / "runs" / "store.sqlite")) as store:
        store.create_project(str(project), "default")

    acp_cmd = [sys.executable, "-m", "mcp_server_nucleus.runs.acp_server"]

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain_tmp)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
    env["PATH"] = f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}"
    # The vendor-dispatch host-load gate can add up to NUCLEUS_VENDOR_LOAD_MAX_WAIT
    # seconds before the fake-agy subprocess spawns — under a saturated host
    # (load >> cpu_count) that ceiling alone exceeds this test's 30s budget.
    # Bound the gate's wait to 1s inside the server process; the gate itself
    # is covered by test_dispatch_load_gate.py, not here.
    env["NUCLEUS_VENDOR_LOAD_MAX_WAIT"] = "1"

    proc = await asyncio.create_subprocess_exec(
        *acp_cmd,
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
                "method": "session/new",
                "params": {
                    "cwd": str(project),
                    "mcpServers": [],
                },
            },
        )
        new_resp = await _read_response(proc, 2)
        new_session_id = new_resp["result"].get("sessionId") or new_resp["result"].get("session_id")
        assert new_session_id

        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "session/prompt",
                "params": {
                    "sessionId": new_session_id,
                    "prompt": [{"type": "text", "text": "write a one-line hello world file"}],
                    "_meta": {"cwd": str(project)},
                },
            },
        )
        response = await _read_response(proc, 3)
        session_id = response["result"]["_meta"]["session_id"]
        assert session_id

        # The run is awaited inside session/prompt, so the response already
        # contains the final state; no separate terminal notification is needed.
        meta = response["result"]["_meta"]
        assert meta["state"] in ("completed", "ready_for_review"), meta["state"]

        # Give any trailing notifications a moment to drain.
        try:
            await _wait_for_terminal_state(proc, session_id, {"completed", "ready_for_review", "failed", "cancelled"}, timeout=2.0)
        except RuntimeError:
            pass
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()
