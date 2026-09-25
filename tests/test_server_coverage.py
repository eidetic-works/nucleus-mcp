"""Coverage tests for mcp_server_nucleus/server.py — MCP resources, prompts,
and the main() entry point."""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from mcp_server_nucleus import server


# ── helpers ─────────────────────────────────────────────────────────

def _make_mcp():
    """Create a mock MCP that captures decorated resources/prompts/tools."""
    captured = {"resources": {}, "prompts": {}}

    def resource_decorator(uri):
        def wrapper(func):
            captured["resources"][uri] = func
            return func
        return wrapper

    def prompt_decorator(*args, **kwargs):
        def wrapper(func):
            captured["prompts"][func.__name__] = func
            return func
        return wrapper

    mcp = MagicMock()
    mcp.resource = resource_decorator
    mcp.prompt = prompt_decorator
    mcp._captured = captured
    return mcp


@pytest.fixture
def brain(tmp_path, monkeypatch):
    bp = tmp_path / ".brain"
    for sub in ["driver", "deltas", "meta", "training", "flywheel", "ledger"]:
        (bp / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(bp))
    return bp


@pytest.fixture
def registered(brain):
    """Register resources and prompts, return the captured dict."""
    mcp = _make_mcp()
    helpers = {
        "get_state": lambda: {"status": "ok"},
        "read_events": lambda limit=20: [{"type": "test"}],
        "get_triggers_impl": lambda: {"triggers": []},
        "depth_show": lambda: {"depth": 0},
        "resource_context_impl": lambda: "context here",
        "activate_synthesizer_prompt": lambda: "synth prompt",
        "start_sprint_prompt": lambda goal: f"sprint: {goal}",
        "cold_start_prompt": lambda: "cold start",
    }
    server.register_resources(mcp, helpers)
    server.register_prompts(mcp, helpers)
    return mcp._captured


# ── register_resources ──────────────────────────────────────────────

class TestRegisterResources:
    def test_all_resources_registered(self, registered):
        uris = list(registered["resources"].keys())
        assert "brain://state" in uris
        assert "brain://events" in uris
        assert "brain://triggers" in uris
        assert "brain://depth" in uris
        assert "brain://context" in uris
        assert "brain://changes" in uris
        assert "brain://traces" in uris
        assert "brain://health" in uris
        assert "brain://cycle" in uris
        assert "brain://arc" in uris
        assert "brain://deltas" in uris
        assert "brain://training" in uris
        assert "brain://frontiers" in uris
        assert "brain://growth" in uris
        assert "brain://flywheel/csr" in uris
        assert "brain://flywheel/dashboard" in uris
        assert "brain://flywheel/thesis" in uris
        assert "brain://flywheel/mentor" in uris
        assert "brain://flywheel/week" in uris


# ── resource functions ──────────────────────────────────────────────

