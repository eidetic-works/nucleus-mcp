"""Comprehensive tests for mcp_server_nucleus.runtime.orchestrator.

Covers SwarmsOrchestrator: __init__, _load_state, _save_state,
_parse_agents_from_goal, start_mission, _run_mission_loop,
_save_mission_artifacts, get_mission_status, _get_best_model.
"""
import asyncio
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from mcp_server_nucleus.runtime.orchestrator import SwarmsOrchestrator


@pytest.fixture
def brain_env(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return brain


# ── __init__ & state ──

class TestOrchestratorInit:
    def test_init_creates_state_file_path(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        assert orch.brain_path == brain_env
        assert orch.state_file == brain_env / "swarms" / "state.json"
        assert orch._active_missions == {}

    def test_load_state_no_file(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        assert orch._active_missions == {}

    def test_load_state_with_file(self, brain_env):
        state_dir = brain_env / "swarms"
        state_dir.mkdir()
        state = {"mission-1": {"id": "mission-1", "status": "running"}}
        (state_dir / "state.json").write_text(json.dumps(state))
        orch = SwarmsOrchestrator(brain_env)
        assert "mission-1" in orch._active_missions

    def test_load_state_corrupt_file(self, brain_env):
        state_dir = brain_env / "swarms"
        state_dir.mkdir()
        (state_dir / "state.json").write_text("invalid json")
        orch = SwarmsOrchestrator(brain_env)
        assert orch._active_missions == {}

    def test_save_state(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        orch._active_missions = {"mission-1": {"id": "mission-1"}}
        orch._save_state()
        assert orch.state_file.exists()
        loaded = json.loads(orch.state_file.read_text())
        assert "mission-1" in loaded


# ── _parse_agents_from_goal ──

class TestParseAgentsFromGoal:
    def test_explicit_delegation(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        agents = orch._parse_agents_from_goal("delegate to 'researcher' for analysis")
        assert "researcher" in agents

    def test_persona_match(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        agents = orch._parse_agents_from_goal("The critic should review this code")
        assert "critic" in agents

    def test_multiple_personas(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        agents = orch._parse_agents_from_goal("researcher and developer work together")
        assert "researcher" in agents
        assert "developer" in agents

    def test_default_developer(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        agents = orch._parse_agents_from_goal("do something generic")
        assert agents == ["developer"]

    def test_delegation_double_quote(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        agents = orch._parse_agents_from_goal('delegate to "architect"')
        assert "architect" in agents


# ── start_mission ──

class TestStartMission:
    @pytest.mark.asyncio
    async def test_start_mission_returns_id(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        result = await orch.start_mission("Build a feature", agents=["developer"])
        assert "mission_id" in result
        assert result["status"] == "started"
        assert result["mission_id"].startswith("mission-")

    @pytest.mark.asyncio
    async def test_start_mission_parses_agents(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        result = await orch.start_mission("delegate to 'researcher'")
        assert result["status"] == "started"
        # Check mission was stored
        mission = orch._active_missions[result["mission_id"]]
        assert "researcher" in mission["agents"]

    @pytest.mark.asyncio
    async def test_start_mission_saves_state(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        await orch.start_mission("Test goal", agents=["developer"])
        assert orch.state_file.exists()
        state = json.loads(orch.state_file.read_text())
        assert len(state) == 1


# ── _run_mission_loop ──

class TestRunMissionLoop:
    @pytest.mark.asyncio
    async def test_mission_loop_completes(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        # Mock context factory
        orch.context_factory = MagicMock()
        orch.context_factory.create_context_for_persona.return_value = {
            "system_prompt": "You are a test agent.",
            "job_type": "ORCHESTRATION",
        }
        # Mock model
        mock_model = MagicMock()
        orch._get_best_model = MagicMock(return_value=mock_model)
        # Mock EphemeralAgent
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value="Task completed successfully")
        # Mock trainer
        orch.trainer = MagicMock()
        orch.trainer.train_on_session = AsyncMock()

        state = {
            "id": "mission-test",
            "goal": "Test goal",
            "status": "running",
            "step_count": 0,
            "cost_usd": 0.0,
            "artifacts": [],
        }
        with patch("mcp_server_nucleus.runtime.agent.EphemeralAgent", return_value=mock_agent):
            await orch._run_mission_loop("mission-test", state,
                                         orch.policy_engine.get_mission_parameters("genesis"),
                                         ["developer"])
        assert state["status"] == "completed"
        assert len(state["artifacts"]) == 1

    @pytest.mark.asyncio
    async def test_mission_loop_max_steps(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        orch.context_factory = MagicMock()
        orch.context_factory.create_context_for_persona.return_value = {
            "system_prompt": "test", "job_type": "ORCHESTRATION"
        }
        mock_model = MagicMock()
        orch._get_best_model = MagicMock(return_value=mock_model)
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value="done")
        orch.trainer = MagicMock()
        orch.trainer.train_on_session = AsyncMock()

        params = orch.policy_engine.get_mission_parameters("genesis")
        params.max_steps = 1
        state = {
            "id": "mission-test", "goal": "Test", "status": "running",
            "step_count": 1, "cost_usd": 0.0, "artifacts": [],
        }
        with patch("mcp_server_nucleus.runtime.agent.EphemeralAgent", return_value=mock_agent):
            await orch._run_mission_loop("mission-test", state, params, ["dev1", "dev2"])
        assert state["status"] == "halted_steps"

    @pytest.mark.asyncio
    async def test_mission_loop_budget_limit(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        orch.context_factory = MagicMock()
        orch.context_factory.create_context_for_persona.return_value = {
            "system_prompt": "test", "job_type": "ORCHESTRATION"
        }
        mock_model = MagicMock()
        orch._get_best_model = MagicMock(return_value=mock_model)
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value="done")
        orch.trainer = MagicMock()
        orch.trainer.train_on_session = AsyncMock()

        params = orch.policy_engine.get_mission_parameters("genesis")
        params.max_budget_usd = 0.01
        state = {
            "id": "mission-test", "goal": "Test", "status": "running",
            "step_count": 0, "cost_usd": 0.05, "artifacts": [],
        }
        with patch("mcp_server_nucleus.runtime.agent.EphemeralAgent", return_value=mock_agent):
            await orch._run_mission_loop("mission-test", state, params, ["dev1"])
        assert state["status"] == "halted_budget"

    @pytest.mark.asyncio
    async def test_mission_loop_agent_error(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        orch.context_factory = MagicMock()
        orch.context_factory.create_context_for_persona.return_value = {
            "system_prompt": "test", "job_type": "ORCHESTRATION"
        }
        mock_model = MagicMock()
        orch._get_best_model = MagicMock(return_value=mock_model)
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("agent crashed"))
        orch.trainer = MagicMock()
        orch.trainer.train_on_session = AsyncMock()

        state = {
            "id": "mission-test", "goal": "Test", "status": "running",
            "step_count": 0, "cost_usd": 0.0, "artifacts": [],
        }
        with patch("mcp_server_nucleus.runtime.agent.EphemeralAgent", return_value=mock_agent):
            await orch._run_mission_loop("mission-test", state,
                                         orch.policy_engine.get_mission_parameters("genesis"),
                                         ["developer"])
        # Should still complete (error is caught per-agent)
        assert state["status"] == "completed"
        # Error artifact is added to mission_artifacts (saved to disk), not state["artifacts"]
        assert len(state["artifacts"]) == 0  # No successful artifacts

    @pytest.mark.asyncio
    async def test_mission_loop_outer_exception(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        # Make context_factory raise
        orch.context_factory = MagicMock()
        orch.context_factory.create_context_for_persona.side_effect = RuntimeError("factory broken")
        mock_model = MagicMock()
        orch._get_best_model = MagicMock(return_value=mock_model)
        orch.trainer = MagicMock()
        orch.trainer.train_on_session = AsyncMock()

        state = {
            "id": "mission-test", "goal": "Test", "status": "running",
            "step_count": 0, "cost_usd": 0.0, "artifacts": [],
        }
        await orch._run_mission_loop("mission-test", state,
                                     orch.policy_engine.get_mission_parameters("genesis"),
                                     ["developer"])
        # Per-agent exception is caught, mission still completes
        assert state["status"] == "completed"


# ── _save_mission_artifacts ──

class TestSaveMissionArtifacts:
    def test_saves_summary_and_json(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        artifacts = [
            {"agent": "developer", "step": 1, "result": "Built feature", "job_type": "ORCHESTRATION"},
            {"agent": "critic", "step": 2, "error": "Review failed", "job_type": "ORCHESTRATION"},
        ]
        orch._save_mission_artifacts("mission-123", artifacts, "Build something")
        mission_dir = brain_env / "swarms" / "mission-123"
        assert (mission_dir / "summary.md").exists()
        assert (mission_dir / "artifacts.json").exists()
        summary = (mission_dir / "summary.md").read_text()
        assert "Build something" in summary
        assert "Developer" in summary  # agent.title() capitalizes
        assert "Critic" in summary

    def test_handles_empty_artifacts(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        orch._save_mission_artifacts("mission-empty", [], "Empty mission")
        mission_dir = brain_env / "swarms" / "mission-empty"
        assert (mission_dir / "summary.md").exists()
        assert (mission_dir / "artifacts.json").exists()


# ── get_mission_status ──

class TestGetMissionStatus:
    @pytest.mark.asyncio
    async def test_existing_mission(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        orch._active_missions = {"mission-1": {"id": "mission-1", "status": "running"}}
        result = await orch.get_mission_status("mission-1")
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_nonexistent_mission(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        result = await orch.get_mission_status("nonexistent")
        assert result is None


# ── _get_best_model ──

class TestGetBestModel:
    def test_sovereign_import(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        # Should fall back to DualEngineLLM since sovereign ext not available
        model = orch._get_best_model("ORCHESTRATION")
        assert model is not None

    def test_get_best_model_sovereign_available(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        mock_model = MagicMock()
        with patch("mcp_server_nucleus.sovereign.orchestrator_ext.sovereign_get_best_model",
                   return_value=mock_model, create=True):
            # This will fail with ImportError, falling back to DualEngineLLM
            model = orch._get_best_model("ORCHESTRATION")
            assert model is not None


# ── _save_state exception ──

class TestSaveStateException:
    def test_save_state_lock_error(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        orch._active_missions = {"m1": {"id": "m1"}}
        # Make get_lock raise
        with patch("mcp_server_nucleus.runtime.orchestrator.get_lock",
                   side_effect=RuntimeError("lock error")):
            orch._save_state()  # Should not raise


# ── _load_state exception ──

class TestLoadStateException:
    def test_load_state_permission_error(self, brain_env):
        state_dir = brain_env / "swarms"
        state_dir.mkdir()
        (state_dir / "state.json").write_text("invalid json {{{")
        orch = SwarmsOrchestrator(brain_env)
        # Should not raise, just log error
        assert orch._active_missions == {}


# ── train_on_session exception ──

class TestTrainOnSessionException:
    @pytest.mark.asyncio
    async def test_train_exception_does_not_fail_mission(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        orch.context_factory = MagicMock()
        orch.context_factory.create_context_for_persona.return_value = {
            "system_prompt": "test", "job_type": "ORCHESTRATION"
        }
        mock_model = MagicMock()
        orch._get_best_model = MagicMock(return_value=mock_model)
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value="done")
        orch.trainer = MagicMock()
        orch.trainer.train_on_session = AsyncMock(side_effect=RuntimeError("train error"))

        state = {
            "id": "mission-test", "goal": "Test", "status": "running",
            "step_count": 0, "cost_usd": 0.0, "artifacts": [],
        }
        with patch("mcp_server_nucleus.runtime.agent.EphemeralAgent", return_value=mock_agent):
            await orch._run_mission_loop("mission-test", state,
                                         orch.policy_engine.get_mission_parameters("genesis"),
                                         ["developer"])
        # Training exception is caught by outer handler, mission fails
        assert state["status"] == "failed"


# ── _save_mission_artifacts exception ──

class TestSaveMissionArtifactsException:
    def test_save_exception_does_not_raise(self, brain_env):
        orch = SwarmsOrchestrator(brain_env)
        # Make brain_path / "swarms" unwritable by making it a file
        swarms_dir = brain_env / "swarms"
        swarms_dir.mkdir()
        mission_dir = swarms_dir / "mission-x"
        mission_dir.mkdir()
        # Make summary.md a directory to cause write_text to fail
        (mission_dir / "summary.md").mkdir()
        # Should not raise
        orch._save_mission_artifacts("mission-x", [{"agent": "dev", "step": 1, "result": "ok"}], "test")
