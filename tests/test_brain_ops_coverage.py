"""
Coverage tests for runtime/capabilities/brain_ops.py
"""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.capabilities.brain_ops import BrainOps


@pytest.fixture
def brain_ops():
    return BrainOps()


@pytest.fixture
def brain_path(tmp_path, monkeypatch):
    bp = tmp_path / ".brain"
    bp.mkdir()
    (bp / "commitments").mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------
class TestProperties:
    def test_name(self, brain_ops):
        assert brain_ops.name == "brain_ops"

    def test_description(self, brain_ops):
        assert "commitment ledger" in brain_ops.description.lower()


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------
class TestGetTools:
    def test_returns_all_tools(self, brain_ops):
        tools = brain_ops.get_tools()
        names = [t["name"] for t in tools]
        assert "brain_add_commitment" in names
        assert "brain_get_open_loops" in names
        assert "brain_scan_commitments" in names
        assert "brain_archive_stale" in names
        assert "brain_orchestrate_swarm" in names
        assert "brain_export" in names
        assert "brain_consolidate_logs" in names
        assert "brain_delegate_task" in names

    def test_add_commitment_required_fields(self, brain_ops):
        tools = brain_ops.get_tools()
        tool = [t for t in tools if t["name"] == "brain_add_commitment"][0]
        assert tool["parameters"]["required"] == ["description"]

    def test_orchestrate_swarm_required_fields(self, brain_ops):
        tools = brain_ops.get_tools()
        tool = [t for t in tools if t["name"] == "brain_orchestrate_swarm"][0]
        assert tool["parameters"]["required"] == ["mission"]

    def test_delegate_task_required_fields(self, brain_ops):
        tools = brain_ops.get_tools()
        tool = [t for t in tools if t["name"] == "brain_delegate_task"][0]
        assert "persona" in tool["parameters"]["required"]
        assert "intent" in tool["parameters"]["required"]


# ---------------------------------------------------------------------------
# brain_add_commitment
# ---------------------------------------------------------------------------
class TestAddCommitment:
    def test_add_commitment_success(self, brain_ops, brain_path, monkeypatch):
        mock_result = {"id": "comm-123", "status": "open"}
        mock_ledger = MagicMock()
        mock_ledger.add_commitment.return_value = mock_result
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.capabilities.brain_ops.commitment_ledger",
            mock_ledger
        )
        result = brain_ops.execute_tool("brain_add_commitment", {
            "description": "Test task",
            "loop_type": "task",
            "priority": 3,
            "source": "test"
        })
        assert "comm-123" in result
        mock_ledger.add_commitment.assert_called_once()

    def test_add_commitment_defaults(self, brain_ops, brain_path, monkeypatch):
        mock_ledger = MagicMock()
        mock_ledger.add_commitment.return_value = {"id": "x"}
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.capabilities.brain_ops.commitment_ledger",
            mock_ledger
        )
        brain_ops.execute_tool("brain_add_commitment", {"description": "Minimal"})
        call_kwargs = mock_ledger.add_commitment.call_args
        # Check defaults are applied
        assert call_kwargs.kwargs["comm_type"] == "task"
        assert call_kwargs.kwargs["priority"] == 3
        assert call_kwargs.kwargs["source"] == "nar_agent"


# ---------------------------------------------------------------------------
# brain_get_open_loops
# ---------------------------------------------------------------------------
class TestGetOpenLoops:
    def test_get_open_loops_with_open(self, brain_ops, brain_path, monkeypatch):
        mock_ledger = MagicMock()
        mock_ledger.load_ledger.return_value = {
            "commitments": [
                {"status": "open", "id": "1"},
                {"status": "closed", "id": "2"},
                {"status": "open", "id": "3"},
            ]
        }
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.capabilities.brain_ops.commitment_ledger",
            mock_ledger
        )
        result = brain_ops.execute_tool("brain_get_open_loops", {})
        assert "2 open loops" in result

    def test_get_open_loops_empty(self, brain_ops, brain_path, monkeypatch):
        mock_ledger = MagicMock()
        mock_ledger.load_ledger.return_value = {"commitments": []}
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.capabilities.brain_ops.commitment_ledger",
            mock_ledger
        )
        result = brain_ops.execute_tool("brain_get_open_loops", {})
        assert "0 open loops" in result


# ---------------------------------------------------------------------------
# brain_scan_commitments
# ---------------------------------------------------------------------------
class TestScanCommitments:
    def test_scan_success(self, brain_ops, brain_path, monkeypatch):
        mock_ledger = MagicMock()
        mock_ledger.scan_for_commitments.return_value = {"scanned": 5}
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.capabilities.brain_ops.commitment_ledger",
            mock_ledger
        )
        result = brain_ops.execute_tool("brain_scan_commitments", {})
        assert "Scan Complete" in result
        assert "5" in result


