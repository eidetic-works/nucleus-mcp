"""Comprehensive tests for mcp_server_nucleus.runtime.triggers.

Covers get_triggers_path, load_triggers, get_default_triggers, save_triggers,
evaluate_condition, resolve_agent, match_triggers, get_agents_for_event,
add_trigger, remove_trigger.
"""
import json
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime import triggers


# ── get_triggers_path ──

class TestGetTriggersPath:
    def test_returns_path(self, tmp_path):
        result = triggers.get_triggers_path(tmp_path)
        assert result == tmp_path / "ledger" / "triggers.json"


# ── get_default_triggers ──

class TestGetDefaultTriggers:
    def test_structure(self):
        result = triggers.get_default_triggers()
        assert result["version"] == "1.0"
        assert isinstance(result["triggers"], list)
        assert len(result["triggers"]) > 0

    def test_has_task_assigned(self):
        result = triggers.get_default_triggers()
        ids = [t["id"] for t in result["triggers"]]
        assert "task-assigned" in ids

    def test_has_wildcard_trigger(self):
        result = triggers.get_default_triggers()
        wildcards = [t for t in result["triggers"] if t["event_type"] == "*"]
        assert len(wildcards) > 0

    def test_all_triggers_have_required_fields(self):
        result = triggers.get_default_triggers()
        for t in result["triggers"]:
            assert "id" in t
            assert "event_type" in t
            assert "condition" in t
            assert "activates" in t
            assert "description" in t


# ── load_triggers ──

class TestLoadTriggers:
    def test_loads_from_disk(self, tmp_path):
        config = {"version": "2.0", "triggers": [{"id": "custom", "event_type": "custom_event",
                    "condition": "always", "activates": "agent1", "description": "test"}]}
        triggers_path = triggers.get_triggers_path(tmp_path)
        triggers_path.parent.mkdir(parents=True, exist_ok=True)
        triggers_path.write_text(json.dumps(config))
        result = triggers.load_triggers(tmp_path)
        assert result == config

    def test_returns_defaults_when_missing(self, tmp_path):
        result = triggers.load_triggers(tmp_path)
        assert result["version"] == "1.0"
        assert len(result["triggers"]) > 0


# ── save_triggers ──

class TestSaveTriggers:
    def test_saves_to_disk(self, tmp_path):
        config = {"version": "1.0", "triggers": []}
        triggers.save_triggers(tmp_path, config)
        triggers_path = triggers.get_triggers_path(tmp_path)
        assert triggers_path.exists()
        loaded = json.loads(triggers_path.read_text())
        assert loaded == config

    def test_creates_parent_dirs(self, tmp_path):
        config = {"version": "1.0", "triggers": []}
        triggers.save_triggers(tmp_path, config)
        assert (tmp_path / "ledger").exists()


# ── evaluate_condition ──

class TestEvaluateCondition:
    def test_always(self):
        assert triggers.evaluate_condition("always", {}) is True

    def test_always_with_event(self):
        assert triggers.evaluate_condition("always", {"severity": "CRITICAL"}) is True

    def test_severity_match(self):
        event = {"severity": "CRITICAL"}
        assert triggers.evaluate_condition("severity == 'CRITICAL'", event) is True

    def test_severity_no_match(self):
        event = {"severity": "ROUTINE"}
        assert triggers.evaluate_condition("severity == 'CRITICAL'", event) is False

    def test_severity_default_routine(self):
        event = {}
        assert triggers.evaluate_condition("severity == 'ROUTINE'", event) is True

    def test_payload_match(self):
        event = {"payload": {"review_type": "code"}}
        assert triggers.evaluate_condition("payload.review_type == 'code'", event) is True

    def test_payload_no_match(self):
        event = {"payload": {"review_type": "design"}}
        assert triggers.evaluate_condition("payload.review_type == 'code'", event) is False

    def test_payload_missing_field(self):
        event = {"payload": {}}
        assert triggers.evaluate_condition("payload.review_type == 'code'", event) is False

    def test_payload_no_payload(self):
        event = {}
        assert triggers.evaluate_condition("payload.review_type == 'code'", event) is False

    def test_event_type_match(self):
        event = {"event_type": "deploy"}
        assert triggers.evaluate_condition("event_type == 'deploy'", event) is True

    def test_event_type_no_match(self):
        event = {"event_type": "build"}
        assert triggers.evaluate_condition("event_type == 'deploy'", event) is False

    def test_unknown_condition(self):
        assert triggers.evaluate_condition("something weird", {}) is False

    def test_double_quote_severity(self):
        event = {"severity": "CRITICAL"}
        assert triggers.evaluate_condition('severity == "CRITICAL"', event) is True


# ── resolve_agent ──

class TestResolveAgent:
    def test_static_agent(self):
        assert triggers.resolve_agent("critic", {}) == "critic"

    def test_dynamic_payload(self):
        event = {"payload": {"target_agent": "researcher"}}
        assert triggers.resolve_agent("{{payload.target_agent}}", event) == "researcher"

    def test_dynamic_event_field(self):
        event = {"agent_name": "developer"}
        assert triggers.resolve_agent("{{agent_name}}", event) == "developer"

    def test_dynamic_missing_field(self):
        event = {"payload": {}}
        assert triggers.resolve_agent("{{payload.target_agent}}", event) is None

    def test_dynamic_missing_event(self):
        assert triggers.resolve_agent("{{agent_name}}", {}) is None

    def test_dynamic_with_spaces(self):
        event = {"payload": {"target_agent": "devops"}}
        assert triggers.resolve_agent("{{ payload.target_agent }}", event) == "devops"


