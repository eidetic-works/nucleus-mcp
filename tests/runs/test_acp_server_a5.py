"""S5-3: ACP stdio server trust-mode prompt and approval tests."""
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


def _make_fake_agy(tmp_path: Path, script: str) -> Path:
    bindir = tmp_path / "fakebin"
    bindir.mkdir(parents=True, exist_ok=True)
    script_path = bindir / "agy"
    script_path.write_text("#!/bin/sh\n" + script)
    script_path.chmod(0o755)
    return bindir


async def _write_message(proc: asyncio.subprocess.Process, msg: dict) -> None:
    line = json.dumps(msg) + "\n"
    proc.stdin.write(line.encode())
    await proc.stdin.drain()


async def _read_messages_until_response(
    proc: asyncio.subprocess.Process,
    req_id: int,
    timeout: float = 30.0,
    idle: float = 0.5,
) -> list[dict]:
    """Read all stdout messages until the matching response, then idle out."""
    messages: list[dict] = []
    end = asyncio.get_event_loop().time() + timeout
    got_response = False
    last_data = asyncio.get_event_loop().time()
    while True:
        now = asyncio.get_event_loop().time()
        if got_response and now - last_data >= idle:
            break
        if now >= end:
            break
        remaining = idle if got_response else max(0.1, end - now)
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
        except asyncio.TimeoutError:
            if got_response:
                break
            continue
        if not line:
            break
        text = line.decode().strip()
        if not text:
            continue
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            continue
        messages.append(msg)
        if isinstance(msg, dict) and msg.get("id") == req_id:
            got_response = True
            last_data = asyncio.get_event_loop().time()
            continue
        if got_response:
            last_data = asyncio.get_event_loop().time()
    return messages


def _find_response(messages: list[dict], req_id: int) -> dict:
    for msg in messages:
        if isinstance(msg, dict) and msg.get("id") == req_id:
            return msg
    raise RuntimeError(f"response for request {req_id} not found")


async def _drain_notifications(
    proc: asyncio.subprocess.Process, session_id: str, timeout: float = 20.0
):
    """Yield session/update notifications for *session_id* until timeout."""
    end = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < end:
        remaining = end - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            line = await asyncio.wait_for(
                proc.stdout.readline(), timeout=max(0.5, remaining)
            )
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
        if (
            msg.get("method") == "session/update"
            and msg.get("params", {}).get("sessionId") == session_id
        ):
            yield msg


def _find_terminal_in_messages(
    messages: list[dict], session_id: str, terminal_states: set[str]
) -> dict | None:
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("method") != "session/update":
            continue
        if msg.get("params", {}).get("sessionId") != session_id:
            continue
        update = msg.get("params", {}).get("update", {})
        meta = update.get("_meta") or update.get("field_meta") or {}
        if meta.get("state") in terminal_states:
            return msg
    return None


async def _wait_for_terminal_state(
    proc: asyncio.subprocess.Process,
    session_id: str,
    terminal_states: set[str],
    timeout: float = 20.0,
    initial_messages: list[dict] | None = None,
) -> dict:
    if initial_messages:
        found = _find_terminal_in_messages(initial_messages, session_id, terminal_states)
        if found:
            return found
    async for note in _drain_notifications(proc, session_id, timeout=timeout):
        update = note.get("params", {}).get("update", {})
        meta = update.get("_meta") or update.get("field_meta") or {}
        state = meta.get("state")
        if state in terminal_states:
            return note
    raise RuntimeError(f"timed out waiting for terminal state in {terminal_states}")


