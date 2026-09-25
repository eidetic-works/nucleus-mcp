"""Test that verifies the push model end-to-end."""
import json
from pathlib import Path
import pytest

from mcp_server_nucleus.runtime.task_ops import _add_task
from mcp_server_nucleus.runtime.posture import declare_posture, approve_posture

@pytest.fixture
def temp_brain(monkeypatch, tmp_path):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path))
    return str(tmp_path)

def test_push_model_e2e(temp_brain):
    """Test that adding a task with required_role routes a relay to the agent's bucket."""
    
    # Setup posture mapping principal to agy
    declare_posture(role="principal", approach="delegate", agent_id="agy")
    approve_posture()

    # Add a task
    _add_task(
        "test push model task",
        priority=3,
        source="test",
        task_id="test_push_e2e_1",
        required_role="principal",
        plan_ref="AGENT_OS_STATE.md#push-model",
    )

    # Verify relay in antigravity/ bucket
    agy_bucket = Path(temp_brain) / "relay" / "antigravity"
    assert agy_bucket.exists(), "antigravity bucket should exist"
    
    relays = list(agy_bucket.glob("*.json"))
    assert len(relays) == 1, "Expected 1 relay in antigravity bucket"
    
    msg = json.loads(relays[0].read_text())
    assert "[TASK]" in msg["subject"]
    assert "test_push_e2e_1" in msg["body"]
    assert "AGENT_OS_STATE.md#push-model" in msg["body"]
    assert msg["from"] == "task_scheduler"
