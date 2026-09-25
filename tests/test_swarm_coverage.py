"""Comprehensive coverage tests for runtime/swarm.py.

Tests get_brain_path (env var + cwd/parent fallbacks), _orchestrate_swarm
(success, default/custom agents, running-loop path, fallback new-loop path,
exception handling), and _get_swarm_status (found, not-found, artifacts,
exception). SwarmsOrchestrator is mocked — no real agents spawned, no
network.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_nucleus.runtime import swarm as swarm_mod
from mcp_server_nucleus.runtime.swarm import (
    _get_swarm_status,
    _orchestrate_swarm,
    get_brain_path,
)


# ---------------------------------------------------------------------------
# Fake orchestrator
# ---------------------------------------------------------------------------
def _fake_orchestrator_cls(mission_id="mission-123", status="running", state=None):
    """Return a fake SwarmsOrchestrator class for patching."""
    class FakeOrchestrator:
        def __init__(self, brain_path):
            self.brain_path = brain_path
            self._active_missions = state or {}

        async def start_mission(self, mission_goal, swarm_type, agents):
            return {"mission_id": mission_id, "status": status}

    return FakeOrchestrator


# ---------------------------------------------------------------------------
# get_brain_path
# ---------------------------------------------------------------------------
class TestGetBrainPath:
    def test_env_var_set_and_exists(self, tmp_path, monkeypatch):
        brain = tmp_path / "brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        assert get_brain_path() == brain

    def test_env_var_set_but_missing_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / "nope"))
        # cwd has .brain
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.chdir(tmp_path)
        assert get_brain_path() == brain

    def test_cwd_brain_exists(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.chdir(tmp_path)
        assert get_brain_path() == brain

    def test_parent_brain_exists(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        brain = tmp_path / ".brain"
        brain.mkdir()
        sub = tmp_path / "sub" / "deep"
        sub.mkdir(parents=True)
        monkeypatch.chdir(sub)
        assert get_brain_path() == brain

    def test_ultimate_fallback(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        # No .brain anywhere
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        result = get_brain_path()
        assert result == Path(".brain")


# ---------------------------------------------------------------------------
# _orchestrate_swarm
# ---------------------------------------------------------------------------
class TestOrchestrateSwarm:
    def test_success_default_agents(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        fake = _fake_orchestrator_cls()
        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", fake):
            result = _orchestrate_swarm("do something")
        assert result["success"] is True
        assert result["mission_id"] == "mission-123"
        assert result["status"] == "running"
        assert result["agents"] == ["developer", "critic"]
        assert "check_results" in result
        assert "check_state" in result

    def test_success_custom_agents(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        fake = _fake_orchestrator_cls()
        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", fake):
            result = _orchestrate_swarm("mission", agents=["researcher", "architect"])
        assert result["agents"] == ["researcher", "architect"]

    def test_success_none_agents_defaults(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        fake = _fake_orchestrator_cls()
        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", fake):
            result = _orchestrate_swarm("mission", agents=None)
        assert result["agents"] == ["developer", "critic"]

    def test_exception_returns_failure(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        class BoomOrchestrator:
            def __init__(self, brain_path):
                raise RuntimeError("init failed")

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", BoomOrchestrator):
            result = _orchestrate_swarm("mission")
        assert result["success"] is False
        assert "init failed" in result["error"]
        assert "Swarm failed to start" in result["message"]

    def test_missing_mission_id_defaults_unknown(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        class FakeNoId:
            def __init__(self, brain_path):
                pass

            async def start_mission(self, mission_goal, swarm_type, agents):
                return {"status": "running"}  # no mission_id

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", FakeNoId):
            result = _orchestrate_swarm("mission")
        assert result["mission_id"] == "unknown"
        assert result["status"] == "running"

    def test_missing_status_defaults_unknown(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        class FakeNoStatus:
            def __init__(self, brain_path):
                pass

            async def start_mission(self, mission_goal, swarm_type, agents):
                return {"mission_id": "m1"}  # no status

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", FakeNoStatus):
            result = _orchestrate_swarm("mission")
        assert result["mission_id"] == "m1"
        assert result["status"] == "unknown"

    def test_running_loop_path(self, monkeypatch, tmp_path):
        """Exercise the branch where a running loop is detected (nest_asyncio)."""
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        fake = _fake_orchestrator_cls()

        async def _runner():
            # Inside a running loop, _orchestrate_swarm should use
            # loop.run_until_complete (reentrant via nest_asyncio).
            with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", fake):
                return _orchestrate_swarm("mission")

        result = asyncio.run(_runner())
        assert result["success"] is True
        assert result["mission_id"] == "mission-123"

    def test_fallback_new_loop_path(self, monkeypatch, tmp_path):
        """Force asyncio.run to fail so the new-loop fallback is exercised."""
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        fake = _fake_orchestrator_cls()

        original_run = asyncio.run
        call_count = {"n": 0}

        def flaky_run(coro, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Close the coro to avoid warnings, then raise
                coro.close()
                raise RuntimeError("asyncio.run exploded")
            return original_run(coro, **kwargs)

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", fake), \
             patch("mcp_server_nucleus.runtime.swarm.asyncio.run", side_effect=flaky_run):
            result = _orchestrate_swarm("mission")
        assert result["success"] is True
        assert result["mission_id"] == "mission-123"

    def test_fallback_loop_also_fails_returns_error(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        class BrokenOrchestrator:
            def __init__(self, brain_path):
                pass

            async def start_mission(self, mission_goal, swarm_type, agents):
                raise RuntimeError("mission always fails")

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", BrokenOrchestrator):
            result = _orchestrate_swarm("mission")
        assert result["success"] is False
        assert "mission always fails" in result["error"]


# ---------------------------------------------------------------------------
# _get_swarm_status
# ---------------------------------------------------------------------------
class TestGetSwarmStatus:
    def test_mission_not_found(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        class FakeOrch:
            def __init__(self, brain_path):
                self._active_missions = {}

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", FakeOrch):
            result = _get_swarm_status("missing-mission")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_mission_found_no_artifacts(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        state = {"mission-1": {"status": "running", "step_count": 3, "cost_usd": 0.5}}

        class FakeOrch:
            def __init__(self, brain_path):
                self._active_missions = state

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", FakeOrch):
            result = _get_swarm_status("mission-1")
        assert result["success"] is True
        assert result["mission_id"] == "mission-1"
        assert result["status"] == "running"
        assert result["step_count"] == 3
        assert result["cost_usd"] == 0.5
        assert result["artifacts"] == []

    def test_mission_found_with_artifacts(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        # Create mission dir with artifacts
        mission_dir = brain / "swarms" / "mission-1"
        mission_dir.mkdir(parents=True)
        (mission_dir / "summary.md").write_text("done")
        (mission_dir / "report.txt").write_text("report")

        state = {"mission-1": {"status": "completed", "step_count": 5, "cost_usd": 1.2}}

        class FakeOrch:
            def __init__(self, brain_path):
                self._active_missions = state

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", FakeOrch):
            result = _get_swarm_status("mission-1")
        assert result["success"] is True
        assert set(result["artifacts"]) == {"summary.md", "report.txt"}

    def test_mission_found_missing_fields_default(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        # Non-empty dict but missing status/step_count/cost_usd keys
        state = {"mission-1": {"id": "mission-1"}}

        class FakeOrch:
            def __init__(self, brain_path):
                self._active_missions = state

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", FakeOrch):
            result = _get_swarm_status("mission-1")
        assert result["success"] is True
        assert result["status"] == "unknown"
        assert result["step_count"] == 0
        assert result["cost_usd"] == 0

    def test_empty_state_dict_treated_as_not_found(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        # Empty dict value is falsy -> treated as not found
        state = {"mission-1": {}}

        class FakeOrch:
            def __init__(self, brain_path):
                self._active_missions = state

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", FakeOrch):
            result = _get_swarm_status("mission-1")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_status_exception_returns_error(self, monkeypatch, tmp_path):
        brain = tmp_path / ".brain"
        brain.mkdir()
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

        class BoomOrch:
            def __init__(self, brain_path):
                raise RuntimeError("status init failed")

        with patch("mcp_server_nucleus.runtime.orchestrator.SwarmsOrchestrator", BoomOrch):
            result = _get_swarm_status("any")
        assert result["success"] is False
        assert "status init failed" in result["error"]
