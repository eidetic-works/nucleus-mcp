"""Coverage tests for runtime/lifecycle.py."""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.lifecycle import AgentState, LifecycleManager


def _brain(tmp_path: Path) -> Path:
    brain = tmp_path / ".brain"
    brain.mkdir()
    return brain


def test_agent_state_enum():
    assert AgentState.ACTIVE.value == "active"
    assert AgentState.STOPPED.value == "stopped"
    assert AgentState.CRASHED.value == "crashed"
    assert AgentState.TOMBSTONED.value == "tombstoned"


def test_init_creates_ledger_dir(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    assert (brain / "ledger").exists()


def test_register_agent(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    assert lm.get_state("a1") == AgentState.ACTIVE


def test_register_tombstoned_raises(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    lm.tombstone_agent("a1", "bad")
    with pytest.raises(PermissionError):
        lm.register_agent("a1")


def test_update_state_unknown_agent_noop(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    # should not raise
    lm.update_state("unknown", AgentState.STOPPED, "r")
    assert lm.get_state("unknown") == AgentState.STOPPED


def test_update_state_normal(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    lm.update_state("a1", AgentState.CRASHED, "boom")
    assert lm.get_state("a1") == AgentState.CRASHED


def test_tombstone_is_final(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    lm.tombstone_agent("a1", "bad")
    with pytest.raises(PermissionError):
        lm.update_state("a1", AgentState.ACTIVE, "revive")


def test_tombstone_again_is_noop(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    lm.tombstone_agent("a1", "bad")
    # setting tombstone again should not raise
    lm.update_state("a1", AgentState.TOMBSTONED, "again")
    assert lm.get_state("a1") == AgentState.TOMBSTONED


def test_record_heartbeat_active(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    lm.record_heartbeat("a1")
    ledger = json.loads((brain / "ledger" / "lifecycle.json").read_text())
    assert "last_heartbeat" in ledger["a1"]


def test_record_heartbeat_unknown_noop(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.record_heartbeat("unknown")
    # no file written
    assert not (brain / "ledger" / "lifecycle.json").exists()


def test_record_heartbeat_stopped_noop(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    lm.update_state("a1", AgentState.STOPPED, "r")
    lm.record_heartbeat("a1")


def test_get_state_unknown_returns_stopped(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    assert lm.get_state("nope") == AgentState.STOPPED


def test_can_execute_tombstoned_false(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    lm.tombstone_agent("a1", "bad")
    assert lm.can_execute("a1") is False


def test_can_execute_active_true(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    assert lm.can_execute("a1") is True


def test_is_alive_unknown_false(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    assert lm.is_alive("nope") is False


def test_is_alive_active_recent(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    assert lm.is_alive("a1") is True


def test_is_alive_active_old_heartbeat_false(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    # rewrite ledger with old heartbeat
    ledger = json.loads((brain / "ledger" / "lifecycle.json").read_text())
    old = (datetime.now() - timedelta(seconds=120)).isoformat()
    ledger["a1"]["last_heartbeat"] = old
    (brain / "ledger" / "lifecycle.json").write_text(json.dumps(ledger))
    assert lm.is_alive("a1", timeout_seconds=60) is False


def test_is_alive_not_active_false(tmp_path):
    brain = _brain(tmp_path)
    lm = LifecycleManager(brain)
    lm.register_agent("a1")
    lm.update_state("a1", AgentState.STOPPED, "r")
    assert lm.is_alive("a1") is False


def test_load_ledger_corrupt_returns_empty(tmp_path):
    brain = _brain(tmp_path)
    (brain / "ledger").mkdir(exist_ok=True)
    (brain / "ledger" / "lifecycle.json").write_text("not json")
    lm = LifecycleManager(brain)
    assert lm._load_ledger() == {}
