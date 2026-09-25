"""Coverage tests for mcp_server_nucleus.tools.orchestration."""
import json
import os
import time
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_nucleus.tools import orchestration as orch_mod


# ── _register_session_impl ──────────────────────────────────────

def test_register_session_impl_basic(tmp_path):
    sessions_path = tmp_path / "sessions.json"
    emit = mock.MagicMock()
    result = orch_mod._register_session_impl("conv1", "Testing", sessions_path=sessions_path, emit_event=emit)
    assert "Registered session" in result
    data = json.loads(sessions_path.read_text())
    assert "conv1" in data["sessions"]
    emit.assert_called_once()


def test_register_session_impl_with_optional_fields(tmp_path):
    sessions_path = tmp_path / "sessions.json"
    emit = mock.MagicMock()
    result = orch_mod._register_session_impl("conv2", "Dev work",
                                              role="sonnet_structure", tier="sonnet",
                                              charter_path="/charter.md",
                                              parent_session="parent1",
                                              sessions_path=sessions_path, emit_event=emit)
    assert "Registered session" in result
    data = json.loads(sessions_path.read_text())
    entry = data["sessions"]["conv2"]
    assert entry["role"] == "sonnet_structure"
    assert entry["tier"] == "sonnet"
    assert entry["charter_path"] == "/charter.md"
    assert entry["parent_session"] == "parent1"


def test_register_session_impl_invalid_tier(tmp_path):
    sessions_path = tmp_path / "sessions.json"
    with pytest.raises(ValueError, match="Invalid tier"):
        orch_mod._register_session_impl("conv3", "Test", tier="invalid",
                                        sessions_path=sessions_path)


def test_register_session_impl_role_tier_mismatch(tmp_path):
    sessions_path = tmp_path / "sessions.json"
    with pytest.raises(ValueError, match="must start with tier prefix"):
        orch_mod._register_session_impl("conv4", "Test", role="opus_role", tier="sonnet",
                                        sessions_path=sessions_path)


def test_register_session_impl_no_emit(tmp_path):
    sessions_path = tmp_path / "sessions.json"
    result = orch_mod._register_session_impl("conv5", "Test", sessions_path=sessions_path)
    assert "Registered session" in result
    # File should still be written
    data = json.loads(sessions_path.read_text())
    assert "conv5" in data["sessions"]


def test_register_session_impl_appends_to_existing(tmp_path):
    sessions_path = tmp_path / "sessions.json"
    sessions_path.write_text(json.dumps({"sessions": {"old": {"focus": "old"}}}))
    orch_mod._register_session_impl("new", "New", sessions_path=sessions_path)
    data = json.loads(sessions_path.read_text())
    assert "old" in data["sessions"]
    assert "new" in data["sessions"]


# ── _fix_code_impl ──────────────────────────────────────────────

def test_fix_code_impl_file_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
    result = orch_mod._fix_code_impl(str(tmp_path / "nonexistent.py"), "fix issues")
    data = json.loads(result)
    assert data["status"] == "error"
    assert "not found" in data["message"]


