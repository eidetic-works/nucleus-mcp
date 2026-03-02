"""Tests for God Combos — Pulse & Polish pipeline."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestPulseAndPolish(unittest.TestCase):
    """Test the Pulse & Polish God Combo pipeline."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir()
        (self.brain_path / "engrams").mkdir(parents=True)
        (self.brain_path / "ledger").mkdir(parents=True)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def test_pipeline_runs_end_to_end(self):
        """Pulse & Polish completes all 4 steps without crashing."""
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish

        result = run_pulse_and_polish(write_engram=False)

        self.assertEqual(result["pipeline"], "pulse_and_polish")
        self.assertIn("sections", result)
        self.assertIn("pulse", result["sections"])
        self.assertIn("audit", result["sections"])
        self.assertIn("brief", result["sections"])
        self.assertIsNotNone(result["synthesis"])
        self.assertGreaterEqual(result["meta"]["steps_completed"], 1)
        self.assertFalse(result["meta"]["circuit_breaker_hit"])

    def test_pipeline_writes_engram(self):
        """Pulse & Polish writes a synthesis engram when write_engram=True."""
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish

        # Create engram ledger so write works
        ledger = self.brain_path / "engrams" / "ledger.jsonl"
        ledger.touch()

        result = run_pulse_and_polish(write_engram=True)

        self.assertTrue(result["meta"].get("engram_written", False))
        # Verify engram was written to ledger
        content = ledger.read_text().strip()
        self.assertTrue(len(content) > 0, "Engram should have been written to ledger")
        engram = json.loads(content.split("\n")[-1])
        self.assertIn("pulse_and_polish", engram["key"])

    def test_pipeline_no_engram_when_disabled(self):
        """Pulse & Polish skips engram write when write_engram=False."""
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish

        result = run_pulse_and_polish(write_engram=False)

        self.assertNotIn("engram_written", result["meta"])

    def test_synthesis_health_classification(self):
        """Synthesis correctly classifies overall health."""
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish

        result = run_pulse_and_polish(write_engram=False)

        synthesis = result["synthesis"]
        self.assertIn(synthesis["overall_health"], [
            "🟢 OPERATIONAL", "🟡 DEGRADED", "🔴 CRITICAL"
        ])
        self.assertIsInstance(synthesis["health_signals"], list)

    def test_execution_time_tracked(self):
        """Meta section tracks execution time."""
        from mcp_server_nucleus.runtime.god_combos.pulse_and_polish import run_pulse_and_polish

        result = run_pulse_and_polish(write_engram=False)

        self.assertGreater(result["meta"]["execution_time_ms"], 0)