# ---------------------------------------------------------------------------
# brain_archive_stale
# ---------------------------------------------------------------------------
class TestArchiveStale:
    def test_archive_success(self, brain_ops, brain_path, monkeypatch):
        mock_ledger = MagicMock()
        mock_ledger.auto_archive_stale.return_value = 3
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.capabilities.brain_ops.commitment_ledger",
            mock_ledger
        )
        result = brain_ops.execute_tool("brain_archive_stale", {})
        assert "Archived 3" in result


# ---------------------------------------------------------------------------
# brain_export
# ---------------------------------------------------------------------------
class TestExport:
    def test_export_with_method(self, brain_ops, brain_path, monkeypatch):
        mock_ledger = MagicMock()
        mock_ledger.export_brain.return_value = "/tmp/export.zip"
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.capabilities.brain_ops.commitment_ledger",
            mock_ledger
        )
        result = brain_ops.execute_tool("brain_export", {})
        assert "Export Complete" in result
        assert "/tmp/export.zip" in result

    def test_export_without_method(self, brain_ops, brain_path, monkeypatch):
        mock_ledger = MagicMock(spec=[])  # No export_brain attribute
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.capabilities.brain_ops.commitment_ledger",
            mock_ledger
        )
        result = brain_ops.execute_tool("brain_export", {})
        assert "not implemented" in result


# ---------------------------------------------------------------------------
# brain_consolidate_logs
# ---------------------------------------------------------------------------
class TestConsolidateLogs:
    def test_no_raw_dir(self, brain_ops, brain_path):
        result = brain_ops.execute_tool("brain_consolidate_logs", {})
        assert "No raw logs" in result

    def test_empty_raw_dir(self, brain_ops, brain_path):
        raw_dir = brain_path / "raw"
        raw_dir.mkdir()
        result = brain_ops.execute_tool("brain_consolidate_logs", {})
        assert "0 logs found" in result

    def test_consolidate_success(self, brain_ops, brain_path):
        raw_dir = brain_path / "raw"
        raw_dir.mkdir()
        (raw_dir / "log1.json").write_text(json.dumps({"event": "test1"}))
        (raw_dir / "log2.json").write_text(json.dumps({"event": "test2"}))

        result = brain_ops.execute_tool("brain_consolidate_logs", {})
        assert "Consolidated 2" in result
        # Original files deleted
        assert not (raw_dir / "log1.json").exists()
        assert not (raw_dir / "log2.json").exists()
        # Archive created
        archive_dir = brain_path / "archive"
        archives = list(archive_dir.glob("*.jsonl"))
        assert len(archives) == 1
        lines = archives[0].read_text().strip().split("\n")
        assert len(lines) == 2

    def test_consolidate_with_invalid_json(self, brain_ops, brain_path, capsys):
        raw_dir = brain_path / "raw"
        raw_dir.mkdir()
        (raw_dir / "good.json").write_text(json.dumps({"ok": True}))
        (raw_dir / "bad.json").write_text("not valid json{{{")

        result = brain_ops.execute_tool("brain_consolidate_logs", {})
        assert "Consolidated 1" in result
        # Bad file should still exist (not processed)
        assert (raw_dir / "bad.json").exists()
        # Good file deleted
        assert not (raw_dir / "good.json").exists()


