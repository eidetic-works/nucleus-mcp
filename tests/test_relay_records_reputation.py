"""Atom 1: relay_post records reputation for the sender."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def isolated_brain(tmp_path, monkeypatch):
    """Route all Nucleus I/O to a throw-away tmp .brain directory."""
    brain_dir = tmp_path / ".brain"
    brain_dir.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain_dir))
    yield brain_dir


def test_relay_post_records_reputation(isolated_brain):
    """Posting a relay must append a telemetry event for the sender."""
    from mcp_server_nucleus.runtime.relay_ops import relay_post

    result = relay_post(
        to="cowork",
        subject="test subject",
        body="test body",
        sender="claude_code_main",
    )
    assert result["sent"] is True

    telemetry_file = isolated_brain / "telemetry" / "relay_metrics.jsonl"
    assert telemetry_file.exists(), (
        f"No telemetry file created at {telemetry_file}. "
        "relay_post Atom-1 reputation block may not be running."
    )

    lines = [ln for ln in telemetry_file.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 1, "Expected at least one reputation event"

    event = json.loads(lines[-1])
    assert event["to_address"] == "claude_code_main@nucleus"
    assert event["from_address"] == "relay_bus"
    assert event["success"] is True
    assert isinstance(event["latency_ms"], int)


def test_relay_post_reputation_failure_does_not_block(isolated_brain):
    """A crash inside ReputationSignals must never fail relay_post."""
    from mcp_server_nucleus.runtime import marketplace as _mp
    from mcp_server_nucleus.runtime.relay_ops import relay_post

    call_log = []

    def _boom(to_address, from_address, latency_ms, success, brain_path=None):
        call_log.append((to_address, from_address, success))
        raise RuntimeError("simulated telemetry failure")

    with patch.object(_mp.ReputationSignals, "record_interaction", staticmethod(_boom)):
        result = relay_post(
            to="cowork",
            subject="test subject",
            body="test body",
            sender="claude_code_main",
        )

    assert result["sent"] is True, (
        "relay_post must succeed even when reputation recording raises"
    )
    assert len(call_log) == 1, (
        f"record_interaction should have been called exactly once; called {len(call_log)}x"
    )
    assert call_log[0][0] == "claude_code_main@nucleus"