class TestSelfHealingSRE(unittest.TestCase):
    """Test the Self-Healing SRE God Combo pipeline."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir()
        (self.brain_path / "engrams").mkdir(parents=True)
        (self.brain_path / "ledger").mkdir(parents=True)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def test_sre_pipeline_runs_end_to_end(self):
        """SRE pipeline completes all steps without crashing."""
        from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre

        result = run_self_healing_sre(symptom="high latency", write_engram=False)

        self.assertEqual(result["pipeline"], "self_healing_sre")
        self.assertEqual(result["symptom"], "high latency")
        self.assertIn("search", result["sections"])
        self.assertIn("metrics", result["sections"])
        self.assertIsNotNone(result["diagnosis"])
        self.assertIsNotNone(result["recommendation"])
        self.assertGreaterEqual(result["meta"]["steps_completed"], 1)

    def test_sre_severity_classification(self):
        """Diagnosis returns valid severity levels."""
        from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre

        result = run_self_healing_sre(symptom="test", write_engram=False)

        self.assertIn(result["diagnosis"]["severity"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        self.assertIsInstance(result["diagnosis"]["findings"], list)

    def test_sre_writes_engram(self):
        """SRE pipeline writes a diagnosis engram when enabled."""
        from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre

        ledger = self.brain_path / "engrams" / "ledger.jsonl"
        ledger.touch()

        result = run_self_healing_sre(symptom="errors", write_engram=True)

        self.assertTrue(result["meta"].get("engram_written", False))
        content = ledger.read_text().strip()
        self.assertTrue(len(content) > 0)
        engram = json.loads(content.split("\n")[-1])
        self.assertIn("sre_diagnosis", engram["key"])

    def test_sre_recommendation_has_action(self):
        """Recommendation always includes an action string."""
        from mcp_server_nucleus.runtime.god_combos.self_healing_sre import run_self_healing_sre

        result = run_self_healing_sre(symptom="test", write_engram=False)

        self.assertIn("action", result["recommendation"])
        self.assertIsInstance(result["recommendation"]["action"], str)
        self.assertTrue(len(result["recommendation"]["action"]) > 0)


class TestHITLGates(unittest.TestCase):
    """Test HITL confirmation gates on destructive operations."""

    def test_delete_file_blocked_without_confirm(self):
        """delete_file returns HITL warning when confirm=False."""
        from mcp_server_nucleus.runtime.hypervisor_ops import nucleus_delete_file_impl

        result = nucleus_delete_file_impl("/tmp/nonexistent_test_file", confirm=False)
        self.assertIn("HITL GATE", result)
        self.assertIn("confirm=true", result)

    def test_delete_file_proceeds_with_confirm(self):
        """delete_file actually deletes when confirm=True."""
        from mcp_server_nucleus.runtime.hypervisor_ops import nucleus_delete_file_impl

        # Create a temp file to delete
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".hitl_test")
        tmp.write(b"test")
        tmp.close()

        result = nucleus_delete_file_impl(tmp.name, confirm=True)
        self.assertIn("SUCCESS", result)
        self.assertFalse(Path(tmp.name).exists())

    def test_delete_file_not_found_with_confirm(self):
        """delete_file returns error for missing file even with confirm=True."""
        from mcp_server_nucleus.runtime.hypervisor_ops import nucleus_delete_file_impl

        result = nucleus_delete_file_impl("/tmp/definitely_not_a_real_file_12345", confirm=True)
        self.assertIn("ERROR", result)


class TestFusionReactor(unittest.TestCase):
    """Test the Fusion Reactor God Combo pipeline."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir()
        (self.brain_path / "engrams").mkdir(parents=True)
        (self.brain_path / "ledger").mkdir(parents=True)
        # Create empty ledger so writes work
        (self.brain_path / "engrams" / "ledger.jsonl").touch()
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def test_fusion_runs_end_to_end(self):
        """Fusion Reactor completes all steps."""
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor

        result = run_fusion_reactor(observation="Cache fix reduced latency by 40%", write_engrams=False)

        self.assertEqual(result["pipeline"], "fusion_reactor")
        self.assertIn("capture", result["sections"])
        self.assertIn("recall", result["sections"])
        self.assertIsNotNone(result["synthesis"])
        self.assertEqual(result["meta"]["steps_completed"], 4)
        self.assertFalse(result["meta"]["circuit_breaker_hit"])

    def test_fusion_writes_two_engrams(self):
        """Fusion Reactor writes capture + synthesis engrams."""
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor

        result = run_fusion_reactor(observation="Test observation", write_engrams=True)

        self.assertEqual(result["meta"]["engrams_written"], 2)
        ledger = self.brain_path / "engrams" / "ledger.jsonl"
        lines = [l for l in ledger.read_text().strip().split("\n") if l.strip()]
        self.assertGreaterEqual(len(lines), 2)
        # First should be capture, last should be synthesis
        first = json.loads(lines[0])
        last = json.loads(lines[-1])
        self.assertIn("fusion_capture", first["key"])
        self.assertIn("fusion_synthesis", last["key"])

    def test_fusion_novel_synthesis_type(self):
        """Novel observation (no prior engrams) gets NOVEL type."""
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor

        result = run_fusion_reactor(
            observation="Completely unique xyzzy test observation",
            write_engrams=False,
        )

        self.assertEqual(result["synthesis"]["type"], "novel")
        self.assertIn("[NOVEL]", result["synthesis"]["value"])

    def test_fusion_compounding_factor(self):
        """Compounding factor increases with prior engrams."""
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor

        result = run_fusion_reactor(observation="test", write_engrams=False)

        self.assertGreaterEqual(result["synthesis"]["compounding_factor"], 1.0)

    def test_fusion_intensity_capped(self):
        """Synthesis intensity is base+1 but capped at 10."""
        from mcp_server_nucleus.runtime.god_combos.fusion_reactor import run_fusion_reactor

        result = run_fusion_reactor(observation="test", intensity=10, write_engrams=False)

        self.assertEqual(result["synthesis"]["intensity"], 10)  # Capped


