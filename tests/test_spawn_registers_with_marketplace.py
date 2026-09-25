"""Tests: spawn_prep auto-registers in CapabilityRegistry; spawn_close records interaction."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def charters_dir(tmp_path):
    """Stub charters directory with a minimal sonnet-helper charter."""
    d = tmp_path / "charters"
    d.mkdir()
    (d / "sonnet_helper.md").write_text("# Sonnet Helper Charter\nStub for tests.")
    return d


def test_spawn_prep_registers_in_registry(tmp_path, charters_dir):
    """spawn_prep registers the sub-agent in CapabilityRegistry."""
    from mcp_server_nucleus.runtime.org_delegate import spawn_prep, _INFLIGHT_SPAWNS
    from mcp_server_nucleus.runtime.marketplace import lookup_by_address

    _INFLIGHT_SPAWNS.clear()
    with patch("mcp_server_nucleus.runtime.marketplace.get_brain_path", return_value=tmp_path):
        prompt, spawn_id = spawn_prep(
            "sonnet_helper", "test brief", "claude-sonnet-4-5", "test_parent",
            charters_dir=charters_dir,
        )
        card = lookup_by_address("sonnet-helper@nucleus", brain_path=tmp_path)

    assert card is not None, "Card should be registered after spawn_prep"
    assert card.get("spawn_id") == spawn_id
    assert card.get("model") == "claude-sonnet-4-5"


def test_spawn_close_records_interaction(tmp_path, charters_dir):
    """spawn_prep + spawn_close writes a reputation interaction entry."""
    from mcp_server_nucleus.runtime.org_delegate import spawn_prep, spawn_close, _INFLIGHT_SPAWNS

    _INFLIGHT_SPAWNS.clear()
    with patch("mcp_server_nucleus.runtime.marketplace.get_brain_path", return_value=tmp_path):
        _, spawn_id = spawn_prep(
            "sonnet_helper", "brief", "claude-sonnet-4-5", "test_parent",
            charters_dir=charters_dir,
        )
        spawn_close(spawn_id, "response text", success=True)

    telemetry_file = tmp_path / "telemetry" / "relay_metrics.jsonl"
    assert telemetry_file.exists(), "Telemetry file should exist after spawn_close"
    lines = [json.loads(l) for l in telemetry_file.read_text().splitlines() if l.strip()]
    assert len(lines) >= 1
    assert lines[-1]["to_address"] == "sonnet-helper@nucleus"
    assert lines[-1]["success"] is True


def test_registry_failure_doesnt_block_spawn(tmp_path, charters_dir):
    """If register_tool raises, spawn_prep still returns a valid (prompt, spawn_id)."""
    from mcp_server_nucleus.runtime.org_delegate import spawn_prep, _INFLIGHT_SPAWNS

    _INFLIGHT_SPAWNS.clear()
    with patch("mcp_server_nucleus.runtime.marketplace.register_tool", side_effect=RuntimeError("registry down")):
        prompt, spawn_id = spawn_prep(
            "sonnet_helper", "brief", "claude-sonnet-4-5", "test_parent",
            charters_dir=charters_dir,
        )

    assert isinstance(prompt, str) and len(prompt) > 0
    assert isinstance(spawn_id, str) and spawn_id.startswith("spawn_")