class TestResourceState:
    def test_state(self, registered):
        r = registered["resources"]["brain://state"]()
        data = json.loads(r)
        assert data["status"] == "ok"

    def test_events(self, registered):
        r = registered["resources"]["brain://events"]()
        data = json.loads(r)
        assert data[0]["type"] == "test"

    def test_triggers_with_impl(self, registered):
        r = registered["resources"]["brain://triggers"]()
        data = json.loads(r)
        assert "triggers" in data

    def test_triggers_without_impl(self, brain):
        mcp = _make_mcp()
        helpers = {"get_state": lambda: {}, "read_events": lambda l: []}
        server.register_resources(mcp, helpers)
        r = mcp._captured["resources"]["brain://triggers"]()
        assert r == "{}"

    def test_depth_with_impl(self, registered):
        r = registered["resources"]["brain://depth"]()
        data = json.loads(r)
        assert data["depth"] == 0

    def test_depth_without_impl(self, brain):
        mcp = _make_mcp()
        helpers = {"get_state": lambda: {}, "read_events": lambda l: []}
        server.register_resources(mcp, helpers)
        r = mcp._captured["resources"]["brain://depth"]()
        assert r == "{}"

    def test_context_with_impl(self, registered):
        r = registered["resources"]["brain://context"]()
        assert r == "context here"

    def test_context_without_impl(self, brain):
        mcp = _make_mcp()
        helpers = {"get_state": lambda: {}, "read_events": lambda l: []}
        server.register_resources(mcp, helpers)
        r = mcp._captured["resources"]["brain://context"]()
        assert r == "Context not available"

    def test_changes(self, registered):
        with patch("mcp_server_nucleus.runtime.event_bus.get_change_ledger") as m:
            ledger = MagicMock()
            ledger.get_snapshot.return_value = {"global_version": 1}
            m.return_value = ledger
            r = registered["resources"]["brain://changes"]()
        data = json.loads(r)
        assert data["global_version"] == 1

    def test_changes_exception(self, registered):
        with patch("mcp_server_nucleus.runtime.event_bus.get_change_ledger", side_effect=Exception("boom")):
            r = registered["resources"]["brain://changes"]()
        data = json.loads(r)
        assert data["global_version"] == 0

    def test_traces(self, registered):
        with patch("mcp_server_nucleus.runtime.engram_ops._dsor_query_decisions_impl", return_value='{"d": []}'):
            r = registered["resources"]["brain://traces"]()
        assert "d" in r

    def test_traces_exception(self, registered):
        with patch("mcp_server_nucleus.runtime.engram_ops._dsor_query_decisions_impl", side_effect=Exception("boom")):
            r = registered["resources"]["brain://traces"]()
        data = json.loads(r)
        assert data["success"] is False


class TestResourceHealth:
    def test_health_empty(self, registered, brain):
        r = registered["resources"]["brain://health"]()
        data = json.loads(r)
        assert data["ground"]["total"] == 0
        assert data["align"]["total"] == 0
        assert data["compound"]["deltas"] == 0

    def test_health_with_data(self, registered, brain):
        (brain / "verification_log.jsonl").write_text(
            json.dumps({"tiers_failed": False}) + "\n" + json.dumps({"tiers_failed": ["x"]}) + "\n")
        (brain / "driver" / "human_verdicts.jsonl").write_text(
            json.dumps({"verdict": "accepted"}) + "\n" + json.dumps({"verdict": "corrected"}) + "\n"
            + json.dumps({"verdict": "pending"}) + "\n")
        (brain / "deltas" / "deltas.jsonl").write_text(json.dumps({"x": 1}) + "\n")
        r = registered["resources"]["brain://health"]()
        data = json.loads(r)
        assert data["ground"]["total"] == 2
        assert data["ground"]["pass_rate"] == 50.0
        assert data["align"]["total"] == 2
        assert data["align"]["corrected"] == 1
        assert data["compound"]["deltas"] == 1

    def test_health_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["resources"]["brain://health"]()
        data = json.loads(r)
        assert "error" in data


class TestResourceCycle:
    def test_no_cycle(self, registered, brain):
        r = registered["resources"]["brain://cycle"]()
        data = json.loads(r)
        assert data["cycle_id"] is None

    def test_with_cycle(self, registered, brain):
        (brain / "meta" / "compounding_cycle.json").write_text('{"cycle_id": "c1"}')
        r = registered["resources"]["brain://cycle"]()
        data = json.loads(r)
        assert data["cycle_id"] == "c1"

    def test_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["resources"]["brain://cycle"]()
        data = json.loads(r)
        assert "error" in data


