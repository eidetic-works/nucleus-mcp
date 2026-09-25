"""Tests for orchestration.py facade event-emission coverage (E4 lane).

Verifies that mutating actions across the 5 sub-facades
(nucleus_orchestration, nucleus_telemetry, nucleus_slots, nucleus_infra,
nucleus_agents) emit `_emit_event()` calls on their success paths.

This is the E4 hygiene-lane test pair for raising event-emission coverage
from 4/63 → ≥30/63 per `.brain/plans/engineering_remaining_20260522.md`.

Each test calls the underlying handler with a stub `emit_event` spy and
asserts the shape (event_type, emitter, data keys) of the recorded call.
"""

from __future__ import annotations

import json
import sys
import types
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

import pytest


# ────────────────────────────────────────────────────────────────────────
# FIXTURES
# ────────────────────────────────────────────────────────────────────────

class _FakeMCP:
    """Minimal MCP stub for tool registration in tests.

    Stores decorated tool callables on `.tools` keyed by function name so
    tests can dispatch into the routers.
    """

    def __init__(self):
        self.tools: Dict[str, Any] = {}

    def tool(self, *_args, **_kwargs):
        def _decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return _decorator


class _EmitSpy:
    """Capture every emit_event call for shape assertions."""

    def __init__(self):
        self.calls: List[Tuple[str, str, Dict[str, Any], str]] = []

    def __call__(self, event_type: str, emitter: str,
                 data: Dict[str, Any], description: str = "") -> str:
        self.calls.append((event_type, emitter, dict(data), description))
        return f"evt-test-{len(self.calls)}"

    def by_type(self, event_type: str) -> List[Tuple[str, str, Dict[str, Any], str]]:
        return [c for c in self.calls if c[0] == event_type]


@pytest.fixture
def emit_spy():
    return _EmitSpy()


@pytest.fixture
def fake_mcp():
    return _FakeMCP()


@pytest.fixture
def registered(fake_mcp, emit_spy, tmp_path, monkeypatch):
    """Register the orchestration facade against a stub MCP + emit-spy."""
    # Force the orchestration module to import fresh so closures pick up
    # the spy via the helpers dict.
    if "mcp_server_nucleus.tools.orchestration" in sys.modules:
        del sys.modules["mcp_server_nucleus.tools.orchestration"]
    from mcp_server_nucleus.tools import orchestration as orch_mod

    brain = tmp_path / ".brain"
    (brain / "ledger").mkdir(parents=True, exist_ok=True)
    (brain / "engrams").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

    helpers = {
        "make_response": lambda ok, data=None, error=None: {
            "ok": ok, "data": data, "error": error,
        },
        "emit_event": emit_spy,
        "get_brain_path": lambda: brain,
        "get_orch": MagicMock(),
    }
    orch_mod.register(fake_mcp, helpers)
    return fake_mcp


# ────────────────────────────────────────────────────────────────────────
# nucleus_orchestration — archive_stale, weekly_challenge
# ────────────────────────────────────────────────────────────────────────

async def test_archive_stale_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.commitment_ledger.auto_archive_stale",
               return_value=3):
        await registered.tools["nucleus_orchestration"]("archive_stale", {})
    calls = emit_spy.by_type("commitments_archived")
    assert len(calls) == 1
    et, emitter, data, _ = calls[0]
    assert emitter == "nucleus_orchestration"
    assert data["action"] == "archive_stale"
    assert data["archived_count"] == 3


async def test_weekly_challenge_set_emits(registered, emit_spy):
    fake_challenge = {"id": "c-1", "title": "Demo",
                      "description": "do x", "reward": "win"}
    with patch("mcp_server_nucleus.commitment_ledger.get_starter_challenges",
               return_value=[fake_challenge]), \
         patch("mcp_server_nucleus.commitment_ledger.set_challenge"):
        await registered.tools["nucleus_orchestration"](
            "weekly_challenge", {"action": "set", "challenge_id": "c-1"}
        )
    calls = emit_spy.by_type("weekly_challenge_set")
    assert len(calls) == 1
    et, emitter, data, _ = calls[0]
    assert emitter == "nucleus_orchestration"
    assert data["challenge_id"] == "c-1"
    assert data["title"] == "Demo"


