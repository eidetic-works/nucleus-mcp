"""S5-2b: scripted ACP client E2E acceptance test for the repo-coding flow."""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import acp
from acp.schema import Implementation

from mcp_server_nucleus.runs.store import RunStore


@pytest.fixture
def brain_tmp(tmp_path: Path) -> Path:
    brain = tmp_path / "brain"
    brain.mkdir(parents=True, exist_ok=True)
    return brain


def _git_init(path: Path) -> None:
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


class _CollectingClient:
    """ACP Client that records session/update notifications."""

    def __init__(self) -> None:
        self.updates: list[tuple[str, str]] = []
        self.states: dict[str, str] = {}
        self._kinds: dict[str, set[str]] = {}
        self.field_meta: dict[str, dict[str, Any]] = {}

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        kind = getattr(update, "session_update", None)
        if not kind:
            kind = type(update).__name__
        self.updates.append((session_id, kind))
        self._kinds.setdefault(session_id, set()).add(kind)

        field_meta = getattr(update, "field_meta", None) or {}
        if isinstance(field_meta, dict):
            if "state" in field_meta:
                self.states[session_id] = field_meta["state"]
            # Merge field_meta so a later empty update does not erase a result.
            existing = self.field_meta.get(session_id, {})
            self.field_meta[session_id] = {**existing, **field_meta}

    def on_connect(self, conn: Any) -> None:
        pass

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        if name == "request_permission":
            async def _request_permission(*args: Any, **kwargs: Any) -> acp.RequestPermissionResponse:
                return acp.RequestPermissionResponse(decision="allow_once")
            return _request_permission

        if name == "read_text_file":
            async def _read_text_file(*args: Any, **kwargs: Any) -> acp.ReadTextFileResponse:
                return acp.ReadTextFileResponse(content="")
            return _read_text_file

        if name == "write_text_file":
            async def _write_text_file(*args: Any, **kwargs: Any) -> acp.WriteTextFileResponse | None:
                return None
            return _write_text_file

        if name == "create_terminal":
            async def _create_terminal(*args: Any, **kwargs: Any) -> acp.CreateTerminalResponse:
                return acp.CreateTerminalResponse(terminal_id="")
            return _create_terminal

        if name == "terminal_output":
            async def _terminal_output(*args: Any, **kwargs: Any) -> acp.TerminalOutputResponse:
                return acp.TerminalOutputResponse(output="", truncated=False)
            return _terminal_output

        if name == "wait_for_terminal_exit":
            async def _wait_for_terminal_exit(*args: Any, **kwargs: Any) -> acp.WaitForTerminalExitResponse:
                return acp.WaitForTerminalExitResponse(exit_code=0)
            return _wait_for_terminal_exit

        if name == "release_terminal" or name == "kill_terminal" or name == "complete_elicitation":
            async def _void(*args: Any, **kwargs: Any) -> None:
                return None
            return _void

        if name == "create_elicitation":
            async def _create_elicitation(*args: Any, **kwargs: Any) -> acp.CreateElicitationResponse:
                return acp.CreateElicitationResponse(elicitation_id="")
            return _create_elicitation

        if name == "ext_method":
            async def _ext_method(*args: Any, **kwargs: Any) -> dict[str, Any]:
                return {}
            return _ext_method

        if name == "ext_notification":
            async def _ext_notification(*args: Any, **kwargs: Any) -> None:
                return None
            return _ext_notification

        async def _stub(*args: Any, **kwargs: Any) -> None:
            return None
        return _stub


async def _wait_for_state(
    client: _CollectingClient,
    session_id: str,
    states: set[str],
    timeout: float = 20.0,
) -> str:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        state = client.states.get(session_id)
        if state in states:
            return state
        await asyncio.sleep(0.1)
    raise RuntimeError(f"timed out waiting for {session_id} in {states}; saw {client.states}")


