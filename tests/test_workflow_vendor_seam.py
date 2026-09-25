"""Targeted test for the workflow-to-vendor seam in mission orchestration.

Verifies the three-layer "worker-agnostic orchestration" goal: a mission whose
``agents`` list mixes a Claude persona and a vendor lane (``devin``) dispatches
the vendor node through the cross-vendor executor, integrates its captured
artifact into mission_artifacts + state, still runs the Claude node, and that
flag-OFF does NOT divert (byte-identical to Claude-only behavior).

The vendor executor (``run_swarm_vendor_persona``) and the Claude agent
(``EphemeralAgent``) are both mocked — no real CLI call, no real LLM call.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_nucleus.runtime.orchestrator import SwarmsOrchestrator


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def brain_env(tmp_path, monkeypatch):
    """A fresh brain dir with cross-vendor OFF by default (no env, no onboard)."""
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEUS_CROSS_VENDOR", raising=False)
    return brain


def _stub_claude_path(orch):
    """Wire mocks for the Claude-persona path so EphemeralAgent.run succeeds.

    Returns the mock_agent so callers can assert on it.
    """
    orch.context_factory = MagicMock()
    orch.context_factory.create_context_for_persona.return_value = {
        "system_prompt": "You are a test agent.",
        "job_type": "ORCHESTRATION",
    }
    mock_model = MagicMock()
    orch._get_best_model = MagicMock(return_value=mock_model)
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value="Claude agent completed the task")
    orch.trainer = MagicMock()
    orch.trainer.train_on_session = AsyncMock()
    return mock_agent


def _make_state(mission_id="mission-test", goal="Build and review a feature"):
    return {
        "id": mission_id,
        "goal": goal,
        "status": "running",
        "step_count": 0,
        "cost_usd": 0.0,
        "artifacts": [],
    }


# ── tests ─────────────────────────────────────────────────────────────────────

class TestWorkflowVendorSeam:
    @pytest.mark.asyncio
    async def test_mixed_lane_mission_integrates_vendor_artifact(self, brain_env):
        """agents=["developer", "devin"]: vendor node routes to the executor,
        its captured artifact flows into mission_artifacts + state, and the
        Claude node still runs."""
        orch = SwarmsOrchestrator(brain_env)
        mock_agent = _stub_claude_path(orch)

        vendor_artifact = {
            "agent": "devin",
            "step": 2,
            "job_type": "VENDOR_CLI:glm",
            "result": "devin produced a review",
            "vendor_status": "ok",
            "artifact_refs": [".brain/swarms/mission-test/summary.md"],
        }

        with patch("mcp_server_nucleus.runtime.agent.EphemeralAgent",
                   return_value=mock_agent), \
             patch("mcp_server_nucleus.runtime.vendor_dispatch.cross_vendor_enabled",
                   return_value=True), \
             patch("mcp_server_nucleus.runtime.vendor_dispatch.run_swarm_vendor_persona",
                   return_value=vendor_artifact) as mock_vendor:

            state = _make_state()
            params = orch.policy_engine.get_mission_parameters("genesis")
            await orch._run_mission_loop(
                "mission-test", state, params, ["developer", "devin"]
            )

        # Mission completed cleanly
        assert state["status"] == "completed"

        # Vendor node was dispatched to the executor (not the Claude path)
        mock_vendor.assert_called_once()
        kwargs = mock_vendor.call_args.kwargs
        assert kwargs["vendor"] == "devin"
        assert kwargs["mission_id"] == "mission-test"
        assert kwargs["step"] == 2

        # Both nodes produced artifacts; vendor artifact integrated into state
        assert len(state["artifacts"]) == 2
        assert state["artifacts"][0]["agent"] == "developer"
        vendor_state_artifact = state["artifacts"][1]
        assert vendor_state_artifact["agent"] == "devin"
        assert vendor_state_artifact["job_type"] == "VENDOR_CLI:glm"
        assert vendor_state_artifact["result"] == "devin produced a review"

        # Step count advanced for both nodes
        assert state["step_count"] == 2

        # Artifacts persisted to disk (mission_artifacts → summary.md + artifacts.json)
        mission_dir = brain_env / "swarms" / "mission-test"
        assert (mission_dir / "summary.md").exists()
        raw = json.loads((mission_dir / "artifacts.json").read_text())
        assert len(raw) == 2
        assert raw[0]["agent"] == "developer"
        assert raw[1]["agent"] == "devin"
        assert raw[1]["job_type"] == "VENDOR_CLI:glm"

    @pytest.mark.asyncio
    async def test_vendor_error_does_not_break_mission_loop(self, brain_env):
        """A vendor node error that escapes the internal handler is caught
        per-node; the mission loop continues and completes (mirrors Claude
        agent error handling)."""
        orch = SwarmsOrchestrator(brain_env)
        mock_agent = _stub_claude_path(orch)

        with patch("mcp_server_nucleus.runtime.agent.EphemeralAgent",
                   return_value=mock_agent), \
             patch("mcp_server_nucleus.runtime.vendor_dispatch.cross_vendor_enabled",
                   return_value=True), \
             patch("mcp_server_nucleus.runtime.vendor_dispatch.run_swarm_vendor_persona",
                   side_effect=RuntimeError("vendor CLI hung")) as mock_vendor:

            state = _make_state(goal="Build and review")
            params = orch.policy_engine.get_mission_parameters("genesis")
            await orch._run_mission_loop(
                "mission-test", state, params, ["developer", "devin"]
            )

        # Mission still completed — vendor error did NOT break the loop
        assert state["status"] == "completed"
        mock_vendor.assert_called_once()

        # Claude node ran successfully (artifact in state)
        assert len(state["artifacts"]) == 1
        assert state["artifacts"][0]["agent"] == "developer"

        # Step count advanced for both (error node still counts as a step)
        assert state["step_count"] == 2

        # The error artifact was captured in mission_artifacts (persisted to disk)
        raw = json.loads(
            (brain_env / "swarms" / "mission-test" / "artifacts.json").read_text()
        )
        assert len(raw) == 2
        assert raw[1]["agent"] == "devin"
        assert "error" in raw[1]

    @pytest.mark.asyncio
    async def test_vendor_internal_error_artifact_not_in_state(self, brain_env):
        """When run_swarm_vendor_persona catches internally and returns an
        error dict, the orchestrator treats it like a Claude agent error:
        the error artifact goes to mission_artifacts only, NOT state["artifacts"]
        — same asymmetry as the Claude error path."""
        orch = SwarmsOrchestrator(brain_env)
        mock_agent = _stub_claude_path(orch)

        vendor_error_artifact = {
            "agent": "devin",
            "step": 2,
            "error": "vendor dispatch failed: timeout",
        }

        with patch("mcp_server_nucleus.runtime.agent.EphemeralAgent",
                   return_value=mock_agent), \
             patch("mcp_server_nucleus.runtime.vendor_dispatch.cross_vendor_enabled",
                   return_value=True), \
             patch("mcp_server_nucleus.runtime.vendor_dispatch.run_swarm_vendor_persona",
                   return_value=vendor_error_artifact):

            state = _make_state(goal="Build and review")
            params = orch.policy_engine.get_mission_parameters("genesis")
            await orch._run_mission_loop(
                "mission-test", state, params, ["developer", "devin"]
            )

        assert state["status"] == "completed"

        # Claude node's artifact is in state; vendor error artifact is NOT
        assert len(state["artifacts"]) == 1
        assert state["artifacts"][0]["agent"] == "developer"

        # But the error artifact IS in mission_artifacts (persisted to disk)
        raw = json.loads(
            (brain_env / "swarms" / "mission-test" / "artifacts.json").read_text()
        )
        assert len(raw) == 2
        assert raw[1]["agent"] == "devin"
        assert "error" in raw[1]

    @pytest.mark.asyncio
    async def test_flag_off_does_not_divert(self, brain_env):
        """With cross-vendor OFF, a "devin" persona does NOT divert to the
        vendor executor — it falls through to the Claude agent path (byte-
        identical to a Claude-only mission)."""
        orch = SwarmsOrchestrator(brain_env)
        mock_agent = _stub_claude_path(orch)

        with patch("mcp_server_nucleus.runtime.agent.EphemeralAgent",
                   return_value=mock_agent), \
             patch("mcp_server_nucleus.runtime.vendor_dispatch.cross_vendor_enabled",
                   return_value=False), \
             patch("mcp_server_nucleus.runtime.vendor_dispatch.run_swarm_vendor_persona",
                   return_value={"agent": "devin", "error": "should not be called"}) as mock_vendor:

            state = _make_state(goal="Build and review")
            params = orch.policy_engine.get_mission_parameters("genesis")
            await orch._run_mission_loop(
                "mission-test", state, params, ["developer", "devin"]
            )

        # Vendor executor was NEVER called
        mock_vendor.assert_not_called()

        # Both nodes went through the Claude path
        assert state["status"] == "completed"
        assert len(state["artifacts"]) == 2
        assert state["artifacts"][0]["agent"] == "developer"
        assert state["artifacts"][1]["agent"] == "devin"  # ran as a Claude agent
        assert state["step_count"] == 2