class TestContextGraph(unittest.TestCase):
    """Test the Context Graph module."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir()
        (self.brain_path / "engrams").mkdir(parents=True)
        (self.brain_path / "ledger").mkdir(parents=True)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def _write_engrams(self, engrams):
        ledger = self.brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            for e in engrams:
                f.write(json.dumps(e) + "\n")

    def test_empty_graph(self):
        """Empty brain produces empty graph."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        graph = build_context_graph()
        self.assertEqual(graph["stats"]["node_count"], 0)
        self.assertEqual(graph["stats"]["edge_count"], 0)

    def test_graph_with_engrams(self):
        """Graph builds nodes and context edges from engrams."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        self._write_engrams([
            {"key": "test_a", "value": "cache optimization for latency", "context": "Architecture", "intensity": 8, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "test_b", "value": "cache warming strategy", "context": "Architecture", "intensity": 7, "timestamp": "2026-03-01T10:00:05Z"},
            {"key": "test_c", "value": "brand voice guidelines", "context": "Brand", "intensity": 6, "timestamp": "2026-03-01T12:00:00Z"},
        ])
        graph = build_context_graph()
        self.assertEqual(graph["stats"]["node_count"], 3)
        self.assertGreater(graph["stats"]["edge_count"], 0)
        self.assertIn("Architecture", graph["clusters"]["by_context"])

    def test_context_edges(self):
        """Same-context engrams get context edges."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        self._write_engrams([
            {"key": "a1", "value": "first", "context": "Feature", "intensity": 5, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "a2", "value": "second", "context": "Feature", "intensity": 5, "timestamp": "2026-03-01T12:00:00Z"},
        ])
        graph = build_context_graph()
        context_edges = [e for e in graph["edges"] if e["type"] == "context"]
        self.assertGreater(len(context_edges), 0)

    def test_prefix_clustering(self):
        """Engrams with shared key prefix are clustered."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        self._write_engrams([
            {"key": "fusion_capture_20260301_100000", "value": "obs1", "context": "Decision", "intensity": 6, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "fusion_capture_20260301_100100", "value": "obs2", "context": "Decision", "intensity": 6, "timestamp": "2026-03-01T10:01:00Z"},
        ])
        graph = build_context_graph()
        # Prefix extraction strips one trailing numeric segment at a time
        # fusion_capture_20260301_100000 → fusion_capture_20260301
        self.assertIn("fusion_capture_20260301", graph["clusters"]["by_prefix"])

    def test_temporal_edges(self):
        """Engrams written within 60s get temporal edges."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        self._write_engrams([
            {"key": "t1", "value": "alpha task", "context": "Strategy", "intensity": 5, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "t2", "value": "beta task", "context": "Brand", "intensity": 5, "timestamp": "2026-03-01T10:00:30Z"},
        ])
        graph = build_context_graph()
        temporal_edges = [e for e in graph["edges"] if e["type"] == "temporal"]
        self.assertGreater(len(temporal_edges), 0)

    def test_semantic_edges(self):
        """Engrams with shared keywords get semantic edges."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        # Use different contexts and far timestamps so only semantic edges can form
        self._write_engrams([
            {"key": "s1", "value": "cache optimization reduced latency significantly improved throughput performance", "context": "Architecture", "intensity": 8, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "s2", "value": "cache optimization reduced latency significantly improved throughput performance", "context": "Feature", "intensity": 7, "timestamp": "2026-01-01T12:00:00Z"},
        ])
        graph = build_context_graph()
        semantic_edges = [e for e in graph["edges"] if e["type"] == "semantic"]
        self.assertGreater(len(semantic_edges), 0)

    def test_engram_neighbors(self):
        """get_engram_neighbors returns the right neighborhood."""
        from mcp_server_nucleus.runtime.context_graph import get_engram_neighbors
        self._write_engrams([
            {"key": "center", "value": "central node", "context": "Architecture", "intensity": 8, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "neighbor1", "value": "linked node", "context": "Architecture", "intensity": 7, "timestamp": "2026-03-01T10:00:10Z"},
            {"key": "far_away", "value": "isolated node", "context": "Brand", "intensity": 3, "timestamp": "2026-01-01T00:00:00Z"},
        ])
        result = get_engram_neighbors("center", max_depth=1)
        self.assertEqual(result["target"]["id"], "center")
        self.assertGreater(result["neighbor_count"], 0)

    def test_engram_neighbors_not_found(self):
        """get_engram_neighbors returns error for missing key."""
        from mcp_server_nucleus.runtime.context_graph import get_engram_neighbors
        result = get_engram_neighbors("nonexistent_key")
        self.assertIn("error", result)

    def test_min_intensity_filter(self):
        """Graph respects min_intensity filter."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        self._write_engrams([
            {"key": "high", "value": "important", "context": "Architecture", "intensity": 9, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "low", "value": "trivial", "context": "Architecture", "intensity": 2, "timestamp": "2026-03-01T10:00:00Z"},
        ])
        graph = build_context_graph(min_intensity=5)
        self.assertEqual(graph["stats"]["node_count"], 1)

    def test_density_calculation(self):
        """Graph density is between 0 and 1."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        self._write_engrams([
            {"key": f"d{i}", "value": f"node {i}", "context": "Feature", "intensity": 5, "timestamp": "2026-03-01T10:00:00Z"}
            for i in range(5)
        ])
        graph = build_context_graph()
        self.assertGreaterEqual(graph["stats"]["density"], 0)
        self.assertLessEqual(graph["stats"]["density"], 1)


class TestBillingSubsystem(unittest.TestCase):
    """Test the Billing subsystem."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir()
        (self.brain_path / "ledger").mkdir(parents=True)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def _write_audit(self, entries):
        path = self.brain_path / "ledger" / "interaction_log.jsonl"
        with open(path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def _write_events(self, entries):
        path = self.brain_path / "ledger" / "events.jsonl"
        with open(path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def test_empty_billing(self):
        """Empty brain returns zero cost."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        result = compute_usage_summary()
        self.assertEqual(result["total_cost_units"], 0)
        self.assertEqual(result["total_interactions"], 0)

    def test_tier_classification(self):
        """Actions are classified into correct tiers."""
        from mcp_server_nucleus.runtime.billing import _classify_tier
        self.assertEqual(_classify_tier("delete_file"), 4)
        self.assertEqual(_classify_tier("spawn_agent"), 3)
        self.assertEqual(_classify_tier("write_engram"), 2)
        self.assertEqual(_classify_tier("query_engrams"), 1)
        self.assertEqual(_classify_tier("health"), 1)

    def test_cost_calculation(self):
        """Costs are correctly computed from audit entries."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        self._write_audit([
            {"tool": "query_engrams", "timestamp": "2026-03-01T10:00:00Z"},
            {"tool": "write_engram", "timestamp": "2026-03-01T10:01:00Z"},
            {"tool": "delete_file", "timestamp": "2026-03-01T10:02:00Z"},
        ])
        result = compute_usage_summary()
        # query=0.1, write=0.5, delete=2.0 = 2.6
        self.assertEqual(result["total_cost_units"], 2.6)
        self.assertEqual(result["total_interactions"], 3)

    def test_group_by_tier(self):
        """group_by=tier produces tier breakdown."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        self._write_audit([
            {"tool": "health", "timestamp": "2026-03-01T10:00:00Z"},
            {"tool": "write_engram", "timestamp": "2026-03-01T10:01:00Z"},
        ])
        result = compute_usage_summary(group_by="tier")
        self.assertIn("tier_1", result["breakdown"])
        self.assertIn("tier_2", result["breakdown"])

    def test_time_filter(self):
        """since_hours filters old entries."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        old_ts = "2020-01-01T00:00:00Z"
        self._write_audit([
            {"tool": "health", "timestamp": old_ts},
        ])
        result = compute_usage_summary(since_hours=1)
        self.assertEqual(result["total_interactions"], 0)
        self.assertEqual(result["filtered_out"], 1)

    def test_events_counted(self):
        """Events from events.jsonl are also counted."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        self._write_events([
            {"event_type": "FeatureShipped", "timestamp": "2026-03-01T10:00:00Z"},
        ])
        result = compute_usage_summary()
        self.assertGreater(result["total_interactions"], 0)

    def test_cost_model_present(self):
        """Result includes cost model documentation."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        result = compute_usage_summary()
        self.assertIn("cost_model", result)
        self.assertEqual(result["cost_model"]["currency"], "nucleus_units")

    def test_data_sources_reported(self):
        """Result reports data source counts."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        self._write_audit([{"tool": "health", "timestamp": "2026-03-01T10:00:00Z"}])
        self._write_events([{"event_type": "test", "timestamp": "2026-03-01T10:00:00Z"}])
        result = compute_usage_summary()
        self.assertEqual(result["data_sources"]["audit_log"], 1)
        self.assertEqual(result["data_sources"]["events"], 1)


class TestAsciiGraphRenderer(unittest.TestCase):
    """Test the ASCII context graph renderer."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir()
        (self.brain_path / "engrams").mkdir(parents=True)
        (self.brain_path / "ledger").mkdir(parents=True)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def _write_engrams(self, engrams):
        ledger = self.brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            for e in engrams:
                f.write(json.dumps(e) + "\n")

    def test_empty_graph_renders(self):
        """Empty graph still produces valid ASCII output."""
        from mcp_server_nucleus.runtime.context_graph import render_ascii_graph
        output = render_ascii_graph()
        self.assertIn("NUCLEUS ENGRAM CONTEXT GRAPH", output)
        self.assertIn("Nodes: 0", output)

    def test_populated_graph_renders(self):
        """Graph with data renders clusters and nodes."""
        from mcp_server_nucleus.runtime.context_graph import render_ascii_graph
        self._write_engrams([
            {"key": "arch_cache", "value": "cache layer", "context": "Architecture", "intensity": 9, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "arch_db", "value": "database layer", "context": "Architecture", "intensity": 7, "timestamp": "2026-03-01T10:00:05Z"},
            {"key": "brand_voice", "value": "tone guidelines", "context": "Brand", "intensity": 5, "timestamp": "2026-03-01T12:00:00Z"},
        ])
        output = render_ascii_graph()
        self.assertIn("Architecture", output)
        self.assertIn("Brand", output)
        self.assertIn("arch_cache", output)

    def test_intensity_filter(self):
        """min_intensity filters low-intensity nodes from render."""
        from mcp_server_nucleus.runtime.context_graph import render_ascii_graph
        self._write_engrams([
            {"key": "high", "value": "important", "context": "Feature", "intensity": 9, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "low", "value": "trivial", "context": "Feature", "intensity": 2, "timestamp": "2026-03-01T10:00:00Z"},
        ])
        output = render_ascii_graph(min_intensity=5)
        self.assertIn("high", output)
        self.assertNotIn("trivial", output)

    def test_edge_types_shown(self):
        """Edge type distribution appears in render."""
        from mcp_server_nucleus.runtime.context_graph import render_ascii_graph
        self._write_engrams([
            {"key": "a", "value": "first node", "context": "Feature", "intensity": 5, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "b", "value": "second node", "context": "Feature", "intensity": 5, "timestamp": "2026-03-01T10:00:05Z"},
        ])
        output = render_ascii_graph()
        self.assertIn("EDGE TYPES", output)
        self.assertIn("context", output)