# ── match_triggers ──

class TestMatchTriggers:
    def test_matches_default_task_assigned(self, tmp_path):
        event = {"event_type": "task_assigned", "payload": {"target_agent": "researcher"}}
        matched = triggers.match_triggers(tmp_path, event)
        agents = [m["agent"] for m in matched]
        assert "researcher" in agents

    def test_matches_wildcard_critical(self, tmp_path):
        event = {"event_type": "anything", "severity": "CRITICAL"}
        matched = triggers.match_triggers(tmp_path, event)
        agents = [m["agent"] for m in matched]
        assert "synthesizer" in agents

    def test_no_match_wrong_event_type(self, tmp_path):
        event = {"event_type": "unknown_event"}
        matched = triggers.match_triggers(tmp_path, event)
        # Should not match event-specific triggers (only wildcard with CRITICAL)
        assert all(m["agent"] != "critic" for m in matched)

    def test_uses_type_fallback(self, tmp_path):
        event = {"type": "implementation_complete"}
        matched = triggers.match_triggers(tmp_path, event)
        agents = [m["agent"] for m in matched]
        assert "critic" in agents

    def test_matched_trigger_has_fields(self, tmp_path):
        event = {"event_type": "implementation_complete"}
        matched = triggers.match_triggers(tmp_path, event)
        assert len(matched) > 0
        m = matched[0]
        assert "trigger_id" in m
        assert "agent" in m
        assert "description" in m
        assert "event" in m

    def test_dynamic_agent_not_found_skipped(self, tmp_path):
        event = {"event_type": "task_assigned", "payload": {}}
        matched = triggers.match_triggers(tmp_path, event)
        # task-assigned trigger should be skipped since target_agent is None
        assert all(m["agent"] is not None for m in matched)

    def test_custom_triggers_from_disk(self, tmp_path):
        config = {"version": "1.0", "triggers": [
            {"id": "custom", "event_type": "custom_evt", "condition": "always",
             "activates": "custom_agent", "description": "custom"}
        ]}
        triggers.save_triggers(tmp_path, config)
        event = {"event_type": "custom_evt"}
        matched = triggers.match_triggers(tmp_path, event)
        assert len(matched) == 1
        assert matched[0]["agent"] == "custom_agent"


# ── get_agents_for_event ──

class TestGetAgentsForEvent:
    def test_returns_unique_agents(self, tmp_path):
        event = {"event_type": "implementation_complete", "severity": "CRITICAL"}
        agents = triggers.get_agents_for_event(tmp_path, event)
        assert isinstance(agents, list)
        assert len(agents) == len(set(agents))  # unique

    def test_empty_when_no_match(self, tmp_path):
        event = {"event_type": "nonexistent"}
        agents = triggers.get_agents_for_event(tmp_path, event)
        assert agents == []


# ── add_trigger ──

class TestAddTrigger:
    def test_adds_trigger(self, tmp_path):
        new_trigger = {"id": "new1", "event_type": "new_evt", "condition": "always",
                       "activates": "agent1", "description": "new"}
        triggers.add_trigger(tmp_path, new_trigger)
        loaded = triggers.load_triggers(tmp_path)
        ids = [t["id"] for t in loaded["triggers"]]
        assert "new1" in ids

    def test_adds_to_existing(self, tmp_path):
        config = {"version": "1.0", "triggers": [
            {"id": "existing", "event_type": "evt", "condition": "always",
             "activates": "a", "description": "d"}
        ]}
        triggers.save_triggers(tmp_path, config)
        new_trigger = {"id": "new2", "event_type": "new", "condition": "always",
                       "activates": "b", "description": "d2"}
        triggers.add_trigger(tmp_path, new_trigger)
        loaded = triggers.load_triggers(tmp_path)
        assert len(loaded["triggers"]) == 2


# ── remove_trigger ──

class TestRemoveTrigger:
    def test_removes_existing(self, tmp_path):
        config = {"version": "1.0", "triggers": [
            {"id": "t1", "event_type": "e1", "condition": "always", "activates": "a", "description": "d"},
            {"id": "t2", "event_type": "e2", "condition": "always", "activates": "b", "description": "d"},
        ]}
        triggers.save_triggers(tmp_path, config)
        result = triggers.remove_trigger(tmp_path, "t1")
        assert result is True
        loaded = triggers.load_triggers(tmp_path)
        ids = [t["id"] for t in loaded["triggers"]]
        assert "t1" not in ids
        assert "t2" in ids

    def test_removes_nonexistent(self, tmp_path):
        config = {"version": "1.0", "triggers": [
            {"id": "t1", "event_type": "e1", "condition": "always", "activates": "a", "description": "d"},
        ]}
        triggers.save_triggers(tmp_path, config)
        result = triggers.remove_trigger(tmp_path, "nonexistent")
        assert result is False

    def test_removes_from_defaults(self, tmp_path):
        # No saved config — uses defaults
        result = triggers.remove_trigger(tmp_path, "task-assigned")
        assert result is True
        loaded = triggers.load_triggers(tmp_path)
        ids = [t["id"] for t in loaded["triggers"]]
        assert "task-assigned" not in ids