# ────────────────────────────────────────────────────────────────────────
# nucleus_telemetry — set_llm_tier, request_handoff, dispatch_metrics
# ────────────────────────────────────────────────────────────────────────

async def test_set_llm_tier_emits(registered, emit_spy):
    await registered.tools["nucleus_telemetry"](
        "set_llm_tier", {"tier": "standard"}
    )
    calls = emit_spy.by_type("llm_tier_set")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_telemetry"
    assert data["tier"] == "standard"


async def test_request_handoff_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.slot_ops._brain_request_handoff_impl",
               return_value="ok"):
        await registered.tools["nucleus_telemetry"](
            "request_handoff",
            {"to_agent": "main", "context": "do x", "request": "review",
             "priority": 2},
        )
    calls = emit_spy.by_type("handoff_requested")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_telemetry"
    assert data["to_agent"] == "main"
    assert data["priority"] == 2


async def test_dispatch_metrics_emits(registered, emit_spy):
    fake_metrics = {"a": 1, "b": 2}
    fake_tel = MagicMock()
    fake_tel.get_metrics.return_value = fake_metrics
    with patch("mcp_server_nucleus.tools._dispatch.get_dispatch_telemetry",
               return_value=fake_tel):
        await registered.tools["nucleus_telemetry"]("dispatch_metrics", {})
    calls = emit_spy.by_type("dispatch_metrics_queried")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_telemetry"
    assert data["metric_count"] == 2


# ────────────────────────────────────────────────────────────────────────
# nucleus_slots — slot_complete, slot_exhaust, autopilot_sprint*,
#                 force_assign, start_mission, halt_sprint, resume_sprint
# ────────────────────────────────────────────────────────────────────────

async def test_slot_complete_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.slot_ops._brain_slot_complete_impl",
               return_value="done"), \
         patch("mcp_server_nucleus.runtime.orchestrate_ops._brain_orchestrate_impl",
               return_value="next"):
        await registered.tools["nucleus_slots"](
            "slot_complete",
            {"slot_id": "S1", "task_id": "T1", "outcome": "success"},
        )
    calls = emit_spy.by_type("slot_completed")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_slots"
    assert data["slot_id"] == "S1"
    assert data["task_id"] == "T1"
    assert data["outcome"] == "success"


async def test_slot_exhaust_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.slot_ops._brain_slot_exhaust_impl",
               return_value="exhausted"):
        await registered.tools["nucleus_slots"](
            "slot_exhaust", {"slot_id": "S2", "reset_hours": 2}
        )
    calls = emit_spy.by_type("slot_exhausted")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_slots"
    assert data["slot_id"] == "S2"
    assert data["reset_hours"] == 2


async def test_autopilot_sprint_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.slot_ops._brain_autopilot_sprint_impl",
               return_value="sprint-ran"):
        await registered.tools["nucleus_slots"](
            "autopilot_sprint", {"mode": "auto", "dry_run": True}
        )
    calls = emit_spy.by_type("autopilot_sprint_started")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_slots"
    assert data["mode"] == "auto"
    assert data["dry_run"] is True


async def test_force_assign_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.slot_ops._brain_force_assign_impl",
               return_value="assigned"):
        await registered.tools["nucleus_slots"](
            "force_assign",
            {"slot_id": "S3", "task_id": "T9", "acknowledge_risk": True},
        )
    calls = emit_spy.by_type("slot_force_assigned")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_slots"
    assert data["slot_id"] == "S3"
    assert data["task_id"] == "T9"
    assert data["acknowledge_risk"] is True


