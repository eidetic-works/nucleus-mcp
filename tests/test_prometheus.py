"""
Tests for Nucleus Prometheus Metrics (AG-015)
"""

import unittest
import os

# Enable metrics for tests
os.environ["NUCLEUS_METRICS"] = "true"

from mcp_server_nucleus.runtime.prometheus import (
    inc_counter, observe_latency, set_gauge,
    get_prometheus_metrics, get_metrics_json,
    reset_metrics, metrics_tracked
)


class TestPrometheusMetrics(unittest.TestCase):
    def setUp(self):
        reset_metrics()
    
    def tearDown(self):
        reset_metrics()
    
    def test_inc_counter_basic(self):
        """Test basic counter increment."""
        inc_counter("test_counter", {"tool": "test"})
        inc_counter("test_counter", {"tool": "test"})
        
        metrics = get_metrics_json()
        self.assertIn("tool_calls", metrics)
    
    def test_observe_latency(self):
        """Test latency observation."""
        observe_latency("test_tool", 0.05)
        observe_latency("test_tool", 0.10)
        observe_latency("test_tool", 0.15)
        
        metrics = get_metrics_json()
        self.assertIn("latencies", metrics)
        self.assertIn("test_tool", metrics["latencies"])
        self.assertEqual(metrics["latencies"]["test_tool"]["count"], 3)
    
    def test_set_gauge(self):
        """Test gauge setting."""
        set_gauge("active_sessions", 5)
        
        metrics = get_metrics_json()
        self.assertIn("gauges", metrics)
    
    def test_prometheus_format_output(self):
        """Test Prometheus exposition format."""
        inc_counter("tool_calls", {"tool": "brain_health"})
        observe_latency("brain_health", 0.025)
        
        output = get_prometheus_metrics()
        
        # Check format
        self.assertIn("# HELP", output)
        self.assertIn("# TYPE", output)
        self.assertIn("nucleus_tool", output)
    
    def test_metrics_json_structure(self):
        """Test JSON metrics structure."""
        inc_counter("json_test", {"tool": "test"})
        
        metrics = get_metrics_json()
        
        self.assertIn("tool_calls", metrics)
        self.assertIn("tool_errors", metrics)
        self.assertIn("latencies", metrics)
        self.assertIn("gauges", metrics)
        self.assertIn("timestamp", metrics)
    
    def test_reset_metrics(self):
        """Test metrics reset."""
        inc_counter("reset_test", {"tool": "test"})
        observe_latency("reset_tool", 0.1)
        
        reset_metrics()
        
        metrics = get_metrics_json()
        self.assertEqual(metrics["tool_calls"], {})
        self.assertEqual(metrics["latencies"], {})
    
    def test_metrics_tracked_decorator(self):
        """Test @metrics_tracked decorator."""
        @metrics_tracked("decorated_tool")
        def sample_tool():
            return "result"
        
        result = sample_tool()
        self.assertEqual(result, "result")
        
        metrics = get_metrics_json()
        self.assertIn("latencies", metrics)
        self.assertIn("decorated_tool", metrics["latencies"])
    
    def test_quantile_calculation(self):
        """Test that quantiles are calculated correctly."""
        # Add 100 observations
        for i in range(100):
            observe_latency("quantile_test", i / 1000.0)  # 0-99ms
        
        metrics = get_metrics_json()
        stats = metrics["latencies"]["quantile_test"]
        
        self.assertIn("quantiles", stats)
        self.assertIn("0.5", stats["quantiles"])  # p50
        self.assertIn("0.9", stats["quantiles"])  # p90
        self.assertIn("0.99", stats["quantiles"])  # p99


if __name__ == "__main__":
    unittest.main()