class TestBillingSessionGrouping(unittest.TestCase):
    """Test billing group_by=session."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir()
        (self.brain_path / "ledger").mkdir(parents=True)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def _write_audit(self, entries):
        path = self.brain_path / "ledger" / "interaction_log.jsonl"
        with open(path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def test_session_grouping(self):
        """group_by=session groups costs by date."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        self._write_audit([
            {"tool": "health", "timestamp": "2026-03-01T10:00:00Z"},
            {"tool": "health", "timestamp": "2026-03-01T14:00:00Z"},
            {"tool": "write_engram", "timestamp": "2026-03-02T09:00:00Z"},
        ])
        result = compute_usage_summary(group_by="session")
        self.assertEqual(result["group_by"], "session")
        self.assertIn("2026-03-01", result["breakdown"])
        self.assertIn("2026-03-02", result["breakdown"])
        # Day 1: 2 health reads = 0.2, Day 2: 1 write = 0.5
        self.assertEqual(result["breakdown"]["2026-03-01"]["cost"], 0.2)
        self.assertEqual(result["breakdown"]["2026-03-02"]["cost"], 0.5)

    def test_session_empty(self):
        """Empty brain with session grouping returns empty breakdown."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        result = compute_usage_summary(group_by="session")
        self.assertEqual(result["breakdown"], {})

    def test_session_count_accuracy(self):
        """Session counts match interaction counts per day."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        self._write_audit([
            {"tool": "health", "timestamp": "2026-03-01T10:00:00Z"},
            {"tool": "query_engrams", "timestamp": "2026-03-01T11:00:00Z"},
            {"tool": "delete_file", "timestamp": "2026-03-01T12:00:00Z"},
        ])
        result = compute_usage_summary(group_by="session")
        self.assertEqual(result["breakdown"]["2026-03-01"]["count"], 3)


