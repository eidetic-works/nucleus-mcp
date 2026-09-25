"""ACP A4 tests: session state persistence in the SQLite run store."""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server_nucleus.runs.acp_server import NucleusAgent
from mcp_server_nucleus.runs.mcp_adapter import RunMcpAdapter
from mcp_server_nucleus.runs.store import RunStore


@pytest.fixture
def brain_tmp(tmp_path: Path) -> Path:
    brain = tmp_path / "brain"
    brain.mkdir(parents=True, exist_ok=True)
    return brain


@pytest.mark.asyncio
async def test_session_survives_restart(brain_tmp: Path) -> None:
    db_path = brain_tmp / "store.sqlite"
    with RunStore(str(db_path)) as store:
        store.create_project(str(brain_tmp / "project"), "default")

    adapter = RunMcpAdapter(db_path)
    agent = NucleusAgent(None, adapter)
    cwd = str(brain_tmp / "project")

    new = await agent.new_session(cwd=cwd, prompt="test prompt")
    session_id = new.session_id

    fresh_adapter = RunMcpAdapter(db_path)
    fresh_agent = NucleusAgent(None, fresh_adapter)
    loaded = await fresh_agent.load_session(cwd=cwd, session_id=session_id)

    assert loaded.field_meta["session_id"] == session_id
    assert loaded.field_meta["cwd"] == cwd
    assert loaded.field_meta["prompt"] == "test prompt"

    session = fresh_adapter.get_session(session_id)
    assert session is not None
    assert session.run_id == session_id
    run = fresh_adapter._store.get_run(session_id)
    assert run.id == session_id
    assert run.conversation_id == session.conversation_id


@pytest.mark.asyncio
async def test_session_list_after_restart(brain_tmp: Path) -> None:
    db_path = brain_tmp / "store.sqlite"
    with RunStore(str(db_path)) as store:
        store.create_project(str(brain_tmp / "p1"), "default")
        store.create_project(str(brain_tmp / "p2"), "default")

    adapter = RunMcpAdapter(db_path)
    agent = NucleusAgent(None, adapter)

    new1 = await agent.new_session(cwd=str(brain_tmp / "p1"), prompt="first session")
    new2 = await agent.new_session(cwd=str(brain_tmp / "p2"), prompt="second session")

    fresh_adapter = RunMcpAdapter(db_path)
    fresh_agent = NucleusAgent(None, fresh_adapter)
    listed = await fresh_agent.list_sessions()

    ids = {s.session_id for s in listed.sessions}
    assert new1.session_id in ids
    assert new2.session_id in ids