async def test_autopilot_sprint_v2_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.sprint_ops._brain_autopilot_sprint_v2_impl",
               return_value="v2-ran"):
        await registered.tools["nucleus_slots"](
            "autopilot_sprint_v2",
            {"mode": "manual", "dry_run": False, "max_tasks_per_slot": 5},
        )
    calls = emit_spy.by_type("autopilot_sprint_v2_started")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_slots"
    assert data["mode"] == "manual"
    assert data["max_tasks_per_slot"] == 5


async def test_start_mission_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.sprint_ops._brain_start_mission_impl",
               return_value="mission-id-123"):
        await registered.tools["nucleus_slots"](
            "start_mission",
            {"name": "Apollo", "goal": "land",
             "task_ids": ["t1", "t2", "t3"]},
        )
    calls = emit_spy.by_type("mission_started")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_slots"
    assert data["name"] == "Apollo"
    assert data["task_count"] == 3


async def test_halt_sprint_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.sprint_ops._brain_halt_sprint_impl",
               return_value="halted"):
        await registered.tools["nucleus_slots"](
            "halt_sprint", {"reason": "budget exhausted"}
        )
    calls = emit_spy.by_type("sprint_halted")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_slots"
    assert data["reason"] == "budget exhausted"


async def test_resume_sprint_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.sprint_ops._brain_resume_sprint_impl",
               return_value="resumed"):
        await registered.tools["nucleus_slots"](
            "resume_sprint", {"sprint_id": "sprint-9"}
        )
    calls = emit_spy.by_type("sprint_resumed")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_slots"
    assert data["sprint_id"] == "sprint-9"


# ────────────────────────────────────────────────────────────────────────
# nucleus_infra — synthesize_strategy, optimize_workflow, manage_strategy,
#                 update_roadmap, growth_pulse, capture_metrics
# ────────────────────────────────────────────────────────────────────────

async def test_synthesize_strategy_emits(registered, emit_spy):
    fake_result = {"status": "success", "path": "/tmp/x"}
    fake_mod = types.ModuleType("mcp_server_nucleus.runtime.capabilities.marketing_engine")
    fake_mod.brain_synthesize_strategy = lambda **_kw: fake_result
    fake_mod.brain_optimize_workflow = lambda **_kw: {"status": "success"}
    with patch.dict(sys.modules,
                    {"mcp_server_nucleus.runtime.capabilities.marketing_engine": fake_mod}):
        await registered.tools["nucleus_infra"](
            "synthesize_strategy", {"focus_topic": "growth"}
        )
    calls = emit_spy.by_type("strategy_synthesized")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_infra"
    assert data["status"] == "success"
    assert data["focus_topic"] == "growth"


async def test_optimize_workflow_emits(registered, emit_spy):
    fake_mod = types.ModuleType("mcp_server_nucleus.runtime.capabilities.marketing_engine")
    fake_mod.brain_synthesize_strategy = lambda **_kw: {"status": "success"}
    fake_mod.brain_optimize_workflow = lambda **_kw: {"status": "success"}
    with patch.dict(sys.modules,
                    {"mcp_server_nucleus.runtime.capabilities.marketing_engine": fake_mod}):
        await registered.tools["nucleus_infra"]("optimize_workflow", {})
    calls = emit_spy.by_type("workflow_optimized")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_infra"
    assert data["status"] == "success"


async def test_manage_strategy_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.strategy._manage_strategy",
               return_value={"ok": True}):
        await registered.tools["nucleus_infra"](
            "manage_strategy", {"action": "read"}
        )
    calls = emit_spy.by_type("strategy_managed")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_infra"
    assert data["sub_action"] == "read"
    assert data["has_content"] is False


async def test_update_roadmap_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.strategy._update_roadmap",
               return_value={"ok": True}):
        await registered.tools["nucleus_infra"](
            "update_roadmap", {"action": "add", "item": "deploy"}
        )
    calls = emit_spy.by_type("roadmap_updated")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_infra"
    assert data["sub_action"] == "add"
    assert data["has_item"] is True