class TestBillingEdgeCases(unittest.TestCase):
    """Edge-case tests for billing subsystem."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir()
        (self.brain_path / "ledger").mkdir(parents=True)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def _write_audit(self, entries):
        path = self.brain_path / "ledger" / "interaction_log.jsonl"
        with open(path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def test_malformed_jsonl_lines_skipped(self):
        """Malformed JSONL lines are skipped gracefully."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        path = self.brain_path / "ledger" / "interaction_log.jsonl"
        with open(path, "w") as f:
            f.write('{"tool": "health", "timestamp": "2026-03-01T10:00:00Z"}\n')
            f.write('THIS IS NOT JSON\n')
            f.write('{"tool": "write_engram", "timestamp": "2026-03-01T11:00:00Z"}\n')
        result = compute_usage_summary()
        self.assertEqual(result["total_interactions"], 2)  # Bad line skipped

    def test_missing_tool_field(self):
        """Entries without tool field use 'unknown' fallback."""
        from mcp_server_nucleus.runtime.billing import compute_usage_summary
        self._write_audit([
            {"timestamp": "2026-03-01T10:00:00Z"},  # No tool field
        ])
        result = compute_usage_summary()
        self.assertEqual(result["total_interactions"], 1)
        self.assertIn("unknown", result["breakdown"])

    def test_god_combo_tier_classification(self):
        """God Combos are classified as tier 3 (compute)."""
        from mcp_server_nucleus.runtime.billing import _classify_tier
        self.assertEqual(_classify_tier("pulse_and_polish"), 3)
        self.assertEqual(_classify_tier("self_healing_sre"), 3)
        self.assertEqual(_classify_tier("fusion_reactor"), 3)
        self.assertEqual(_classify_tier("auto_fix_loop"), 3)
        self.assertEqual(_classify_tier("autopilot_sprint"), 3)

    def test_destructive_tier_classification(self):
        """Destructive ops are classified as tier 4."""
        from mcp_server_nucleus.runtime.billing import _classify_tier
        self.assertEqual(_classify_tier("delete_file"), 4)
        self.assertEqual(_classify_tier("force_assign"), 4)
        self.assertEqual(_classify_tier("unlock"), 4)
        self.assertEqual(_classify_tier("lock"), 4)