@pytest.mark.asyncio
async def test_session_new_requests_trust_mode(brain_tmp: Path) -> None:
    project = brain_tmp / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_fake_agy(
        brain_tmp,
        'cat > /dev/null\necho changed > out.txt\necho done\nexit 0\n',
    )

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
        messages = await _read_messages_until_response(proc, 1)
        init = _find_response(messages, 1)
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
        messages = await _read_messages_until_response(proc, 2)
        new = _find_response(messages, 2)

        result = new["result"]
        assert result["stop_reason"] == "request_permission"
        field_meta = result["field_meta"]
        assert field_meta["permission_type"] == "trust_mode"
        assert field_meta["choices"] == ["permissive", "default", "strict"]
        session_id = field_meta["session_id"]
        assert session_id

        # Find the session/update notification emitted for this request.
        notes = [
            m
            for m in messages
            if isinstance(m, dict)
            and m.get("method") == "session/update"
            and m.get("params", {}).get("sessionId") == session_id
        ]
        assert len(notes) >= 1
        update = notes[0]["params"]["update"]
        assert update["kind"] == "request_permission"
        assert update["field_meta"]["permission_type"] == "trust_mode"
        assert update["field_meta"]["choices"] == ["permissive", "default", "strict"]
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_approve_trust_mode_then_prompt(brain_tmp: Path) -> None:
    project = brain_tmp / "project"
    project.mkdir()
    _git_init(project)
    fakebin = _make_fake_agy(
        brain_tmp,
        'cat > /dev/null\necho changed > out.txt\necho done\nexit 0\n',
    )

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
        messages = await _read_messages_until_response(proc, 1)
        assert _find_response(messages, 1)["result"]["protocolVersion"] == 1

        # 1. session/new should request permission for an untrusted project root.
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
        messages = await _read_messages_until_response(proc, 2)
        new = _find_response(messages, 2)
        assert new["result"]["stop_reason"] == "request_permission"
        session_id = new["result"]["field_meta"]["session_id"]

        # 2. Approve the trust mode and supply the prompt in one call.
        await _write_message(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "session/approve_permission",
                "params": {
                    "sessionId": session_id,
                    "trust_mode": "permissive",
                    "prompt": "write a file",
                },
            },
        )
        messages = await _read_messages_until_response(proc, 3)
        accept = _find_response(messages, 3)
        result = accept["result"]
        stop_reason = result.get("stop_reason") or result.get("stopReason")
        assert stop_reason == "end_turn", result
        run_id = result.get("field_meta", {}).get("session_id") or result.get("_meta", {}).get("session_id")
        assert run_id

        # 3. Wait for the run to finish and out.txt to appear.
        # The terminal update may have already arrived during the response read,
        # so scan those messages first before draining the stream.
        final = await _wait_for_terminal_state(
            proc,
            run_id,
            {"completed", "ready_for_review", "failed", "cancelled"},
            timeout=20.0,
            initial_messages=messages,
        )
        meta = final["params"]["update"].get("_meta") or final["params"]["update"].get("field_meta") or {}
        assert meta["state"] in ("completed", "ready_for_review"), meta["state"]

        # The runner writes into the isolated workspace worktree, not the base.
        db_path = brain_tmp / "runs" / "store.sqlite"
        with RunStore(str(db_path)) as store:
            run = store.get_run(run_id)
        assert run.workspace
        assert (Path(run.workspace) / "out.txt").exists()
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_existing_project_skips_prompt(brain_tmp: Path) -> None:
    project = brain_tmp / "project"
    project.mkdir()
    _git_init(project)

    # Pre-create the project with a valid trust mode in the run store.
    db_path = brain_tmp / "runs" / "store.sqlite"
    with RunStore(str(db_path)) as store:
        store.create_project(str(project), "permissive")

    fakebin = _make_fake_agy(
        brain_tmp,
        'cat > /dev/null\necho changed > out.txt\necho done\nexit 0\n',
    )

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
        messages = await _read_messages_until_response(proc, 1)
        assert _find_response(messages, 1)["result"]["protocolVersion"] == 1

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
        messages = await _read_messages_until_response(proc, 2)
        new = _find_response(messages, 2)
        result = new["result"]
        assert result["sessionId"]
        meta = result.get("_meta") or result.get("field_meta") or {}
        assert meta.get("stop_reason") == "acceptance"

        # A run should have been created for the existing trusted project.
        with RunStore(str(db_path)) as store:
            runs = store.list_runs()
        assert len(runs) >= 1
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()
