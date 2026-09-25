"""Unit tests for Orchestration Demand telemetry recorder and report generator."""

import json
import os
import sys
from pathlib import Path
from unittest import mock

pytest_plugins = ["pytest_asyncio"]
import pytest

from mcp_server_nucleus.tools import orchestration as orch_mod
from mcp_server_nucleus.tools._dispatch import _record_orchestration_demand


@pytest.fixture
def test_demand_log(tmp_path):
    log_path = tmp_path / "orchestration_demand.jsonl"
    with mock.patch.dict(os.environ, {"NUCLEUS_DEMAND_LOG": str(log_path)}):
        yield log_path


def _mock_mcp_and_helpers():
    tools = {}
    mcp = mock.MagicMock()
    mcp.tool = lambda **kwargs: lambda func: tools.update({func.__name__: func}) or func
    helpers = {
        "make_response": lambda ok, data=None, error=None: f"{ok}:{data}:{error}",
        "emit_event": lambda *a, **kw: None,
        "get_brain_path": lambda: None,
        "get_orch": lambda: None,
    }
    return mcp, helpers, tools


@pytest.mark.asyncio
async def test_recorder_records_real_facade_invocation(test_demand_log):
    mcp, helpers, tools = _mock_mcp_and_helpers()
    with mock.patch("mcp_server_nucleus.runtime.satellite_ops._get_satellite_view", return_value={}):
        with mock.patch("mcp_server_nucleus.runtime.satellite_ops._format_satellite_cli", return_value="sat_view"):
            orch_mod.register(mcp, helpers)

    nucleus_orchestration = tools["nucleus_orchestration"]
    res = await nucleus_orchestration("satellite", {})
    assert res is not None

    assert test_demand_log.exists()
    lines = [json.loads(l) for l in test_demand_log.read_text().strip().split("\n")]
    assert len(lines) == 1
    row = lines[0]
    assert row["facade"] == "nucleus_orchestration"
    assert row["action"] == "satellite"
    assert row["well_formed"] is True
    assert "ts" in row


@pytest.mark.asyncio
async def test_recorder_never_raises_on_error(test_demand_log):
    # Pass a path that raises an exception during write
    with mock.patch.dict(os.environ, {"NUCLEUS_DEMAND_LOG": "/unwritable_dir/non_existent.jsonl"}):
        # Should catch exception silently without raising
        _record_orchestration_demand("nucleus_orchestration", "satellite", {})


def test_report_logic_insufficient_when_log_missing(tmp_path):
    sys_path_save = list(sys.path)

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from scripts.orchestration_demand_report import generate_report

    missing_log = tmp_path / "non_existent.jsonl"
    report = generate_report(missing_log)

    assert report["log_status"] == "MISSING"
    assert report["recorder_proven"] is False
    assert report["overall_summary"]["INSUFFICIENT"] == 71
    assert report["overall_summary"]["CALLED"] == 0
    assert report["overall_summary"]["UNCALLED"] == 0

    sys.path = sys_path_save


def test_report_logic_called_and_uncalled(tmp_path):
    log_file = tmp_path / "demand.jsonl"
    row = {
        "ts": "2026-08-03T12:00:00+00:00",
        "facade": "nucleus_telemetry",
        "action": "get_llm_status",
        "caller": "test_agent",
        "well_formed": True,
        "params_well_formed": True,
    }
    log_file.write_text(json.dumps(row) + "\n")

    sys_path_save = list(sys.path)
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from scripts.orchestration_demand_report import generate_report

    report = generate_report(log_file)

    assert report["log_status"] == "READABLE"
    assert report["recorder_proven"] is True
    assert report["overall_summary"]["CALLED"] == 1
    assert report["overall_summary"]["UNCALLED"] == 70
    assert report["overall_summary"]["INSUFFICIENT"] == 0

    telemetry_actions = report["actions_detail"]["nucleus_telemetry"]
    assert telemetry_actions["get_llm_status"]["verdict"] == "CALLED"
    assert telemetry_actions["set_llm_tier"]["verdict"] == "UNCALLED"

    sys.path = sys_path_save
