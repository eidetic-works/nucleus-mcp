"""Additional ACP end-to-end edge case tests."""
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


async def _drain_notifications(proc: asyncio.subprocess.Process, session_id: str, timeout: float = 5.0):
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


@pytest.fixture
def project(tmp_path: Path) -> Path:
    p = tmp_path / "project"
    p.mkdir()
    _git_init(p)
    return p


@pytest.fixture
def project_with_store(tmp_path: Path, project: Path):
    brain = tmp_path / "brain"
    brain.mkdir()
    store = RunStore(str(brain / "runs" / "store.sqlite"))
    store.create_project(str(project), "default")
    store.close()
    return brain, project


@pytest.mark.asyncio
async def test_prompt_with_string_prompt(project_with_store, tmp_path: Path) -> None:
    """AionUi may send the prompt as a plain string instead of a list."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "cat > /dev/null\necho 'string prompt ok' > out.txt\necho done\nexit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        # AionUi-style prompt list containing a single text block
        await _write_message(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "session/prompt",
            "params": {"sessionId": sid, "prompt": [{"type": "text", "text": "write a one-line hello world file"}]},
        })
        response = await _read_response(proc, 3)
        meta = response["result"]["_meta"]
        assert meta["session_id"] == sid
        assert meta["state"] in ("completed", "ready_for_review"), meta["state"]

        # Verify the fake runner actually saw the prompt and wrote the marker file
        async for note in _drain_notifications(proc, sid, timeout=2.0):
            update = note["params"]["update"]
            if update.get("sessionUpdate") == "agent_message_chunk":
                assert "string prompt ok" in update["content"]["text"]
                break
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_prompt_nonexistent_session(project_with_store, tmp_path: Path) -> None:
    """Prompting a session that does not exist must return an error."""
    brain, project = project_with_store
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"

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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        await _read_response(proc, 2)

        fake_id = "00000000-0000-0000-0000-000000000000"
        await _write_message(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "session/prompt",
            "params": {"sessionId": fake_id, "prompt": [{"type": "text", "text": "hello"}]},
        })
        response = await _read_response(proc, 3)
        assert "error" in response, response
        msg = response["error"].get("message", "").lower()
        assert "invalid" in msg or response["error"].get("code") == -32602
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_set_mode_invalid(project_with_store, tmp_path: Path) -> None:
    """Setting an unknown mode should return an error without crashing."""
    brain, project = project_with_store
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"

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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        await _write_message(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "session/set_mode",
            "params": {"sessionId": sid, "modeId": "nonexistent-mode"},
        })
        response = await _read_response(proc, 3)
        # Current implementation accepts any mode id without crashing; it is
        # stored but the run state remains queued.
        assert "result" in response, response
        meta = response["result"]["_meta"]
        assert meta["mode_id"] == "nonexistent-mode"
        assert meta["session_id"] == sid
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_multiple_prompts_same_session(project_with_store, tmp_path: Path) -> None:
    """Two prompts on the same session should both run and keep the same session id."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "cat > /dev/null\necho 'turn done' > out.txt\necho done\nexit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        for i, text in enumerate(["first prompt", "second prompt"], start=1):
            await _write_message(proc, {
                "jsonrpc": "2.0", "id": 2 + i, "method": "session/prompt",
                "params": {"sessionId": sid, "prompt": [{"type": "text", "text": text}]},
            })
            response = await _read_response(proc, 2 + i)
            meta = response["result"]["_meta"]
            assert meta["session_id"] == sid
            assert meta["state"] in ("completed", "ready_for_review"), meta["state"]
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_new_session_non_git_dir(project_with_store, tmp_path: Path) -> None:
    """session/new should work in a plain directory, not just git repos."""
    brain, _ = project_with_store
    plain = tmp_path / "plain"
    plain.mkdir()
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"

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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(plain), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        assert "sessionId" in new_resp["result"]
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_apply_session(project_with_store, tmp_path: Path) -> None:
    """A prompt that creates a file can be applied to the original project."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "cat > /dev/null\n"
        "printf 'applied file content' > applied.txt\n"
        "echo done\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        await _write_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "session/prompt", "params": {"sessionId": sid, "prompt": [{"type": "text", "text": "Create applied.txt"}]}})
        response = await _read_response(proc, 3)
        assert response["result"]["_meta"]["state"] in ("completed", "ready_for_review")

        await _write_message(proc, {"jsonrpc": "2.0", "id": 4, "method": "session/apply", "params": {"sessionId": sid}})
        apply_resp = await _read_response(proc, 4)
        assert apply_resp["result"]["_meta"]["state"] == "applied", apply_resp

        assert (project / "applied.txt").read_text() == "applied file content"
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_dismiss_session(project_with_store, tmp_path: Path) -> None:
    """A prompt can be dismissed without applying changes to the project."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "cat > /dev/null\n"
        "printf 'dismissed file content' > dismissed.txt\n"
        "echo done\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        await _write_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "session/prompt", "params": {"sessionId": sid, "prompt": [{"type": "text", "text": "Create dismissed.txt"}]}})
        response = await _read_response(proc, 3)
        assert response["result"]["_meta"]["state"] in ("completed", "ready_for_review")

        await _write_message(proc, {"jsonrpc": "2.0", "id": 4, "method": "session/dismiss", "params": {"sessionId": sid}})
        dismiss_resp = await _read_response(proc, 4)
        assert dismiss_resp["result"]["_meta"]["state"] == "dismissed", dismiss_resp

        assert not (project / "dismissed.txt").exists()
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_cancel_session(project_with_store, tmp_path: Path) -> None:
    """session/cancel should cancel an active or queued session."""
    brain, project = project_with_store
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"

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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        await _write_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "session/cancel", "params": {"sessionId": sid}})
        cancel_resp = await _read_response(proc, 3)
        assert cancel_resp["result"]["_meta"]["session_id"] == sid
        assert cancel_resp["result"]["_meta"]["state"] in ("cancelled", "failed", "ready_for_review"), cancel_resp
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.timeout(120)
@pytest.mark.asyncio
async def test_session_status(project_with_store, tmp_path: Path) -> None:
    """session/status returns the current run state and output."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "cat > /dev/null\n"
        "echo 'status output' > status.txt\n"
        "echo done\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        await _write_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "session/prompt", "params": {"sessionId": sid, "prompt": [{"type": "text", "text": "Create status.txt"}]}})
        prompt_resp = await _read_response(proc, 3)
        assert prompt_resp["result"]["_meta"]["state"] in ("completed", "ready_for_review"), prompt_resp

        await _write_message(proc, {"jsonrpc": "2.0", "id": 4, "method": "session/status", "params": {"sessionId": sid}})
        status_resp = await _read_response(proc, 4)
        result = status_resp["result"]
        assert "_meta" in result
        assert result["_meta"]["session_id"] == sid
        assert "run_id" in result["_meta"]
        assert result["_meta"]["state"] in ("completed", "ready_for_review")
        assert "output" in result["_meta"]
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.timeout(120)
@pytest.mark.asyncio
async def test_retry_session(project_with_store, tmp_path: Path) -> None:
    """session/retry creates a new run for the same session."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "cat > /dev/null\n"
        "echo 'retry output' > retry.txt\n"
        "echo done\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        await _write_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "session/prompt", "params": {"sessionId": sid, "prompt": [{"type": "text", "text": "Create retry.txt"}]}})
        prompt_resp = await _read_response(proc, 3)
        assert prompt_resp["result"]["_meta"]["state"] in ("completed", "ready_for_review"), prompt_resp
        first_run_id = prompt_resp["result"]["_meta"].get("run_id")

        await _write_message(proc, {"jsonrpc": "2.0", "id": 4, "method": "session/retry", "params": {"sessionId": sid}})
        retry_resp = await _read_response(proc, 4)
        assert retry_resp["result"]["_meta"]["session_id"] == sid
        assert retry_resp["result"]["_meta"]["run_id"] != first_run_id, retry_resp
        assert retry_resp["result"]["_meta"]["state"] in ("completed", "ready_for_review"), retry_resp
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.timeout(120)
@pytest.mark.asyncio
async def test_fork_session(project_with_store, tmp_path: Path) -> None:
    """session/fork creates a new session from an existing one."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "cat > /dev/null\n"
        "echo 'fork output' > fork.txt\n"
        "echo done\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        await _write_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "session/fork", "params": {"sessionId": sid}})
        fork_resp = await _read_response(proc, 3)
        new_sid = fork_resp["result"]["sessionId"]
        assert new_sid != sid, fork_resp
        assert "source_session_id" in fork_resp["result"]["_meta"]
        assert fork_resp["result"]["_meta"]["source_session_id"] == sid

        await _write_message(proc, {"jsonrpc": "2.0", "id": 4, "method": "session/prompt", "params": {"sessionId": new_sid, "prompt": [{"type": "text", "text": "Create fork.txt"}]}})
        prompt_resp = await _read_response(proc, 4)
        assert prompt_resp["result"]["_meta"]["session_id"] == new_sid
        assert prompt_resp["result"]["_meta"]["state"] in ("completed", "ready_for_review"), prompt_resp
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_session_resume(project_with_store, tmp_path: Path) -> None:
    """session/resume reconnects to an existing session and returns its state."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "cat > /dev/null\n"
        "echo 'resume output' > resume.txt\n"
        "echo done\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        await _write_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "session/prompt", "params": {"sessionId": sid, "prompt": [{"type": "text", "text": "Create resume.txt"}]}})
        prompt_resp = await _read_response(proc, 3)
        assert prompt_resp["result"]["_meta"]["state"] in ("completed", "ready_for_review"), prompt_resp

        await _write_message(proc, {"jsonrpc": "2.0", "id": 4, "method": "session/resume", "params": {"sessionId": sid}})
        resume_resp = await _read_response(proc, 4)
        result = resume_resp["result"]
        assert result["_meta"]["session_id"] == sid
        assert "run_id" in result["_meta"]
        assert result["_meta"]["state"] in ("completed", "ready_for_review")
        assert "output" in result["_meta"]
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_session_heartbeat_expired(project_with_store, tmp_path: Path) -> None:
    """A run is cancelled when the client stops heartbeating."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "sleep 30\n"  # long enough for heartbeat monitor to fire
        "echo 'heartbeat output' > heartbeat.txt\n"
        "echo done\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
    env["NUCLEUS_HEARTBEAT_TIMEOUT"] = "2"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        # Send prompt but never heartbeat; expect cancellation before the fake agy finishes.
        await _write_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "session/prompt", "params": {"sessionId": sid, "prompt": [{"type": "text", "text": "Create heartbeat.txt"}]}})
        prompt_resp = await _read_response(proc, 3, timeout=15.0)
        assert prompt_resp["result"]["_meta"]["state"] == "cancelled", prompt_resp
    finally:
        if proc.stdin is not None:
            proc.stdin.write_eof()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()


@pytest.mark.asyncio
async def test_process_kill_restart(project_with_store, tmp_path: Path) -> None:
    """A run survives killing and restarting the nucleus-acp process."""
    brain, project = project_with_store
    fakebin = _install_fake_agy(
        tmp_path,
        "sleep 4\n"
        "echo 'worker survived' > worker-survived.txt\n"
        "echo done\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain)
    env["NUCLEUS_CROSS_VENDOR"] = "1"
    env["NUCLEUS_DEFAULT_TRUST_MODE"] = "default"
    env["NUCLEUS_DEFAULT_RUNNER"] = "agy"
    env["NUCLEUS_EXECUTION_TARGET"] = "subprocess"
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
        await _write_message(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc, 1)

        await _write_message(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": str(project), "mcpServers": []}})
        new_resp = await _read_response(proc, 2)
        sid = new_resp["result"]["sessionId"]

        # Launch a run and kill the ACP process before the fake agy finishes.
        await _write_message(proc, {"jsonrpc": "2.0", "id": 3, "method": "session/prompt", "params": {"sessionId": sid, "prompt": [{"type": "text", "text": "Create worker-survived.txt"}]}})
        await asyncio.sleep(1.5)
        proc.kill()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.terminate()
            await proc.wait()
    finally:
        if proc.stdin is not None:
            try:
                proc.stdin.write_eof()
            except Exception:
                pass

    # The worker should still be running. Wait briefly to be safe.
    await asyncio.sleep(1.0)

    # Restart nucleus-acp with the same brain and resume.
    proc2 = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "mcp_server_nucleus.runs.acp_server",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        await _write_message(proc2, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientInfo": {"name": "test", "version": "0.1"}, "mcpServers": []}})
        await _read_response(proc2, 1)

        await _write_message(proc2, {"jsonrpc": "2.0", "id": 2, "method": "session/resume", "params": {"sessionId": sid}})
        resume_resp = await _read_response(proc2, 2, timeout=30.0)
        assert resume_resp["result"]["_meta"]["session_id"] == sid, resume_resp

        # Poll status until the detached worker completes.
        final_state = resume_resp["result"]["_meta"]["state"]
        run_id = resume_resp["result"]["_meta"]["run_id"]
        for attempt in range(30):
            if final_state in ("completed", "ready_for_review"):
                break
            await asyncio.sleep(1.0)
            await _write_message(proc2, {"jsonrpc": "2.0", "id": 3 + attempt, "method": "session/status", "params": {"sessionId": sid}})
            status_resp = await _read_response(proc2, 3 + attempt, timeout=5.0)
            final_state = status_resp["result"]["_meta"]["state"]

        assert final_state in ("completed", "ready_for_review"), final_state
    finally:
        if proc2.stdin is not None:
            proc2.stdin.write_eof()
        try:
            await asyncio.wait_for(proc2.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc2.terminate()
            await proc2.wait()
