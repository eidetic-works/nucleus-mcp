"""Tests for the cold-start acceptance endpoint instrument (PRINCIPAL G1 crit 2).

Authority: docs/PRINCIPAL.md:71-74.

The instrument wires THREE existing nucleus capabilities end-to-end:
  1. ``cli.init_brain_default`` — the EXISTING brain scaffold.
  2. The project-local ``.mcp.json`` config write (EXISTING pattern from
     ``cli._finish_init_with_value`` step a).
  3. ``engram_ops._brain_write_engram_impl`` + ``_brain_search_engrams_impl``
     — the EXISTING engram write + substring search.

These tests assert:
  1. The instrument PASSes: config written AND seed engram recalled.
  2. The recalled value is captured (on-screen proof — not a no-op).
  3. Wall time is measured to the acceptance endpoint and is within budget.
  4. The instrument is rerunnable (second run produces a fresh record).
  5. A missing config (simulated) is detected as FAIL — silence cannot pass.
  6. The instrument is named and cites its principal authority in the run log.
"""

import json
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.cold_start_instrument import (
    INSTRUMENT_NAME,
    run_cold_start_instrument,
    _evidence_log_path,
)


@pytest.fixture
def isolated_brain(tmp_path, monkeypatch):
    """Isolated brain + env so the instrument doesn't touch the real .brain.

    Unsets NUCLEUS_RELAY_URL so the relay falls back to local file transport
    instead of trying to HTTP POST to the (down) remote relay.
    """
    brain = tmp_path / "brain"
    brain.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    monkeypatch.delenv("NUCLEUS_RELAY_URL", raising=False)
    monkeypatch.delenv("NUCLEUS_RELAY_BEARER", raising=False)
    return brain


def _read_run_log(brain: Path) -> list[dict]:
    path = _evidence_log_path(brain)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().strip().splitlines() if line]


def test_cold_start_passes(isolated_brain):
    """The instrument PASSes: config written AND seed engram recalled."""
    result = run_cold_start_instrument(brain_path=isolated_brain)
    assert result["verdict"] == "PASS", result
    assert result["config_written"] is True
    assert result["seed_engram_recalled"] is True


def test_recalled_value_captured(isolated_brain):
    """The recalled value is captured — on-screen proof, not a no-op."""
    result = run_cold_start_instrument(brain_path=isolated_brain)
    assert result["verdict"] == "PASS", result
    recalled = result.get("recalled_value")
    assert recalled is not None
    assert "Nucleus initialized" in recalled
    # The seed value and recalled value must agree (memory survived).
    assert result.get("seed_value") == recalled


def test_wall_time_measured_and_within_budget(isolated_brain):
    """Wall time is measured to the acceptance endpoint and within the 5-min budget."""
    result = run_cold_start_instrument(brain_path=isolated_brain)
    assert result["verdict"] == "PASS", result
    wall = result.get("wall_time_seconds")
    assert wall is not None
    assert isinstance(wall, (int, float))
    assert wall > 0  # measured, not a zero no-op
    assert result["within_budget"] is True
    assert wall <= 300  # G1 criterion 2: ≤5 min


def test_rerunnable_produces_fresh_record(isolated_brain):
    """A second run appends a new record (rerunnable, not one-shot)."""
    r1 = run_cold_start_instrument(brain_path=isolated_brain)
    r2 = run_cold_start_instrument(brain_path=isolated_brain)
    assert r1["run_id"] != r2["run_id"]
    records = _read_run_log(isolated_brain)
    assert len(records) >= 2
    assert records[-1]["run_id"] == r2["run_id"]


def test_run_log_named_and_authority_cited(isolated_brain):
    """The run log record is named and cites its principal authority."""
    run_cold_start_instrument(brain_path=isolated_brain)
    records = _read_run_log(isolated_brain)
    last = records[-1]
    assert last["instrument"] == INSTRUMENT_NAME
    assert last["authority"] == "docs/PRINCIPAL.md:71-74"
    assert last["immutable_source"] == "docs/PRINCIPAL.md@principal-v3"
    assert last["verdict"] == "PASS"
    assert last["config_written"] is True
    assert last["seed_engram_recalled"] is True


def test_init_failure_detected_as_fail(isolated_brain, monkeypatch):
    """If init_brain_default crashes, the instrument reports FAIL — silence cannot pass."""
    import mcp_server_nucleus.runtime.cold_start_instrument as mod

    def _boom(_brain_path):
        raise RuntimeError("simulated init failure")

    monkeypatch.setattr(mod, "init_brain_default", _boom, raising=False)
    # The instrument imports init_brain_default lazily inside the function via
    # `from ..cli import init_brain_default`, so patch the cli module's symbol.
    import mcp_server_nucleus.cli as cli_mod
    monkeypatch.setattr(cli_mod, "init_brain_default", _boom)
    result = run_cold_start_instrument(brain_path=isolated_brain)
    assert result["verdict"] == "FAIL"
    assert "init_brain_default crashed" in result.get("error", "")