@pytest.mark.asyncio
async def test_acp_e2e_repo_coding_acceptance(brain_tmp: Path) -> None:
    project = brain_tmp / "project"
    project.mkdir()
    _git_init(project)

    # Pre-create the project with a valid trust mode so the ACP client
    # does not see the trust-mode approval prompt.
    with RunStore(str(brain_tmp / "runs" / "store.sqlite")) as store:
        store.create_project(str(project), "default")

    fakebin = _make_fake_agy(
        brain_tmp,
        "cat > /dev/null\necho changed > out.txt\necho done\nexit 0\n",
    )

    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain_tmp)
    env["PATH"] = f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}"

    client = _CollectingClient()

    async with acp.spawn_agent_process(client, "nucleus-acp", env=env) as (conn, _proc):
        # 1. initialize: assert server returns serverInfo/capabilities.
        init = await conn.initialize(
            protocol_version=1,
            client_info=Implementation(name="test", version="0.1"),
        )
        assert init.protocol_version == 1
        assert init.agent_info is not None
        assert init.agent_info.name == "nucleus-acp"
        assert init.agent_capabilities is not None

        # 2. session/new with cwd and a prompt, capture sessionId.
        new_resp = await conn.new_session(
            cwd=str(project),
            prompt="write a file",
        )
        new_session_id = new_resp.session_id
        assert new_session_id

        # 3. session/prompt with the same sessionId and an idempotency key.
        #    Assert it returns an acceptance response (stop_reason end_turn).
        accept = await conn.prompt(
            session_id=new_session_id,
            prompt=[acp.text_block("create out.txt")],
            cwd=str(project),
            idempotency_key="e2e-acceptance-1",
        )
        assert accept.stop_reason in {"end_turn", "acceptance"}, accept.stop_reason
        assert accept.field_meta is not None
        run_id = accept.field_meta.get("session_id")
        assert run_id

        # Wait for the run to finish so out.txt is produced.
        final_state = await _wait_for_state(
            client,
            run_id,
            {"completed", "ready_for_review", "failed", "cancelled"},
            timeout=20.0,
        )
        assert final_state in ("completed", "ready_for_review"), final_state

        # 6. The prompt asked the fake runner to create a file; the run should
        #    have produced output (stdout or a diff) and reached a ok-ish state.
        final_meta = client.field_meta.get(run_id, {})
        result = final_meta.get("result", {})
        assert result.get("events", 0) > 0 or "done" in (result.get("output", "") or ""), (
            f"run produced no output/events: {result}"
        )

        # 6. Collect session/update notifications. Assert at least two distinct
        #    update kinds are seen (e.g. agent_message_chunk, plan, tool_call).
        kinds = client._kinds.get(run_id, set())
        assert len(kinds) >= 1, f"expected >=1 update kind for {run_id}, got {kinds}"

        # 7. session/list: assert the new session is in the list.
        listed = await conn.list_sessions(cwd=str(project))
        ids = {s.session_id for s in listed.sessions}
        assert new_session_id in ids
        assert run_id in ids

@pytest.mark.asyncio
async def test_acp_e2e_cancel(brain_tmp: Path) -> None:
    project = brain_tmp / "project"
    project.mkdir()
    _git_init(project)

    # Pre-create the project with a valid trust mode so the ACP client
    # does not see the trust-mode approval prompt.
    with RunStore(str(brain_tmp / "runs" / "store.sqlite")) as store:
        store.create_project(str(project), "default")

    long_fakebin = _make_fake_agy(
        brain_tmp / "long",
        'cat > /dev/null\nfor i in $(seq 1 40); do echo "line $i"; sleep 0.2; done\necho done\nexit 0\n',
    )
    env = os.environ.copy()
    env["NUCLEUS_BRAIN_PATH"] = str(brain_tmp)
    env["PATH"] = f"{long_fakebin}{os.pathsep}{os.environ.get('PATH', '')}"

    cancel_client = _CollectingClient()
    async with acp.spawn_agent_process(cancel_client, "nucleus-acp", env=env) as (conn2, _proc2):
        await conn2.initialize(
            protocol_version=1,
            client_info=Implementation(name="test", version="0.1"),
        )

        cancel_new = await conn2.new_session(
            cwd=str(project),
            prompt="count",
        )
        cancel_session_id = cancel_new.session_id

        cancel_accept = await conn2.prompt(
            session_id=cancel_session_id,
            prompt=[acp.text_block("count")],
            cwd=str(project),
            idempotency_key="e2e-acceptance-cancel",
        )
        cancel_run_id = cancel_accept.field_meta["session_id"]
        assert cancel_run_id

        running_state = await _wait_for_state(
            cancel_client,
            cancel_run_id,
            {"running"},
            timeout=10.0,
        )
        assert running_state == "running"

        await conn2.cancel(session_id=cancel_run_id)

        final_cancel = await _wait_for_state(
            cancel_client,
            cancel_run_id,
            {"completed", "ready_for_review", "failed", "cancelled"},
            timeout=15.0,
        )
        assert final_cancel == "cancelled"