class TestResourceArc:
    def test_arc(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.session_ops._load_session_arc", return_value={"sessions": []}):
            r = registered["resources"]["brain://arc"]()
        data = json.loads(r)
        assert "sessions" in data

    def test_arc_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.session_ops._load_session_arc", side_effect=Exception("boom")):
            r = registered["resources"]["brain://arc"]()
        data = json.loads(r)
        assert "error" in data


class TestResourceDeltas:
    def test_no_deltas(self, registered, brain):
        r = registered["resources"]["brain://deltas"]()
        data = json.loads(r)
        assert data["total_deltas"] == 0

    def test_with_deltas(self, registered, brain):
        now = datetime.now(timezone.utc).isoformat()
        (brain / "deltas" / "deltas.jsonl").write_text(
            json.dumps({"timestamp": now, "delta": {"direction": "positive"}}) + "\n"
            + json.dumps({"timestamp": now, "delta": {"direction": "negative"}}) + "\n"
            + json.dumps({"timestamp": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                          "delta": {"direction": "positive"}}) + "\n"
        )
        r = registered["resources"]["brain://deltas"]()
        data = json.loads(r)
        assert data["total_deltas"] == 3
        assert data["last_7d"] == 2
        assert data["positive"] == 1
        assert data["negative"] == 1

    def test_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["resources"]["brain://deltas"]()
        data = json.loads(r)
        assert "error" in data


class TestResourceTraining:
    def test_empty(self, registered, brain):
        r = registered["resources"]["brain://training"]()
        data = json.loads(r)
        assert data["total_turns"] == 0
        assert data["retrain_recommended"] is False

    def test_with_data(self, registered, brain):
        (brain / "training" / "loop_turns.jsonl").write_text('{"t": 1}\n{"t": 2}\n')
        (brain / "training" / "preference_pairs.jsonl").write_text('{"p": 1}\n')
        r = registered["resources"]["brain://training"]()
        data = json.loads(r)
        assert data["total_turns"] == 2
        assert data["total_preferences"] == 1
        assert data["retrain_recommended"] is False

    def test_retrain_threshold(self, registered, brain):
        (brain / "training" / "loop_turns.jsonl").write_text("\n".join(["{}"] * 50))
        r = registered["resources"]["brain://training"]()
        data = json.loads(r)
        assert data["retrain_recommended"] is True

    def test_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["resources"]["brain://training"]()
        data = json.loads(r)
        assert "error" in data


class TestResourceFrontiers:
    def test_empty(self, registered, brain):
        r = registered["resources"]["brain://frontiers"]()
        data = json.loads(r)
        assert data["GROUND"]["verified_count"] == 0
        assert data["ALIGN"]["human_reviews"] == 0
        assert data["COMPOUND"]["deltas_recorded"] == 0

    def test_with_data(self, registered, brain):
        (brain / "verification_log.jsonl").write_text(
            json.dumps({"tiers_failed": False}) + "\n" + json.dumps({"tiers_failed": True}) + "\n")
        (brain / "driver" / "human_verdicts.jsonl").write_text(
            json.dumps({"verdict": "accepted"}) + "\n" + json.dumps({"verdict": "corrected"}) + "\n")
        (brain / "deltas" / "deltas.jsonl").write_text(
            json.dumps({"delta": {"direction": "positive"}}) + "\n")
        r = registered["resources"]["brain://frontiers"]()
        data = json.loads(r)
        assert data["GROUND"]["verified_count"] == 2
        assert data["GROUND"]["pass_rate"] == 0.5
        assert data["ALIGN"]["human_reviews"] == 2
        assert data["ALIGN"]["accept_rate"] == 0.5
        assert data["COMPOUND"]["deltas_recorded"] == 1

    def test_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["resources"]["brain://frontiers"]()
        data = json.loads(r)
        assert "error" in data


class TestResourceGrowth:
    def test_no_data(self, registered, brain):
        r = registered["resources"]["brain://growth"]()
        data = json.loads(r)
        assert data["status"] == "no growth data"

    def test_with_data(self, registered, brain):
        (brain / "meta" / "growth_metrics.json").write_text('{"gates": {"x": 1}}')
        r = registered["resources"]["brain://growth"]()
        data = json.loads(r)
        assert data["gates"]["x"] == 1

    def test_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["resources"]["brain://growth"]()
        data = json.loads(r)
        assert "error" in data


class TestResourceFlywheel:
    def test_csr(self, registered, brain):
        with patch("mcp_server_nucleus.flywheel.read_csr", return_value={"ratio": 1.0}):
            r = registered["resources"]["brain://flywheel/csr"]()
        data = json.loads(r)
        assert data["ratio"] == 1.0

    def test_csr_exception(self, registered, brain):
        with patch("mcp_server_nucleus.flywheel.read_csr", side_effect=Exception("boom")):
            r = registered["resources"]["brain://flywheel/csr"]()
        data = json.loads(r)
        assert "error" in data

    def test_dashboard(self, registered, brain):
        with patch("mcp_server_nucleus.flywheel.render_dashboard_json", return_value={"csr": {}}):
            r = registered["resources"]["brain://flywheel/dashboard"]()
        data = json.loads(r)
        assert "csr" in data

    def test_dashboard_exception(self, registered, brain):
        with patch("mcp_server_nucleus.flywheel.render_dashboard_json", side_effect=Exception("boom")):
            r = registered["resources"]["brain://flywheel/dashboard"]()
        data = json.loads(r)
        assert "error" in data

    def test_thesis_exists(self, registered, brain):
        (brain / "flywheel" / "thesis.md").write_text("# My thesis")
        r = registered["resources"]["brain://flywheel/thesis"]()
        assert "My thesis" in r

    def test_thesis_missing(self, registered, brain):
        r = registered["resources"]["brain://flywheel/thesis"]()
        assert "not yet seeded" in r

    def test_mentor_exists(self, registered, brain):
        (brain / "flywheel" / "mentor.md").write_text("# Mentor")
        r = registered["resources"]["brain://flywheel/mentor"]()
        assert "Mentor" in r

    def test_mentor_missing(self, registered, brain):
        r = registered["resources"]["brain://flywheel/mentor"]()
        assert "not yet seeded" in r

    def test_week_exists(self, registered, brain):
        week = datetime.now(timezone.utc).isocalendar()[1]
        (brain / "flywheel" / f"week-{week}.md").write_text("# Week report")
        r = registered["resources"]["brain://flywheel/week"]()
        assert "Week report" in r

    def test_week_missing(self, registered, brain):
        r = registered["resources"]["brain://flywheel/week"]()
        assert "No activity" in r

    def test_thesis_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["resources"]["brain://flywheel/thesis"]()
        assert "error" in r

    def test_mentor_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["resources"]["brain://flywheel/mentor"]()
        assert "error" in r

    def test_week_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["resources"]["brain://flywheel/week"]()
        assert "error" in r


# ── register_prompts ────────────────────────────────────────────────

class TestRegisterPrompts:
    def test_all_prompts_registered(self, registered):
        names = list(registered["prompts"].keys())
        assert "activate_synthesizer" in names
        assert "start_sprint" in names
        assert "cold_start" in names
        assert "compound_context" in names
        assert "align_review" in names
        assert "weekly_synthesis" in names
        assert "flywheel_check" in names
        assert "flywheel_brief" in names


class TestPrompts:
    def test_activate_synthesizer(self, registered):
        assert registered["prompts"]["activate_synthesizer"]() == "synth prompt"

    def test_activate_synthesizer_no_impl(self, brain):
        mcp = _make_mcp()
        server.register_prompts(mcp, {})
        assert mcp._captured["prompts"]["activate_synthesizer"]() == "Prompt not available"

    def test_start_sprint(self, registered):
        assert "sprint: MVP" in registered["prompts"]["start_sprint"]("MVP")

    def test_start_sprint_no_impl(self, brain):
        mcp = _make_mcp()
        server.register_prompts(mcp, {})
        assert mcp._captured["prompts"]["start_sprint"]() == "Prompt not available"

    def test_cold_start(self, registered):
        assert registered["prompts"]["cold_start"]() == "cold start"

    def test_cold_start_no_impl(self, brain):
        mcp = _make_mcp()
        server.register_prompts(mcp, {})
        assert mcp._captured["prompts"]["cold_start"]() == "Prompt not available"

    def test_compound_context_no_deltas(self, registered, brain):
        r = registered["prompts"]["compound_context"]()
        assert "No Deltas" in r

    def test_compound_context_with_deltas(self, registered, brain):
        now = datetime.now(timezone.utc).isoformat()
        (brain / "deltas" / "deltas.jsonl").write_text(
            json.dumps({"timestamp": now, "delta": {"direction": "negative", "insight": "failed"}}) + "\n"
            + json.dumps({"timestamp": now, "delta": {"direction": "positive"}}) + "\n")
        r = registered["prompts"]["compound_context"]()
        assert "COMPOUND Frontier" in r
        assert "Recurring Negatives" in r

    def test_compound_context_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["prompts"]["compound_context"]()
        assert "Error" in r

    def test_align_review_no_verdicts(self, registered, brain):
        r = registered["prompts"]["align_review"]()
        assert "No human verdicts" in r

    def test_align_review_with_verdicts(self, registered, brain):
        (brain / "driver" / "human_verdicts.jsonl").write_text(
            json.dumps({"verdict": "accepted", "reason": "good"}) + "\n"
            + json.dumps({"verdict": "corrected", "reason": "bad"}) + "\n")
        r = registered["prompts"]["align_review"]()
        assert "ALIGN Frontier" in r
        assert "Recent Corrections" in r

    def test_align_review_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["prompts"]["align_review"]()
        assert "Error" in r

    def test_weekly_synthesis_no_cycle(self, registered, brain):
        r = registered["prompts"]["weekly_synthesis"]()
        assert "Weekly Synthesis" in r

    def test_weekly_synthesis_with_cycle(self, registered, brain):
        (brain / "meta" / "compounding_cycle.json").write_text('{"cycle_id": "c1", "weekly_delta": "+5"}')
        r = registered["prompts"]["weekly_synthesis"]()
        assert "Cycle c1" in r

    def test_weekly_synthesis_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["prompts"]["weekly_synthesis"]()
        assert "Error" in r

    def test_flywheel_check(self, registered, brain):
        with patch("mcp_server_nucleus.flywheel.render_dashboard_json",
                   return_value={"csr": {"ratio": 0.9, "claims_survived": 9, "claims_total": 10},
                                 "tickets": {"open": 3}, "curriculum": {"pending": 2, "ready": 1},
                                 "recent_claims": [{"survived": True, "step": "s1", "at": now_iso()}]}):
            r = registered["prompts"]["flywheel_check"]()
        assert "FLYWHEEL Status" in r
        assert "90.0%" in r

    def test_flywheel_check_exception(self, registered, brain):
        with patch("mcp_server_nucleus.flywheel.render_dashboard_json", side_effect=Exception("boom")):
            r = registered["prompts"]["flywheel_check"]()
        assert "Error" in r

    def test_flywheel_brief_exists(self, registered, brain):
        week = datetime.now(timezone.utc).isocalendar()[1]
        (brain / "flywheel" / f"week-{week}.md").write_text("# Week report")
        r = registered["prompts"]["flywheel_brief"]()
        assert "Week report" in r

    def test_flywheel_brief_missing(self, registered, brain):
        r = registered["prompts"]["flywheel_brief"]()
        assert "No activity this week" in r

    def test_flywheel_brief_exception(self, registered, brain):
        with patch("mcp_server_nucleus.runtime.common.get_brain_path", side_effect=Exception("boom")):
            r = registered["prompts"]["flywheel_brief"]()
        assert "Error" in r

    def test_compound_context_no_negatives(self, registered, brain):
        now = datetime.now(timezone.utc).isoformat()
        (brain / "deltas" / "deltas.jsonl").write_text(
            json.dumps({"timestamp": now, "delta": {"direction": "positive"}}) + "\n")
        r = registered["prompts"]["compound_context"]()
        assert "COMPOUND Frontier" in r
        assert "Recurring Negatives" not in r

    def test_align_review_no_corrections(self, registered, brain):
        (brain / "driver" / "human_verdicts.jsonl").write_text(
            json.dumps({"verdict": "accepted", "reason": "good"}) + "\n")
        r = registered["prompts"]["align_review"]()
        assert "ALIGN Frontier" in r
        assert "Recent Corrections" not in r

    def test_weekly_synthesis_with_frontiers(self, registered, brain):
        """When resource_frontiers is available as a module global, frontiers data is included."""
        (brain / "meta" / "compounding_cycle.json").write_text('{"cycle_id": "c1", "weekly_delta": "+5"}')
        (brain / "verification_log.jsonl").write_text(json.dumps({"tiers_failed": False}) + "\n")
        (brain / "driver" / "human_verdicts.jsonl").write_text(json.dumps({"verdict": "accepted"}) + "\n")
        (brain / "deltas" / "deltas.jsonl").write_text(json.dumps({"delta": {"direction": "positive"}}) + "\n")
        # Inject resource_frontiers as a module global so weekly_synthesis can find it
        def _mock_frontiers():
            return json.dumps({"GROUND": {"verified_count": 1}, "ALIGN": {"human_reviews": 1},
                               "COMPOUND": {"deltas_recorded": 1}})
        with patch.object(server, "resource_frontiers", _mock_frontiers, create=True):
            r = registered["prompts"]["weekly_synthesis"]()
        assert "Cycle c1" in r
        assert "Frontiers" in r
        assert "GROUND" in r

    def test_weekly_synthesis_frontiers_unavailable(self, registered, brain):
        """Without resource_frontiers in scope, frontiers data is unavailable."""
        (brain / "meta" / "compounding_cycle.json").write_text('{"cycle_id": "c1"}')
        r = registered["prompts"]["weekly_synthesis"]()
        assert "frontiers data unavailable" in r

    def test_flywheel_check_no_recent(self, registered, brain):
        with patch("mcp_server_nucleus.flywheel.render_dashboard_json",
                   return_value={"csr": {"ratio": 0.9}, "tickets": {"open": 3},
                                 "curriculum": {"pending": 2, "ready": 1}, "recent_claims": []}):
            r = registered["prompts"]["flywheel_check"]()
        assert "FLYWHEEL Status" in r
        assert "Last 5 claims" not in r


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── main ────────────────────────────────────────────────────────────

class TestMain:
    def test_stdio_fallback(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", True), \
             patch("mcp_server_nucleus.mcp", MagicMock()), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.runtime.stdio_server.StdioServer") as srv_cls, \
             patch("asyncio.run") as async_run:
            srv = MagicMock()
            srv_cls.return_value = srv
            server.main()
        async_run.assert_called_once()

    def test_full_server_start(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", return_value=MagicMock()), \
             patch("mcp_server_nucleus.runtime.event_bus.get_event_bus", return_value=MagicMock()), \
             patch("mcp_server_nucleus.runtime.event_bus.get_change_ledger", return_value=MagicMock()), \
             patch("mcp_server_nucleus.runtime.relay_ops.auto_start_relay_watcher"), \
             patch("mcp_server_nucleus.runtime.event_ops._emit_event"):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            server.main()
        mock_mcp.run.assert_called_once()

    def test_main_mcp_run_exception(self, brain, monkeypatch):
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        mock_mcp.run.side_effect = RuntimeError("crash")
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", side_effect=ImportError("no")):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            with pytest.raises(RuntimeError, match="crash"):
                server.main()

    def test_main_tier_exception_swallows(self, brain, monkeypatch):
        """Tier info exception should be swallowed, not crash main."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", side_effect=Exception("tier fail")), \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", side_effect=ImportError("no")):
            server.main()
        mock_mcp.run.assert_called_once()

    def test_main_file_monitor_init(self, brain, monkeypatch):
        """File monitor initializes with event bridge when brain path exists."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        mock_monitor = MagicMock()
        mock_bus = MagicMock()
        mock_ledger = MagicMock()
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", return_value=mock_monitor) as init_fm, \
             patch("mcp_server_nucleus.runtime.file_monitor.FileChangeEvent"), \
             patch("mcp_server_nucleus.runtime.event_bus.get_event_bus", return_value=mock_bus), \
             patch("mcp_server_nucleus.runtime.event_bus.get_change_ledger", return_value=mock_ledger), \
             patch("mcp_server_nucleus.runtime.event_bus.BrainFileEvent") as evt_cls, \
             patch("mcp_server_nucleus.runtime.event_ops._emit_event") as emit, \
             patch("mcp_server_nucleus.runtime.relay_ops.auto_start_relay_watcher"):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            server.main()
        mock_monitor.start.assert_called_once()
        mock_bus.subscribe.assert_called_once()
        init_fm.assert_called_once()

    def test_main_file_monitor_callback(self, brain, monkeypatch):
        """The _on_brain_file_change callback emits events for meaningful paths."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        mock_monitor = MagicMock()
        mock_bus = MagicMock()
        # Capture the callback passed to init_file_monitor
        captured_cb = []

        def capture_cb(path, on_change=None):
            captured_cb.append(on_change)
            return mock_monitor

        brain_str = str(brain)
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain_str), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", side_effect=capture_cb), \
             patch("mcp_server_nucleus.runtime.file_monitor.FileChangeEvent"), \
             patch("mcp_server_nucleus.runtime.event_bus.get_event_bus", return_value=mock_bus), \
             patch("mcp_server_nucleus.runtime.event_bus.get_change_ledger", return_value=MagicMock()), \
             patch("mcp_server_nucleus.runtime.event_bus.BrainFileEvent"), \
             patch("mcp_server_nucleus.runtime.event_ops._emit_event") as emit, \
             patch("mcp_server_nucleus.runtime.relay_ops.auto_start_relay_watcher"):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            server.main()
        # Invoke the callback with a meaningful path
        assert len(captured_cb) == 1
        cb = captured_cb[0]
        event = MagicMock()
        event.path = brain_str + "/tasks.json"
        event.event_type = "modified"
        cb(event)
        emit.assert_any_call(
            "file_modified", "FILE_MONITOR",
            {"path": "tasks.json", "event_type": "modified"},
            "Brain file modified: tasks.json",
        )
        mock_bus.publish.assert_called_once()

    def test_main_file_monitor_callback_ignores_irrelevant(self, brain, monkeypatch):
        """The _on_brain_file_change callback ignores irrelevant paths."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        mock_monitor = MagicMock()
        mock_bus = MagicMock()
        captured_cb = []

        def capture_cb(path, on_change=None):
            captured_cb.append(on_change)
            return mock_monitor

        brain_str = str(brain)
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain_str), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", side_effect=capture_cb), \
             patch("mcp_server_nucleus.runtime.file_monitor.FileChangeEvent"), \
             patch("mcp_server_nucleus.runtime.event_bus.get_event_bus", return_value=mock_bus), \
             patch("mcp_server_nucleus.runtime.event_bus.get_change_ledger", return_value=MagicMock()), \
             patch("mcp_server_nucleus.runtime.event_bus.BrainFileEvent"), \
             patch("mcp_server_nucleus.runtime.event_ops._emit_event") as emit, \
             patch("mcp_server_nucleus.runtime.relay_ops.auto_start_relay_watcher"):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            server.main()
        cb = captured_cb[0]
        event = MagicMock()
        event.path = brain_str + "/random_file.txt"
        event.event_type = "modified"
        emit.reset_mock()
        mock_bus.reset_mock()
        cb(event)
        emit.assert_not_called()
        mock_bus.publish.assert_not_called()

    def test_main_file_monitor_callback_exception(self, brain, monkeypatch):
        """The _on_brain_file_change callback swallows exceptions."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        mock_monitor = MagicMock()
        mock_bus = MagicMock()
        captured_cb = []

        def capture_cb(path, on_change=None):
            captured_cb.append(on_change)
            return mock_monitor

        brain_str = str(brain)
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain_str), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", side_effect=capture_cb), \
             patch("mcp_server_nucleus.runtime.file_monitor.FileChangeEvent"), \
             patch("mcp_server_nucleus.runtime.event_bus.get_event_bus", return_value=mock_bus), \
             patch("mcp_server_nucleus.runtime.event_bus.get_change_ledger", return_value=MagicMock()), \
             patch("mcp_server_nucleus.runtime.event_bus.BrainFileEvent"), \
             patch("mcp_server_nucleus.runtime.event_ops._emit_event", side_effect=Exception("boom")), \
             patch("mcp_server_nucleus.runtime.relay_ops.auto_start_relay_watcher"):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            server.main()
        cb = captured_cb[0]
        event = MagicMock()
        event.path = brain_str + "/tasks.json"
        event.event_type = "modified"
        # Should not raise
        cb(event)

    def test_main_file_monitor_generic_exception(self, brain, monkeypatch):
        """File monitor init with generic Exception (not ImportError) is caught."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", side_effect=Exception("boom")), \
             patch("mcp_server_nucleus.runtime.relay_ops.auto_start_relay_watcher"):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            server.main()
        mock_mcp.run.assert_called_once()

    def test_main_relay_watcher_exception(self, brain, monkeypatch):
        """Relay watcher auto-start exception is caught."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", side_effect=ImportError("no")), \
             patch("mcp_server_nucleus.runtime.relay_ops.auto_start_relay_watcher", side_effect=Exception("boom")):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            server.main()
        mock_mcp.run.assert_called_once()

    def test_main_session_started_exception(self, brain, monkeypatch):
        """session_started emission exception is caught."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=brain), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor", side_effect=ImportError("no")), \
             patch("mcp_server_nucleus.runtime.relay_ops.auto_start_relay_watcher"), \
             patch("mcp_server_nucleus.runtime.event_ops._emit_event", side_effect=Exception("boom")):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            server.main()
        mock_mcp.run.assert_called_once()

    def test_main_brain_path_not_exists(self, brain, monkeypatch):
        """When brain path doesn't exist, file monitor is skipped."""
        monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(brain))
        mock_mcp = MagicMock()
        nonexistent = "/nonexistent/brain/path"
        with patch("mcp_server_nucleus.USE_STDIO_FALLBACK", False), \
             patch("mcp_server_nucleus.mcp", mock_mcp), \
             patch("mcp_server_nucleus.get_brain_path", return_value=nonexistent), \
             patch("mcp_server_nucleus.__version__", "1.0"), \
             patch("mcp_server_nucleus.tool_tiers.get_active_tier", return_value=0), \
             patch("mcp_server_nucleus.tool_tiers.get_tier_info",
                   return_value={"tier_name": "LAUNCH", "active_tier": 0}), \
             patch("mcp_server_nucleus.tool_tiers.tier_manager") as tm, \
             patch("mcp_server_nucleus.runtime.file_monitor.init_file_monitor") as init_fm, \
             patch("mcp_server_nucleus.runtime.relay_ops.auto_start_relay_watcher"):
            tm.registered_tools = set()
            tm.filtered_tools = set()
            server.main()
        init_fm.assert_not_called()
        mock_mcp.run.assert_called_once()
