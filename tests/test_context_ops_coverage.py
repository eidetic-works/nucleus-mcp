"""Comprehensive coverage tests for runtime/context_ops.py."""
import json
from pathlib import Path

import pytest


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def brain(tmp_path, monkeypatch):
    """Create a fully-structured brain directory and point env at it."""
    b = tmp_path / ".brain"
    for sub in ["ledger", "artifacts", "memory", "sessions", "workflows",
                "meta", "config", "engrams"]:
        (b / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(b))
    return b


def _write_state(brain, state):
    """Helper to write state.json."""
    (brain / "ledger" / "state.json").write_text(json.dumps(state))


# ─── _resource_context_impl ────────────────────────────────────────────────

class TestResourceContextImpl:
    def test_basic_context(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
        _write_state(brain, {
            "current_sprint": {"name": "Sprint1", "focus": "Fix bugs", "status": "active"},
            "active_agents": ["agent_a", "agent_b"],
            "top_3_leverage_actions": [
                {"action": "Fix critical bug"},
                {"action": "Write tests"},
                {"action": "Deploy"},
            ],
        })
        result = _resource_context_impl()
        assert "Nucleus Brain Context" in result
        assert "Sprint1" in result
        assert "Fix bugs" in result
        assert "agent_a" in result
        assert "Fix critical bug" in result

    def test_no_sprint(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
        _write_state(brain, {})
        result = _resource_context_impl()
        assert "No active sprint" in result
        assert "None" in result

    def test_actions_as_strings(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
        _write_state(brain, {
            "top_3_leverage_actions": ["do thing 1", "do thing 2"],
        })
        result = _resource_context_impl()
        assert "do thing 1" in result

    def test_no_actions(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
        _write_state(brain, {})
        result = _resource_context_impl()
        assert "(None set)" in result

    def test_with_events(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
        _write_state(brain, {})
        events = [
            json.dumps({"type": "task_assigned", "description": "Assigned task A to agent"}),
            json.dumps({"type": "sprint_started", "description": "Started sprint"}),
        ]
        (brain / "ledger" / "events.jsonl").write_text("\n".join(events) + "\n")
        result = _resource_context_impl()
        assert "task_assigned" in result
        assert "sprint_started" in result

    def test_no_events(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
        _write_state(brain, {})
        result = _resource_context_impl()
        assert "(No recent events)" in result

    def test_with_workflow(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
        _write_state(brain, {})
        (brain / "workflows" / "lead_agent_model.md").write_text("# Workflow")
        result = _resource_context_impl()
        assert "Workflow" in result
        assert "lead_agent_model.md" in result

    def test_no_workflow(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
        _write_state(brain, {})
        result = _resource_context_impl()
        assert "lead_agent_model.md" not in result

    def test_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.context_ops import _resource_context_impl
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _resource_context_impl()
        assert "Error loading context" in result


# ─── _activate_synthesizer_prompt ──────────────────────────────────────────

class TestActivateSynthesizerPrompt:
    def test_with_sprint(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _activate_synthesizer_prompt
        _write_state(brain, {
            "current_sprint": {"name": "Sprint X", "focus": "Build feature"}
        })
        result = _activate_synthesizer_prompt()
        assert "Synthesizer" in result
        assert "Sprint X" in result
        assert "Build feature" in result

    def test_no_sprint(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _activate_synthesizer_prompt
        _write_state(brain, {})
        result = _activate_synthesizer_prompt()
        assert "Unknown" in result

    def test_no_state_file(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _activate_synthesizer_prompt
        result = _activate_synthesizer_prompt()
        assert "Synthesizer" in result


# ─── _start_sprint_prompt ──────────────────────────────────────────────────

class TestStartSprintPrompt:
    def test_default_goal(self):
        from mcp_server_nucleus.runtime.context_ops import _start_sprint_prompt
        result = _start_sprint_prompt()
        assert "MVP Launch" in result
        assert "brain_update_state" in result

    def test_custom_goal(self):
        from mcp_server_nucleus.runtime.context_ops import _start_sprint_prompt
        result = _start_sprint_prompt("Ship v2.0")
        assert "Ship v2.0" in result

    def test_empty_goal(self):
        from mcp_server_nucleus.runtime.context_ops import _start_sprint_prompt
        result = _start_sprint_prompt("")
        assert "Goal:" in result


# ─── _cold_start_prompt ────────────────────────────────────────────────────

class TestColdStartPrompt:
    def test_basic(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {
            "current_sprint": {"name": "Sprint1", "focus": "Focus1", "status": "active"},
            "active_agents": ["agent_a"],
            "top_3_leverage_actions": [{"action": "Do A"}, {"action": "Do B"}],
        })
        result = _cold_start_prompt()
        assert "Nucleus Brain Card" in result
        assert "Sprint1" in result
        assert "Focus1" in result
        assert "Do A" in result

    def test_no_state(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        result = _cold_start_prompt()
        assert "Nucleus Brain Card" in result
        assert "No active sprint" in result

    def test_with_events(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        events = [
            json.dumps({"type": "task_started", "description": "Started task A"}),
            json.dumps({"type": "task_done", "description": "Completed task B"}),
        ]
        (brain / "ledger" / "events.jsonl").write_text("\n".join(events) + "\n")
        result = _cold_start_prompt()
        assert "task_started" in result
        assert "task_done" in result

    def test_no_events(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        result = _cold_start_prompt()
        assert "(No recent events)" in result

    def test_with_artifacts(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        (brain / "artifacts" / "doc1.md").write_text("content")
        (brain / "artifacts" / "doc2.md").write_text("content")
        result = _cold_start_prompt()
        assert "doc1.md" in result or "doc2.md" in result

    def test_no_artifacts(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        result = _cold_start_prompt()
        assert "None" in result

    def test_with_workflow(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        (brain / "workflows" / "lead_agent_model.md").write_text("# Workflow")
        result = _cold_start_prompt()
        assert "lead_agent_model.md" in result

    def test_with_engrams(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        engrams = [
            {"key": "lesson1", "context": "coding", "intensity": 8, "value": "Always test"},
            {"key": "lesson2", "context": "deploy", "intensity": 5, "value": "Check logs"},
        ]
        (brain / "memory" / "engrams.json").write_text(json.dumps(engrams))
        result = _cold_start_prompt()
        assert "Memory" in result
        assert "2 engrams" in result
        assert "lesson1" in result

    def test_engrams_empty_list(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        (brain / "memory" / "engrams.json").write_text("[]")
        result = _cold_start_prompt()
        assert "Memory" in result
        assert "0 engrams" in result

    def test_no_engrams_file(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        result = _cold_start_prompt()
        assert "No engrams file" in result

    def test_engrams_corrupt(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        (brain / "memory" / "engrams.json").write_text("not json")
        result = _cold_start_prompt()
        assert "Could not read engrams" in result

    def test_with_tasks(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        tasks = [
            {"id": "t1", "description": "Task 1", "status": "READY", "priority": 1},
            {"id": "t2", "description": "Task 2", "status": "IN_PROGRESS", "priority": 2},
            {"id": "t3", "description": "Task 3", "status": "DONE", "priority": 3},
        ]
        (brain / "ledger" / "tasks.json").write_text(json.dumps(tasks))
        result = _cold_start_prompt()
        assert "Top Tasks" in result
        assert "t1" in result
        assert "2 actionable" in result

    def test_tasks_no_actionable(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        tasks = [{"id": "t1", "description": "Task 1", "status": "DONE", "priority": 1}]
        (brain / "ledger" / "tasks.json").write_text(json.dumps(tasks))
        result = _cold_start_prompt()
        assert "No high-priority tasks" in result

    def test_tasks_empty(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        (brain / "ledger" / "tasks.json").write_text("[]")
        result = _cold_start_prompt()
        assert "No tasks found" in result

    def test_no_tasks_file(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        result = _cold_start_prompt()
        assert "No tasks found" in result

    def test_tasks_corrupt(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        (brain / "ledger" / "tasks.json").write_text("not json")
        result = _cold_start_prompt()
        assert "Could not read tasks" in result

    def test_with_mounts_dict(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        mounts = {"server_a": {"type": "mcp"}, "server_b": {"type": "mcp"}}
        (brain / "mounts.json").write_text(json.dumps(mounts))
        result = _cold_start_prompt()
        assert "Mounts" in result
        assert "server_a" in result
        assert "2 connected" in result

    def test_with_mounts_list(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        mounts = [{"name": "server_a"}, {"name": "server_b"}]
        (brain / "mounts.json").write_text(json.dumps(mounts))
        result = _cold_start_prompt()
        assert "Mounts" in result
        assert "2 connected" in result

    def test_mounts_empty_list(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        (brain / "mounts.json").write_text("[]")
        result = _cold_start_prompt()
        assert "No external servers mounted" in result

    def test_no_mounts_file(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        result = _cold_start_prompt()
        assert "No mounts configured" in result

    def test_mounts_corrupt(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        (brain / "mounts.json").write_text("not json")
        result = _cold_start_prompt()
        assert "Could not read mounts" in result

    def test_with_session_arc(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        # Mock _load_session_arc
        from mcp_server_nucleus.runtime import session_ops
        monkeypatch.setattr(session_ops, "_load_session_arc",
                            lambda b: {"recent_sessions": [
                                {"timestamp": "2026-01-15T10:00:00Z", "value": "Worked on feature X"}
                            ], "todays_focus": "Fix bugs"})
        result = _cold_start_prompt()
        assert "Session Arc" in result
        assert "feature X" in result
        assert "Today's focus" in result

    def test_session_arc_no_recent(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        from mcp_server_nucleus.runtime import session_ops
        monkeypatch.setattr(session_ops, "_load_session_arc",
                            lambda b: {"recent_sessions": []})
        result = _cold_start_prompt()
        assert "Session Arc" not in result

    def test_session_arc_exception(self, brain, monkeypatch):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        from mcp_server_nucleus.runtime import session_ops
        def _raise(b):
            raise Exception("arc error")
        monkeypatch.setattr(session_ops, "_load_session_arc", _raise)
        result = _cold_start_prompt()
        assert "Session Arc" not in result

    def test_with_compounding_cycle(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        cycle = {
            "cycle_id": "2026-W03",
            "weekly_score_start": 42,
            "days": {
                today: {"action": "build", "completed": True},
                "2026-01-14": {"action": "test", "completed": True},
            }
        }
        (brain / "meta" / "compounding_cycle.json").write_text(json.dumps(cycle))
        result = _cold_start_prompt()
        assert "Compounding Pulse" in result
        assert "2026-W03" in result

    def test_compounding_cycle_no_score(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        cycle = {"cycle_id": "W1", "days": {}}
        (brain / "meta" / "compounding_cycle.json").write_text(json.dumps(cycle))
        result = _cold_start_prompt()
        assert "Score: pending" in result

    def test_no_compounding_cycle(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        result = _cold_start_prompt()
        assert "Compounding Pulse" not in result

    def test_compounding_cycle_corrupt(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        (brain / "meta" / "compounding_cycle.json").write_text("not json")
        result = _cold_start_prompt()
        assert "Compounding Pulse" not in result

    def test_actions_as_strings(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {
            "top_3_leverage_actions": ["action one", "action two"],
        })
        result = _cold_start_prompt()
        assert "action one" in result

    def test_no_actions(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {})
        result = _cold_start_prompt()
        assert "None set" in result

    def test_agents_as_dicts(self, brain):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        _write_state(brain, {
            "active_agents": [{"codename": "shadow"}, {"codename": "phantom"}],
        })
        result = _cold_start_prompt()
        assert "shadow" in result
        assert "phantom" in result

    def test_exception(self, monkeypatch):
        from mcp_server_nucleus.runtime.context_ops import _cold_start_prompt
        monkeypatch.delenv("NUCLEUS_BRAIN_PATH", raising=False)
        monkeypatch.delenv("NUCLEAR_BRAIN_PATH", raising=False)
        monkeypatch.chdir("/tmp")
        result = _cold_start_prompt()
        assert "Could not load brain state" in result