async def test_growth_pulse_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.growth_ops.growth_pulse",
               return_value={"ok": True}):
        await registered.tools["nucleus_infra"](
            "growth_pulse", {"write_engrams": False}
        )
    calls = emit_spy.by_type("growth_pulse_run")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_infra"
    assert data["write_engrams"] is False


async def test_capture_metrics_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.growth_ops.capture_metrics",
               return_value={"ok": True}):
        await registered.tools["nucleus_infra"](
            "capture_metrics", {"write_engram": False}
        )
    calls = emit_spy.by_type("metrics_captured")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_infra"
    assert data["write_engram"] is False


# ────────────────────────────────────────────────────────────────────────
# nucleus_agents — apply_critique, orchestrate_swarm, handoff_task,
#                  fix_code, ingest_tasks, rollback_ingestion,
#                  set_alert_threshold
# (spawn_agent is async and HITL-gated; tested separately with confirm=True
#  through a more elaborate mock — skipped here to keep test surface tight.)
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_critique_emits(fake_mcp, emit_spy, tmp_path, monkeypatch):
    """apply_critique closures bind _read_artifact + _trigger_agent_impl at
    register-time. Patch BEFORE registering so the closures pick up mocks."""
    brain = tmp_path / ".brain"
    (brain / "ledger").mkdir(parents=True, exist_ok=True)
    (brain / "artifacts").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

    review = {"payload": {
        "target": "/tmp/foo.py",
        "issues": [{"severity": "high", "description": "bad"}],
    }}
    (brain / "artifacts" / "r1.json").write_text(json.dumps(review))

    # Patch _trigger_agent_impl on its source module before register imports it.
    with patch("mcp_server_nucleus.runtime.trigger_ops._trigger_agent_impl",
               return_value="triggered"):
        if "mcp_server_nucleus.tools.orchestration" in sys.modules:
            del sys.modules["mcp_server_nucleus.tools.orchestration"]
        from mcp_server_nucleus.tools import orchestration as orch_mod
        helpers = {
            "make_response": lambda ok, data=None, error=None: {
                "ok": ok, "data": data, "error": error,
            },
            "emit_event": emit_spy,
            "get_brain_path": lambda: brain,
            "get_orch": MagicMock(),
        }
        orch_mod.register(fake_mcp, helpers)
        await fake_mcp.tools["nucleus_agents"](
            "apply_critique", {"review_path": "r1.json"}
        )
    calls = emit_spy.by_type("critique_applied")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_agents"
    assert data["target"] == "/tmp/foo.py"
    assert data["issue_count"] == 1


@pytest.mark.asyncio
async def test_orchestrate_swarm_emits(fake_mcp, emit_spy, tmp_path, monkeypatch):
    if "mcp_server_nucleus.tools.orchestration" in sys.modules:
        del sys.modules["mcp_server_nucleus.tools.orchestration"]
    from mcp_server_nucleus.tools import orchestration as orch_mod

    brain = tmp_path / ".brain"
    (brain / "ledger").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))

    fake_orch = MagicMock()
    async def _start_mission(*a, **kw):
        return "started"
    fake_orch.start_mission = _start_mission

    helpers = {
        "make_response": lambda ok, data=None, error=None: {
            "ok": ok, "data": data, "error": error,
        },
        "emit_event": emit_spy,
        "get_brain_path": lambda: brain,
        "get_orch": lambda: fake_orch,
    }
    orch_mod.register(fake_mcp, helpers)
    await fake_mcp.tools["nucleus_agents"](
        "orchestrate_swarm",
        {"mission": "test mission", "agents": ["a1", "a2"]},
    )
    calls = emit_spy.by_type("swarm_orchestrated")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_agents"
    assert data["agent_count"] == 2


@pytest.mark.asyncio
async def test_handoff_task_emits(registered, emit_spy):
    # _add_task is imported into the closure inside register(); patch at
    # the module path that the closure references (re-imported each call).
    await registered.tools["nucleus_agents"](
        "handoff_task",
        {"task_description": "review pr", "priority": 2},
    )
    calls = emit_spy.by_type("task_handed_off")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_agents"
    assert "task_id" in data and data["task_id"]
    assert data["priority"] == 2