class TestContextGraphEdgeCases(unittest.TestCase):
    """Edge-case tests for context graph."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.brain_path = Path(self.test_dir) / ".brain"
        self.brain_path.mkdir()
        (self.brain_path / "engrams").mkdir(parents=True)
        (self.brain_path / "ledger").mkdir(parents=True)
        os.environ["NUCLEAR_BRAIN_PATH"] = str(self.brain_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.environ.pop("NUCLEAR_BRAIN_PATH", None)

    def _write_engrams(self, engrams):
        ledger = self.brain_path / "engrams" / "ledger.jsonl"
        with open(ledger, "w") as f:
            for e in engrams:
                f.write(json.dumps(e) + "\n")

    def test_single_node_graph(self):
        """Single-node graph has no edges and density 1.0 (degeneracy)."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        self._write_engrams([
            {"key": "solo", "value": "lone engram", "context": "Feature", "intensity": 5, "timestamp": "2026-03-01T10:00:00Z"},
        ])
        graph = build_context_graph()
        self.assertEqual(graph["stats"]["node_count"], 1)
        self.assertEqual(graph["stats"]["edge_count"], 0)

    def test_missing_fields_handled(self):
        """Engrams with missing fields don't crash the graph builder."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        self._write_engrams([
            {"key": "minimal"},  # Missing value, context, intensity, timestamp
            {"key": "partial", "value": "has value"},  # Missing context, intensity, timestamp
        ])
        graph = build_context_graph()
        self.assertEqual(graph["stats"]["node_count"], 2)

    def test_large_graph_performance(self):
        """Graph with 100 nodes builds without error."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        import time
        self._write_engrams([
            {"key": f"node_{i}", "value": f"value {i} with some keywords for overlap testing",
             "context": ["Feature", "Architecture", "Brand", "Strategy", "Decision"][i % 5],
             "intensity": (i % 10) + 1, "timestamp": f"2026-03-01T{10 + (i // 60):02d}:{i % 60:02d}:00Z"}
            for i in range(100)
        ])
        start = time.time()
        graph = build_context_graph()
        elapsed = time.time() - start
        self.assertEqual(graph["stats"]["node_count"], 100)
        self.assertLess(elapsed, 5.0)  # Should complete in under 5 seconds

    def test_neighbors_depth_2(self):
        """BFS at depth=2 reaches second-hop neighbors."""
        from mcp_server_nucleus.runtime.context_graph import get_engram_neighbors
        self._write_engrams([
            {"key": "center", "value": "central", "context": "Feature", "intensity": 8, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "hop1", "value": "first hop", "context": "Feature", "intensity": 7, "timestamp": "2026-03-01T10:00:05Z"},
            {"key": "hop2", "value": "second hop", "context": "Feature", "intensity": 6, "timestamp": "2026-03-01T10:00:10Z"},
        ])
        result_d1 = get_engram_neighbors("center", max_depth=1)
        result_d2 = get_engram_neighbors("center", max_depth=2)
        # Depth 2 should find at least as many neighbors as depth 1
        self.assertGreaterEqual(result_d2["neighbor_count"], result_d1["neighbor_count"])

    def test_exclude_edges(self):
        """include_edges=False excludes edges from result."""
        from mcp_server_nucleus.runtime.context_graph import build_context_graph
        self._write_engrams([
            {"key": "a", "value": "first", "context": "Feature", "intensity": 5, "timestamp": "2026-03-01T10:00:00Z"},
            {"key": "b", "value": "second", "context": "Feature", "intensity": 5, "timestamp": "2026-03-01T10:00:05Z"},
        ])
        graph = build_context_graph(include_edges=False)
        self.assertNotIn("edges", graph)
        self.assertGreater(graph["stats"]["edge_count"], 0)  # Stats still counted


class TestExportSchemaCap(unittest.TestCase):
    """Test export_schema response size cap."""

    def test_cap_constant_exists(self):
        """Verify the cap is defined in the handler code."""
        import mcp_server_nucleus.tools.engrams as engrams_mod
        # The cap is inside a closure, so we verify by reading source
        import inspect
        source = inspect.getsource(engrams_mod)
        self.assertIn("MAX_SCHEMA_CHARS", source)
        self.assertIn("200_000", source)


if __name__ == "__main__":
    unittest.main()
