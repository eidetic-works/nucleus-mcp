"""Comprehensive tests for mcp_server_nucleus.runtime.agent.

Covers DecisionMade, ActionRequested, EphemeralAgent (run, _run_llm,
_run_heuristic, _execute_tool, _compute_context_hash, _emit_decision),
get_brain_path_internal.
"""
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from mcp_server_nucleus.runtime.agent import (
    DecisionMade,
    ActionRequested,
    EphemeralAgent,
    get_brain_path_internal,
)


@pytest.fixture
def brain_env(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    return brain


# ── get_brain_path_internal ──

class TestGetBrainPathInternal:
    def test_with_env(self, brain_env):
        assert get_brain_path_internal() == brain_env

    def test_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        result = get_brain_path_internal()
        assert result == Path("./.brain")


# ── DecisionMade ──

class TestDecisionMade:
    def test_init(self):
        d = DecisionMade("dec-1", "because", "hash123", confidence=0.8)
        assert d.decision_id == "dec-1"
        assert d.reasoning == "because"
        assert d.context_hash == "hash123"
        assert d.confidence == 0.8
        assert d.timestamp is not None

    def test_to_dict(self):
        d = DecisionMade("dec-1", "because", "hash123", confidence=0.8)
        result = d.to_dict()
        assert result["decision_id"] == "dec-1"
        assert result["reasoning"] == "because"
        assert result["context_hash"] == "hash123"
        assert result["confidence"] == 0.8
        assert "timestamp" in result

    def test_default_confidence(self):
        d = DecisionMade("dec-1", "because", "hash123")
        assert d.confidence == 1.0


# ── ActionRequested ──

class TestActionRequested:
    def test_init(self):
        a = ActionRequested("act-1", "dec-1", "my_tool", {"arg": "val"})
        assert a.action_id == "act-1"
        assert a.decision_id == "dec-1"
        assert a.tool_name == "my_tool"
        assert a.args == {"arg": "val"}


# ── EphemeralAgent ──

class TestEphemeralAgentInit:
    def test_init_basic(self, brain_env):
        context = {"persona": "developer", "intent": "build something", "tools": []}
        agent = EphemeralAgent(context)
        assert agent.context == context
        assert agent.active is True
        assert agent.history == []
        assert agent._decision_ledger == []

    def test_init_with_model(self, brain_env):
        model = MagicMock()
        context = {"persona": "developer", "intent": "test", "tools": []}
        agent = EphemeralAgent(context, model=model)
        assert agent.model == model

    def test_init_with_timeout(self, brain_env):
        context = {"persona": "developer", "intent": "test", "tools": []}
        agent = EphemeralAgent(context, timeout_seconds=60)
        assert agent._timeout_seconds == 60


# ── _compute_context_hash ──

class TestComputeContextHash:
    def test_basic_hash(self, brain_env):
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        h = agent._compute_context_hash([])
        assert len(h) == 16

    def test_hash_changes_with_history(self, brain_env):
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        h1 = agent._compute_context_hash([])
        h2 = agent._compute_context_hash(["step 1"])
        assert h1 != h2

    def test_hash_deterministic(self, brain_env):
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        h1 = agent._compute_context_hash(["step 1"])
        h2 = agent._compute_context_hash(["step 1"])
        assert h1 == h2

    def test_hash_with_tools(self, brain_env):
        context = {"persona": "dev", "intent": "test",
                   "tools": [{"name": "tool1"}, {"name": "tool2"}]}
        agent = EphemeralAgent(context)
        h = agent._compute_context_hash([])
        assert len(h) == 16


# ── _emit_decision ──

class TestEmitDecision:
    def test_emits_decision(self, brain_env):
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        decision = agent._emit_decision("my_tool", {"arg": 1}, "reasoning", [])
        assert decision.decision_id.startswith("dec-")
        assert "my_tool" in decision.reasoning
        assert len(agent._decision_ledger) == 1

    def test_emits_multiple_decisions(self, brain_env):
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        agent._emit_decision("tool1", {}, "r1", [])
        agent._emit_decision("tool2", {}, "r2", [])
        assert len(agent._decision_ledger) == 2


# ── run (heuristic mode) ──

class TestRunHeuristic:
    @pytest.mark.asyncio
    async def test_run_heuristic_no_match(self, brain_env):
        context = {"persona": "dev", "intent": "something random", "tools": []}
        agent = EphemeralAgent(context)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        result = await agent.run()
        assert "Heuristic" in result

    @pytest.mark.asyncio
    async def test_run_heuristic_list_services(self, brain_env):
        context = {
            "persona": "devops",
            "intent": "list all services",
            "tools": [{"name": "render_list_services", "description": "List services"}],
        }
        agent = EphemeralAgent(context)
        # Mock execution manager
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "Heuristic" in result

    @pytest.mark.asyncio
    async def test_run_heuristic_deploy(self, brain_env):
        context = {
            "persona": "devops",
            "intent": "deploy the service",
            "tools": [{"name": "render_deploy_service", "description": "Deploy"},
                      {"name": "render_list_services", "description": "List"}],
        }
        agent = EphemeralAgent(context)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "Heuristic" in result

    @pytest.mark.asyncio
    async def test_run_spawn_failure(self, brain_env):
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        agent._execution_manager = MagicMock()
        agent._execution_manager.spawn_agent.side_effect = RuntimeError("rate limited")
        result = await agent.run()
        assert "spawn failed" in result


# ── run (LLM mode) ──

class TestRunLLM:
    @pytest.mark.asyncio
    async def test_run_llm_mission_complete(self, brain_env):
        context = {
            "persona": "Synthesizer",
            "intent": "summarize results",
            "tools": [],
            "system_prompt": "You are a synthesizer.",
            "session_id": "test-session-123",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="Here is the final summary. MISSION_COMPLETE")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "Mode: LLM" in result
        assert "Mission complete" in result

    @pytest.mark.asyncio
    async def test_run_llm_tool_call(self, brain_env):
        context = {
            "persona": "developer",
            "intent": "build a feature",
            "tools": [{"name": "brain_write", "description": "Write to brain",
                       "parameters": {}}],
            "system_prompt": "You are a developer.",
            "session_id": "test-session",
        }
        model = MagicMock()
        # First response: tool call
        tool_response = MagicMock()
        tool_response.text = '```json\n{"tool": "brain_write", "args": {"key": "val"}}\n```'
        # Second response: mission complete
        complete_response = MagicMock()
        complete_response.text = "Done. MISSION_COMPLETE"
        model.generate_content.side_effect = [tool_response, complete_response]
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "Tool detected" in result

    @pytest.mark.asyncio
    async def test_run_llm_none_response(self, brain_env):
        context = {
            "persona": "developer",
            "intent": "do something",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = None
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "LLM" in result

    @pytest.mark.asyncio
    async def test_run_llm_no_text_attribute(self, brain_env):
        context = {
            "persona": "developer",
            "intent": "do something",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        response = MagicMock()
        del response.text
        response.candidates = []
        model.generate_content.return_value = response
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "LLM" in result

    @pytest.mark.asyncio
    async def test_run_llm_exception(self, brain_env):
        context = {
            "persona": "developer",
            "intent": "do something",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.side_effect = RuntimeError("API error")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "LLM Error" in result


# ── _execute_tool ──

class TestExecuteTool:
    def test_tool_not_found(self, brain_env):
        context = {"persona": "dev", "intent": "test", "tools": [],
                   "capability_instances": []}
        agent = EphemeralAgent(context)
        result = agent._execute_tool("nonexistent", {})
        assert "not found" in result

    def test_tool_found_in_capability(self, brain_env):
        cap = MagicMock()
        cap.get_tools.return_value = [{"name": "my_tool"}]
        cap.execute_tool.return_value = "tool result"
        context = {
            "persona": "dev", "intent": "test", "tools": [],
            "capability_instances": [cap],
        }
        agent = EphemeralAgent(context)
        result = agent._execute_tool("my_tool", {"arg": 1})
        assert result == "tool result"
        cap.execute_tool.assert_called_once_with("my_tool", {"arg": 1})

    def test_tool_with_ipc_token(self, brain_env):
        cap = MagicMock()
        cap.get_tools.return_value = [{"name": "my_tool"}]
        cap.execute_tool.return_value = "result"
        context = {
            "persona": "dev", "intent": "test", "tools": [],
            "capability_instances": [cap],
        }
        agent = EphemeralAgent(context)
        # Set a mock IPC token
        mock_token = MagicMock()
        mock_token.token_id = "tok-123"
        agent._current_ipc_token = mock_token
        result = agent._execute_tool("my_tool", {})
        assert result == "result"
        assert agent._current_ipc_token is None  # consumed

    def test_tool_ipc_token_exception(self, brain_env):
        cap = MagicMock()
        cap.get_tools.return_value = [{"name": "my_tool"}]
        cap.execute_tool.return_value = "result"
        context = {
            "persona": "dev", "intent": "test", "tools": [],
            "capability_instances": [cap],
        }
        agent = EphemeralAgent(context)
        mock_token = MagicMock()
        mock_token.token_id = "tok-123"
        agent._current_ipc_token = mock_token
        # IPC manager will raise - should not block execution
        with patch("mcp_server_nucleus.runtime.agent.get_ipc_auth_manager",
                   side_effect=RuntimeError("ipc error")):
            result = agent._execute_tool("my_tool", {})
        assert result == "result"

    def test_tool_ipc_valid_token(self, brain_env):
        cap = MagicMock()
        cap.get_tools.return_value = [{"name": "my_tool"}]
        cap.execute_tool.return_value = "result"
        context = {
            "persona": "dev", "intent": "test", "tools": [],
            "capability_instances": [cap],
        }
        agent = EphemeralAgent(context)
        mock_token = MagicMock()
        mock_token.token_id = "tok-123"
        agent._current_ipc_token = mock_token
        mock_ipc = MagicMock()
        mock_ipc.validate_token.return_value = (True, None)
        with patch("mcp_server_nucleus.runtime.agent.get_ipc_auth_manager",
                   return_value=mock_ipc):
            result = agent._execute_tool("my_tool", {"arg": 1})
        assert result == "result"
        mock_ipc.consume_token.assert_called_once()


# ── run (LLM mode - critic intervention) ──

class TestRunLLMCritic:
    @pytest.mark.asyncio
    async def test_critic_intervention_tool_call(self, brain_env):
        """Test that critic intervention leads to tool call after retry."""
        context = {
            "persona": "developer",
            "intent": "build a feature",
            "tools": [{"name": "brain_write", "description": "Write to brain",
                       "parameters": {}}],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        # First response: no tool call (triggers critic)
        no_tool_response = MagicMock()
        no_tool_response.text = "I think we should write to the brain."
        # Critic retry: tool call
        tool_response = MagicMock()
        tool_response.text = '```json\n{"tool": "brain_write", "args": {"key": "val"}}\n```'
        # Third response: mission complete
        complete_response = MagicMock()
        complete_response.text = "Done. MISSION_COMPLETE"
        model.generate_content.side_effect = [no_tool_response, tool_response, complete_response]
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "Tool detected" in result

    @pytest.mark.asyncio
    async def test_critic_intervention_no_tool_after_retry(self, brain_env):
        """Test that critic intervention with no tool call saves orphan output."""
        context = {
            "persona": "developer",
            "intent": "build a feature",
            "tools": [{"name": "brain_write", "description": "Write to brain",
                       "parameters": {}}],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        # First response: no tool call
        no_tool_response = MagicMock()
        no_tool_response.text = "I think we should write to the brain."
        # Critic retry: still no tool call
        no_tool_retry = MagicMock()
        no_tool_retry.text = "I still don't want to call a tool."
        model.generate_content.side_effect = [no_tool_response, no_tool_retry]
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "failed to call tool" in result

    @pytest.mark.asyncio
    async def test_llm_final_answer_not_synthesizer(self, brain_env):
        """Test MISSION_COMPLETE detection for non-Synthesizer persona."""
        context = {
            "persona": "developer",
            "intent": "build a feature",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="All done. MISSION_COMPLETE")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "Mission complete" in result

    @pytest.mark.asyncio
    async def test_llm_final_answer_marker(self, brain_env):
        """Test FINAL_ANSWER detection."""
        context = {
            "persona": "developer",
            "intent": "build a feature",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="The FINAL_ANSWER is 42.")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "Mission complete" in result

    @pytest.mark.asyncio
    async def test_llm_context_gate(self, brain_env):
        """Test context gate injects engrams when needs_context is True."""
        # Create some engrams in the brain
        engrams_dir = brain_env / "engrams"
        engrams_dir.mkdir(parents=True)
        (engrams_dir / "active.jsonl").write_text(
            json.dumps({"key": "auth_config", "value": "JWT validation settings"}) + "\n" +
            json.dumps({"key": "db_config", "value": "database connection settings"}) + "\n"
        )
        context = {
            "persona": "developer",
            "intent": "configure the authentication system",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="Done. MISSION_COMPLETE")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        # Mock tool enforcer to return needs_context=True
        mock_intent_result = MagicMock()
        mock_intent_result.needs_context = True
        mock_intent_result.has_requirements.return_value = False
        agent._tool_enforcer = MagicMock()
        agent._tool_enforcer.pre_flight.return_value = mock_intent_result
        agent._tool_enforcer.generate_enforcement_prompt.return_value = ""
        result = await agent.run()
        assert "Context Gate" in result

    @pytest.mark.asyncio
    async def test_llm_context_gate_no_engrams(self, brain_env):
        """Test context gate with no matching engrams."""
        context = {
            "persona": "developer",
            "intent": "configure something unrelated",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="Done. MISSION_COMPLETE")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        mock_intent_result = MagicMock()
        mock_intent_result.needs_context = True
        mock_intent_result.has_requirements.return_value = False
        agent._tool_enforcer = MagicMock()
        agent._tool_enforcer.pre_flight.return_value = mock_intent_result
        agent._tool_enforcer.generate_enforcement_prompt.return_value = ""
        result = await agent.run()
        assert "Context Gate" in result

    @pytest.mark.asyncio
    async def test_llm_intent_analysis_with_requirements(self, brain_env):
        """Test intent analysis with required tools."""
        context = {
            "persona": "developer",
            "intent": "deploy the application",
            "tools": [{"name": "render_deploy_service", "description": "Deploy",
                       "parameters": {}}],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="Done. MISSION_COMPLETE")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        mock_intent_result = MagicMock()
        mock_intent_result.needs_context = False
        mock_intent_result.has_requirements.return_value = True
        mock_intent_result.required_tools = ["render_deploy_service"]
        agent._tool_enforcer = MagicMock()
        agent._tool_enforcer.pre_flight.return_value = mock_intent_result
        agent._tool_enforcer.generate_enforcement_prompt.return_value = "Use the deploy tool."
        result = await agent.run()
        assert "Intent" in result or "Mission complete" in result

    @pytest.mark.asyncio
    async def test_llm_tool_discovery_filter(self, brain_env):
        """Test tool discovery filtering when >25 tools."""
        context = {
            "persona": "developer",
            "intent": "build a feature",
            "tools": [{"name": f"tool_{i}", "description": f"Tool {i}",
                       "parameters": {}} for i in range(30)],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="Done. MISSION_COMPLETE")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        agent._tool_recommender = MagicMock()
        agent._tool_recommender.filter_tools.return_value = context["tools"][:5]
        result = await agent.run()
        assert "Tool Discovery" in result

    @pytest.mark.asyncio
    async def test_llm_intent_analysis_exception(self, brain_env):
        """Test intent analysis exception is handled gracefully."""
        context = {
            "persona": "developer",
            "intent": "build a feature",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="Done. MISSION_COMPLETE")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        agent._tool_enforcer = MagicMock()
        agent._tool_enforcer.pre_flight.side_effect = RuntimeError("enforcer error")
        result = await agent.run()
        assert "Intent analysis skipped" in result


# ── Heuristic mode - brain ops ──

class TestRunHeuristicBrainOps:
    @pytest.mark.asyncio
    async def test_heuristic_brain_intent(self, brain_env):
        """Test heuristic mode with brain/task/scan intent (line 592-594)."""
        context = {
            "persona": "developer",
            "intent": "scan the brain for tasks",
            "tools": [],
        }
        agent = EphemeralAgent(context)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        result = await agent.run()
        assert "Heuristic" in result
        assert "No heuristic action map found" in result


# ── Snapshot verification ──

class TestSnapshotVerification:
    @pytest.mark.asyncio
    async def test_snapshot_verification_success(self, brain_env):
        """Test that state snapshots are taken and verified."""
        context = {
            "persona": "developer",
            "intent": "do something",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="Done. MISSION_COMPLETE")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        # Mock context manager with proper snapshot/verification
        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = "snap-123"
        mock_snapshot.state_hash = "abc123"
        mock_verification = MagicMock()
        mock_verification.is_valid = True
        mock_verification.mutations_detected = []
        agent._context_manager = MagicMock()
        agent._context_manager.take_snapshot.return_value = mock_snapshot
        agent._context_manager.verify_state_integrity.return_value = mock_verification
        await agent.run()
        # Verify snapshots were taken and persisted
        assert agent._context_manager.take_snapshot.call_count == 2
        agent._context_manager.verify_state_integrity.assert_called_once()
        assert agent._context_manager.persist_snapshot.call_count == 2

    @pytest.mark.asyncio
    async def test_snapshot_verification_mutations(self, brain_env):
        """Test that state mutations are detected."""
        context = {
            "persona": "developer",
            "intent": "do something",
            "tools": [],
            "system_prompt": "You are a developer.",
            "session_id": "test",
        }
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="Done. MISSION_COMPLETE")
        agent = EphemeralAgent(context, model=model)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = "snap-123"
        mock_snapshot.state_hash = "abc123"
        mock_verification = MagicMock()
        mock_verification.is_valid = False
        mock_verification.mutations_detected = ["unexpected_mutation"]
        agent._context_manager = MagicMock()
        agent._context_manager.take_snapshot.return_value = mock_snapshot
        agent._context_manager.verify_state_integrity.return_value = mock_verification
        await agent.run()
        # Verify verification was called
        agent._context_manager.verify_state_integrity.assert_called_once()


# ── _emit_decision persistence ──

class TestEmitDecisionPersistence:
    def test_emit_decision_persists_to_ledger(self, brain_env):
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        decision = agent._emit_decision("my_tool", {}, "reasoning", [])
        # Check decision ledger file was created
        decisions_file = brain_env / "ledger" / "decisions" / "decisions.jsonl"
        assert decisions_file.exists()
        saved = json.loads(decisions_file.read_text().strip())
        assert saved["decision_id"] == decision.decision_id

    def test_emit_decision_ipc_exception(self, brain_env):
        """Test _emit_decision handles IPC auth manager exception (lines 135-136)."""
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        with patch("mcp_server_nucleus.runtime.agent.get_ipc_auth_manager",
                   side_effect=RuntimeError("ipc error")):
            decision = agent._emit_decision("my_tool", {}, "reasoning", [])
        assert decision is not None
        assert agent._current_ipc_token is None

    def test_emit_decision_persistence_exception(self, brain_env):
        """Test _emit_decision handles persistence exception (lines 148-149)."""
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        # Make brain_path unwritable by making ledger/decisions a file
        decisions_dir = brain_env / "ledger" / "decisions"
        decisions_dir.parent.mkdir(parents=True)
        decisions_dir.write_text("blocking")  # Make it a file, not a dir
        decision = agent._emit_decision("my_tool", {}, "reasoning", [])
        assert decision is not None  # Should still return decision


class TestRunExceptionHandlers:
    @pytest.mark.asyncio
    async def test_run_commitment_ledger_exception(self, brain_env):
        """Test run() handles commitment_ledger exception (lines 181-182)."""
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        with patch("mcp_server_nucleus.runtime.agent.commitment_ledger.record_interaction",
                   side_effect=RuntimeError("ledger error")):
            result = await agent.run()
        assert "Heuristic" in result  # Should still run

    @pytest.mark.asyncio
    async def test_run_before_snapshot_exception(self, brain_env):
        """Test run() handles before snapshot exception (lines 199-200)."""
        context = {"persona": "dev", "intent": "test", "tools": []}
        agent = EphemeralAgent(context)
        agent._execution_manager = MagicMock()
        agent._execution_manager.complete_execution.return_value = None
        mock_exec = MagicMock()
        mock_exec.agent_id = "test-id"
        agent._execution_manager.spawn_agent.return_value = mock_exec
        agent._context_manager = MagicMock()
        agent._context_manager.take_snapshot.side_effect = RuntimeError("snapshot error")
        result = await agent.run()
        assert "Heuristic" in result  # Should still run