@pytest.mark.asyncio
async def test_fix_code_emits(registered, emit_spy, tmp_path):
    target = tmp_path / "x.py"
    target.write_text("print('hi')\n")
    # Patch the LLM client so no network call happens.
    fake_resp = MagicMock()
    fake_resp.text = "```\nprint('fixed')\n```"
    fake_llm = MagicMock()
    fake_llm.generate_content.return_value = fake_resp
    with patch("mcp_server_nucleus.runtime.llm_client.DualEngineLLM",
               return_value=fake_llm):
        await registered.tools["nucleus_agents"](
            "fix_code", {"file_path": str(target), "issues_context": "bug X"}
        )
    calls = emit_spy.by_type("code_fixed")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_agents"
    assert data["file"] == str(target)
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_ingest_tasks_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.ingestion_ops._brain_ingest_tasks_impl",
               return_value="ingested"):
        await registered.tools["nucleus_agents"](
            "ingest_tasks",
            {"source": "stdin", "source_type": "jsonl", "dry_run": True},
        )
    calls = emit_spy.by_type("tasks_ingested")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_agents"
    assert data["source_type"] == "jsonl"
    assert data["dry_run"] is True


@pytest.mark.asyncio
async def test_rollback_ingestion_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.ingestion_ops._brain_rollback_ingestion_impl",
               return_value="rolled-back"):
        await registered.tools["nucleus_agents"](
            "rollback_ingestion",
            {"batch_id": "B-9", "reason": "wrong source"},
        )
    calls = emit_spy.by_type("ingestion_rolled_back")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_agents"
    assert data["batch_id"] == "B-9"


@pytest.mark.asyncio
async def test_set_alert_threshold_emits(registered, emit_spy):
    with patch("mcp_server_nucleus.runtime.dashboard_ops._brain_set_alert_threshold_impl",
               return_value="set"):
        await registered.tools["nucleus_agents"](
            "set_alert_threshold",
            {"metric": "latency", "level": "high", "value": 500},
        )
    calls = emit_spy.by_type("alert_threshold_set")
    assert len(calls) == 1
    _, emitter, data, _ = calls[0]
    assert emitter == "nucleus_agents"
    assert data["metric"] == "latency"
    assert data["level"] == "high"
    assert data["value"] == 500


# ────────────────────────────────────────────────────────────────────────
# Coverage gate — total distinct emit_event call sites in orchestration.py
# ────────────────────────────────────────────────────────────────────────

async def test_orchestration_emit_coverage_at_least_30():
    """Static-grep gate: orchestration.py must emit on ≥30 distinct actions.

    Counted via grep against the source file; acceptance criterion from
    .brain/plans/engineering_remaining_20260522.md (E4 deliverable).
    """
    import pathlib
    src = pathlib.Path(__file__).parent.parent / "src" / "mcp_server_nucleus" / "tools" / "orchestration.py"
    text = src.read_text(encoding="utf-8")
    # Count call sites that look like `_emit_event("` / `emit_event("` / the
    # `_emit_telemetry("` helper, but not signature kwargs (`emit_event=None`,
    # `emit_event=_emit_event`).
    #
    # QG-4 replaced 27+1 inline `try: _emit_event(...) except Exception: pass`
    # swallows with one `_emit_telemetry(...)` helper that still emits but logs
    # the failure instead of discarding it. The emission sites did not go away,
    # they were renamed, so a pattern matching only the old name counts 3 and
    # reads a logging fix as a loss of coverage.
    import re
    pattern = re.compile(r"\b_?emit_(?:event|telemetry)\(\s*[\"']")
    sites = pattern.findall(text)
    assert len(sites) >= 30, (
        f"expected ≥30 emit_event call sites in orchestration.py, "
        f"found {len(sites)}"
    )