# ---------------------------------------------------------------------------
# brain_delegate_task
# ---------------------------------------------------------------------------
class TestDelegateTask:
    def test_delegate_success(self, brain_ops, brain_path, monkeypatch):
        from unittest.mock import AsyncMock

        # Mock the factory, agent, and llm
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="Delegation result log")

        mock_factory = MagicMock()
        mock_factory.create_context_for_persona.return_value = MagicMock()

        mock_llm = MagicMock()

        # Patch imports inside execute_tool
        monkeypatch.setattr("uuid.uuid4", lambda: "test-uuid-1234")
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.factory.ContextFactory",
            lambda: mock_factory
        )
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.agent.EphemeralAgent",
            lambda ctx, model: mock_agent
        )
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.llm_client.DualEngineLLM",
            lambda: mock_llm
        )
        # Mock asyncio to avoid real async execution
        # Mock nest_asyncio.apply to prevent global event loop patching
        monkeypatch.setattr("nest_asyncio.apply", lambda loop=None: None)
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = "Delegation result log"
        monkeypatch.setattr("asyncio.get_running_loop", lambda: mock_loop)

        result = brain_ops.execute_tool("brain_delegate_task", {
            "persona": "researcher",
            "intent": "Research something"
        })
        assert "Delegation" in result or "queued" in result or "Delegation Complete" in result

    def test_delegate_async_fallback(self, brain_ops, brain_path, monkeypatch):
        """When asyncio.get_running_loop raises RuntimeError and asyncio.run works."""
        from unittest.mock import AsyncMock

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="async result")

        mock_factory = MagicMock()
        mock_factory.create_context_for_persona.return_value = MagicMock()

        monkeypatch.setattr("uuid.uuid4", lambda: "test-uuid")
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.factory.ContextFactory",
            lambda: mock_factory
        )
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.agent.EphemeralAgent",
            lambda ctx, model: mock_agent
        )
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.llm_client.DualEngineLLM",
            lambda: MagicMock()
        )

        import asyncio
        # Mock nest_asyncio.apply to prevent global event loop patching
        # which corrupts the event loop for subsequent TestClient tests.
        monkeypatch.setattr("nest_asyncio.apply", lambda loop=None: None)
        monkeypatch.setattr("asyncio.get_running_loop", MagicMock(side_effect=RuntimeError("no loop")))
        # Mock asyncio.run to avoid creating/closing a real event loop.
        async def _fake_run(coro):
            try:
                return await coro
            finally:
                coro.close()
        monkeypatch.setattr("asyncio.run", _fake_run)

        result = brain_ops.execute_tool("brain_delegate_task", {
            "persona": "librarian",
            "intent": "Do thing"
        })
        assert "async result" in result or "Delegation Complete" in result

    def test_delegate_runtime_error_fallback(self, brain_ops, brain_path, monkeypatch):
        """When both async approaches raise RuntimeError, return queued message."""
        mock_agent = MagicMock()
        mock_agent.run = MagicMock(return_value="result")

        mock_factory = MagicMock()
        mock_factory.create_context_for_persona.return_value = MagicMock()

        monkeypatch.setattr("uuid.uuid4", lambda: "test-uuid")
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.factory.ContextFactory",
            lambda: mock_factory
        )
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.agent.EphemeralAgent",
            lambda ctx, model: mock_agent
        )
        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.llm_client.DualEngineLLM",
            lambda: MagicMock()
        )

        import asyncio
        # Mock nest_asyncio.apply to prevent global event loop patching
        monkeypatch.setattr("nest_asyncio.apply", lambda loop=None: None)
        # Both raise RuntimeError
        monkeypatch.setattr("asyncio.get_running_loop", MagicMock(side_effect=RuntimeError("no loop")))
        monkeypatch.setattr("asyncio.run", MagicMock(side_effect=RuntimeError("cannot run")))

        result = brain_ops.execute_tool("brain_delegate_task", {
            "persona": "critic",
            "intent": "Review code"
        })
        assert "queued" in result or "Cannot block" in result


# ---------------------------------------------------------------------------
# brain_orchestrate_swarm
# ---------------------------------------------------------------------------
class TestOrchestrateSwarm:
    def test_swarm_success(self, brain_ops, brain_path, monkeypatch):
        from unittest.mock import AsyncMock

        mock_orchestrator = MagicMock()
        mock_orchestrator.start_mission = AsyncMock(return_value={
            "mission_id": "mission-123",
            "status": "started"
        })

        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator",
            lambda brain_path: mock_orchestrator
        )

        import asyncio
        monkeypatch.setattr("nest_asyncio.apply", lambda loop=None: None)
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = {
            "mission_id": "mission-123",
            "status": "started"
        }
        monkeypatch.setattr("asyncio.get_running_loop", lambda: mock_loop)

        result = brain_ops.execute_tool("brain_orchestrate_swarm", {
            "mission": "Build feature X",
            "agents": ["developer", "architect"],
            "swarm_type": "genesis"
        })
        assert "mission-123" in result or "Swarm" in result

    def test_swarm_no_agents(self, brain_ops, brain_path, monkeypatch):
        from unittest.mock import AsyncMock

        mock_orchestrator = MagicMock()
        mock_orchestrator.start_mission = AsyncMock(return_value={
            "mission_id": "m1",
            "status": "started"
        })

        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator",
            lambda brain_path: mock_orchestrator
        )

        import asyncio
        monkeypatch.setattr("nest_asyncio.apply", lambda loop=None: None)
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = {"mission_id": "m1", "status": "started"}
        monkeypatch.setattr("asyncio.get_running_loop", lambda: mock_loop)

        result = brain_ops.execute_tool("brain_orchestrate_swarm", {
            "mission": "Test mission"
        })
        assert "auto-detected" in result

    def test_swarm_runtime_error_fallback(self, brain_ops, brain_path, monkeypatch):
        from unittest.mock import AsyncMock

        mock_orchestrator = MagicMock()
        mock_orchestrator.start_mission = AsyncMock(return_value={"mission_id": "m1"})

        monkeypatch.setattr(
            "mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator",
            lambda brain_path: mock_orchestrator
        )

        import asyncio
        # Mock nest_asyncio.apply to prevent global event loop patching
        monkeypatch.setattr("nest_asyncio.apply", lambda loop=None: None)
        monkeypatch.setattr("asyncio.get_running_loop", MagicMock(side_effect=RuntimeError("no loop")))
        monkeypatch.setattr("asyncio.run", MagicMock(side_effect=RuntimeError("cannot run")))

        result = brain_ops.execute_tool("brain_orchestrate_swarm", {
            "mission": "Test"
        })
        assert "queued" in result or "async issue" in result


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------
class TestUnknownTool:
    def test_unknown_tool_returns_message(self, brain_ops, brain_path):
        result = brain_ops.execute_tool("nonexistent_tool", {})
        assert "not found" in result