def test_fix_code_impl_path_traversal(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    # Use a path that's truly outside the workspace (brain parent = tmp_path)
    outside = Path("/tmp") / "outside_test_file_12345.py"
    outside.write_text("code")
    try:
        result = orch_mod._fix_code_impl(str(outside), "fix issues")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "outside workspace" in data["message"]
    finally:
        outside.unlink(missing_ok=True)


def test_fix_code_impl_file_too_large(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    workspace = tmp_path
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    target = workspace / "big.py"
    target.write_text("x" * 200_000)
    result = orch_mod._fix_code_impl(str(target), "fix issues")
    data = json.loads(result)
    assert data["status"] == "error"
    assert "too large" in data["message"]


def test_fix_code_impl_success(tmp_path, monkeypatch):
    brain = tmp_path / ".brain"
    brain.mkdir()
    workspace = tmp_path
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
    target = workspace / "code.py"
    target.write_text("print('hello')")
    mock_instance = mock.MagicMock()
    mock_instance.generate_content.return_value.text = "```python\nprint('fixed')\n```"
    with mock.patch("mcp_server_nucleus.runtime.llm_client.DualEngineLLM", return_value=mock_instance):
        result = orch_mod._fix_code_impl(str(target), "fix the print")
    data = json.loads(result)
    assert data["status"] == "success"
    assert target.read_text().strip() == "print('fixed')"
    assert ".bak" in data["backup"]


def test_fix_code_impl_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(tmp_path / ".brain"))
    with mock.patch("mcp_server_nucleus.runtime.llm_client.DualEngineLLM", side_effect=Exception("LLM error")):
        target = tmp_path / "code.py"
        target.write_text("code")
        result = orch_mod._fix_code_impl(str(target), "fix")
    data = json.loads(result)
    assert data["status"] == "error"


# ── register ────────────────────────────────────────────────────

def _mock_mcp():
    """Create a mock MCP that captures tool registrations."""
    tools = {}

    class _McpToolDecorator:
        def __init__(self, title, annotations):
            self.title = title
            self.annotations = annotations

        def __call__(self, fn):
            tools[fn.__name__] = fn
            return fn

    mcp = mock.MagicMock()

    def tool(title="", annotations=None):
        return _McpToolDecorator(title, annotations or {})

    mcp.tool = tool
    return mcp, tools


def _mock_helpers(tmp_path):
    return {
        "make_response": lambda ok, data=None, error=None: json.dumps({"ok": ok, "data": data, "error": error}),
        "emit_event": mock.MagicMock(),
        "get_brain_path": mock.MagicMock(return_value=tmp_path / ".brain"),
        "get_orch": mock.MagicMock(),
    }


def test_register_returns_5_tools(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        result = orch_mod.register(mcp, helpers)
    assert len(result) == 5
    names = [r[0] for r in result]
    assert "nucleus_orchestration" in names
    assert "nucleus_telemetry" in names
    assert "nucleus_slots" in names
    assert "nucleus_infra" in names
    assert "nucleus_agents" in names


@pytest.mark.asyncio
async def test_nucleus_orchestration_satellite(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.satellite_ops._get_satellite_view", return_value={}):
            with mock.patch("mcp_server_nucleus.runtime.satellite_ops._format_satellite_cli", return_value="satellite view"):
                orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    result = await nucleus_orchestration("satellite", {})
    assert "satellite" in result.lower() or "ok" in result.lower()


@pytest.mark.asyncio
async def test_nucleus_orchestration_scan_commitments(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.scan_for_commitments", return_value={"new_found": 3}):
        result = await nucleus_orchestration("scan_commitments", {})
    assert "3" in result


@pytest.mark.asyncio
async def test_nucleus_orchestration_scan_commitments_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.scan_for_commitments", side_effect=Exception("fail")):
        result = await nucleus_orchestration("scan_commitments", {})
    assert '"ok": false' in result and "fail" in result  # structured envelope now, not an "Error" prefix


@pytest.mark.asyncio
async def test_nucleus_orchestration_unknown_action(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
        nucleus_orchestration = tools["nucleus_orchestration"]
        result = await nucleus_orchestration("nonexistent", {})
    # async_dispatch returns error for unknown actions
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_nucleus_telemetry_record_interaction(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.telemetry_ops._brain_record_interaction_impl", return_value="ok"):
        result = await nucleus_telemetry("record_interaction", {"agent": "test", "task": "task"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_nucleus_telemetry_unknown_action(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
        nucleus_telemetry = tools["nucleus_telemetry"]
        result = await nucleus_telemetry("nonexistent", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_nucleus_slots_orchestrate(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.orchestrate_ops._brain_orchestrate_impl", return_value="orchestrated"):
        result = await nucleus_slots("orchestrate", {"task": "do something"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_nucleus_slots_unknown_action(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
        nucleus_slots = tools["nucleus_slots"]
        result = await nucleus_slots("nonexistent", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_nucleus_infra_unknown_action(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
        nucleus_infra = tools["nucleus_infra"]
        result = await nucleus_infra("nonexistent", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_nucleus_agents_unknown_action(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
        nucleus_agents = tools["nucleus_agents"]
        result = await nucleus_agents("nonexistent", {})
    assert isinstance(result, str)


# ── Additional nucleus_orchestration handler tests ──────────────

@pytest.mark.asyncio
async def test_orchestration_archive_stale(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.auto_archive_stale", return_value=3):
        result = await nucleus_orchestration("archive_stale", {})
    assert "3" in result


@pytest.mark.asyncio
async def test_orchestration_archive_stale_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.auto_archive_stale", side_effect=Exception("fail")):
        result = await nucleus_orchestration("archive_stale", {})
    assert '"ok": false' in result and "fail" in result  # structured envelope now, not an "Error" prefix


@pytest.mark.asyncio
async def test_orchestration_export(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.export_brain", return_value="exported"):
        result = await nucleus_orchestration("export", {})
    assert "exported" in result


@pytest.mark.asyncio
async def test_orchestration_list_commitments_empty(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger", return_value={"commitments": []}):
        result = await nucleus_orchestration("list_commitments", {})
    assert "No open" in result


@pytest.mark.asyncio
async def test_orchestration_list_commitments_with_data(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    comm = {"status": "open", "tier": "green", "description": "Test comm", "age_days": 5,
            "suggested_action": "close", "suggested_reason": "done", "id": "c1"}
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"commitments": [comm]}):
        result = await nucleus_orchestration("list_commitments", {})
    assert "Test comm" in result


@pytest.mark.asyncio
async def test_orchestration_commitment_health(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    stats = {"total_open": 0, "green_tier": 0, "yellow_tier": 0, "red_tier": 0, "by_type": {}}
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"stats": stats, "last_scan": "2026-01-01"}):
        result = await nucleus_orchestration("commitment_health", {})
    assert "Commitment Health" in result


@pytest.mark.asyncio
async def test_orchestration_open_loops_empty(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"commitments": []}):
        result = await nucleus_orchestration("open_loops", {})
    assert "No open loops" in result


@pytest.mark.asyncio
async def test_orchestration_open_loops_with_data(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    comm = {"status": "open", "tier": "red", "description": "Urgent loop", "age_days": 10,
            "suggested_action": "close", "id": "l1", "type": "task"}
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"commitments": [comm]}):
        result = await nucleus_orchestration("open_loops", {})
    assert "Open Loops" in result


@pytest.mark.asyncio
async def test_orchestration_add_loop(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    comm = {"id": "new1", "suggested_action": "close", "suggested_reason": "done"}
    with mock.patch("mcp_server_nucleus.commitment_ledger.add_commitment", return_value=comm):
        result = await nucleus_orchestration("add_loop", {"description": "New task", "loop_type": "task"})
    assert "Loop created" in result


@pytest.mark.asyncio
async def test_orchestration_close_commitment(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    comm = {"description": "Test", "age_days": 5, "closed_at": "2026-01-01"}
    with mock.patch("mcp_server_nucleus.commitment_ledger.close_commitment", return_value=comm):
        result = await nucleus_orchestration("close_commitment", {"commitment_id": "c1", "method": "done"})
    assert "Commitment closed" in result


@pytest.mark.asyncio
async def test_orchestration_close_commitment_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.close_commitment", side_effect=Exception("not found")):
        result = await nucleus_orchestration("close_commitment", {"commitment_id": "c1", "method": "done"})
    assert "Error" in result


@pytest.mark.asyncio
async def test_orchestration_weekly_challenge_list(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    challenges = [{"id": "ch1", "title": "Test Challenge", "description": "Do something", "reward": "pride"}]
    with mock.patch("mcp_server_nucleus.commitment_ledger.get_starter_challenges", return_value=challenges):
        result = await nucleus_orchestration("weekly_challenge", {"action": "list"})
    assert "Test Challenge" in result


@pytest.mark.asyncio
async def test_orchestration_weekly_challenge_get(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    result = await nucleus_orchestration("weekly_challenge", {"action": "get"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_orchestration_weekly_challenge_set_no_id(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    result = await nucleus_orchestration("weekly_challenge", {"action": "set"})
    assert "challenge_id" in result


@pytest.mark.asyncio
async def test_orchestration_metrics(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.runtime.event_ops._read_events", return_value=[]):
        result = await nucleus_orchestration("metrics", {})
    assert isinstance(result, str)


# ── Additional nucleus_telemetry handler tests ──────────────────

@pytest.mark.asyncio
async def test_telemetry_set_llm_tier_valid(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    result = await nucleus_telemetry("set_llm_tier", {"tier": "standard"})
    assert "standard" in result


@pytest.mark.asyncio
async def test_telemetry_set_llm_tier_invalid(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    result = await nucleus_telemetry("set_llm_tier", {"tier": "invalid"})
    assert "Invalid" in result


@pytest.mark.asyncio
async def test_telemetry_get_llm_status(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    result = await nucleus_telemetry("get_llm_status", {})
    assert "LLM Tier" in result


@pytest.mark.asyncio
async def test_telemetry_value_ratio(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.telemetry_ops._brain_value_ratio_impl", return_value="ratio"):
        result = await nucleus_telemetry("value_ratio", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_telemetry_check_kill_switch(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.telemetry_ops._brain_check_kill_switch_impl", return_value="ok"):
        result = await nucleus_telemetry("check_kill_switch", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_telemetry_pause_notifications(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.telemetry_ops._brain_pause_notifications_impl", return_value="paused"):
        result = await nucleus_telemetry("pause_notifications", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_telemetry_resume_notifications(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.telemetry_ops._brain_resume_notifications_impl", return_value="resumed"):
        result = await nucleus_telemetry("resume_notifications", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_telemetry_record_feedback(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.telemetry_ops._brain_record_feedback_impl", return_value="ok"):
        result = await nucleus_telemetry("record_feedback", {"feedback": "good"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_telemetry_mark_high_impact(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.telemetry_ops._brain_mark_high_impact_impl", return_value="ok"):
        result = await nucleus_telemetry("mark_high_impact", {"event_id": "e1"})
    assert isinstance(result, str)


# ── Additional nucleus_slots handler tests ──────────────────────

@pytest.mark.asyncio
async def test_slots_list_tasks(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]):
        result = await nucleus_slots("list_tasks", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_slots_add_task(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", return_value={"success": True, "task_id": "t1"}):
        result = await nucleus_slots("add_task", {"description": "test task"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_slots_start_sprint(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.sprint_ops._brain_autopilot_sprint_v2_impl", return_value="sprint started"):
        result = await nucleus_slots("start_sprint", {"task_description": "do work"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_slots_start_mission(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.sprint_ops._brain_start_mission_impl", return_value="mission started"):
        result = await nucleus_slots("start_mission", {"mission": "test"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_slots_mission_status(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.sprint_ops._brain_mission_status_impl", return_value="status"):
        result = await nucleus_slots("mission_status", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_slots_halt_sprint(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.sprint_ops._brain_halt_sprint_impl", return_value="halted"):
        result = await nucleus_slots("halt_sprint", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_slots_resume_sprint(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.sprint_ops._brain_resume_sprint_impl", return_value="resumed"):
        result = await nucleus_slots("resume_sprint", {})
    assert isinstance(result, str)


# ── Additional nucleus_infra handler tests ──────────────────────

@pytest.mark.asyncio
async def test_infra_read_artifact(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.artifact_ops._read_artifact", return_value="content"):
        result = await nucleus_infra("read_artifact", {"path": "test.txt"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_infra_start_deploy(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.deployment_ops._start_deploy_poll", return_value={"status": "ok"}):
        result = await nucleus_infra("start_deploy_poll", {"service_id": "s1"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_infra_check_deploy(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.deployment_ops._check_deploy_status", return_value={"status": "ok"}):
        result = await nucleus_infra("check_deploy", {"service_id": "s1"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_infra_complete_deploy(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.deployment_ops._complete_deploy", return_value={"status": "ok"}):
        result = await nucleus_infra("complete_deploy", {"service_id": "s1", "success": True})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_infra_smoke_test(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.deployment_ops._run_smoke_test", return_value={"status": "ok"}):
        result = await nucleus_infra("smoke_test", {"url": "http://test.com"})
    assert isinstance(result, str)


# ── Additional nucleus_agents handler tests ─────────────────────

@pytest.mark.asyncio
async def test_agents_trigger_agent(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.trigger_ops._trigger_agent_impl", return_value="triggered"):
        result = await nucleus_agents("trigger_agent", {"agent": "test", "task_description": "do work"})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_agents_get_triggers(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.trigger_ops._get_triggers_impl", return_value="triggers"):
        result = await nucleus_agents("get_triggers", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_agents_ingest_tasks(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.ingestion_ops._brain_ingest_tasks_impl", return_value="ingested"):
        result = await nucleus_agents("ingest_tasks", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_agents_ingestion_stats(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.ingestion_ops._brain_ingestion_stats_impl", return_value="stats"):
        result = await nucleus_agents("ingestion_stats", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_agents_rollback_ingestion(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.ingestion_ops._brain_rollback_ingestion_impl", return_value="rolled back"):
        result = await nucleus_agents("rollback_ingestion", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_agents_enhanced_dashboard(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.dashboard_ops._brain_enhanced_dashboard_impl", return_value="dashboard"):
        result = await nucleus_agents("enhanced_dashboard", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_agents_snapshot_dashboard(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.dashboard_ops._brain_snapshot_dashboard_impl", return_value="snapshot"):
        result = await nucleus_agents("snapshot_dashboard", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_agents_list_snapshots(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.dashboard_ops._brain_list_snapshots_impl", return_value="snapshots"):
        result = await nucleus_agents("list_snapshots", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_agents_register_session(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "ledger").mkdir()
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("register_session", {"conversation_id": "conv1", "focus_area": "test"})
    assert "Registered" in result


# ── Orchestration: edge cases & branches ────────────────────────

@pytest.mark.asyncio
async def test_orchestration_satellite_detail(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.satellite_ops._get_satellite_view", return_value={}):
            with mock.patch("mcp_server_nucleus.runtime.satellite_ops._format_satellite_cli", return_value="detail view"):
                orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    result = await nucleus_orchestration("satellite", {"detail_level": "full"})
    assert "detail view" in result.lower() or "ok" in result.lower()


@pytest.mark.asyncio
async def test_orchestration_archive_stale_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.auto_archive_stale", return_value=2):
        result = await nucleus_orchestration("archive_stale", {})
    assert "2" in result


@pytest.mark.asyncio
async def test_orchestration_export_no_attr(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger") as mock_ledger:
        del mock_ledger.export_brain
        result = await nucleus_orchestration("export", {})
    assert "Error" in result or "export" in result.lower()


@pytest.mark.asyncio
async def test_orchestration_export_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.export_brain", side_effect=Exception("fail")):
        result = await nucleus_orchestration("export", {})
    assert '"ok": false' in result and "fail" in result  # structured envelope now, not an "Error" prefix


@pytest.mark.asyncio
async def test_orchestration_list_commitments_with_tier(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    comm = {"status": "open", "tier": "green", "description": "Green comm", "age_days": 3,
            "suggested_action": "close", "suggested_reason": "done", "id": "c1"}
    comm2 = {"status": "open", "tier": "red", "description": "Red comm", "age_days": 10,
             "suggested_action": "close", "suggested_reason": "urgent", "id": "c2"}
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"commitments": [comm, comm2]}):
        result = await nucleus_orchestration("list_commitments", {"tier": "green"})
    assert "Green comm" in result
    assert "Red comm" not in result


@pytest.mark.asyncio
async def test_orchestration_list_commitments_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger", side_effect=Exception("fail")):
        result = await nucleus_orchestration("list_commitments", {})
    assert "Error" in result


@pytest.mark.asyncio
async def test_orchestration_commitment_health_red(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    stats = {"total_open": 5, "green_tier": 1, "yellow_tier": 1, "red_tier": 3, "by_type": {"task": 3, "todo": 2}}
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"stats": stats, "last_scan": "2026-01-01T12:00:00"}):
        result = await nucleus_orchestration("commitment_health", {})
    assert "HIGH" in result


@pytest.mark.asyncio
async def test_orchestration_commitment_health_yellow(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    stats = {"total_open": 5, "green_tier": 2, "yellow_tier": 3, "red_tier": 0, "by_type": {}}
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"stats": stats, "last_scan": "2026-01-01"}):
        result = await nucleus_orchestration("commitment_health", {})
    assert "MEDIUM" in result


@pytest.mark.asyncio
async def test_orchestration_commitment_health_zero(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    stats = {"total_open": 0, "green_tier": 0, "yellow_tier": 0, "red_tier": 0, "by_type": {}}
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"stats": stats, "last_scan": None}):
        result = await nucleus_orchestration("commitment_health", {})
    assert "ZERO" in result


@pytest.mark.asyncio
async def test_orchestration_commitment_health_low(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    stats = {"total_open": 2, "green_tier": 2, "yellow_tier": 0, "red_tier": 0, "by_type": {"task": 2}}
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"stats": stats, "last_scan": "2026-01-01"}):
        result = await nucleus_orchestration("commitment_health", {})
    assert "LOW" in result


@pytest.mark.asyncio
async def test_orchestration_commitment_health_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger", side_effect=Exception("fail")):
        result = await nucleus_orchestration("commitment_health", {})
    assert "Error" in result


@pytest.mark.asyncio
async def test_orchestration_open_loops_with_filters(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    comms = [
        {"status": "open", "tier": "red", "description": "Task A", "age_days": 10, "type": "task", "id": "l1", "suggested_action": "close"},
        {"status": "open", "tier": "green", "description": "Todo B", "age_days": 2, "type": "todo", "id": "l2", "suggested_action": "close"},
    ]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"commitments": comms}):
        result = await nucleus_orchestration("open_loops", {"type_filter": "task"})
    assert "Task A" in result
    assert "Todo B" not in result


@pytest.mark.asyncio
async def test_orchestration_open_loops_tier_filter(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    comms = [
        {"status": "open", "tier": "red", "description": "Red loop", "age_days": 10, "type": "task", "id": "l1", "suggested_action": "close"},
        {"status": "open", "tier": "green", "description": "Green loop", "age_days": 2, "type": "todo", "id": "l2", "suggested_action": "close"},
    ]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"commitments": comms}):
        result = await nucleus_orchestration("open_loops", {"tier_filter": "red"})
    assert "Red loop" in result
    assert "Green loop" not in result


@pytest.mark.asyncio
async def test_orchestration_open_loops_many_items(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    comms = [{"status": "open", "tier": "green", "description": f"Loop {i}", "age_days": i,
              "type": "task", "id": f"l{i}", "suggested_action": "close"} for i in range(8)]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger",
                    return_value={"commitments": comms}):
        result = await nucleus_orchestration("open_loops", {})
    assert "more" in result


@pytest.mark.asyncio
async def test_orchestration_open_loops_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_ledger", side_effect=Exception("fail")):
        result = await nucleus_orchestration("open_loops", {})
    assert "Error" in result


@pytest.mark.asyncio
async def test_orchestration_add_loop_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    comm = {"id": "new1", "suggested_action": "close", "suggested_reason": "done"}
    with mock.patch("mcp_server_nucleus.commitment_ledger.add_commitment", return_value=comm):
        result = await nucleus_orchestration("add_loop", {"description": "New task"})
    assert "Loop created" in result


@pytest.mark.asyncio
async def test_orchestration_add_loop_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.add_commitment", side_effect=Exception("fail")):
        result = await nucleus_orchestration("add_loop", {"description": "New task"})
    assert "Error" in result


@pytest.mark.asyncio
async def test_orchestration_weekly_challenge_set_valid(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    challenges = [{"id": "ch1", "title": "Test Challenge", "description": "Do something", "reward": "pride"}]
    with mock.patch("mcp_server_nucleus.commitment_ledger.get_starter_challenges", return_value=challenges):
        with mock.patch("mcp_server_nucleus.commitment_ledger.set_challenge") as mock_set:
            result = await nucleus_orchestration("weekly_challenge", {"action": "set", "challenge_id": "ch1"})
    assert "Challenge Accepted" in result
    mock_set.assert_called_once()


@pytest.mark.asyncio
async def test_orchestration_weekly_challenge_set_not_found(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    challenges = [{"id": "ch1", "title": "Test", "description": "Do", "reward": "pride"}]
    with mock.patch("mcp_server_nucleus.commitment_ledger.get_starter_challenges", return_value=challenges):
        result = await nucleus_orchestration("weekly_challenge", {"action": "set", "challenge_id": "nonexistent"})
    assert "not found" in result


@pytest.mark.asyncio
async def test_orchestration_weekly_challenge_get_active(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    challenge = {"title": "Active Challenge", "description": "Do it", "started_at": "2026-01-01T12:00:00", "reward": "glory"}
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_challenge", return_value=challenge):
        result = await nucleus_orchestration("weekly_challenge", {"action": "get"})
    assert "Active Challenge" in result


@pytest.mark.asyncio
async def test_orchestration_weekly_challenge_no_active(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_challenge", return_value=None):
        result = await nucleus_orchestration("weekly_challenge", {"action": "get"})
    assert "No active challenge" in result


@pytest.mark.asyncio
async def test_orchestration_weekly_challenge_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_challenge", side_effect=Exception("fail")):
        result = await nucleus_orchestration("weekly_challenge", {"action": "get"})
    assert "Error" in result


@pytest.mark.asyncio
async def test_orchestration_patterns_learn(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.learn_patterns", return_value=[{"name": "p1"}]):
        result = await nucleus_orchestration("patterns", {"action": "learn"})
    assert "Learning complete" in result


@pytest.mark.asyncio
async def test_orchestration_patterns_list_with_data(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    patterns = [{"name": "Pattern1", "keywords": ["kw1", "kw2"], "action": "do something"}]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_patterns", return_value=patterns):
        result = await nucleus_orchestration("patterns", {"action": "list"})
    assert "Pattern1" in result


@pytest.mark.asyncio
async def test_orchestration_patterns_empty(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_patterns", return_value=[]):
        result = await nucleus_orchestration("patterns", {"action": "list"})
    assert "No patterns" in result


@pytest.mark.asyncio
async def test_orchestration_patterns_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.load_patterns", side_effect=Exception("fail")):
        result = await nucleus_orchestration("patterns", {})
    assert "Error" in result


@pytest.mark.asyncio
async def test_orchestration_metrics_with_data(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    metrics = {"velocity_7d": 5, "avg_days_to_close": 3.5,
               "closure_rates": {"task": 2, "todo": 1},
               "current_load": {"total": 3, "red": 1}}
    with mock.patch("mcp_server_nucleus.commitment_ledger.calculate_metrics", return_value=metrics):
        result = await nucleus_orchestration("metrics", {})
    assert "task" in result


@pytest.mark.asyncio
async def test_orchestration_metrics_no_closures(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    metrics = {"velocity_7d": 0, "avg_days_to_close": 0,
               "closure_rates": {}, "current_load": {"total": 0, "red": 0}}
    with mock.patch("mcp_server_nucleus.commitment_ledger.calculate_metrics", return_value=metrics):
        result = await nucleus_orchestration("metrics", {})
    assert "No closed" in result


@pytest.mark.asyncio
async def test_orchestration_metrics_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.commitment_ledger.calculate_metrics", side_effect=Exception("fail")):
        result = await nucleus_orchestration("metrics", {})
    assert "Error" in result


@pytest.mark.asyncio
async def test_orchestration_pr_watch(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.runtime.pr_watch.run_pr_watch", return_value="pr watch result"):
        result = await nucleus_orchestration("pr_watch", {"threshold_days": 7, "dry_run": True})
    assert "pr watch result" in result


@pytest.mark.asyncio
async def test_orchestration_pr_watch_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_orchestration = tools["nucleus_orchestration"]
    with mock.patch("mcp_server_nucleus.runtime.pr_watch.run_pr_watch", side_effect=Exception("fail")):
        result = await nucleus_orchestration("pr_watch", {})
    assert "Error" in result


# ── Telemetry: additional handler tests ─────────────────────────

@pytest.mark.asyncio
async def test_telemetry_set_llm_tier_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    result = await nucleus_telemetry("set_llm_tier", {"tier": "standard"})
    assert "standard" in result


@pytest.mark.asyncio
async def test_telemetry_get_llm_status_with_file(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()
    tier_status = {"tier_results": {"standard": {"status": "SUCCESS", "model": "gpt-4", "latency_ms": 100}},
                   "recommended_tier": "standard"}
    (brain / "tier_status.json").write_text(json.dumps(tier_status))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    result = await nucleus_telemetry("get_llm_status", {})
    assert "gpt-4" in result


@pytest.mark.asyncio
async def test_telemetry_get_llm_status_corrupt_file(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "tier_status.json").write_text("not json")
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    result = await nucleus_telemetry("get_llm_status", {})
    assert "Could not load" in result


@pytest.mark.asyncio
async def test_telemetry_check_protocol(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._check_protocol_compliance", return_value={"ok": True}):
        result = await nucleus_telemetry("check_protocol", {"agent_id": "agent1"})
    assert "ok" in result


@pytest.mark.asyncio
async def test_telemetry_request_handoff(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_request_handoff_impl", return_value="handoff done"):
        result = await nucleus_telemetry("request_handoff", {"to_agent": "dev", "context": "ctx", "request": "do work"})
    assert "handoff done" in result


@pytest.mark.asyncio
async def test_telemetry_request_handoff_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_request_handoff_impl", return_value="handoff done"):
        result = await nucleus_telemetry("request_handoff", {"to_agent": "dev", "context": "ctx", "request": "do work"})
    assert "handoff done" in result


@pytest.mark.asyncio
async def test_telemetry_get_handoffs(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_get_handoffs_impl", return_value="handoffs"):
        result = await nucleus_telemetry("get_handoffs", {"agent_id": "a1"})
    assert "handoffs" in result


@pytest.mark.asyncio
async def test_telemetry_agent_cost_dashboard(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    mock_mgr = mock.MagicMock()
    mock_mgr.get_dashboard_metrics.return_value = {"cost": 1.0}
    with mock.patch("mcp_server_nucleus.runtime.agent_runtime_v2.get_execution_manager", return_value=mock_mgr):
        result = await nucleus_telemetry("agent_cost_dashboard", {})
    assert "cost" in result


@pytest.mark.asyncio
async def test_telemetry_dispatch_metrics(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    mock_tel = mock.MagicMock()
    mock_tel.get_metrics.return_value = {"count": 5}
    with mock.patch("mcp_server_nucleus.tools._dispatch.get_dispatch_telemetry", return_value=mock_tel):
        result = await nucleus_telemetry("dispatch_metrics", {})
    assert "count" in result


@pytest.mark.asyncio
async def test_telemetry_dispatch_metrics_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    mock_tel = mock.MagicMock()
    mock_tel.get_metrics.return_value = {"count": 5}
    with mock.patch("mcp_server_nucleus.tools._dispatch.get_dispatch_telemetry", return_value=mock_tel):
        result = await nucleus_telemetry("dispatch_metrics", {})
    assert "count" in result


@pytest.mark.asyncio
async def test_telemetry_rate_limit_status(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_telemetry = tools["nucleus_telemetry"]
    mock_rl = mock.MagicMock()
    mock_rl.get_status.return_value = {"limit": 100}
    with mock.patch("mcp_server_nucleus.tools._dispatch.get_dispatch_rate_limiter", return_value=mock_rl):
        result = await nucleus_telemetry("rate_limit_status", {})
    assert "limit" in result


# ── Slots: additional handler tests ─────────────────────────────

@pytest.mark.asyncio
async def test_slots_slot_complete(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_slot_complete_impl", return_value="completed"):
        with mock.patch("mcp_server_nucleus.runtime.orchestrate_ops._brain_orchestrate_impl", return_value="next task"):
            result = await nucleus_slots("slot_complete", {"slot_id": "s1", "task_id": "t1"})
    assert "completed" in result


@pytest.mark.asyncio
async def test_slots_slot_complete_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_slot_complete_impl", return_value="completed"):
        with mock.patch("mcp_server_nucleus.runtime.orchestrate_ops._brain_orchestrate_impl", return_value="next"):
            result = await nucleus_slots("slot_complete", {"slot_id": "s1", "task_id": "t1"})
    assert "completed" in result


@pytest.mark.asyncio
async def test_slots_slot_exhaust(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_slot_exhaust_impl", return_value="exhausted"):
        result = await nucleus_slots("slot_exhaust", {"slot_id": "s1", "reset_hours": 3})
    assert "exhausted" in result


@pytest.mark.asyncio
async def test_slots_slot_exhaust_invalid_hours(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    result = await nucleus_slots("slot_exhaust", {"slot_id": "s1", "reset_hours": "not_a_number"})
    assert "must be a number" in result


@pytest.mark.asyncio
async def test_slots_slot_exhaust_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_slot_exhaust_impl", return_value="exhausted"):
        result = await nucleus_slots("slot_exhaust", {"slot_id": "s1"})
    assert "exhausted" in result


@pytest.mark.asyncio
async def test_slots_autopilot_sprint(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_autopilot_sprint_impl", return_value="sprint result"):
        result = await nucleus_slots("autopilot_sprint", {"mode": "auto"})
    assert "sprint result" in result


@pytest.mark.asyncio
async def test_slots_autopilot_sprint_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_autopilot_sprint_impl", return_value="sprint result"):
        result = await nucleus_slots("autopilot_sprint", {"mode": "auto"})
    assert "sprint result" in result


@pytest.mark.asyncio
async def test_slots_force_assign(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_force_assign_impl", return_value="assigned"):
        result = await nucleus_slots("force_assign", {"slot_id": "s1", "task_id": "t1"})
    assert "assigned" in result


@pytest.mark.asyncio
async def test_slots_force_assign_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_force_assign_impl", return_value="assigned"):
        result = await nucleus_slots("force_assign", {"slot_id": "s1", "task_id": "t1"})
    assert "assigned" in result


@pytest.mark.asyncio
async def test_slots_autopilot_sprint_v2_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sprint_ops._brain_autopilot_sprint_v2_impl", return_value="sprint v2"):
            orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    result = await nucleus_slots("autopilot_sprint_v2", {"mode": "auto"})
    assert "sprint v2" in result


@pytest.mark.asyncio
async def test_slots_start_mission_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sprint_ops._brain_start_mission_impl", return_value="mission started"):
            orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    result = await nucleus_slots("start_mission", {"name": "m1", "goal": "g1", "task_ids": ["t1"]})
    assert "mission started" in result


@pytest.mark.asyncio
async def test_slots_halt_sprint_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sprint_ops._brain_halt_sprint_impl", return_value="halted"):
            orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    result = await nucleus_slots("halt_sprint", {"reason": "test"})
    assert "halted" in result


@pytest.mark.asyncio
async def test_slots_resume_sprint_emit_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    helpers["emit_event"] = mock.MagicMock(side_effect=Exception("emit fail"))
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.sprint_ops._brain_resume_sprint_impl", return_value="resumed"):
            orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    result = await nucleus_slots("resume_sprint", {"sprint_id": "sp1"})
    assert "resumed" in result


@pytest.mark.asyncio
async def test_slots_status_dashboard(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_slots = tools["nucleus_slots"]
    with mock.patch("mcp_server_nucleus.runtime.slot_ops._brain_status_dashboard_impl", return_value="dashboard"):
        result = await nucleus_slots("status_dashboard", {})
    assert "dashboard" in result


# ── Infra: comprehensive handler tests ──────────────────────────

@pytest.mark.asyncio
async def test_infra_file_changes_active(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    mock_monitor = mock.MagicMock()
    mock_monitor.is_running = True
    mock_monitor.get_pending_events.return_value = []
    with mock.patch("mcp_server_nucleus.runtime.file_monitor.get_file_monitor", return_value=mock_monitor):
        result = await nucleus_infra("file_changes", {})
    assert "active" in result


@pytest.mark.asyncio
async def test_infra_file_changes_stopped(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    mock_monitor = mock.MagicMock()
    mock_monitor.is_running = False
    with mock.patch("mcp_server_nucleus.runtime.file_monitor.get_file_monitor", return_value=mock_monitor):
        result = await nucleus_infra("file_changes", {})
    assert "stopped" in result


@pytest.mark.asyncio
async def test_infra_file_changes_no_monitor(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    mock_bus = mock.MagicMock()
    mock_bus.get_recent.return_value = []
    with mock.patch("mcp_server_nucleus.runtime.file_monitor.get_file_monitor", return_value=None):
        with mock.patch("mcp_server_nucleus.runtime.event_bus.get_event_bus", return_value=mock_bus):
            result = await nucleus_infra("file_changes", {})
    assert "degraded" in result


@pytest.mark.asyncio
async def test_infra_file_changes_import_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.file_monitor.get_file_monitor", side_effect=ImportError("no watchdog")):
        result = await nucleus_infra("file_changes", {})
    assert "unavailable" in result


@pytest.mark.asyncio
async def test_infra_file_changes_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.file_monitor.get_file_monitor", side_effect=Exception("fail")):
        result = await nucleus_infra("file_changes", {})
    assert "error" in result


@pytest.mark.asyncio
async def test_infra_gcloud_status(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    mock_ops = mock.MagicMock()
    mock_ops.check_auth_status.return_value = {"authenticated": True}
    with mock.patch("mcp_server_nucleus.runtime.gcloud_ops.get_gcloud_ops", return_value=mock_ops):
        result = await nucleus_infra("gcloud_status", {})
    assert "authenticated" in result


@pytest.mark.asyncio
async def test_infra_gcloud_status_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.gcloud_ops.get_gcloud_ops", side_effect=Exception("fail")):
        result = await nucleus_infra("gcloud_status", {})
    assert "error" in result


@pytest.mark.asyncio
async def test_infra_gcloud_services(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    mock_ops = mock.MagicMock()
    mock_ops.is_available = True
    mock_result = mock.MagicMock()
    mock_result.to_dict.return_value = {"services": []}
    mock_ops.list_cloud_run_services.return_value = mock_result
    with mock.patch("mcp_server_nucleus.runtime.gcloud_ops.GCloudOps", return_value=mock_ops):
        result = await nucleus_infra("gcloud_services", {"project": "test", "region": "us-central1"})
    assert "services" in result


@pytest.mark.asyncio
async def test_infra_gcloud_services_not_available(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    mock_ops = mock.MagicMock()
    mock_ops.is_available = False
    with mock.patch("mcp_server_nucleus.runtime.gcloud_ops.GCloudOps", return_value=mock_ops):
        result = await nucleus_infra("gcloud_services", {})
    assert "not found" in result


@pytest.mark.asyncio
async def test_infra_gcloud_services_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.gcloud_ops.GCloudOps", side_effect=Exception("fail")):
        result = await nucleus_infra("gcloud_services", {})
    assert "error" in result


@pytest.mark.asyncio
async def test_infra_list_services(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    mock_ops = mock.MagicMock()
    mock_ops.list_services.return_value = [{"name": "svc1"}]
    with mock.patch("mcp_server_nucleus.runtime.render_ops.get_render_ops", return_value=mock_ops):
        result = await nucleus_infra("list_services", {})
    assert "svc1" in result


@pytest.mark.asyncio
async def test_infra_list_services_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.render_ops.get_render_ops", side_effect=Exception("fail")):
        result = await nucleus_infra("list_services", {})
    assert "error" in result


@pytest.mark.asyncio
async def test_infra_scan_marketing_log_not_found(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    result = await nucleus_infra("scan_marketing_log", {})
    assert "not found" in result.lower() or "error" in result.lower()


@pytest.mark.asyncio
async def test_infra_scan_marketing_log_with_failures(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    log_dir = tmp_path / "docs" / "marketing"
    log_dir.mkdir(parents=True)
    log_content = "## Marketing Log\n\n[FAILURE][TIMEOUT] Something failed\nMore content\n"
    (log_dir / "marketing_log.md").write_text(log_content)
    monkeypatch.chdir(tmp_path)
    result = await nucleus_infra("scan_marketing_log", {})
    assert "degraded" in result


@pytest.mark.asyncio
async def test_infra_scan_marketing_log_healthy(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    log_dir = tmp_path / "docs" / "marketing"
    log_dir.mkdir(parents=True)
    (log_dir / "marketing_log.md").write_text("## Marketing Log\n\nAll good\n")
    monkeypatch.chdir(tmp_path)
    result = await nucleus_infra("scan_marketing_log", {})
    assert "healthy" in result


@pytest.mark.asyncio
async def test_infra_synthesize_strategy_success(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.marketing_engine.brain_synthesize_strategy",
                    return_value={"status": "success", "path": "/strategy.md"}):
        result = await nucleus_infra("synthesize_strategy", {})
    assert "Strategy Updated" in result


@pytest.mark.asyncio
async def test_infra_synthesize_strategy_failed(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.marketing_engine.brain_synthesize_strategy",
                    return_value={"status": "error", "message": "failed"}):
        result = await nucleus_infra("synthesize_strategy", {})
    assert "Failed" in result


@pytest.mark.asyncio
async def test_infra_synthesize_strategy_error(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.marketing_engine.brain_synthesize_strategy",
                    side_effect=Exception("fail")):
        result = await nucleus_infra("synthesize_strategy", {})
    assert "Error" in result


@pytest.mark.asyncio
async def test_infra_status_report_success(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.synthesizer.brain_synthesize_status_report",
                    return_value={"status": "success", "report": "Status report content"}):
        result = await nucleus_infra("status_report", {})
    assert "Status report" in result


@pytest.mark.asyncio
async def test_infra_status_report_failed(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.synthesizer.brain_synthesize_status_report",
                    return_value={"status": "error", "message": "failed"}):
        result = await nucleus_infra("status_report", {})
    assert "Failed" in result


@pytest.mark.asyncio
async def test_infra_status_report_error(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.synthesizer.brain_synthesize_status_report",
                    side_effect=Exception("fail")):
        result = await nucleus_infra("status_report", {})
    assert "Error" in result


@pytest.mark.asyncio
async def test_infra_optimize_workflow_success(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.marketing_engine.brain_optimize_workflow",
                    return_value={"status": "success"}):
        result = await nucleus_infra("optimize_workflow", {})
    assert "Optimized" in result


@pytest.mark.asyncio
async def test_infra_optimize_workflow_skipped(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.marketing_engine.brain_optimize_workflow",
                    return_value={"status": "skipped", "message": "no changes needed"}):
        result = await nucleus_infra("optimize_workflow", {})
    assert "Skipped" in result


@pytest.mark.asyncio
async def test_infra_optimize_workflow_failed(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.marketing_engine.brain_optimize_workflow",
                    return_value={"status": "error", "message": "failed"}):
        result = await nucleus_infra("optimize_workflow", {})
    assert "Failed" in result


@pytest.mark.asyncio
async def test_infra_optimize_workflow_error(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    monkeypatch.chdir(tmp_path)
    with mock.patch("mcp_server_nucleus.runtime.capabilities.marketing_engine.brain_optimize_workflow",
                    side_effect=Exception("fail")):
        result = await nucleus_infra("optimize_workflow", {})
    assert "Error" in result


@pytest.mark.asyncio
async def test_infra_manage_strategy(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.strategy._manage_strategy", return_value={"ok": True}):
        result = await nucleus_infra("manage_strategy", {"action": "read"})
    assert "ok" in result


@pytest.mark.asyncio
async def test_infra_manage_strategy_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.strategy._manage_strategy", side_effect=Exception("fail")):
        result = await nucleus_infra("manage_strategy", {"action": "read"})
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_infra_update_roadmap(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.strategy._update_roadmap", return_value={"ok": True}):
        result = await nucleus_infra("update_roadmap", {"action": "read"})
    assert "ok" in result


@pytest.mark.asyncio
async def test_infra_update_roadmap_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.strategy._update_roadmap", side_effect=Exception("fail")):
        result = await nucleus_infra("update_roadmap", {"action": "read"})
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_infra_growth_pulse(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.growth_ops.growth_pulse", return_value={"status": "ok"}):
        result = await nucleus_infra("growth_pulse", {})
    assert "ok" in result


@pytest.mark.asyncio
async def test_infra_growth_pulse_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.growth_ops.growth_pulse", side_effect=Exception("fail")):
        result = await nucleus_infra("growth_pulse", {})
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_infra_capture_metrics(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.growth_ops.capture_metrics", return_value={"status": "ok"}):
        result = await nucleus_infra("capture_metrics", {})
    assert "ok" in result


@pytest.mark.asyncio
async def test_infra_capture_metrics_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_infra = tools["nucleus_infra"]
    with mock.patch("mcp_server_nucleus.runtime.growth_ops.capture_metrics", side_effect=Exception("fail")):
        result = await nucleus_infra("capture_metrics", {})
    assert "error" in result.lower()


# ── Agents: comprehensive handler tests ─────────────────────────

@pytest.mark.asyncio
async def test_agents_spawn_agent_no_confirm(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("spawn_agent", {"intent": "do work"})
    assert "HITL GATE" in result


@pytest.mark.asyncio
async def test_agents_spawn_agent_rate_limited(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    mock_mgr = mock.MagicMock()
    from mcp_server_nucleus.runtime.rate_limiter import RateLimitError
    mock_mgr.spawn_agent.side_effect = RateLimitError(30.0, "rate limited")
    with mock.patch("mcp_server_nucleus.runtime.agent_runtime_v2.get_execution_manager", return_value=mock_mgr):
        result = await nucleus_agents("spawn_agent", {"intent": "do work", "confirm": True})
    assert "rate-limited" in result


@pytest.mark.asyncio
async def test_agents_spawn_agent_success(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    mock_mgr = mock.MagicMock()
    mock_exec = mock.MagicMock()
    mock_exec.agent_id = "agent-123"
    mock_mgr.spawn_agent.return_value = mock_exec
    mock_mgr.complete_execution.return_value = None
    with mock.patch("mcp_server_nucleus.runtime.agent_runtime_v2.get_execution_manager", return_value=mock_mgr):
        with mock.patch("mcp_server_nucleus.runtime.factory.ContextFactory") as mock_factory_cls:
            mock_factory = mock.MagicMock()
            mock_factory.create_context.return_value = {
                "persona": "default", "job_type": "ORCHESTRATION",
                "capabilities": ["read"], "tools": []
            }
            mock_factory_cls.return_value = mock_factory
            result = await nucleus_agents("spawn_agent", {"intent": "do work", "confirm": True, "execute_now": False})
    assert "Factory Receipt" in result
    assert "No tools mapped" in result


@pytest.mark.asyncio
async def test_agents_spawn_agent_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    mock_mgr = mock.MagicMock()
    mock_exec = mock.MagicMock()
    mock_exec.agent_id = "agent-123"
    mock_mgr.spawn_agent.return_value = mock_exec
    mock_mgr.complete_execution.return_value = None
    with mock.patch("mcp_server_nucleus.runtime.agent_runtime_v2.get_execution_manager", return_value=mock_mgr):
        with mock.patch("mcp_server_nucleus.runtime.factory.ContextFactory", side_effect=Exception("factory fail")):
            result = await nucleus_agents("spawn_agent", {"intent": "do work", "confirm": True, "execute_now": False})
    assert "Error spawning" in result


@pytest.mark.asyncio
async def test_agents_apply_critique(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    review_json = json.dumps({"payload": {"target": "file.py", "issues": [{"severity": "high", "description": "bug"}]}})
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.artifact_ops._read_artifact", return_value=review_json):
            with mock.patch("mcp_server_nucleus.runtime.trigger_ops._trigger_agent_impl", return_value="triggered"):
                orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("apply_critique", {"review_path": "artifacts/review.json"})
    assert "success" in result.lower()


@pytest.mark.asyncio
async def test_agents_apply_critique_error_reading(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.artifact_ops._read_artifact", return_value="Error: not found"):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("apply_critique", {"review_path": "artifacts/review.json"})
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_agents_apply_critique_invalid_format(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    review_json = json.dumps({"payload": {"target": None, "issues": []}})
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.artifact_ops._read_artifact", return_value=review_json):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("apply_critique", {"review_path": "artifacts/review.json"})
    assert "error" in result.lower() or "Invalid" in result


@pytest.mark.asyncio
async def test_agents_apply_critique_exception(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.artifact_ops._read_artifact", side_effect=Exception("fail")):
        result = await nucleus_agents("apply_critique", {"review_path": "artifacts/review.json"})
    assert "error" in result.lower() or "Failed" in result


@pytest.mark.asyncio
async def test_agents_orchestrate_swarm(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    mock_orch = mock.AsyncMock()
    mock_orch.start_mission.return_value = "swarm result"
    helpers["get_orch"] = mock.MagicMock(return_value=mock_orch)
    # Need to re-register with updated helpers
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("orchestrate_swarm", {"mission": "test mission"})
    assert "swarm result" in result


@pytest.mark.asyncio
async def test_agents_orchestrate_swarm_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    mock_orch = mock.AsyncMock()
    mock_orch.start_mission.side_effect = Exception("swarm fail")
    helpers["get_orch"] = mock.MagicMock(return_value=mock_orch)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("orchestrate_swarm", {"mission": "test mission"})
    assert "Swarm failed" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_agents_search_memory(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.memory._search_memory", return_value={"result": "found"}):
        result = await nucleus_agents("search_memory", {"query": "test"})
    assert "found" in result


@pytest.mark.asyncio
async def test_agents_search_memory_non_str(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("search_memory", {"query": 123})
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_agents_read_memory(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.memory._read_memory", return_value={"data": "content"}):
        result = await nucleus_agents("read_memory", {"category": "test"})
    assert "content" in result


@pytest.mark.asyncio
async def test_agents_read_memory_non_str(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("read_memory", {"category": 123})
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_agents_respond_to_consent(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("respond_to_consent", {"agent_id": "a1", "choice": "cold"})
    assert "Consent recorded" in result


@pytest.mark.asyncio
async def test_agents_respond_to_consent_non_str(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("respond_to_consent", {"agent_id": 123})
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_agents_list_pending_consents(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("list_pending_consents", {})
    assert "pending" in result.lower()


@pytest.mark.asyncio
async def test_agents_critique_code(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    brain = tmp_path / ".brain"
    brain.mkdir()
    helpers = _mock_helpers(tmp_path)
    helpers["get_brain_path"] = mock.MagicMock(return_value=brain)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    target = tmp_path / "code.py"
    target.write_text("print('hello')")
    mock_llm = mock.MagicMock()
    mock_llm.generate_content.return_value.text = '{"status": "PASS", "score": 90, "issues": []}'
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        with mock.patch("mcp_server_nucleus.runtime.llm_client.DualEngineLLM", return_value=mock_llm):
            result = await nucleus_agents("critique_code", {"file_path": str(target), "context": "review"})
    assert "PASS" in result


@pytest.mark.asyncio
async def test_agents_critique_code_not_found(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    brain = tmp_path / ".brain"
    brain.mkdir()
    helpers = _mock_helpers(tmp_path)
    helpers["get_brain_path"] = mock.MagicMock(return_value=brain)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        result = await nucleus_agents("critique_code", {"file_path": str(tmp_path / "nonexistent.py")})
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_agents_critique_code_path_traversal(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    brain = tmp_path / ".brain"
    brain.mkdir()
    helpers = _mock_helpers(tmp_path)
    helpers["get_brain_path"] = mock.MagicMock(return_value=brain)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    outside = Path("/tmp/outside_critique_test_12345.py")
    outside.write_text("code")
    try:
        with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
            result = await nucleus_agents("critique_code", {"file_path": str(outside)})
        assert "outside workspace" in result.lower() or "error" in result.lower()
    finally:
        outside.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_agents_critique_code_too_large(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    brain = tmp_path / ".brain"
    brain.mkdir()
    helpers = _mock_helpers(tmp_path)
    helpers["get_brain_path"] = mock.MagicMock(return_value=brain)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    target = tmp_path / "big.py"
    target.write_text("x" * 200_000)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        result = await nucleus_agents("critique_code", {"file_path": str(target)})
    assert "too large" in result.lower()


@pytest.mark.asyncio
async def test_agents_critique_code_error(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    brain = tmp_path / ".brain"
    brain.mkdir()
    helpers = _mock_helpers(tmp_path)
    helpers["get_brain_path"] = mock.MagicMock(return_value=brain)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    target = tmp_path / "code.py"
    target.write_text("print('hello')")
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        with mock.patch("mcp_server_nucleus.runtime.llm_client.DualEngineLLM", side_effect=Exception("LLM error")):
            result = await nucleus_agents("critique_code", {"file_path": str(target)})
    assert "error" in result.lower()


@pytest.mark.asyncio
async def test_agents_session_briefing_no_conv(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]):
        result = await nucleus_agents("session_briefing", {})
    assert "Session Briefing" in result


@pytest.mark.asyncio
async def test_agents_session_briefing_with_conv(tmp_path):
    mcp, tools = _mock_mcp()
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "meta").mkdir()
    registry = brain / "meta" / "thread_registry.md"
    registry.write_text("conv1234 | focus | role | sonnet_dev | extra\n")
    helpers = _mock_helpers(tmp_path)
    helpers["get_brain_path"] = mock.MagicMock(return_value=brain)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", return_value=[]):
        result = await nucleus_agents("session_briefing", {"conversation_id": "conv12345678"})
    assert "Session Briefing" in result


@pytest.mark.asyncio
async def test_agents_session_briefing_with_tasks(tmp_path):
    # Re-import orch_mod fresh — test_facade_orchestration_events.py may have
    # deleted sys.modules["mcp_server_nucleus.tools.orchestration"], leaving
    # the module-level orch_mod reference stale.
    import importlib
    import mcp_server_nucleus.tools.orchestration as orch_mod
    orch_mod = importlib.reload(orch_mod)
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    in_progress = [{"description": "Working task", "claimed_by": "agent1"}]
    pending = [{"description": "Pending task", "priority": 2}]
    def mock_list_tasks(status=None, **kwargs):
        if status == "IN_PROGRESS":
            return in_progress
        return pending
    # Patch _list_tasks BEFORE register() so the closure captures the mock
    with mock.patch("mcp_server_nucleus.runtime.task_ops._list_tasks", side_effect=mock_list_tasks), \
         mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("session_briefing", {})
    assert "In Progress" in result
    assert "Pending" in result


@pytest.mark.asyncio
async def test_agents_register_session_error(tmp_path):
    # Re-import orch_mod fresh — test_facade_orchestration_events.py may have
    # deleted sys.modules["mcp_server_nucleus.tools.orchestration"], leaving
    # the module-level orch_mod reference stale.
    import importlib
    import mcp_server_nucleus.tools.orchestration as orch_mod
    orch_mod = importlib.reload(orch_mod)
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    # Use patch.object on orch_mod directly — test_facade_orchestration_events.py
    # deletes sys.modules["mcp_server_nucleus.tools.orchestration"], causing a
    # re-import.  String-path patching would target the new module while the
    # closures still reference the old one.
    with mock.patch.object(orch_mod, "_register_session_impl", side_effect=Exception("fail")):
        result = await nucleus_agents("register_session", {"conversation_id": "conv1", "focus_area": "test"})
    assert "Error" in result


@pytest.mark.asyncio
async def test_agents_handoff_task(tmp_path):
    mcp, tools = _mock_mcp()
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "ledger").mkdir()
    helpers = _mock_helpers(tmp_path)
    helpers["get_brain_path"] = mock.MagicMock(return_value=brain)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.task_ops._add_task",
                    return_value={"success": True, "task": {"id": "t1"}}):
        result = await nucleus_agents("handoff_task", {"task_description": "do work"})
    assert "handed off" in result


@pytest.mark.asyncio
async def test_agents_handoff_task_with_target(tmp_path):
    mcp, tools = _mock_mcp()
    brain = tmp_path / ".brain"
    brain.mkdir()
    (brain / "ledger").mkdir()
    helpers = _mock_helpers(tmp_path)
    helpers["get_brain_path"] = mock.MagicMock(return_value=brain)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    with mock.patch("mcp_server_nucleus.runtime.task_ops._add_task",
                    return_value={"success": True, "task": {"id": "t1"}}):
        result = await nucleus_agents("handoff_task", {"task_description": "do work", "target_session_id": "sess12345678"})
    assert "handed off" in result


@pytest.mark.asyncio
async def test_agents_handoff_task_failed(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.task_ops._add_task",
                        return_value={"success": False, "error": "db error"}):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("handoff_task", {"task_description": "do work"})
    assert "Error" in result


@pytest.mark.asyncio
async def test_agents_handoff_task_error(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.task_ops._add_task", side_effect=Exception("fail")):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("handoff_task", {"task_description": "do work"})
    assert "Error" in result


@pytest.mark.asyncio
async def test_agents_fix_code(tmp_path, monkeypatch):
    mcp, tools = _mock_mcp()
    brain = tmp_path / ".brain"
    brain.mkdir()
    helpers = _mock_helpers(tmp_path)
    helpers["get_brain_path"] = mock.MagicMock(return_value=brain)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    target = tmp_path / "code.py"
    target.write_text("print('hello')")
    mock_instance = mock.MagicMock()
    mock_instance.generate_content.return_value.text = "print('fixed')"
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(brain)}):
        with mock.patch("mcp_server_nucleus.runtime.llm_client.DualEngineLLM", return_value=mock_instance):
            result = await nucleus_agents("fix_code", {"file_path": str(target), "issues_context": "fix the print"})
    assert "success" in result.lower() or "fixed" in result.lower()


@pytest.mark.asyncio
async def test_agents_ingest_tasks_with_params(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.ingestion_ops._brain_ingest_tasks_impl", return_value="ingested"):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("ingest_tasks", {"source": "file.md", "source_type": "markdown", "dry_run": True})
    assert "ingested" in result


@pytest.mark.asyncio
async def test_agents_rollback_ingestion_with_params(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.ingestion_ops._brain_rollback_ingestion_impl", return_value="rolled back"):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("rollback_ingestion", {"batch_id": "b1", "reason": "test"})
    assert "rolled back" in result


@pytest.mark.asyncio
async def test_agents_set_alert_threshold(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.dashboard_ops._brain_set_alert_threshold_impl", return_value="threshold set"):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("set_alert_threshold", {"metric": "cpu", "level": "warn", "value": 80})
    assert "threshold set" in result


@pytest.mark.asyncio
async def test_agents_dashboard(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.dashboard_ops._brain_enhanced_dashboard_impl", return_value="dashboard"):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("dashboard", {"detail_level": "full"})
    assert "dashboard" in result


@pytest.mark.asyncio
async def test_agents_snapshot_dashboard(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.dashboard_ops._brain_snapshot_dashboard_impl", return_value="snapshot"):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("snapshot_dashboard", {"name": "snap1"})
    assert "snapshot" in result


@pytest.mark.asyncio
async def test_agents_list_dashboard_snapshots(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.dashboard_ops._brain_list_snapshots_impl", return_value="snapshots"):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("list_dashboard_snapshots", {"limit": 5})
    assert "snapshots" in result


@pytest.mark.asyncio
async def test_agents_get_alerts(tmp_path):
    mcp, tools = _mock_mcp()
    helpers = _mock_helpers(tmp_path)
    with mock.patch.dict(os.environ, {"NUCLEUS_BRAIN_PATH": str(tmp_path / ".brain")}):
        with mock.patch("mcp_server_nucleus.runtime.dashboard_ops._brain_get_alerts_impl", return_value="alerts"):
            orch_mod.register(mcp, helpers)
    nucleus_agents = tools["nucleus_agents"]
    result = await nucleus_agents("get_alerts", {})
    assert "alerts" in result
